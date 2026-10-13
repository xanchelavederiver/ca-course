"""Long-running operations (gen, PDF builds, issue, regen, validate-all) as jobs.

``POST`` endpoints return a job id; clients follow progress over
Server-Sent Events (``GET /jobs/{id}/events``). A single in-process FIFO is
enough: there is one user and one engine worker.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable

from taskgen_web.worker import EngineError

JobFn = Callable[["Job"], Awaitable[Any]]


@dataclass
class Job:
    id: str
    kind: str
    title: str
    status: str = "queued"  # queued | running | done | failed
    created: float = field(default_factory=time.time)
    finished: float | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    result: Any = None
    error: dict[str, Any] | None = None
    _changed: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    def log(self, message: str, **data: Any) -> None:
        """Append a progress event (shown in the UI's job log)."""
        self._emit({"type": "log", "message": message, **data})

    def _emit(self, event: dict[str, Any]) -> None:
        self.events.append({"seq": len(self.events), "t": time.time(), **event})
        self._changed.set()

    def summary(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "title": self.title, "status": self.status,
                "created": self.created, "finished": self.finished, "result": self.result,
                "error": self.error, "events": self.events}


class JobManager:
    def __init__(self, keep: int = 50) -> None:
        self.jobs: dict[str, Job] = {}
        self._queue: asyncio.Queue[tuple[Job, JobFn]] = asyncio.Queue()
        self._ids = itertools.count(1)
        self._keep = keep
        self._runner: asyncio.Task | None = None

    def start(self) -> None:
        if self._runner is None:
            self._runner = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._runner is not None:
            self._runner.cancel()
            try:
                await self._runner
            except asyncio.CancelledError:
                pass
            self._runner = None

    def submit(self, kind: str, title: str, fn: JobFn) -> Job:
        job = Job(id=f"{int(time.time())}-{next(self._ids)}", kind=kind, title=title)
        self.jobs[job.id] = job
        job._emit({"type": "status", "status": "queued"})
        self._queue.put_nowait((job, fn))
        self._prune()
        return job

    def _prune(self) -> None:
        done = [j for j in self.jobs.values() if j.status in ("done", "failed")]
        for j in done[:-self._keep] if len(done) > self._keep else []:
            del self.jobs[j.id]

    async def _run(self) -> None:
        while True:
            job, fn = await self._queue.get()
            job.status = "running"
            job._emit({"type": "status", "status": "running"})
            try:
                job.result = await fn(job)
                job.status = "done"
            except EngineError as e:
                job.status = "failed"
                job.error = {"kind": e.kind, "message": str(e), "traceback": e.traceback}
            except Exception as e:  # noqa: BLE001 - reported to the client
                job.status = "failed"
                job.error = {"kind": type(e).__name__, "message": str(e),
                             "traceback": traceback.format_exc()}
            job.finished = time.time()
            job._emit({"type": "status", "status": job.status, "result": job.result,
                       "error": job.error})
            self._queue.task_done()

    async def wait(self, job_id: str, timeout: float | None = None) -> Job:
        """Wait until a job has finished (used by tests)."""
        job = self.jobs[job_id]

        async def _wait() -> None:
            while job.status not in ("done", "failed"):
                job._changed.clear()
                await job._changed.wait()
        await asyncio.wait_for(_wait(), timeout)
        return job

    async def events(self, job_id: str, start: int = 0) -> AsyncIterator[str]:
        """SSE stream of a job's events from ``start`` until it finishes."""
        job = self.jobs[job_id]
        i = start
        while True:
            while i < len(job.events):
                ev = job.events[i]
                i += 1
                yield f"id: {ev['seq']}\nevent: {ev['type']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
            if job.status in ("done", "failed"):
                return
            job._changed.clear()
            if i < len(job.events):
                continue
            try:
                await asyncio.wait_for(job._changed.wait(), timeout=15)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
