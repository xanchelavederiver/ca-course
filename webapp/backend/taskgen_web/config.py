"""Settings from the environment (all optional)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_REPO = Path(__file__).resolve().parents[3]


@dataclass
class Settings:
    # Repository root: the same files the CLI uses (bind-mounted at /work in docker).
    repo: Path = field(default_factory=lambda: Path(os.environ.get("TASKGEN_REPO", DEFAULT_REPO)).resolve())
    # latex-worker service (scripts/latex-worker.py); empty = PDF builds unavailable.
    latex_url: str = field(default_factory=lambda: os.environ.get("LATEX_WORKER_URL", ""))
    # Built SPA (webapp/frontend/dist); served at / when present.
    static_dir: Path | None = field(default_factory=lambda: Path(os.environ["WEB_STATIC_DIR"])
                                    if os.environ.get("WEB_STATIC_DIR") else None)
    # Seconds before a hanging engine call is killed (the worker is respawned).
    engine_timeout: float = field(default_factory=lambda: float(os.environ.get("ENGINE_TIMEOUT", "300")))
    # Restart the engine worker when taskgen/ changes.
    watch: bool = field(default_factory=lambda: os.environ.get("ENGINE_WATCH", "1") != "0")

    @property
    def static(self) -> Path:
        return self.static_dir or self.repo / "webapp" / "frontend" / "dist"
