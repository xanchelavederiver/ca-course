"""Backend tests run against a temporary git copy of the repo (tasks, sheets, latex)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from taskgen_web.app import create_app
from taskgen_web.config import Settings

REPO = Path(__file__).resolve().parents[3]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True).stdout


def make_repo(dst: Path) -> Path:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    for d in ("taskgen", "sheets", "latex", "scripts"):
        shutil.copytree(REPO / d, dst / d, ignore=ignore)
    (dst / "archive").mkdir()
    (dst / ".gitignore").write_text("/build/\n__pycache__/\n")
    git(dst, "init", "-q", "-b", "main")
    git(dst, "-c", "user.email=t@example.com", "-c", "user.name=t", "add", "-A")
    git(dst, "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-q", "-m", "init")
    return dst


@pytest.fixture(scope="session")
def repo(tmp_path_factory) -> Path:
    return make_repo(tmp_path_factory.mktemp("repo"))


class FakeLatex:
    """Stands in for the latex-worker: writes a stub PDF next to the .tex."""

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.built: list[str] = []
        self.fail: set[str] = set()

    available = True

    async def build(self, tex: str, outdir: str | None = None) -> dict:
        self.built.append(tex)
        if any(tex.endswith(f) for f in self.fail):
            return {"ok": False, "log": "! Undefined control sequence."}
        out = Path(outdir or Path("build") / Path(tex).parent)
        pdf = out / (Path(tex).stem + ".pdf")
        (self.repo / pdf).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / pdf).write_bytes(b"%PDF-1.5 stub " + tex.encode())
        return {"ok": True, "pdf": str(pdf)}

    async def health(self) -> bool:
        return True


@pytest.fixture(scope="session")
def client(repo):
    app = create_app(Settings(repo=repo, latex_url="", watch=False, engine_timeout=120))
    fake = FakeLatex(repo)
    app.state.ctx.latex = fake
    with TestClient(app) as c:
        c.fake_latex = fake  # type: ignore[attr-defined]
        c.ctx = app.state.ctx  # type: ignore[attr-defined]
        yield c


@pytest.fixture
def clean_repo(repo, client):
    """Restore the temp repo (tracked + untracked files) after a mutating test."""
    yield repo
    git(repo, "checkout", "-q", "--", ".")
    git(repo, "clean", "-qfd", "--", "taskgen", "sheets")
    client.ctx.worker.mark_stale()


def wait_job(client, job_id: str, timeout: float = 300) -> dict:
    import time

    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "failed"):
            return j
        time.sleep(0.1)
    raise TimeoutError(job_id)
