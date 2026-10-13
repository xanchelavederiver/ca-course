"""Repo-relative path handling with traversal protection."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from fastapi import HTTPException

# Top-level directories whose files may be served (PDF/tex/json/log downloads).
FILE_ROOTS = ("build", "archive", "materials")
# Directories the latex worker may build in (mirrors scripts/latex-worker.py).
BUILD_ROOTS = ("build", "archive", "materials")


def resolve(repo: Path, rel: str, roots: tuple[str, ...], suffixes: tuple[str, ...] | None = None,
            must_exist: bool = False) -> Path:
    """Resolve a repo-relative path that must lie under one of ``roots``.

    Rejects absolute paths, ``..`` components and symlink escapes (404 for a
    disallowed path so the whitelist is not probeable, 400 for bad syntax).
    """
    p = PurePosixPath(rel)
    if not rel or p.is_absolute() or ".." in p.parts or "\\" in rel or "\x00" in rel:
        raise HTTPException(400, f"bad path: {rel!r}")
    if p.parts[0] not in roots:
        raise HTTPException(404, f"not found: {rel}")
    full = (repo / p).resolve()
    allowed = [(repo / r).resolve() for r in roots]
    if not any(full == a or a in full.parents for a in allowed):
        raise HTTPException(404, f"not found: {rel}")
    if suffixes is not None and full.suffix not in suffixes:
        raise HTTPException(400, f"unsupported file type: {rel}")
    if must_exist and not full.is_file():
        raise HTTPException(404, f"not found: {rel}")
    return full


def rel(repo: Path, p: Path) -> str:
    return str(p.resolve().relative_to(repo))
