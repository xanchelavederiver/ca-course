"""Audit trail: manifest contents, regen reproduces identical output, seal."""

import json

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
    assert set(m["files"]) == {render.SHEET_FILE, render.SOLUTIONS_FILE}
    assert len(m["variants"]) == 126
    v = m["variants"][0]
    assert v["key"] == "6411/1" and len(v["tasks"]) == 5
    assert all("seed" in t and "answer" in t for t in v["tasks"])


def test_regen_identical(tmp_path):
    mpath = _issue(tmp_path)
    report = audit.regen(mpath, tmp_path / "regen")
    assert report.identical, report.mismatches
    for name in (render.SHEET_FILE, render.SOLUTIONS_FILE):
        assert (tmp_path / "regen" / name).read_bytes() == (tmp_path / "run" / name).read_bytes()


def test_regen_single_variant(tmp_path):
    mpath = _issue(tmp_path)
    report = audit.regen(mpath, tmp_path / "one", only={"6413/42"})
    assert report.identical and report.checked == ["6413/42"]
    assert "Вариант 42" in (tmp_path / "one" / render.SHEET_FILE).read_text(encoding="utf-8")


def test_regen_uses_spec_snapshot_and_detects_tampering(tmp_path):
    mpath = _issue(tmp_path)
    m = json.loads(mpath.read_text(encoding="utf-8"))
    m["master_seed"] += 1
    mpath.write_text(json.dumps(m), encoding="utf-8")
    report = audit.regen(mpath, tmp_path / "regen")
    assert not report.identical
    assert render.SHEET_FILE in report.mismatches


def test_seal_records_pdfs(tmp_path):
    mpath = _issue(tmp_path, "sem2/seminar-demo.yaml")
    (mpath.parent / "tasks.pdf").write_bytes(b"%PDF-1.5 fake")
    assert audit.seal(mpath.parent) == ["tasks.pdf"]
    assert "tasks.pdf" in audit.load_manifest(mpath)["files"]


def test_new_run_dir_unique(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "ARCHIVE_DIR", tmp_path)
    a = audit.new_run_dir("x")
    a.mkdir(parents=True)
    b = audit.new_run_dir("x")
    assert a != b and a.parent == b.parent
