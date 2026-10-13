"""Audit archive: issued runs, manifests, verification (regen)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from taskgen_web.context import Ctx, get_ctx

router = APIRouter(tags=["archive"])
SEG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _run_dir(ctx: Ctx, sheet: str, run: str) -> Path:
    if not SEG.match(sheet) or not SEG.match(run):
        raise HTTPException(400, "bad sheet/run name")
    d = ctx.repo / "archive" / sheet / run
    if not (d / "manifest.json").is_file():
        raise HTTPException(404, f"no archived run archive/{sheet}/{run}")
    return d


def _summary(m: dict, d: Path) -> dict:
    files = m.get("files", {})
    return {"run": d.name, "sheet_id": m.get("sheet_id"), "created_at": m.get("created_at"),
            "master_seed": m.get("master_seed"), "engine_version": m.get("engine_version"),
            "git": m.get("git"), "layout": m.get("layout", "combined"),
            "variants": len(m.get("variants", [])),
            "sealed": [f for f in files if f.endswith(".pdf")],
            "path": f"archive/{d.parent.name}/{d.name}"}


@router.get("/archive")
async def archive(ctx: Ctx = Depends(get_ctx)) -> list[dict]:
    root = ctx.repo / "archive"
    out = []
    for sheet_dir in sorted(p for p in root.glob("*") if p.is_dir()) if root.is_dir() else []:
        runs = []
        for m in sorted(sheet_dir.glob("*/manifest.json"), reverse=True):
            try:
                runs.append(_summary(json.loads(m.read_text(encoding="utf-8")), m.parent))
            except (OSError, ValueError) as e:
                runs.append({"run": m.parent.name, "error": str(e)})
        if runs:
            out.append({"sheet_id": sheet_dir.name, "runs": runs})
    return out


@router.get("/archive/{sheet}/{run}")
async def archived_run(sheet: str, run: str, ctx: Ctx = Depends(get_ctx)) -> dict:
    d = _run_dir(ctx, sheet, run)
    m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    on_disk = sorted(p.name for p in d.iterdir() if p.is_file())
    return {**_summary(m, d), "manifest": m, "files_on_disk": on_disk}


class RegenBody(BaseModel):
    variants: list[str] | None = None


@router.post("/archive/{sheet}/{run}/regen")
async def regen(sheet: str, run: str, body: RegenBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    d = _run_dir(ctx, sheet, run)
    rel = f"archive/{sheet}/{run}"

    async def job_fn(job):
        what = ", ".join(body.variants) if body.variants else "all variants"
        job.log(f"regenerating {rel} ({what})", step="regen")
        res = await ctx.worker.call("regen", run_dir=rel, only=body.variants, timeout=3600)
        for w in res["warnings"]:
            job.log(f"warning: {w}", step="regen", level="warning")
        job.log("IDENTICAL" if res["identical"] else "DIFFERENT: " + ", ".join(res["mismatches"]),
                step="compare", identical=res["identical"])
        return res

    assert d.is_dir()
    job = ctx.jobs.submit("regen", f"Verify {rel}", job_fn)
    return {"job": job.id}
