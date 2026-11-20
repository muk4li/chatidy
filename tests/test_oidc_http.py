"""Synthetic OIDC browser paths; no real credentials, IdP or user exports."""
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from chatidy.server import Handler
from chatidy.db import connect
ISSUER="https://idp.example.invalid/application/o/test/"

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,url):return None

class BrowserOIDCTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"registry.sqlite3"
        self.env=patch.dict(os.environ,{
            "CHATIDY_DB":str(self.path),"CHATIDY_AUTH_REQUIRED":"1",
            "CHATIDY_PUBLIC_ORIGIN":"https://app.example.invalid",
            "CHATIDY_OIDC_ISSUER":ISSUER,
            "CHATIDY_OIDC_AUTHORIZE":"https://idp.example.invalid/authorize",
            "CHATIDY_OIDC_TOKEN":"https://idp.example.invalid/token",
            "CHATIDY_OIDC_JWKS":"https://idp.example.invalid/jwks",
            "CHATIDY_OIDC_CLIENT_ID":"synthetic-client"})
        self.env.start()
        self.srv=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        self.t=threading.Thread(target=self.srv.serve_forever,daemon=True)
        self.t.start()
        self.base=f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.client=urllib.request.build_opener(NoRedirect)

    def tearDown(self):
        self.srv.shutdown();self.t.join(timeout=5);self.srv.server_close()
        self.env.stop();self.tmp.cleanup()

    def get(self,path,cookie=None,method="GET",origin=None):
        headers={"Host":"app.example.invalid"}
        if cookie:headers["Cookie"]=cookie
        if method=="POST":headers["Origin"]=origin if origin is not None else "https://app.example.invalid"
        req=urllib.request.Request(self.base+path,headers=headers,method=method,data=b"" if method=="POST" else None)
        try:
            with self.client.open(req,timeout=5) as r:return r.status,r.read(),r.headers
        except urllib.error.HTTPError as e:
            try:return e.code,e.read(),e.headers
            finally:e.close()

    def challenge(self):
        code,_,headers=self.get("/login")
        self.assertEqual(code,302)
        target=urllib.parse.urlsplit(headers["Location"])
        self.assertEqual(target.hostname,"idp.example.invalid")
        args=urllib.parse.parse_qs(target.query)
        self.assertEqual(args["code_challenge_method"],["S256"])
        c=headers.get_all("Set-Cookie")[0]
        self.assertIn("Secure",c);self.assertIn("HttpOnly",c)
        return args["state"][0],c.split(";",1)[0]

    def callback(self,state,cookie):
        return self.get("/auth/callback?"+urllib.parse.urlencode({"state":state,"code":"synthetic-code"}),cookie)

    def test_unknown_account_and_replay_rejected(self):
        state,binding=self.challenge()
        with patch("chatidy.server.identity_from_code",return_value={"issuer":ISSUER,"subject":"unregistered"}) as mock:
            self.assertEqual(self.callback(state,binding)[0],401)
            self.assertEqual(self.callback(state,binding)[0],401)
            self.assertEqual(mock.call_count,1)
        self.assertEqual(self.get("/api/stats")[0],401)

    def test_wrong_browser_does_not_consume_state(self):
        state,binding=self.challenge()
        with patch("chatidy.server.identity_from_code",return_value={"issuer":ISSUER,"subject":"stranger"}) as mock:
            self.assertEqual(self.callback(state,"chatidy_oidc="+"x"*64)[0],401)
            mock.assert_not_called()
            self.assertEqual(self.callback(state,binding)[0],401)
            self.assertEqual(mock.call_count,1)

    def test_enrolled_session_and_logout(self):
        with closing(connect(self.path)) as db:
            with db:db.execute("INSERT INTO users(oidc_issuer,oidc_sub) VALUES(?,?)",
                               (ISSUER,"synthetic-enrolled"))
        state,binding=self.challenge()
        with patch("chatidy.server.identity_from_code",return_value={"issuer":ISSUER,"subject":"synthetic-enrolled"}):
            status,_,headers=self.callback(state,binding)
        self.assertEqual(status,302)
        self.assertEqual(headers["Location"],"/app")
        cookie=[x for x in headers.get_all("Set-Cookie") if x.startswith("chatidy_session=")][0]
        self.assertIn("Secure",cookie)
        self.assertIn("HttpOnly",cookie)
        self.assertIn("SameSite=Lax",cookie)
        token=cookie.split(";",1)[0]
        self.assertEqual(self.get("/api/stats",token)[0],200)
        import json
        session_code,session_body,_=self.get("/api/session",token)
        self.assertEqual(session_code,200)
        self.assertEqual(json.loads(session_body)["role"],"member")
        self.assertEqual(self.get("/logout",token,method="POST")[0],302)
        self.assertEqual(self.get("/api/stats",token)[0],401)
        self.assertEqual(self.get("/api/session",token)[0],401)

    def test_cross_origin_logout_denied(self):
        self.assertEqual(self.get("/logout",method="POST",origin="https://evil.invalid")[0],403)

if __name__=="__main__":unittest.main()
