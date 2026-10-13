"""FastAPI app factory.

    uvicorn taskgen_web.app:create_app --factory --host 127.0.0.1 --port 8000

The API lives under ``/api``; the built SPA (if present) is served at ``/``.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from taskgen_web.config import Settings
from taskgen_web.context import BuildFailed, Ctx
from taskgen_web.jobs import JobManager
from taskgen_web.latex import LatexClient, LatexUnavailable
from taskgen_web.routers import archive, files, git, meta, runs, sheets, tasks, topics
from taskgen_web.taskedit import TaskIndex
from taskgen_web.worker import EngineError, EngineWorker

log = logging.getLogger("taskgen_web")

# Engine exceptions that are the client's fault -> HTTP status
ENGINE_STATUS = {"KeyError": 404, "TaskError": 400, "ValueError": 400, "ValidationError": 400,
                 "SamplingError": 422, "TaskValidationError": 422, "EngineTimeout": 504,
                 "EngineCrashed": 500}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        ctx: Ctx = app.state.ctx
        ctx.jobs.start()
        warm = asyncio.create_task(ctx.worker.start())  # Sage import in the background
        watcher = asyncio.create_task(ctx.worker.watch()) if settings.watch else None
        try:
            yield
        finally:
            for t in (warm, watcher):
                if t is not None:
                    t.cancel()
                    with contextlib.suppress(asyncio.CancelledError, Exception):
                        await t
            await ctx.jobs.stop()
            await ctx.worker.stop()

    app = FastAPI(title="taskgen web", version="0.1.0", lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.ctx = Ctx(settings=settings,
                        worker=EngineWorker(settings.repo, settings.engine_timeout),
                        jobs=JobManager(), latex=LatexClient(settings.latex_url),
                        index=TaskIndex(settings.repo))

    @app.exception_handler(EngineError)
    async def engine_error(request: Request, exc: EngineError) -> JSONResponse:
        msg = str(exc)
        if exc.kind == "KeyError":
            msg = msg.strip("'\"")
        return JSONResponse({"detail": msg, "kind": exc.kind, "traceback": exc.traceback},
                            status_code=ENGINE_STATUS.get(exc.kind, 500))

    @app.exception_handler(LatexUnavailable)
    async def latex_unavailable(request: Request, exc: LatexUnavailable) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=503)

    @app.exception_handler(BuildFailed)
    async def build_failed(request: Request, exc: BuildFailed) -> JSONResponse:
        return JSONResponse({"detail": str(exc), "log": exc.log}, status_code=422)

    for r in (meta, tasks, topics, sheets, runs, files, archive, git):
        app.include_router(r.router, prefix="/api")

    _mount_spa(app, settings.static)
    return app


def _mount_spa(app: FastAPI, dist: Path) -> None:
    """Serve the built SPA; unknown non-API paths fall back to index.html (client routing)."""

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        index = dist / "index.html"
        if not index.is_file():
            return JSONResponse({"detail": "frontend not built (cd webapp/frontend && npm run build)"},
                                status_code=404)
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
