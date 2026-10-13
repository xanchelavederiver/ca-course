"""Git status and diffs (read-only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from taskgen_web import gitops
from taskgen_web.context import Ctx, get_ctx

router = APIRouter(tags=["git"])


def _check(path: str | None) -> None:
    if path is not None and (path.startswith(("/", "-")) or ".." in path.split("/")):
        raise HTTPException(400, f"bad path {path!r}")


@router.get("/git/status")
async def status(ctx: Ctx = Depends(get_ctx)) -> dict:
    return gitops.status(ctx.repo)


@router.get("/git/diff", response_class=PlainTextResponse)
async def diff(path: str | None = None, ctx: Ctx = Depends(get_ctx)) -> str:
    _check(path)
    try:
        return gitops.diff(ctx.repo, path)
    except gitops.GitError as e:
        raise HTTPException(400, str(e)) from None


@router.get("/git/head")
async def head(path: str, ctx: Ctx = Depends(get_ctx)) -> dict:
    """A file's content at HEAD (for side-by-side diffs in the editor)."""
    _check(path)
    return {"path": path, "content": gitops.show_head(ctx.repo, path)}
