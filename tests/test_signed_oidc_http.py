"""AUTH-022: signed synthetic OIDC ID tokens reach HTTP sessions only when valid."""
import importlib.util
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from chatidy.db import connect
from chatidy.server import Handler

AUTH_AVAILABLE=(importlib.util.find_spec("jwt") is not None
                and importlib.util.find_spec("cryptography") is not None)
ISSUER="https://idp.example.invalid/application/o/synthetic/"

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,url):return None

@unittest.skipUnless(AUTH_AVAILABLE,"Optional OIDC cryptography not installed")
class SignedCallbackTests(unittest.TestCase):
    def setUp(self):
        import jwt
        from cryptography.hazmat.primitives.asymmetric import rsa
        self.jwt=jwt
        self.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        self.jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
        self.jwk.update(kid="synthetic-only",alg="RS256",use="sig")
        self.tmp=tempfile.TemporaryDirectory()
        self.registry=Path(self.tmp.name)/"registry.sqlite3"
        self.env=patch.dict(os.environ,{
            "CHATIDY_DB":str(self.registry),"CHATIDY_AUTH_REQUIRED":"1",
            "CHATIDY_PUBLIC_ORIGIN":"https://app.example.invalid",
            "CHATIDY_OIDC_ISSUER":ISSUER,
            "CHATIDY_OIDC_AUTHORIZE":"https://idp.example.invalid/authorize",
            "CHATIDY_OIDC_TOKEN":"https://idp.example.invalid/token",
            "CHATIDY_OIDC_JWKS":"https://idp.example.invalid/jwks",
            "CHATIDY_OIDC_CLIENT_ID":"synthetic-client",
            "CHATIDY_OIDC_CLIENT_SECRET":"synthetic-only-client-secret-42"})
        self.env.start()
        with closing(connect(self.registry)) as db:
            with db:db.execute("INSERT INTO users(oidc_issuer,oidc_sub) VALUES(?,?)",
                               (ISSUER,"synthetic-enrolled"))
        self.srv=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        self.thread=threading.Thread(target=self.srv.serve_forever,daemon=True)
        self.thread.start()
        self.url=f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.client=urllib.request.build_opener(NoRedirect)

    def tearDown(self):
        self.srv.shutdown();self.thread.join(timeout=5);self.srv.server_close()
        self.env.stop();self.tmp.cleanup()

    def req(self,path,cookie=None):
        headers={"Host":"app.example.invalid"}
        if cookie:headers["Cookie"]=cookie
        request=urllib.request.Request(self.url+path,headers=headers)
        try:
            with self.client.open(request,timeout=5) as response:
                return response.status,response.read(),response.headers
        except urllib.error.HTTPError as exc:
            try:return exc.code,exc.read(),exc.headers
            finally:exc.close()

    def start(self):
        status,_,headers=self.req("/login")
        self.assertEqual(status,302)
        params=urllib.parse.parse_qs(urllib.parse.urlsplit(headers["Location"]).query)
        return params["state"][0],params["nonce"][0],headers.get_all("Set-Cookie")[0].split(";",1)[0]

    def token(self,expected_nonce,**overrides):
        now=int(time.time())
        payload={"iss":ISSUER,"sub":"synthetic-enrolled","aud":"synthetic-client",
                 "iat":now,"exp":now+600,"nonce":expected_nonce}
        payload.update(overrides)
        return self.jwt.encode(payload,self.key,algorithm="RS256",headers={"kid":"synthetic-only"})

    def callback(self,raw_token,state,cookie):
        url="/auth/callback?"+urllib.parse.urlencode({"state":state,"code":"synthetic-code"})
        with patch("chatidy.oidc_exchange.exchange_code",return_value=raw_token),\
             patch("chatidy.oidc_exchange.load_trusted_jwks",return_value={"keys":[self.jwk]}):
            return self.req(url,cookie)

    def test_valid_signed_token_creates_session_and_replay_is_denied(self):
        state,nonce,binding=self.start()
        status,_,headers=self.callback(self.token(nonce),state,binding)
        self.assertEqual(status,302)
        session=[c for c in headers.get_all("Set-Cookie") if c.startswith("__Host-chatidy_session=")][0].split(";",1)[0]
        self.assertEqual(self.req("/api/session",session)[0],200)
        self.assertEqual(self.callback(self.token(nonce),state,binding)[0],401)

    def test_invalid_signature_nonce_issuer_audience_and_expiry_do_not_issue_session(self):
        now=int(time.time())
        for override in ({"nonce":"wrong-nonce"},{"iss":"https://bad.invalid"},
                         {"aud":"wrong-client"},{"exp":now-120}):
            with self.subTest(invalid=override):
                state,nonce,binding=self.start()
                code,_,headers=self.callback(self.token(nonce,**override),state,binding)
                self.assertEqual(code,401)
                self.assertIsNone(headers.get("Set-Cookie"))
                self.assertEqual(self.req("/api/stats")[0],401)

    def test_full_exchange_and_jwks_fixture_reaches_http_session(self):
        # Exercise the real exchange/JWKS/verification chain, replacing only HTTPS I/O.
        import io
        state, nonce, binding = self.start()
        raw_token = self.token(nonce)
        requests = []
        class Response:
            status = 200
            def __init__(self, value): self.body = io.BytesIO(json.dumps(value).encode())
            def read(self, size): return self.body.read(size)
            def __enter__(self): return self
            def __exit__(self, *args): self.body.close()
        class Provider:
            def open(self, request, timeout):
                requests.append(request)
                if request.full_url.endswith('/token'):
                    body = urllib.parse.parse_qs(request.data.decode())
                    assert body['code'] == ['synthetic-code']
                    assert len(body['code_verifier'][0]) >= 43
                    assert request.get_header('Authorization').startswith('Basic ')
                    return Response({'id_token': raw_token})
                assert request.full_url.endswith('/jwks')
                return Response({'keys': [self_test.jwk]})
        self_test = self
        with patch('chatidy.oidc_exchange.urllib.request.build_opener', return_value=Provider()):
            status, _, headers = self.req('/auth/callback?' + urllib.parse.urlencode({
                'state': state, 'code': 'synthetic-code'}), binding)
        self.assertEqual(status, 302)
        session = [c for c in headers.get_all('Set-Cookie') if c.startswith('__Host-chatidy_session=')][0].split(';', 1)[0]
        self.assertEqual(self.req('/api/session', session)[0], 200)
        self.assertEqual([r.full_url for r in requests], [
            'https://idp.example.invalid/token', 'https://idp.example.invalid/jwks'])

    def test_wrong_rsa_signature_rejected(self):
        from cryptography.hazmat.primitives.asymmetric import rsa
        different_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        state,nonce,binding=self.start()
        now=int(time.time())
        payload={"iss":ISSUER,"sub":"synthetic-enrolled","aud":"synthetic-client",
                 "iat":now,"exp":now+600,"nonce":nonce}
        forged=self.jwt.encode(payload,different_key,algorithm="RS256",
                               headers={"kid":"synthetic-only"})
        status,_,headers=self.callback(forged,state,binding)
        self.assertEqual(status,401)
        self.assertIsNone(headers.get("Set-Cookie"))

    def test_signed_but_unenrolled_subject_rejected(self):
        state,nonce,binding=self.start()
        code,_,headers=self.callback(self.token(nonce,sub="synthetic-stranger"),state,binding)
        self.assertEqual(code,401)
        self.assertIsNone(headers.get("Set-Cookie"))

if __name__=="__main__":unittest.main()
