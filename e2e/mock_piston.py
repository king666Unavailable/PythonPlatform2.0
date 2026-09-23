"""Mock Piston API for sandbox E2E verification.

Implements the two endpoints used by glotio.py:
  GET  /api/v2/runtimes
  POST /api/v2/execute  (runs the python files locally with subprocess)
"""

import json
import subprocess
import sys
import tempfile
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Use the interpreter that started the server so it also works on Windows.
PY = sys.executable


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[mock-piston]", fmt % args, flush=True)

    def _send(self, payload, code=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/v2/runtimes":
            self._send([{"language": "python", "version": "3.12.6", "aliases": ["py", "python3"]}])
        else:
            self._send({"message": "not found"}, 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path != "/api/v2/execute":
            self._send({"message": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length) or b"{}")
        files = payload.get("files") or []
        stdin = payload.get("stdin") or ""
        run_timeout = int(payload.get("run_timeout") or 10000) / 1000
        started = time.time()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                for item in files:
                    (Path(tmp) / str(item.get("name") or "main.py")).write_text(
                        str(item.get("content") or ""), encoding="utf-8"
                    )
                entry = next((f["name"] for f in files if f.get("name") == "main.py"), files[0]["name"] if files else None)
                try:
                    proc = subprocess.run(
                        [PY, entry], cwd=tmp, input=stdin, capture_output=True, text=True, timeout=run_timeout
                    )
                    run = {"stdout": proc.stdout, "stderr": proc.stderr, "code": proc.returncode, "output": ""}
                except subprocess.TimeoutExpired as exc:
                    run = {
                        "stdout": exc.stdout or "",
                        "stderr": exc.stderr or "",
                        "code": 124,
                        "output": "",
                    }
                    self._send(
                        {
                            "language": payload.get("language"),
                            "version": payload.get("version"),
                            "run": run,
                            "compile": {"code": 0, "stderr": "", "output": ""},
                        }
                    )
                    return
            self._send(
                {
                    "language": payload.get("language"),
                    "version": payload.get("version"),
                    "run": run,
                    "compile": {"code": 0, "stderr": "", "output": ""},
                }
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._send({"message": f"mock piston failure: {exc}"}, 500)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 2000), Handler)
    print("[mock-piston] listening on http://127.0.0.1:2000", flush=True)
    server.serve_forever()
