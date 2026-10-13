"""Engine worker: a warm child process that imports taskgen (and Sage).

The API process never imports task modules itself. Every engine operation
(``OPS`` below, thin wrappers over ``taskgen.service``) runs in a child
process started with the *spawn* context, so

* the slow Sage/registry import is paid once, not per request;
* task edits take effect: a file watcher on ``taskgen/`` marks the worker
  stale and it is restarted (``registry.discover()`` is import-once);
* a crashing or looping task cannot take the API down: each call has a
  timeout, after which the worker is killed and respawned.

Calls are serialized (one user, one worker). Long operations may report
progress, which is forwarded to the caller's ``on_progress`` callback.
"""

from __future__ import annotations

import asyncio
import logging
import multiprocessing as mp
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("taskgen_web.worker")


class EngineError(Exception):
    """An engine operation raised; carries the remote traceback."""

    def __init__(self, kind: str, message: str, tb: str = "") -> None:
        super().__init__(message)
        self.kind = kind
        self.traceback = tb


class EngineTimeout(EngineError):
    pass


class EngineCrashed(EngineError):
    pass


# --- child side ------------------------------------------------------------------

def _ops() -> dict[str, Callable[..., Any]]:
    from taskgen import service
    from taskgen.core import registry

    def ping() -> dict:
        registry.discover(strict=False)
        return {"version": service.version(), "import_errors": dict(registry.IMPORT_ERRORS),
                "tasks": len(registry.all_tasks())}

    def preview(ref: str, seed: int | None = None, count: int = 1, statement: str | None = None,
                solution: str | None = None, tex_path: str | None = None) -> dict:
        inst = service.preview(ref, seed, count, statement, solution)
        if tex_path:
            out = service.REPO_ROOT / tex_path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(service.preview_tex(inst, f"Предпросмотр: {ref}"), encoding="utf-8")
        return {"instances": [i.to_dict() for i in inst], "tex": tex_path}

    def validate(target: str = "all", count: int = 50, seed: int = 0, _progress=None) -> dict:
        def report(check, done, total):
            if _progress:
                _progress({"ref": check.ref, "ok": check.ok, "error": check.error,
                           "done": done, "total": total})
        return service.validation_dict(service.validate(target, count, seed, progress=report))

    def generate(spec_text: str, seed: int | None = None, draft: bool = False,
                 only: list[str] | None = None, spec_path: str | None = None) -> dict:
        res = service.generate(spec_text, seed, draft=draft, only=set(only) if only else None,
                               spec_path=spec_path)
        return service.gen_dict(res)

    def regen(run_dir: str, only: list[str] | None = None) -> dict:
        report, out = service.regen(service.REPO_ROOT / run_dir, set(only) if only else None)
        return {"identical": report.identical, "mismatches": report.mismatches,
                "warnings": report.warnings, "checked": report.checked, "out_dir": service.rel(out),
                "files": sorted(p.name for p in out.glob("*.tex"))}

    def seal(run_dir: str) -> list[str]:
        return service.seal(service.REPO_ROOT / run_dir)

    return {
        "ping": ping,
        "list_tasks": service.list_tasks,
        "task_info": service.task_info,
        "topics": service.topics,
        "preview": preview,
        "validate": validate,
        "check_sheet": service.check_sheet_text,
        "sheet_schema": service.sheet_schema,
        "sheet_variants": service.sheet_variants,
        "variant_stats": service.variant_stats,
        "generate": generate,
        "regen": regen,
        "seal": seal,
    }


def _child_main(conn, repo: str) -> None:  # pragma: no cover - runs in the child
    sys.path.insert(0, repo)
    from taskgen.core import registry

    registry.discover(strict=False)
    ops = _ops()
    while True:
        try:
            op, kwargs = conn.recv()
        except EOFError:
            return
        try:
            fn = ops[op]
            if op == "validate":
                kwargs["_progress"] = lambda data: conn.send(("progress", data))
            result = fn(**kwargs)
            conn.send(("ok", result))
        except BaseException as e:  # noqa: BLE001 - everything goes back to the parent
            conn.send(("error", (type(e).__name__, str(e), traceback.format_exc())))


# --- parent side -----------------------------------------------------------------

class EngineWorker:
    def __init__(self, repo: Path, timeout: float = 300.0) -> None:
        self.repo = repo
        self.timeout = timeout
        self._ctx = mp.get_context("spawn")
        self._proc: mp.process.BaseProcess | None = None
        self._conn = None
        self._lock = asyncio.Lock()
        self.stale = False
        self.restarts = 0
        self.started_at: float | None = None
        self.state = "stopped"  # stopped | starting | ready | busy
        self.info: dict[str, Any] = {}

    # lifecycle (call with the lock held) ------------------------------------------
    def _spawn(self) -> None:
        parent, child = self._ctx.Pipe()
        proc = self._ctx.Process(target=_child_main, args=(child, str(self.repo)),
                                 name="taskgen-engine", daemon=True)
        proc.start()
        child.close()
        self._proc, self._conn = proc, parent
        self.stale = False
        self.started_at = time.time()
        self.state = "starting"

    def _kill(self) -> None:
        if self._proc is not None:
            if self._proc.is_alive():
                self._proc.kill()
            self._proc.join(timeout=5)
        if self._conn is not None:
            self._conn.close()
        self._proc = self._conn = None
        self.state = "stopped"

    async def start(self) -> None:
        await self.call("ping")

    async def stop(self) -> None:
        async with self._lock:
            self._kill()

    async def restart(self) -> None:
        self.stale = True
        await self.call("ping")

    def mark_stale(self) -> None:
        self.stale = True

    # calls ---------------------------------------------------------------------------
    async def call(self, op: str, *, timeout: float | None = None,
                   on_progress: Callable[[dict], None] | None = None, **kwargs: Any) -> Any:
        """Run ``op`` in the worker; (re)spawns it first if it is stale or dead."""
        async with self._lock:
            if self._proc is None or not self._proc.is_alive() or self.stale:
                if self._proc is not None:
                    self.restarts += 1
                self._kill()
                self._spawn()
                try:
                    self.info = await self._roundtrip("ping", {}, timeout, None)
                except EngineError as e:
                    self.info = {"error": str(e)}
                    raise
                if op == "ping":
                    return self.info
            result = await self._roundtrip(op, kwargs, timeout, on_progress)
            if op == "ping":
                self.info = result
            return result

    async def _roundtrip(self, op: str, kwargs: dict, timeout: float | None,
                         on_progress: Callable[[dict], None] | None) -> Any:
        assert self._conn is not None
        conn = self._conn
        self.state = "busy"
        limit = timeout or self.timeout
        deadline = time.monotonic() + limit
        try:
            conn.send((op, kwargs))
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._kill()  # respawned (and warmed up) by the next call
                    self.restarts += 1
                    raise EngineTimeout("EngineTimeout", f"engine call {op!r} timed out after "
                                                         f"{limit:.0f}s; worker restarted")
                if not await asyncio.to_thread(conn.poll, min(remaining, 0.25)):
                    continue
                kind, payload = conn.recv()
                if kind == "progress":
                    if on_progress:
                        on_progress(payload)
                    continue
                if kind == "ok":
                    return payload
                name, msg, tb = payload
                raise EngineError(name, msg, tb)
        except (EOFError, BrokenPipeError, ConnectionResetError, OSError) as e:
            self._kill()
            self.restarts += 1
            raise EngineCrashed("EngineCrashed", f"engine worker died during {op!r} "
                                                 f"({type(e).__name__}); restarted") from e
        finally:
            if self.state == "busy":
                self.state = "ready"

    def status(self) -> dict[str, Any]:
        return {"state": self.state if not self.stale else "stale", "restarts": self.restarts,
                "started_at": self.started_at, "pid": self._proc.pid if self._proc else None,
                **{k: v for k, v in self.info.items()}}

    # file watcher --------------------------------------------------------------------
    async def watch(self) -> None:
        """Restart the worker after changes under ``taskgen/`` (runs until cancelled)."""
        import watchfiles

        def relevant(change, path: str) -> bool:
            return path.endswith((".py", ".yaml", ".j2")) and "__pycache__" not in path

        async for changes in watchfiles.awatch(self.repo / "taskgen", watch_filter=relevant,
                                               debounce=300):
            mtimes = [Path(path).stat().st_mtime for _, path in changes if Path(path).exists()]
            if self.started_at and mtimes and max(mtimes) < self.started_at and not self.stale:
                continue  # already restarted after this change (e.g. by a request)
            log.info("taskgen changed (%d file(s)); restarting engine worker", len(changes))
            try:
                await self.restart()
            except Exception:  # keep watching
                log.exception("engine restart failed")
