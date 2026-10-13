"""Audit trail: manifest contents, regen reproduces identical output, seal."""

import json
import shutil
from pathlib import Path

from taskgen import render
from taskgen.core import audit, engine
from taskgen.core.sheet import load_sheet

from .conftest import SHEETS


def _issue(tmp_path, sheet="sem2/kontrolnaya.yaml", seed=99):
    spec, source = load_sheet(SHEETS / sheet)
    run = engine.generate(spec, seed)
    return audit.write_run(run, source, f"sheets/{sheet}", tmp_path / "run")


def test_manifest_contents(tmp_path):
    m = audit.load_manifest(_issue(tmp_path))
    assert m["master_seed"] == 99 and m["sheet_id"] == "sem2-kontrolnaya"
    assert {"commit", "dirty"} <= set(m["git"])
    assert m["engine_version"]
    assert m["layout"] == render.LAYOUT_PER_GROUP
    assert set(m["files"]) == {f"{stem}-{g}.tex" for stem in ("tasks", "tasks_solutions")
                               for g in ("6411", "6412", "6413")}
    assert len(m["variants"]) == 126
    v = m["variants"][0]
    assert v["key"] == "6411/1" and len(v["tasks"]) == 5
    assert all("seed" in t and "answer" in t for t in v["tasks"])


def test_regen_identical(tmp_path):
    mpath = _issue(tmp_path)
    report = audit.regen(mpath, tmp_path / "regen")
    assert report.identical, report.mismatches
    for name in audit.load_manifest(mpath)["files"]:
        assert (tmp_path / "regen" / name).read_bytes() == (tmp_path / "run" / name).read_bytes()


def test_regen_single_variant(tmp_path):
    mpath = _issue(tmp_path)
    report = audit.regen(mpath, tmp_path / "one", only={"6413/42"})
    assert report.identical and report.checked == ["6413/42"]
    assert [p.name for p in sorted((tmp_path / "one").glob("*.tex"))] == \
        ["tasks-6413.tex", "tasks_solutions-6413.tex"]
    assert "Вариант 42" in (tmp_path / "one" / "tasks-6413.tex").read_text(encoding="utf-8")


def test_regen_uses_spec_snapshot_and_detects_tampering(tmp_path):
    mpath = _issue(tmp_path)
    m = json.loads(mpath.read_text(encoding="utf-8"))
    m["master_seed"] += 1
    mpath.write_text(json.dumps(m), encoding="utf-8")
    report = audit.regen(mpath, tmp_path / "regen")
    assert not report.identical
    assert "tasks-6411.tex" in report.mismatches


def test_seal_records_pdfs(tmp_path):
    mpath = _issue(tmp_path, "sem2/seminar-demo.yaml")
    assert audit.load_manifest(mpath)["layout"] == render.LAYOUT_PER_GROUP
    assert set(audit.load_manifest(mpath)["files"]) == {render.SHEET_FILE, render.SOLUTIONS_FILE}
    (mpath.parent / "tasks.pdf").write_bytes(b"%PDF-1.5 fake")
    assert audit.seal(mpath.parent) == ["tasks.pdf"]
    assert "tasks.pdf" in audit.load_manifest(mpath)["files"]


def test_new_run_dir_unique(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "ARCHIVE_DIR", tmp_path)
    a = audit.new_run_dir("x")
    a.mkdir(parents=True)
    b = audit.new_run_dir("x")
    assert a != b and a.parent == b.parent


def test_per_group_split_keeps_variant_digests(tmp_path):
    spec, source = load_sheet(SHEETS / "sem1/kontrolnaya.yaml")
    run = engine.generate(spec, 5)
    per_group = audit.load_manifest(audit.write_run(run, source, None, tmp_path / "a"))
    combined = audit.load_manifest(audit.write_run(run, source, None, tmp_path / "b",
                                                   layout=render.LAYOUT_COMBINED))
    assert per_group["variants"] == combined["variants"]
    assert set(combined["files"]) == {render.SHEET_FILE, render.SOLUTIONS_FILE}
    # each group file holds exactly that group's variants, with the group in the title
    doc = (tmp_path / "a" / "tasks-6412.tex").read_text(encoding="utf-8")
    assert r"\section{Варианты группы 6412}" in doc and "6411" not in doc.split(r"\begin{document}")[1]
    assert r"\sheettitle{Контрольная работа. Группа 6412}" in doc
    assert doc.count(r"\subsection{Вариант") == 42
    sol = (tmp_path / "a" / "tasks_solutions-6412.tex").read_text(encoding="utf-8")
    assert r"\sheettitle{Контрольная работа. Группа 6412. Решения}" in sol


def test_regen_legacy_combined_layout(tmp_path):
    """A run archived before the per-group layout (no ``layout`` in its
    manifest, engine 0.2.0) still regenerates byte-identically."""
    fixture = Path(__file__).parent / "fixtures" / "legacy-run"
    run_dir = tmp_path / "legacy-run"
    shutil.copytree(fixture, run_dir)
    assert "layout" not in audit.load_manifest(run_dir)
    report = audit.regen(run_dir / audit.MANIFEST, tmp_path / "regen")
    assert report.identical, report.mismatches
    assert any("engine version differs" in w for w in report.warnings)
    assert sorted(p.name for p in (tmp_path / "regen").glob("*.tex")) == \
        [render.SHEET_FILE, render.SOLUTIONS_FILE]


def test_slugify_group_names():
    assert render.slugify("6411") == "6411"
    assert render.slugify("Группа А-1") == "gruppa-a-1"
    assert render.slugify("!!!") == "group"
