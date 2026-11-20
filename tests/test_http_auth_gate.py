"""AUTH-009: HTTP gate, synthetic sessions, and per-account isolation."""
import json
import io
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from chatidy.server import Handler
from chatidy.db import connect, upsert, chat_detail
from chatidy.auth_state import issue_session
from chatidy.users import enrolled_user
from chatidy.library_scope import account_library
from chatidy import jobs

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, url):
        return None

class HttpGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.registry=Path(self.tmp.name)/"registry.sqlite3"
        self.env=patch.dict(os.environ,CHATIDY_DB=str(self.registry),
                            CHATIDY_AUTH_REQUIRED="1",
                            CHATIDY_PUBLIC_ORIGIN="https://app.example.invalid")
        self.env.start()
        self.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.url=f"http://127.0.0.1:{self.server.server_address[1]}"
        self.opener=urllib.request.build_opener(NoRedirect)

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        self.env.stop()
        self.tmp.cleanup()

    def request(self,path,token=None,method="GET",data=None,origin=None):
        headers={"Host":"app.example.invalid"}
        if token:headers["Cookie"]="chatidy_session="+token
        if method=="POST":headers["Origin"]=origin if origin is not None else "https://app.example.invalid"
        req=urllib.request.Request(self.url+path,data=data,headers=headers,method=method)
        try:
            with self.opener.open(req,timeout=6) as response:
                return response.status,response.read(),response.headers
        except urllib.error.HTTPError as exc:
            try:return exc.code,exc.read(),exc.headers
            finally:exc.close()

    def session(self,subject):
        with closing(connect(self.registry)) as db:
            with db:db.execute("INSERT INTO users(oidc_issuer,oidc_sub) VALUES(?,?)",
                               ("https://idp.example.invalid",subject))
            user=enrolled_user(db,"https://idp.example.invalid",subject)
            token=issue_session(db,user)
        return user,token

    def test_public_landing_and_private_data(self):
        code,html,_=self.request("/")
        self.assertEqual(code,200)
        self.assertIn(b"chatidy",html.lower())
        self.assertEqual(self.request("/landing.css")[0],200)
        for path in ("/api/stats","/api/import/jobs","/api/chat/synthetic",
                     "/api/export","/app.js","/reading.js","/style.css",
                     "/api/import/jobs/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"):
            with self.subTest(path=path):self.assertEqual(self.request(path)[0],401)
        code,_,headers=self.request("/app")
        self.assertEqual(code,302)
        self.assertEqual(headers["Location"],"/login")
        self.assertEqual(self.request("/api/import/analyze",method="POST",data=b"synthetic")[0],401)
        self.assertEqual(self.request("/api/stats",method="POST",data=b"x",origin="https://evil.invalid")[0],403)
        self.assertEqual(self.request("/api/import/jobs",method="POST",data=b"x",origin="")[0],403)
        self.assertEqual(self.request("/unknown")[0],404)

    def test_other_account_cannot_read_resume_confirm_or_delete_import_job(self):
        alice, token_alice = self.session("synthetic-owner-job")
        bob, token_bob = self.session("synthetic-other-job")
        payload = json.dumps([
            {"id": "synthetic-job-chat", "title": "Synthetic job",
             "messages": [{"id": "synthetic-message", "role": "user",
                           "content": "Completely synthetic"}]}
        ]).encode("utf-8")
        with account_library(alice, self.registry):
            job_id = jobs.create(io.BytesIO(payload), len(payload), "synthetic.json")
            self.assertEqual(jobs.status(job_id)["state"], "uploaded")
        with account_library(bob, self.registry):
            self.assertEqual(jobs.listing()["count"], 0)
        listing_code, listing, _ = self.request("/api/import/jobs", token=token_bob)
        self.assertEqual(listing_code, 200)
        self.assertEqual(json.loads(listing)["count"], 0)
        for path in ("/api/import/jobs/" + job_id,):
            with self.subTest(path=path):
                code, body, _ = self.request(path, token=token_bob)
                self.assertIn(code, (400, 404))
                self.assertNotIn(b"Synthetic job", body)
        for action, submitted in (("resume", {}), ("delete", {"confirm": True}),
                                  ("confirm", {"confirm": True})):
            with self.subTest(action=action):
                path = "/api/import/jobs/" + job_id + "/" + action
                code, _, _ = self.request(path, token=token_bob, method="POST",
                                          data=json.dumps(submitted).encode("utf-8"))
                self.assertIn(code, (400, 404))
                with account_library(alice, self.registry):
                    self.assertEqual(jobs.status(job_id)["state"], "uploaded")
        code, job_body, _ = self.request("/api/import/jobs/" + job_id, token=token_alice)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(job_body)["id"], job_id)
        code, _, _ = self.request("/api/import/jobs/" + job_id + "/delete",
                                  token=token_alice, method="POST",
                                  data=b'{"confirm":true}')
        self.assertEqual(code, 200)
        with account_library(alice, self.registry):
            self.assertEqual(jobs.listing()["count"], 0)

    def test_two_sessions_isolate_same_chat_id(self):
        one,token1=self.session("synthetic-user-1")
        two,token2=self.session("synthetic-user-2")
        for user,num in ((one,1),(two,2)):
            with account_library(user,self.registry):
                with closing(connect()) as db:
                    upsert(db,[{"id":"same-chat","title":"Synthetic "+str(num),
                                "messages":[{"id":"msg","role":"user","content":"Account "+str(num)}]}])
        for token,num in ((token1,1),(token2,2)):
            code,body,_=self.request("/api/chats",token=token)
            self.assertEqual(code,200)
            self.assertEqual(json.loads(body)[0]["title"],"Synthetic "+str(num))
            self.assertEqual(self.request("/api/import/jobs",token=token)[0],200)
            self.assertEqual(self.request("/app",token=token)[0],200)
        with closing(connect(self.registry)) as db:
            self.assertIsNone(chat_detail(db,"same-chat"))
            with db:db.execute("UPDATE users SET status='disabled' WHERE id=?",(one.id,))
        self.assertEqual(self.request("/api/chats",token=token1)[0],401)
        self.assertEqual(self.request("/api/chats",token=token2)[0],200)

if __name__=="__main__":
    unittest.main()
