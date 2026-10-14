"""Local-only source parsing service. No Lean execution, shell, or arbitrary file reads."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
from urllib.parse import urlsplit
from .model import Document
from .render import html_document
from .source import parse_source

MAX_BODY = 4_000_000


def make_handler(document: Document):
    page = html_document(document).encode()
    class Handler(BaseHTTPRequestHandler):
        server_version = "ProofReader/0.1"
        def _allowed(self) -> bool:
            expected = f"127.0.0.1:{self.server.server_port}"
            host = self.headers.get("Host", "")
            if host != expected: return False
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + expected: return False
            return True
        def _reply(self, status, content, content_type="application/json; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.end_headers(); self.wfile.write(content)
        def do_GET(self):
            if not self._allowed(): return self._reply(403,b'{"error":"Local origin required"}')
            if self.path == "/": return self._reply(200,page,"text/html; charset=utf-8")
            if self.path == "/health": return self._reply(200,b'{"status":"ok","lean_execution":false}')
            self._reply(404,b'{"error":"Not found"}')
        def do_POST(self):
            if not self._allowed(): return self._reply(403,b'{"error":"Local origin required"}')
            if self.path != "/api/read": return self._reply(404,b'{"error":"Not found"}')
            if self.headers.get("Transfer-Encoding"): return self._reply(400,b'{"error":"Chunked uploads are not accepted"}')
            if self.headers.get("Content-Type","").split(";",1)[0] != "application/json": return self._reply(415,b'{"error":"JSON required"}')
            try:
                n=int(self.headers.get("Content-Length","0"))
                if n <= 0 or n > MAX_BODY: return self._reply(413,b'{"error":"Upload exceeds limit"}')
                self.connection.settimeout(10)
                raw=self.rfile.read(n)
                if len(raw)!=n: raise ValueError("Incomplete body")
                data=json.loads(raw)
                if not isinstance(data,dict) or not isinstance(data.get("source"),str): raise ValueError("A source string is required")
                name=data.get("name","Input.lean")
                if not isinstance(name,str) or len(name)>256: raise ValueError("Invalid display filename")
                result=parse_source(data["source"], name)
                self._reply(200,result.to_json().encode())
            except (ValueError,UnicodeError,RecursionError,TimeoutError) as exc:
                self._reply(400,json.dumps({"error":str(exc)}).encode())
        def log_message(self, fmt, *args):
            # Do not echo attacker-controlled source/body text to terminal logs.
            pass
    return Handler


def serve(document: Document, port: int = 8765):
    if not 0 <= port <= 65535: raise ValueError("Invalid port")
    with ThreadingHTTPServer(("127.0.0.1",port),make_handler(document)) as server:
        print(f"ProofReader: http://127.0.0.1:{server.server_port}",flush=True)
        print("Source parsing only. No build or execution endpoints.",flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
