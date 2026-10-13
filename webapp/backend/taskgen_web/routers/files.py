"""File downloads (path-whitelisted) and ad-hoc PDF builds."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from taskgen_web.context import Ctx, get_ctx
from taskgen_web.latex import LatexUnavailable
from taskgen_web.paths import BUILD_ROOTS, FILE_ROOTS, resolve

router = APIRouter(tags=["files"])

MEDIA = {".pdf": "application/pdf", ".tex": "text/plain; charset=utf-8",
         ".json": "application/json", ".log": "text/plain; charset=utf-8",
         ".yaml": "text/plain; charset=utf-8"}


@router.get("/files/{path:path}")
async def get_file(path: str, download: bool = False, ctx: Ctx = Depends(get_ctx)) -> FileResponse:
    full = resolve(ctx.repo, path, FILE_ROOTS, tuple(MEDIA), must_exist=True)
    return FileResponse(full, media_type=MEDIA[full.suffix],
                        filename=full.name if download else None,
                        content_disposition_type="attachment" if download else "inline",
                        headers={"Cache-Control": "no-store"})


class BuildBody(BaseModel):
    tex: str
    outdir: str | None = None


@router.post("/builds")
async def build(body: BuildBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    resolve(ctx.repo, body.tex, BUILD_ROOTS, (".tex",), must_exist=True)
    if body.outdir:
        resolve(ctx.repo, body.outdir, BUILD_ROOTS)
    try:
        return await ctx.latex.build(body.tex, body.outdir)
    except LatexUnavailable as e:
        raise HTTPException(503, str(e)) from None
