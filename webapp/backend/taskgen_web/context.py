"""Shared application state (one instance per app, at ``app.state.ctx``)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

from taskgen_web.config import Settings
from taskgen_web.jobs import Job, JobManager
from taskgen_web.latex import LatexClient
from taskgen_web.taskedit import TaskIndex
from taskgen_web.worker import EngineWorker


class BuildFailed(Exception):
    def __init__(self, tex: str, log: str) -> None:
        super().__init__(f"LaTeX build failed: {tex}")
        self.tex = tex
        self.log = log


@dataclass
class Ctx:
    settings: Settings
    worker: EngineWorker
    jobs: JobManager
    latex: LatexClient
    index: TaskIndex
    # task id -> last validation {ok, at, count, results: [...]}
    validation: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def repo(self) -> Path:
        return self.settings.repo

    def record_validation(self, results: list[dict[str, Any]], count: int) -> None:
        by_task: dict[str, list[dict[str, Any]]] = {}
        for r in results:
            by_task.setdefault(r["ref"].split("@")[0], []).append(r)
        for tid, rs in by_task.items():
            self.validation[tid] = {"ok": all(r["ok"] for r in rs), "at": time.time(),
                                    "count": count, "results": rs}

    async def build_pdfs(self, job: Job | None, out_dir: str, files: list[str]) -> list[str]:
        """Compile every .tex of a run directory via the latex worker (in order)."""
        pdfs = []
        for name in files:
            if not name.endswith(".tex"):
                continue
            if job:
                job.log(f"pdflatex {name}", step="build", file=name)
            res = await self.latex.build(f"{out_dir}/{name}", out_dir)
            if not res.get("ok"):
                raise BuildFailed(f"{out_dir}/{name}", res.get("log", ""))
            pdfs.append(res["pdf"])
        return pdfs


def get_ctx(request: Request) -> Ctx:
    return request.app.state.ctx


def not_found(msg: str) -> HTTPException:
    return HTTPException(404, msg)
