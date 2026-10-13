"""Draft and issue runs (as jobs), job status and SSE progress."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from taskgen_web import gitops
from taskgen_web.context import Ctx, get_ctx
from taskgen_web.latex import LatexUnavailable
from taskgen_web.routers.sheets import _sheet_path

router = APIRouter(tags=["runs"])


class DraftBody(BaseModel):
    path: str | None = None
    yaml: str | None = None  # unsaved edits (wins over path)
    seed: int | None = None
    variants: list[str] | None = None
    pdf: bool = True


@router.post("/runs/draft")
async def draft(body: DraftBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    if body.yaml is None and body.path is None:
        raise HTTPException(400, "give a sheet path or yaml")
    text = body.yaml if body.yaml is not None else \
        _sheet_path(ctx, body.path).read_text(encoding="utf-8")  # type: ignore[arg-type]

    async def run(job):
        job.log("generating", step="gen")
        res = await ctx.worker.call("generate", spec_text=text, seed=body.seed, draft=True,
                                    only=body.variants, spec_path=body.path)
        job.log(f"{len(res['variants'])} variant(s), master seed {res['master_seed']}",
                step="gen", out_dir=res["out_dir"])
        res["pdfs"], res["warning"] = [], None
        if body.pdf:
            try:
                res["pdfs"] = await ctx.build_pdfs(job, res["out_dir"], res["files"])
            except LatexUnavailable as e:
                res["warning"] = str(e)
        return res

    job = ctx.jobs.submit("draft", f"Draft {body.path or 'unsaved sheet'}", run)
    return {"job": job.id}


class IssueBody(BaseModel):
    path: str
    seed: int | None = None


@router.post("/runs/issue")
async def issue(body: IssueBody, ctx: Ctx = Depends(get_ctx)) -> Any:
    """Same path as ``make issue``: gen -> build every PDF -> seal.

    A dirty working tree only produces a warning (in the job log and the
    result); the manifest records ``git.dirty: true``, as the CLI does.
    """
    full = _sheet_path(ctx, body.path)
    text = full.read_text(encoding="utf-8")
    problems = await ctx.worker.call("check_sheet", text=text)
    if problems:
        return JSONResponse({"detail": "invalid sheet spec", "problems": problems}, status_code=422)
    git = gitops.status(ctx.repo)
    dirty_files = git.get("dirty_files") or []
    if not ctx.latex.available:
        raise HTTPException(503, "PDF builds are unavailable (LATEX_WORKER_URL is not set)")

    async def run(job):
        if dirty_files:
            job.log(f"warning: {len(dirty_files)} uncommitted file(s); the manifest's git commit "
                    "does not fully describe the generator (recorded as git.dirty)",
                    step="git", level="warning", files=dirty_files)
        job.log("generating", step="gen")
        res = await ctx.worker.call("generate", spec_text=text, seed=body.seed, draft=False,
                                    spec_path=body.path)
        job.log(f"archived {res['out_dir']}: {len(res['variants'])} variant(s), "
                f"master seed {res['master_seed']}", step="gen", out_dir=res["out_dir"])
        res["pdfs"] = await ctx.build_pdfs(job, res["out_dir"], res["files"])
        sealed = await ctx.worker.call("seal", run_dir=res["out_dir"])
        job.log(f"sealed {', '.join(sealed)}", step="seal")
        res["sealed"] = sealed
        res["dirty_files"] = dirty_files
        return res

    job = ctx.jobs.submit("issue", f"Issue {body.path}", run)
    return {"job": job.id}


@router.get("/jobs")
async def jobs(ctx: Ctx = Depends(get_ctx)) -> list[dict]:
    return [{k: v for k, v in j.summary().items() if k != "events"}
            for j in reversed(list(ctx.jobs.jobs.values()))]


@router.get("/jobs/{job_id}")
async def job(job_id: str, ctx: Ctx = Depends(get_ctx)) -> dict:
    j = ctx.jobs.jobs.get(job_id)
    if j is None:
        raise HTTPException(404, f"no such job {job_id}")
    return j.summary()


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str, start: int = 0, ctx: Ctx = Depends(get_ctx)) -> StreamingResponse:
    if job_id not in ctx.jobs.jobs:
        raise HTTPException(404, f"no such job {job_id}")
    return StreamingResponse(ctx.jobs.events(job_id, start), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
