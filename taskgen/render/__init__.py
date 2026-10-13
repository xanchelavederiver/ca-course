"""Rendering of generated sheets to LaTeX.

PDFs are built by the `latex` container (scripts/latex-build.sh, see Makefile).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from taskgen.core import tex
from taskgen.core.engine import SheetRun, Variant
from taskgen.core.sheet import ClassroomSheet

SHEET_FILE = "tasks.tex"
SOLUTIONS_FILE = "tasks_solutions.tex"


@dataclass
class _Group:
    name: str
    variants: list[Variant]


@dataclass
class _Section:
    title: str
    intro: str | None
    instances: list


def render_sheet(run: SheetRun, solutions: bool) -> str:
    spec = run.spec
    ctx: dict = {"spec": spec, "doc": spec.document, "solutions": solutions,
                 "master_seed": run.master_seed}
    if isinstance(spec, ClassroomSheet):
        default_template = "classroom.tex.j2"
        (variant,) = run.variants
        it = iter(variant.instances)
        ctx["sections"] = [_Section(s.title, s.intro, [next(it) for _ in s.tasks])
                           for s in spec.sections]
    else:
        default_template = "individual.tex.j2"
        groups: dict[str, _Group] = {}
        for v in run.variants:
            groups.setdefault(v.vkey.group or "", _Group(v.vkey.group or "", [])).variants.append(v)
        ctx["groups"] = list(groups.values())
    template = tex.env().get_template(spec.template or default_template)
    return template.render(**ctx)


def write_sources(run: SheetRun, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, sol in ((SHEET_FILE, False), (SOLUTIONS_FILE, True)):
        path = out_dir / name
        path.write_text(render_sheet(run, solutions=sol), encoding="utf-8")
        files[name] = path
    return files

