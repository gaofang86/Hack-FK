"""Real HTTP end-to-end tests with temporary vaults and local service fakes."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.config import Config
from app.server import App, serve
from tests.test_navigation import person


class Fake(BaseHTTPRequestHandler):
    seen=[]
    def log_message(self,*_):pass
    def do_GET(self):
        raw=json.dumps({"models":[{"name":"test-local"}]}).encode()
        self.send_response(200);self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
        self.seen.append((self.path,body))
        lines=[l.split(". ",1)[0] for l in body.get("prompt","").splitlines() if ". " in l]
        payload={"response":"\n".join(f"{n}. LOCAL TEST TRANSLATION {n}" for n in lines)} if self.path=="/api/generate" else {
            "results":[{"url":"https://example.org/clinic","title":"Test source clinic","content":"Primary care in Boston. Call (617) 555-0100."}]}
        if self.path == "/api/chat":
            payload = {"message": {"content": json.dumps({"action": "propose_reply", "replies": [
                {"key": "language", "result": "yes", "evidence": "有中文翻译"},
                {"key": "availability", "result": "no", "evidence": "目前不收新病人"}]}, ensure_ascii=False)}}
        self.send_response(200);self.send_header("Content-Type","application/json");self.end_headers();self.wfile.write(json.dumps(payload).encode())


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();Fake.seen=[]
        cls.fake=ThreadingHTTPServer(("127.0.0.1",0),Fake)
        threading.Thread(target=cls.fake.serve_forever,daemon=True).start()
        cfg=Config();cfg.port=0;cfg.store_path=Path(cls.tmp.name)/"vault";cfg.exa_key="";cfg.tavily_key="test-key"
        cfg.tavily_base=f"http://127.0.0.1:{cls.fake.server_port}";cfg.ollama_url=cfg.tavily_base;cfg.ollama_model="test-local";cfg.ollama_agent_model="test-local"
        cls.app=App(cfg);cls.server=serve(cls.app,block=False);cls.base=f"http://127.0.0.1:{cls.server.server_port}"
        cls.request("/api/vault/create",{"passphrase":"disposable-test-passphrase"})

    @classmethod
    def tearDownClass(cls):
        cls.server.stop_idle.set();cls.server.shutdown();cls.server.server_close()
        cls.fake.shutdown();cls.fake.server_close();cls.tmp.cleanup()

    @classmethod
    def request(cls,path,body=None,headers=None):
        req=Request(cls.base+path,data=json.dumps(body).encode() if body is not None else None,
                    headers=headers if headers is not None else {"X-FirstVisit":"local","Content-Type":"application/json"})
        with urlopen(req,timeout=10) as response:return json.load(response)

    def test_agent_review_over_http_uses_local_schema_and_rejects_replay(self):
        from datetime import date
        p = person(); p["demo"] = False
        preview = self.request("/api/preview", p)
        case = self.request("/api/search", dict(token=preview["token"], approved=True, live=False))
        provider = case["providers"][0]
        draft = self.request("/api/agent/turn", dict(id=case["id"], provider_id=provider["id"],
                             message="这家诊所有中文翻译，但目前不收新病人。"))
        self.assertEqual(draft["state"], "proposal")
        self.assertFalse(self.app.get_case(case["id"])["providers"][0].get("answers"))
        body = dict(id=case["id"], token=draft["token"], confirmed=True,
                    results={"language": "yes", "availability": "no"},
                    source="Synthetic HTTP test office", checked_on=date.today().isoformat())
        saved = self.request("/api/agent/confirm", body)
        self.assertEqual(saved["saved"], 2)
        self.assertTrue(saved["case"]["results"][-1]["unavailable"])
        self.assertEqual(saved["case"]["results"][-1]["provider"]["id"], provider["id"])
        with self.assertRaises(HTTPError) as caught:
            self.request("/api/agent/confirm", body)
        self.assertEqual(caught.exception.code, 400)
        chats = [b for path, b in Fake.seen if path == "/api/chat"]
        self.assertTrue(chats[-1]["format"])
        self.assertNotIn(p["history"], json.dumps(chats[-1]))

    def test_cross_origin_and_rebinding_refused(self):
        for headers in ({},{"X-FirstVisit":"local","Origin":"https://attacker.example"},{"X-FirstVisit":"local","Host":"attacker.example"}):
            with self.subTest(headers=headers),self.assertRaises(HTTPError) as caught:self.request("/api/state",headers=headers)
            self.assertEqual(caught.exception.code,403)

    def test_end_to_end_search_model_and_privacy(self):
        p=person();p["demo"]=False
        preview=self.request("/api/preview",p)
        self.assertNotIn(p["description"],json.dumps(preview))
        self.assertNotIn(p["history"],json.dumps(preview))
        self.assertNotIn(p["plan"]["name"],json.dumps(preview))
        result=self.request("/api/search",dict(token=preview["token"],approved=True,live=True))
        self.assertTrue(result["live_searched"])
        self.assertTrue(any(r["provider"]["name"]=="Test source clinic" for r in result["results"]))
        requests=[b for path,b in Fake.seen if path=="/search"]
        self.assertTrue(requests)
        self.assertTrue(all(p["description"] not in json.dumps(b) and p["history"] not in json.dumps(b) for b in requests))
        prep=self.request("/api/case/preparation",dict(id=result["id"],use_model=True))
        self.assertIn("local model",prep["source"])
        self.assertIn("LOCAL TEST TRANSLATION 1",prep["text"])
        self.assertIn("Are you accepting new adult patients",prep["text"])  # English line kept beside its translation
        model_calls=json.dumps([b for path,b in Fake.seen if path=="/api/generate"])
        self.assertIs(json.loads(model_calls)[-1]["think"],False)
        self.assertTrue(p["description"] not in model_calls and p["history"] not in model_calls)
        privacy=self.request("/api/privacy")
        self.assertGreater(privacy["attempted"],0)
        self.assertNotIn("test-key",json.dumps(privacy))

    def test_static_policy_and_path_traversal(self):
        with urlopen(self.base) as response:
            self.assertIn("frame-ancestors 'none'",response.headers["Content-Security-Policy"])
            self.assertEqual(response.headers["Cache-Control"],"no-store")
        with urlopen(self.base + "/navigation.js") as response:
            self.assertIn("javascript", response.headers["Content-Type"])
            self.assertIn("class NavigationTrail", response.read().decode())
        with self.assertRaises(HTTPError) as caught:urlopen(self.base+"/../app/config.py")
        self.assertEqual(caught.exception.code,404)


if __name__=="__main__":unittest.main()
