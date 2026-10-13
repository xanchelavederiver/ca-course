#!/usr/bin/env python3
"""Tiny PDF build service for the web app (runs in the `latex` container).

    POST /build  {"tex": "build/x/doc.tex", "outdir": "build/x"}
      -> 200 {"ok": true, "pdf": "build/x/doc.pdf", "seconds": 1.2}
      -> 200 {"ok": false, "log": "<error excerpt>"}
    GET  /health -> {"ok": true}

Only repo-relative paths under build/, archive/ and materials/ are accepted.
Builds run one at a time via scripts/latex-build.sh, exactly like `make pdf`.
Stdlib only: the service is reachable only on the internal compose network,
so the web container needs no access to the docker socket.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path, PurePosixPath

REPO = Path(os.environ.get("REPO", "/work")).resolve()
ROOTS = ("build", "archive", "materials")
TIMEOUT = int(os.environ.get("LATEX_TIMEOUT", "600"))
_lock = threading.Lock()


def safe(rel: str, suffix: str | None = None) -> str:
    p = PurePosixPath(rel)
    if not rel or p.is_absolute() or ".." in p.parts or p.parts[0] not in ROOTS:
        raise ValueError(f"path not allowed: {rel!r}")
    full = (REPO / p).resolve()
    if not any(full == (REPO / r).resolve() or (REPO / r).resolve() in full.parents for r in ROOTS):
        raise ValueError(f"path not allowed: {rel!r}")
    if suffix and p.suffix != suffix:
        raise ValueError(f"expected a {suffix} file: {rel!r}")
    return str(p)


def build(tex: str, outdir: str | None) -> dict:
    tex = safe(tex, ".tex")
    outdir = safe(outdir) if outdir else str(PurePosixPath("build") / PurePosixPath(tex).parent)
    if not (REPO / tex).is_file():
        return {"ok": False, "log": f"no such file: {tex}"}
    t0 = time.monotonic()
    with _lock:
        proc = subprocess.run(["scripts/latex-build.sh", tex, outdir], cwd=REPO,
                              capture_output=True, text=True, timeout=TIMEOUT)
    if proc.returncode != 0:
        return {"ok": False, "log": (proc.stderr or proc.stdout)[-20000:]}
    return {"ok": True, "pdf": proc.stdout.strip().splitlines()[-1],
            "seconds": round(time.monotonic() - t0, 2)}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"ok": False, "log": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/build":
            self._send(404, {"ok": False, "log": "not found"})
            return
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            self._send(200, build(req["tex"], req.get("outdir")))
        except (ValueError, KeyError, TypeError) as e:
            self._send(400, {"ok": False, "log": str(e)})
        except subprocess.TimeoutExpired:
            self._send(200, {"ok": False, "log": f"timeout after {TIMEOUT}s"})

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("latex-worker: " + fmt % args + "\n")


def main() -> None:
    port = int(os.environ.get("PORT", "8001"))
    print(f"latex-worker listening on :{port} (repo {REPO})", file=sys.stderr, flush=True)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
