"""Health, engine status and the MathJax macro shim."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends

from taskgen_web.context import Ctx, get_ctx

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health() -> dict:
    return {"ok": True}


@router.get("/engine")
async def engine_status(ctx: Ctx = Depends(get_ctx)) -> dict:
    return {**ctx.worker.status(), "latex": {"configured": ctx.latex.available,
                                             "reachable": await ctx.latex.health()},
            "repo": str(ctx.repo)}


@router.post("/engine/restart")
async def engine_restart(ctx: Ctx = Depends(get_ctx)) -> dict:
    await ctx.worker.restart()
    return ctx.worker.status()


_NEWCOMMAND = re.compile(r"^\\(?:re)?newcommand\{\\(\w+)\}(?:\[(\d)\])?\{(.*)\}\s*(?:%.*)?$")
_OPERATOR = re.compile(r"^\\DeclareMathOperator\{\\(\w+)\}\{(.*)\}\s*(?:%.*)?$")


@lru_cache(maxsize=4)
def _macros(path: Path, mtime: float) -> dict:
    out: dict = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if m := _NEWCOMMAND.match(line):
            name, nargs, body = m.groups()
            if "@" in body or "\\par" in body:
                continue
            out[name] = [body, int(nargs)] if nargs else body
        elif m := _OPERATOR.match(line):
            out[m.group(1)] = r"\operatorname{" + m.group(2) + "}"
    return out


@router.get("/latex/macros")
async def latex_macros(ctx: Ctx = Depends(get_ctx)) -> dict:
    """MathJax ``tex.macros`` generated from ``latex/ca-common.sty``."""
    sty = ctx.repo / "latex" / "ca-common.sty"
    if not sty.is_file():
        return {}
    return _macros(sty, sty.stat().st_mtime)
