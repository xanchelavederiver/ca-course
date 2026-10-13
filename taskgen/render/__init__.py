"""Rendering of generated sheets to LaTeX.

PDFs are built by the `latex` container (scripts/latex-build.sh, see Makefile).

Output layouts (recorded as ``layout`` in the run manifest):

* ``per-group`` (current) — classroom sheets: ``tasks.tex`` + ``tasks_solutions.tex``;
  individual sheets: one pair ``tasks-<group>.tex`` + ``tasks_solutions-<group>.tex``
  per group, each with its own title, ToC and that group's variants;
* ``combined`` (engine < 0.3, manifests without ``layout``) — one
  ``tasks.tex`` + ``tasks_solutions.tex`` with all groups.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from taskgen.core import tex
from taskgen.core.engine import SheetRun, Variant
from taskgen.core.sheet import ClassroomSheet

SHEET_FILE = "tasks.tex"
SOLUTIONS_FILE = "tasks_solutions.tex"
SHEET_STEM = "tasks"
SOLUTIONS_STEM = "tasks_solutions"

LAYOUT_PER_GROUP = "per-group"
LAYOUT_COMBINED = "combined"
LAYOUTS = (LAYOUT_PER_GROUP, LAYOUT_COMBINED)

_TRANSLIT = dict(zip(
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "i", "k", "l", "m", "n", "o", "p",
     "r", "s", "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "", "y", "", "e", "yu", "ya"]))


def slugify(name: str) -> str:
    """File-name-safe ASCII slug of a group name ("6411" -> "6411", "Группа А" -> "gruppa-a")."""
    s = "".join(_TRANSLIT.get(c, c) for c in name.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "group"


@dataclass
class _Group:
    name: str
    variants: list[Variant]


@dataclass
class _Section:
    title: str
    intro: str | None
    instances: list


def _groups(run: SheetRun) -> list[_Group]:
    groups: dict[str, _Group] = {}
    for v in run.variants:
        groups.setdefault(v.vkey.group or "", _Group(v.vkey.group or "", [])).variants.append(v)
    return list(groups.values())


def render_sheet(run: SheetRun, solutions: bool, group: str | None = None) -> str:
    """Render the sheet (or solution manual) of ``run``.

    For individual sheets ``group`` selects one group (per-group layout: the
    group name is added to the title); ``None`` renders all groups.
    """
    spec = run.spec
    ctx: dict = {"spec": spec, "doc": spec.document, "solutions": solutions,
                 "master_seed": run.master_seed, "group_title": None}
    if isinstance(spec, ClassroomSheet):
        default_template = "classroom.tex.j2"
        (variant,) = run.variants
        it = iter(variant.instances)
        ctx["sections"] = [_Section(s.title, s.intro, [next(it) for _ in s.tasks])
                           for s in spec.sections]
    else:
        default_template = "individual.tex.j2"
        groups = _groups(run)
        if group is not None:
            groups = [g for g in groups if g.name == group]
            if not groups:
                raise KeyError(f"no variants of group {group!r} in this run")
            ctx["group_title"] = group
        ctx["groups"] = groups
    template = tex.env().get_template(spec.template or default_template)
    return template.render(**ctx)


def output_files(run: SheetRun, layout: str = LAYOUT_PER_GROUP) -> list[tuple[str, bool, str | None]]:
    """``[(file name, solutions?, group or None)]`` written for ``run`` in ``layout``."""
    if layout not in LAYOUTS:
        raise ValueError(f"unknown layout {layout!r}")
    if layout == LAYOUT_COMBINED or isinstance(run.spec, ClassroomSheet):
        return [(SHEET_FILE, False, None), (SOLUTIONS_FILE, True, None)]
    out, used = [], set()
    for g in _groups(run):
        slug, n = slugify(g.name), 1
        while slug in used:
            n += 1
            slug = f"{slugify(g.name)}-{n}"
        used.add(slug)
        out += [(f"{SHEET_STEM}-{slug}.tex", False, g.name),
                (f"{SOLUTIONS_STEM}-{slug}.tex", True, g.name)]
    return out


def write_sources(run: SheetRun, out_dir: Path, layout: str = LAYOUT_PER_GROUP) -> dict[str, Path]:
    """Write the LaTeX sources of ``run``; returns ``{file name: path}`` in build order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, sol, group in output_files(run, layout):
        path = out_dir / name
        path.write_text(render_sheet(run, solutions=sol, group=group), encoding="utf-8")
        files[name] = path
    return files
