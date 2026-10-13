"""Audit trail of issued sheets.

Every issued generation run lives in ``archive/<sheet-id>/<run-ts>/``:

* ``manifest.json`` — master seed, sheet spec snapshot (parsed + raw YAML),
  git commit/dirty flag, engine version, per-variant task list with seeds,
  answers and digests, SHA-256 of every archived file;
* ``tasks.tex`` / ``tasks_solutions.tex`` — the generated sources;
* ``tasks.pdf`` / ``tasks_solutions.pdf`` — added by the PDF build and
  recorded in the manifest by ``taskgen seal``.

``regen`` re-runs the generation from the manifest alone (spec snapshot +
master seed) and compares the result byte-for-byte with the archive.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import taskgen
from taskgen import render
from taskgen.core import engine
from taskgen.core.sheet import parse_sheet

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = REPO_ROOT / "archive"
MANIFEST = "manifest.json"
SCHEMA_VERSION = 1


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_info(root: Path = REPO_ROOT) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()
    try:
        commit = git("rev-parse", "HEAD")
    except (OSError, subprocess.CalledProcessError):
        commit = None
    try:
        status = git("status", "--porcelain", "--", ".", ":(exclude)archive", ":(exclude)build")
        dirty: bool | None = bool(status)
    except (OSError, subprocess.CalledProcessError):
        dirty = None
    return {"commit": commit, "dirty": dirty}


def variant_digest(v: engine.Variant) -> str:
    data = [{k: d[k] for k in ("task_id", "preset", "seed", "params", "statement",
                               "solution", "answer")}
            for d in (i.to_dict() for i in v.instances)]
    blob = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _variant_record(v: engine.Variant) -> dict[str, Any]:
    return {
        "key": v.key,
        "group": v.vkey.group,
        "number": v.vkey.number,
        "student": v.vkey.student,
        "digest": variant_digest(v),
        "tasks": [{"slot": i, "task": inst.task_id, "preset": inst.preset,
                   "complexity": inst.complexity, "seed": inst.seed, "answer": inst.answer}
                  for i, inst in enumerate(v.instances)],
    }


def new_run_dir(sheet_id: str, now: dt.datetime | None = None) -> Path:
    now = now or dt.datetime.now(dt.timezone.utc)
    base = ARCHIVE_DIR / sheet_id / now.strftime("%Y%m%d-%H%M%SZ")
    path, n = base, 1
    while path.exists():
        n += 1
        path = base.with_name(f"{base.name}-{n}")
    return path


def write_run(run: engine.SheetRun, spec_source: str, spec_path: str | None,
              out_dir: Path) -> Path:
    """Write sources + manifest of ``run`` to ``out_dir``; returns the manifest path."""
    files = render.write_sources(run, out_dir)
    manifest = {
        "schema": SCHEMA_VERSION,
        "sheet_id": run.spec.id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "engine_version": taskgen.__version__,
        "git": git_info(),
        "master_seed": run.master_seed,
        "spec_path": spec_path,
        "spec": run.spec.model_dump(mode="json"),
        "spec_source": spec_source,
        "variants": [_variant_record(v) for v in run.variants],
        "files": {name: sha256_file(p) for name, p in files.items()},
    }
    path = out_dir / MANIFEST
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_manifest(path: Path) -> dict[str, Any]:
    if path.is_dir():
        path = path / MANIFEST
    return json.loads(path.read_text(encoding="utf-8"))


def seal(run_dir: Path) -> list[str]:
    """Record SHA-256 of the built PDFs in the manifest; returns their names."""
    mpath = run_dir / MANIFEST
    manifest = load_manifest(mpath)
    added = []
    for pdf in sorted(run_dir.glob("*.pdf")):
        manifest["files"][pdf.name] = sha256_file(pdf)
        added.append(pdf.name)
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return added


@dataclass
class RegenReport:
    identical: bool = True
    mismatches: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)


def regen(manifest_path: Path, out_dir: Path, only: set[str] | None = None) -> RegenReport:
    """Regenerate a run from its manifest into ``out_dir`` and compare.

    With ``only`` (variant keys) only those variants are regenerated and
    compared via their digests; otherwise the full .tex sources are compared
    byte-for-byte as well.
    """
    manifest = load_manifest(manifest_path)
    report = RegenReport()
    if manifest.get("engine_version") != taskgen.__version__:
        report.warnings.append(f"engine version differs: archived {manifest.get('engine_version')}, "
                               f"current {taskgen.__version__}")
    cur = git_info()
    if manifest["git"].get("commit") and cur["commit"] != manifest["git"]["commit"]:
        report.warnings.append(f"git commit differs: archived {manifest['git']['commit']}, "
                               f"current {cur['commit']}")

    spec = parse_sheet(manifest["spec_source"])
    run = engine.generate(spec, int(manifest["master_seed"]), only=only)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = render.write_sources(run, out_dir)

    archived = {v["key"]: v for v in manifest["variants"]}
    for v in run.variants:
        report.checked.append(v.key)
        if archived.get(v.key, {}).get("digest") != variant_digest(v):
            report.identical = False
            report.mismatches.append(f"variant {v.key}")
    if only is None:
        if set(archived) != {v.key for v in run.variants}:
            report.identical = False
            report.mismatches.append("variant list")
        for name, path in files.items():
            if manifest["files"].get(name) != sha256_file(path):
                report.identical = False
                report.mismatches.append(name)
    return report
