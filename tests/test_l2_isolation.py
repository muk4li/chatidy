"""AUTH-014: negative HTTP isolation tests across separate synthetic accounts."""
import json
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

from chatidy.db import connect, upsert, create_folder, chat_detail
from chatidy.auth_state import issue_session
from chatidy.library_scope import account_library
from chatidy.server import Handler
from chatidy.users import enrolled_user

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,url):return None

class CrossAccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.registry=Path(self.tmp.name)/"registry.sqlite3"
        self.env=patch.dict(os.environ,{
            "CHATIDY_DB":str(self.registry),"CHATIDY_AUTH_REQUIRED":"1",
            "CHATIDY_PUBLIC_ORIGIN":"https://app.example.invalid"})
        self.env.start()
        self.users=[]
        with closing(connect(self.registry)) as db:
            for n in (1,2):
                sub="synthetic-account-"+str(n)
                with db:
                    db.execute("INSERT INTO users(oidc_issuer,oidc_sub) VALUES(?,?)",
                               ("https://idp.example.invalid",sub))
                user=enrolled_user(db,"https://idp.example.invalid",sub)
                self.users.append((user,issue_session(db,user)))
        for n,(user,token) in enumerate(self.users,1):
            with account_library(user,self.registry):
                with closing(connect()) as db:
                    upsert(db,[{"id":"synthetic-"+str(n),
                                "title":"Private synthetic "+str(n),
                                "messages":[{"id":"msg","role":"user",
                                             "content":"UniqueText"+str(n)}]}])
                    create_folder(db,"Only account "+str(n))
        self.http=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        self.t=threading.Thread(target=self.http.serve_forever,daemon=True)
        self.t.start()
        self.host=f"http://127.0.0.1:{self.http.server_address[1]}"
        self.client=urllib.request.build_opener(NoRedirect)

    def tearDown(self):
        self.http.shutdown()
        self.t.join(timeout=5)
        self.http.server_close()
        self.env.stop()
        self.tmp.cleanup()

    def request(self,path,token=None,payload=None):
        headers={"Host":"app.example.invalid"}
        if token:headers["Cookie"]="__Host-chatidy_session="+token
        method="POST" if payload is not None else "GET"
        data=json.dumps(payload).encode() if payload is not None else None
        if data is not None:
            headers.update({"Origin":"https://app.example.invalid",
                            "Content-Type":"application/json"})
        req=urllib.request.Request(self.host+path,data=data,headers=headers,method=method)
        try:
            with self.client.open(req,timeout=5) as res:
                return res.status,json.loads(res.read())
        except urllib.error.HTTPError as exc:
            try:return exc.code,json.loads(exc.read())
            finally:exc.close()

    def test_cross_account_read_and_search_never_expose_other_data(self):
        for n,(user,token) in enumerate(self.users,1):
            foreign=2 if n==1 else 1
            self.assertEqual(self.request("/api/chat/synthetic-"+str(foreign),token)[0],404)
            own=self.request("/api/chat/synthetic-"+str(n),token)
            self.assertEqual(own[0],200)
            self.assertEqual(own[1]["chat"]["title"],"Private synthetic "+str(n))
            self.assertEqual(self.request("/api/chats?q=UniqueText"+str(foreign),token)[1],[])
            folders=self.request("/api/folders",token)[1]
            self.assertIn("Only account "+str(n),[row["name"] for row in folders])
            self.assertNotIn("Only account "+str(foreign),[row["name"] for row in folders])
            exports=self.request("/api/export",token,{"ids":["synthetic-"+str(foreign)]})[1]
            self.assertEqual(exports["exported"],[])

    def test_cross_account_review_cannot_change_foreign_chat(self):
        one,t1=self.users[0]
        two,t2=self.users[1]
        code,_=self.request("/api/review",t2,{"conversation_id":"synthetic-1","reviewed":True})
        self.assertEqual(code,404)
        with account_library(one,self.registry):
            with closing(connect()) as db:
                self.assertEqual(chat_detail(db,"synthetic-1")["chat"]["reviewed"],0)
        code,_=self.request("/api/review",t1,{"conversation_id":"synthetic-1","reviewed":True})
        self.assertEqual(code,200)
        with account_library(one,self.registry):
            with closing(connect()) as db:
                self.assertEqual(chat_detail(db,"synthetic-1")["chat"]["reviewed"],1)

    def test_anonymous_cannot_write_or_export(self):
        self.assertEqual(self.request("/api/export",None,{"ids":[]})[0],401)
        self.assertEqual(self.request("/api/review",None,{"conversation_id":"synthetic-1"})[0],401)
        self.assertEqual(self.request("/api/chats")[0],401)

if __name__=="__main__":unittest.main()
