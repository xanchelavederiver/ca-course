"""The regenerated 1st-semester контрольная matches the legacy document structure.

Fixture ``fixtures/legacy-sem1-tasks.tex`` is the output of the legacy
``main-1sem.py`` (5 variants per group, fixed seed). We compare the document
skeleton and, slot by slot, the task statements with all numbers masked.
"""

import re
from pathlib import Path

from taskgen import render
from taskgen.core import engine, tex
from taskgen.core.rng import make_rng
from taskgen.core.sheet import load_sheet, slot_candidates

from .conftest import SHEETS

LEGACY = Path(__file__).parent / "fixtures" / "legacy-sem1-tasks.tex"


def skeleton(s: str) -> str:
    return " ".join(re.sub(r"\d+", "N", s).split())


def parse(doc: str):
    """-> [(section title, [[item, ...] per subsection])]"""
    body = doc.split(r"\begin{document}", 1)[1]
    out = []
    for sec in re.split(r"\\section\{", body)[1:]:
        title = sec.split("}", 1)[0]
        subs = []
        for sub in re.split(r"\\subsection\{Вариант \d+\}", sec)[1:]:
            enum = sub.split(r"\begin{enumerate}", 1)[1].split(r"\end{enumerate}", 1)[0]
            subs.append([i.strip() for i in re.split(r"\\item\s", enum)[1:]])
        out.append((title, subs))
    return out


def test_structure_matches_legacy():
    spec, _ = load_sheet(SHEETS / "sem1" / "kontrolnaya.yaml")
    new_doc = render.render_sheet(engine.generate(spec, 2026), solutions=False)
    legacy, new = parse(LEGACY.read_text(encoding="utf-8")), parse(new_doc)

    assert [t for t, _ in new] == [t for t, _ in legacy] == [
        "Варианты группы 6411", "Варианты группы 6412", "Варианты группы 6413"]
    assert all(len(v) == 7 for _, subs in legacy + new for v in subs)
    assert [len(subs) for _, subs in new] == [42, 42, 42]
    for marker in (r"\tableofcontents", r"\clearpage"):
        assert marker in new_doc

    # Slot by slot, every legacy statement shape is one the new sheet can produce.
    shapes = []
    for k, slot in enumerate(spec.slots):
        cands = slot_candidates(slot, spec.preset)
        shapes.append({skeleton(t.generate(make_rng(k, t.id, i)).statement)
                       for t in cands for i in range(30)})
    for _, subs in legacy:
        for items in subs:
            for k, item in enumerate(items):
                assert skeleton(item) in shapes[k], f"slot {k}: {item[:80]}"


def test_new_items_are_valid_latex():
    spec, _ = load_sheet(SHEETS / "sem1" / "kontrolnaya.yaml")
    doc = render.render_sheet(engine.generate(spec, 1, only={"6411/1"}), solutions=True)
    assert tex.latex_problems(doc.split(r"\begin{document}")[1]) == []
