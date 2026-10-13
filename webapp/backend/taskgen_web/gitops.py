"""Read-only git: status and diffs. Committing stays in the instructor's own tools."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class GitError(Exception):
    pass


def _git(repo: Path, *args: str, check: bool = True) -> str:
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise GitError(str(e)) from e
    if check and proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def status(repo: Path) -> dict[str, Any]:
    """Branch, HEAD and changed files (``git status --porcelain``)."""
    try:
        head = _git(repo, "rev-parse", "HEAD").strip()
    except GitError as e:
        return {"available": False, "error": str(e), "files": [], "dirty": None}
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD", check=False).strip()
    subject = _git(repo, "log", "-1", "--format=%s", check=False).strip()
    files = []
    for line in _git(repo, "status", "--porcelain=v1", "-uall").splitlines():
        code, path = line[:2], line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append({"path": path.strip('"'), "status": code})
    # Same notion of "dirty" as the audit manifest (archive/ and build/ excluded).
    relevant = [f for f in files if not f["path"].startswith(("archive/", "build/"))]
    return {"available": True, "branch": branch, "head": head, "subject": subject,
            "files": files, "dirty": bool(relevant), "dirty_files": [f["path"] for f in relevant]}


def diff(repo: Path, path: str | None = None) -> str:
    """Working tree vs HEAD (staged + unstaged); untracked files as whole-file additions."""
    args = ["diff", "HEAD", "--no-color", "--no-ext-diff"]
    out = _git(repo, *args, *(["--", path] if path else []))
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard",
                     *(["--", path] if path else [])).splitlines()
    for f in untracked:
        out += _git(repo, "diff", "--no-color", "--no-index", "--", "/dev/null", f, check=False)
    return out


def show_head(repo: Path, path: str) -> str | None:
    """File content at HEAD (None if untracked)."""
    try:
        return _git(repo, "show", f"HEAD:{path}")
    except GitError:
        return None
