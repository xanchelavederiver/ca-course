"""Engine operations shared by the CLI (``taskgen.cli``) and the web app.

Every function here is a thin, importable wrapper over ``taskgen.core`` that
returns structured data instead of printing, so the command line and the web
UI cannot drift apart. The web app runs these functions in its engine worker
process (``webapp/backend/taskgen_web/worker.py``); results must stay
picklable, and the ``*_dict`` helpers give their JSON form.
"""

from __future__ import annotations

import shutil
import traceback
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

import taskgen
from taskgen import render
from taskgen.core import audit, engine, registry, sampler, taxonomy, tex
from taskgen.core.rng import derive_seed, make_rng, new_master_seed
from taskgen.core.sheet import IndividualSheet, parse_sheet, slot_candidates, variants
from taskgen.core.task import Task, TaskInstance

REPO_ROOT = audit.REPO_ROOT
DRAFTS_DIR = REPO_ROOT / "build" / "sheets"
REGEN_DIR = REPO_ROOT / "build" / "regen"


def rel(p: Path) -> str:
    """Repo-relative path (absolute if outside the repo)."""
    try:
        return str(Path(p).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


# --- tasks & topics ---------------------------------------------------------------

def task_summary(cls: type[Task]) -> dict[str, Any]:
    file, start, end = registry.source_location(cls)
    return {
        "id": cls.id,
        "title": cls.title_ru,
        "topics": list(cls.topics),
        "complexity": cls.complexity,
        "family": cls.family,
        "family_name": cls.family_name(),
        "solution_detail": cls.solution_detail.value,
        "presets": list(cls.presets),
        "notes": cls.notes,
        "module": cls.__module__,
        "class_name": cls.__qualname__,
        "file": rel(Path(file)) if file else None,
        "line_start": start,
        "line_end": end,
    }


def list_tasks(topics: list[str] | None = None, complexity: list[int] | None = None,
               family: str | None = None, text: str | None = None) -> list[dict[str, Any]]:
    """Registered tasks (filters: topic prefixes, complexities, family, substring of id/title)."""
    classes = registry.tasks_matching(topics, complexity) if topics else registry.all_tasks()
    if complexity and not topics:
        classes = [c for c in classes if c.complexity in complexity]
    if family:
        classes = [c for c in classes if c.family_name() == family]
    if text:
        t = text.lower()
        classes = [c for c in classes if t in c.id.lower() or t in c.title_ru.lower()]
    return [task_summary(c) for c in classes]


def task_info(task_id: str) -> dict[str, Any]:
    """Summary plus the effective templates and preset values of a task."""
    cls = registry.task_class(task_id)
    from taskgen.core.task import jsonable

    return {
        **task_summary(cls),
        "statement": cls.statement,
        "solution": cls.solution,
        "preset_values": {name: jsonable(cls(name).cfg.__dict__) for name in cls.presets},
    }


def topics() -> list[dict[str, Any]]:
    """Taxonomy in file order with the number of tasks under each topic."""
    return [{"slug": slug, "title": title, "depth": slug.count("."),
             "count": len(registry.tasks_matching([slug]))}
            for slug, title in taxonomy.taxonomy().items()]


def import_errors() -> dict[str, str]:
    """Task modules that failed to import (non-strict discovery only)."""
    registry.discover()
    return dict(registry.IMPORT_ERRORS)


# --- preview ----------------------------------------------------------------------

def preview_seeds(seed: int, count: int) -> list[int]:
    return [seed if k == 0 else derive_seed(seed, k) for k in range(count)]


def preview(ref: str, seed: int | None = None, count: int = 1,
            statement: str | None = None, solution: str | None = None) -> list[TaskInstance]:
    """``count`` instances of a task; ``statement``/``solution`` override the templates
    (live preview of unsaved edits)."""
    task = registry.get_task(ref)
    if statement is not None:
        task.statement = statement
    if solution is not None:
        task.solution = solution
    base = new_master_seed() if seed is None else seed
    return [task.generate(make_rng(s), seed=s) for s in preview_seeds(base, count)]


def preview_tex(instances: list[TaskInstance], title: str = "Предпросмотр") -> str:
    """A standalone ``ca-sheet`` document with statements and solutions of ``instances``."""
    return tex.env().get_template("preview.tex.j2").render(title=title, instances=instances)


# --- validation -------------------------------------------------------------------

@dataclass
class TaskCheck:
    ref: str
    ok: bool
    error: str | None = None
    traceback: str | None = None
    seed: int | None = None


@dataclass
class ValidationReport:
    results: list[TaskCheck] = field(default_factory=list)
    taxonomy: list[str] = field(default_factory=list)
    import_errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results) and not self.taxonomy and not self.import_errors


def validate(target: str = "all", count: int = 50, seed: int = 0,
             progress: Callable[[TaskCheck, int, int], None] | None = None) -> ValidationReport:
    """Generate ``count`` instances of each task/preset twice: self-checks + determinism.

    ``target`` is ``"all"``, ``"<id>"`` (all presets) or ``"<id>@<preset>"``;
    ``progress(check, done, total)`` is called after each task/preset.
    """
    report = ValidationReport()
    if target == "all":
        report.taxonomy = taxonomy.check_taxonomy()
        report.import_errors = import_errors()
        tasks = [cls(p) for cls in registry.all_tasks() for p in cls.presets]
    else:
        tid, preset = registry.parse_ref(target)
        cls = registry.task_class(tid)
        tasks = [cls(preset)] if preset else [cls(p) for p in cls.presets]
    for n, t in enumerate(tasks, 1):
        s = None
        try:
            for k in range(count):
                s = derive_seed(seed, t.ref, k)
                a = t.generate(make_rng(s), seed=s)
                b = t.generate(make_rng(s), seed=s)
                if a != b:
                    raise AssertionError(f"non-deterministic for seed {s}")
            report.results.append(TaskCheck(t.ref, True))
        except Exception as e:  # report and continue
            report.results.append(TaskCheck(t.ref, False, str(e) or type(e).__name__,
                                            traceback.format_exc(), s))
        if progress is not None:
            progress(report.results[-1], n, len(tasks))
    return report


def validation_dict(report: ValidationReport) -> dict[str, Any]:
    return {"ok": report.ok, "results": [asdict(r) for r in report.results],
            "taxonomy": report.taxonomy, "import_errors": report.import_errors}


# --- sheets -----------------------------------------------------------------------

def check_sheet_text(text: str) -> list[str]:
    """Problems of a sheet spec (YAML text); empty if it is valid."""
    from pydantic import ValidationError

    try:
        parse_sheet(text)
    except ValidationError as e:
        return [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()]
    except ValueError as e:
        msg = str(e)
        prefix = "invalid sheet spec:\n"
        if msg.startswith(prefix):
            return [line.strip() for line in msg[len(prefix):].splitlines() if line.strip()]
        return [msg]
    except Exception as e:  # YAML syntax errors etc.
        return [f"{type(e).__name__}: {e}"]
    return []


def sheet_schema() -> dict[str, Any]:
    """JSON Schema of the sheet spec models (both kinds, discriminated by ``kind``)."""
    from pydantic import TypeAdapter

    from taskgen.core.sheet import Sheet

    return TypeAdapter(Sheet).json_schema()


def sheet_variants(text: str) -> list[dict[str, Any]]:
    spec = parse_sheet(text)
    return [{"key": v.key, "group": v.group, "number": v.number, "student": v.student}
            for v in variants(spec)]


@dataclass
class GenResult:
    run: engine.SheetRun
    out_dir: Path
    manifest_path: Path
    files: list[str]
    draft: bool
    git: dict[str, Any] | None = None


def generate(spec_text: str, seed: int | None = None, draft: bool = False,
             only: set[str] | None = None, spec_path: str | None = None,
             out_dir: Path | None = None) -> GenResult:
    """Generate a sheet run from spec text.

    Drafts (and partial runs with ``only``) go to ``build/sheets/<id>/``, which
    is cleared first; issued runs get a fresh ``archive/<id>/<ts>/``.
    """
    spec = parse_sheet(spec_text)
    master = new_master_seed() if seed is None else seed
    run = engine.generate(spec, master, only=only)
    draft = draft or bool(only)
    git = None
    if out_dir is not None:
        out = out_dir
    elif draft:
        out = DRAFTS_DIR / spec.id
        if out.exists():
            shutil.rmtree(out)
    else:
        out = audit.new_run_dir(spec.id)
        git = audit.git_info()
    manifest = audit.write_run(run, spec_text, spec_path, out)
    files = list(audit.load_manifest(manifest)["files"])
    return GenResult(run, out, manifest, files, draft, git)


def gen_dict(res: GenResult) -> dict[str, Any]:
    return {
        "sheet_id": res.run.spec.id,
        "kind": res.run.spec.kind,
        "master_seed": res.run.master_seed,
        "out_dir": rel(res.out_dir),
        "manifest": rel(res.manifest_path),
        "files": res.files,
        "draft": res.draft,
        "git": res.git,
        "variants": [{"key": v.key, "group": v.vkey.group, "number": v.vkey.number,
                      "student": v.vkey.student,
                      "tasks": [i.ref for i in v.instances]} for v in res.run.variants],
    }


def regen(run_dir: Path, only: set[str] | None = None,
          out_dir: Path | None = None) -> tuple[audit.RegenReport, Path]:
    """Reproduce an archived run (default output: ``build/regen/<sheet-id>/<run>``)."""
    mpath = run_dir / audit.MANIFEST if run_dir.is_dir() else run_dir
    data = audit.load_manifest(mpath)
    out = out_dir or REGEN_DIR / data["sheet_id"] / mpath.parent.name
    return audit.regen(mpath, out, only=only), out


def seal(run_dir: Path) -> list[str]:
    return audit.seal(run_dir)


# --- variant statistics -----------------------------------------------------------

def variant_stats(spec_text: str, seed: int = 0, samples: int | None = None) -> dict[str, Any]:
    """How an individual sheet's slots/budget randomize the variants.

    Runs only the task *selection* (no instance generation) for every variant
    of the sheet (or ``samples`` simulated variants) and reports the
    distribution of total complexity, the per-slot task frequencies and how
    often a candidate was skipped to avoid a family collision.
    """
    spec = parse_sheet(spec_text)
    if not isinstance(spec, IndividualSheet):
        raise ValueError("variant statistics are only defined for individual sheets")
    pools = [slot_candidates(s, spec.preset) for s in spec.slots]
    keys = [v.key for v in variants(spec)] if samples is None else \
        [f"sample/{k}" for k in range(samples)]
    totals: Counter[int] = Counter()
    per_slot: list[Counter[str]] = [Counter() for _ in pools]
    combos: Counter[tuple[str, ...]] = Counter()
    counters: dict[str, int] = {"family_skips": 0}
    for key in keys:
        rng = make_rng(seed, spec.id, key, "select")
        chosen = sampler.select(pools, rng, spec.budget, spec.distinct_families, stats=counters)
        totals[sum(t.complexity for t in chosen)] += 1
        for i, t in enumerate(chosen):
            per_slot[i][t.ref] += 1
        combos[tuple(t.ref for t in chosen)] += 1
    return {
        "variants": len(keys),
        "distinct_combinations": len(combos),
        "max_repeats": max(combos.values(), default=0),
        "family_skips": counters["family_skips"],
        "total_complexity": {str(k): v for k, v in sorted(totals.items())},
        "slots": [{"title": slot.title or f"Слот {i + 1}",
                   "candidates": [{"ref": t.ref, "complexity": t.complexity,
                                   "count": per_slot[i][t.ref]} for t in pool]}
                  for i, (slot, pool) in enumerate(zip(spec.slots, pools))],
    }


def version() -> str:
    return taskgen.__version__
