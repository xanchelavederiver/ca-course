"""Capstone configuration: ``materials/capstone/capstone.yaml`` + ``NN-slug/bench/config.yaml``.

Per-capstone ``bench/config.yaml``::

    generator: pohlig_hellman      # taskgen.capstone.gens.<name>, or a dotted module path
    seed: 20261014                 # vector seed (recorded in vectors/manifest.json)
    image: taskgen                 # compose service the reference runs in: taskgen | capstone-c
    build: make -C reference       # optional, run (in the capstone dir) before benchmarking
    command: sage -python reference/main.py   # the reference solver, run in the capstone dir
    slack: 10                      # optional override of capstone.yaml
    timeout: 300                   # optional, seconds per vector
    x_label: "p, бит"              # plot axis
    sizes:                         # size classes, in increasing difficulty
      - name: p50
        x: 50                      # plot abscissa (e.g. bits)
        count: 10
        commit: true               # commit vectors/p50.jsonl (else regenerated, gitignored)
        timeout: 120               # optional per-class override
        params: {bits: 50, ...}    # passed to generate()
    requirements:                  # -> requirements.tex macros \\<Name>
      ReqBitsMax: {value: 100}
      ReqSeconds: {size: p100, stat: max, round: nice}   # slack * stat(wall time), rounded up
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "materials" / "capstone"
GLOBAL_FILE = ROOT / "capstone.yaml"

DEFAULTS = {"slack": 10, "timeout": 600, "warmup": True, "memory": "8g", "cpus": 2}


@dataclass
class Size:
    name: str
    count: int
    params: dict[str, Any]
    x: float | None = None
    commit: bool = True
    timeout: float | None = None


@dataclass
class Capstone:
    n: int
    slug: str
    title: str
    dir: Path
    generator: str
    seed: int
    image: str
    command: str
    sizes: list[Size]
    build: str | None = None
    slack: float = DEFAULTS["slack"]
    timeout: float = DEFAULTS["timeout"]
    warmup: bool = True
    x_label: str = "размер"
    requirements: dict[str, dict] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def vectors_dir(self) -> Path:
        return self.dir / "vectors"

    @property
    def bench_dir(self) -> Path:
        return self.dir / "bench"

    def size(self, name: str) -> Size:
        for s in self.sizes:
            if s.name == name:
                return s
        raise KeyError(f"{self.slug}: no size class {name!r} "
                       f"(have {', '.join(s.name for s in self.sizes)})")

    def timeout_for(self, size: Size) -> float:
        return float(size.timeout or self.timeout)

    def gen(self):
        mod = self.generator if "." in self.generator else f"taskgen.capstone.gens.{self.generator}"
        return importlib.import_module(mod)


def load_global(path: Path = GLOBAL_FILE) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {**DEFAULTS, **(data or {})}


def capstone_dir(entry: dict, root: Path = ROOT) -> Path:
    return root / f"{int(entry['n']):02d}-{entry['slug']}"


def load(slug: str, root: Path = ROOT, slack: float | None = None) -> Capstone:
    """Load one capstone by slug (or ``NN-slug`` / number); ``slack`` overrides config."""
    g = load_global(root / "capstone.yaml")
    entries = g.get("capstones") or []
    for e in entries:
        if slug in (e["slug"], f"{int(e['n']):02d}-{e['slug']}", str(e["n"])):
            break
    else:
        raise KeyError(f"unknown capstone {slug!r} (have {', '.join(e['slug'] for e in entries)})")
    d = capstone_dir(e, root)
    cfg_path = d / "bench" / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"{cfg_path} is missing")
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    sizes = [Size(name=s["name"], count=int(s.get("count", 10)), params=dict(s.get("params") or {}),
                  x=s.get("x"), commit=bool(s.get("commit", True)), timeout=s.get("timeout"))
             for s in cfg.get("sizes") or []]
    return Capstone(
        n=int(e["n"]), slug=e["slug"], title=e.get("title", e["slug"]), dir=d,
        generator=cfg["generator"], seed=int(cfg.get("seed", 0)), image=cfg.get("image", "taskgen"),
        command=cfg["command"], build=cfg.get("build"), sizes=sizes,
        slack=float(slack if slack is not None else cfg.get("slack", g["slack"])),
        timeout=float(cfg.get("timeout", g["timeout"])),
        warmup=bool(cfg.get("warmup", g["warmup"])),
        x_label=cfg.get("x_label", "размер"),
        requirements=dict(cfg.get("requirements") or {}), raw=cfg,
    )


def slugs(root: Path = ROOT) -> list[str]:
    """Slugs of the capstones that have a bench/config.yaml, in capstone.yaml order."""
    g = load_global(root / "capstone.yaml")
    return [e["slug"] for e in g.get("capstones") or []
            if (capstone_dir(e, root) / "bench" / "config.yaml").exists()]
