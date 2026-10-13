"""Service layer used by the CLI and the web app."""

from pathlib import Path

import pytest

from taskgen import render, service
from taskgen.core import audit, registry

from .conftest import SHEETS

SMALL = """
id: test-small
kind: individual
title: T
preset: sem2
budget: {min: 2, max: 4}
groups:
  - {name: "A", count: 3}
  - {name: "Б 2", students: [Иванов, Петров]}
slots:
  - tasks: [dlp.shanks, powmod.binary_mod]
  - topics: [ecc]
"""


def test_list_tasks_filters():
    all_ = service.list_tasks()
    assert len(all_) == len(registry.all_tasks())
    dlp = service.list_tasks(topics=["dlp"])
    assert {t["id"] for t in dlp} == {"dlp.shanks", "dlp.pohlig_hellman", "dlp.index_calculus"}
    assert all(t["complexity"] == 1 for t in service.list_tasks(complexity=[1]))
    assert {t["id"] for t in service.list_tasks(family="montgomery")} >= {"arithmetic.montgomery_mul"}
    assert [t["id"] for t in service.list_tasks(text="Шенкс")] == ["dlp.shanks"]


def test_task_info_has_source_location():
    info = service.task_info("dlp.shanks")
    assert info["file"] == "taskgen/tasks/dlp/dlp_mod_p.py"
    src = (audit.REPO_ROOT / info["file"]).read_text(encoding="utf-8").splitlines()
    assert src[info["line_start"] - 1].startswith("class Shanks(")
    assert info["line_end"] > info["line_start"]
    assert info["preset_values"]["default"]["primes"]
    assert r"\VAR{g}" in info["statement"]


def test_topics_counts():
    t = {x["slug"]: x for x in service.topics()}
    assert t["dlp"]["count"] == 3 and t["dlp.generic"]["depth"] == 1


def test_preview_seeded_and_template_override():
    a = service.preview("powmod.binary_mod@sem2", seed=5, count=2)
    b = service.preview("powmod.binary_mod@sem2", seed=5, count=2)
    assert a == b and a[0].seed == 5 and a[1].seed != 5
    c = service.preview("dlp.shanks", seed=1, statement=r"Найти $x$: \VAR{g}^x = \VAR{h}.")
    assert c[0].statement.startswith("Найти $x$:")
    tex = service.preview_tex(a)
    assert r"\documentclass" in tex and tex.count(r"\item") == 2


def test_validate_structured():
    rep = service.validate("crypto.lcg", count=3)
    assert rep.ok and [r.ref for r in rep.results] == ["crypto.lcg", "crypto.lcg@sem2"]
    d = service.validation_dict(rep)
    assert d["ok"] and d["results"][0]["error"] is None


def test_validate_reports_failure(monkeypatch):
    cls = registry.task_class("dlp.shanks")

    def bad(self, p):
        raise AssertionError("boom")

    monkeypatch.setattr(cls, "check", bad)
    rep = service.validate("dlp.shanks", count=2)
    assert not rep.ok
    (r,) = rep.results
    assert "boom" in r.error and r.seed is not None and "Traceback" in r.traceback


def test_check_sheet_text():
    assert service.check_sheet_text(SMALL) == []
    assert service.check_sheet_text("id: x\nkind: classroom\ntitle: t\nsections: "
                                    "[{title: s, tasks: [nope.task]}]")[0].startswith("sections[0]")
    assert service.check_sheet_text("kind: [") != []
    probs = service.check_sheet_text("id: x\nkind: individual\ntitle: t\n")
    assert any(p.startswith("individual.groups") for p in probs)


def test_schema_has_both_kinds():
    s = service.sheet_schema()
    assert {"ClassroomSheet", "IndividualSheet"} <= set(s["$defs"])
    assert s["discriminator"]["propertyName"] == "kind"


def test_generate_draft_per_group(tmp_path):
    res = service.generate(SMALL, seed=3, draft=True, out_dir=tmp_path / "d")
    assert res.files == ["tasks-a.tex", "tasks_solutions-a.tex",
                         "tasks-b-2.tex", "tasks_solutions-b-2.tex"]
    d = service.gen_dict(res)
    assert d["master_seed"] == 3 and len(d["variants"]) == 5
    assert d["variants"][3]["student"] == "Иванов"
    assert "Иванов" in (tmp_path / "d" / "tasks-b-2.tex").read_text(encoding="utf-8")


def test_generate_draft_clears_stale_files(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "DRAFTS_DIR", tmp_path)
    (tmp_path / "test-small").mkdir()
    (tmp_path / "test-small" / "tasks-old.pdf").write_bytes(b"x")
    res = service.generate(SMALL, seed=3, draft=True)
    assert res.out_dir == tmp_path / "test-small"
    assert not (res.out_dir / "tasks-old.pdf").exists()


def test_generate_issue_and_regen(monkeypatch, tmp_path):
    monkeypatch.setattr(audit, "ARCHIVE_DIR", tmp_path / "archive")
    res = service.generate(SMALL, seed=11, spec_path="sheets/x.yaml")
    assert not res.draft and res.git is not None
    assert res.out_dir.parent == tmp_path / "archive" / "test-small"
    report, out = service.regen(res.out_dir, out_dir=tmp_path / "regen")
    assert report.identical, report.mismatches
    one, _ = service.regen(res.out_dir, only={"Б 2/1"}, out_dir=tmp_path / "one")
    assert one.identical and one.checked == ["Б 2/1"]


def test_cli_and_service_issue_identical(monkeypatch, tmp_path):
    """The CLI is a wrapper: same sheet + seed -> byte-identical sources and variants."""
    from click.testing import CliRunner

    from taskgen.cli import main

    monkeypatch.setattr(audit, "ARCHIVE_DIR", tmp_path / "archive")
    sheet = SHEETS / "sem2" / "seminar-demo.yaml"
    r = CliRunner().invoke(main, ["gen", str(sheet), "--seed", "8", "--quiet"])
    assert r.exit_code == 0, r.output
    cli_dir = Path(r.output.strip().splitlines()[-1])
    cli_dir = cli_dir if cli_dir.is_absolute() else audit.REPO_ROOT / cli_dir
    res = service.generate(sheet.read_text(encoding="utf-8"), seed=8,
                           spec_path="sheets/sem2/seminar-demo.yaml")
    a, b = audit.load_manifest(cli_dir), audit.load_manifest(res.out_dir)
    assert a["variants"] == b["variants"] and a["files"] == b["files"]
    assert a["spec_path"] == b["spec_path"]


def test_variant_stats():
    st = service.variant_stats(SMALL, seed=1)
    assert st["variants"] == 5
    assert sum(st["total_complexity"].values()) == 5
    assert all(2 <= int(k) <= 4 for k in st["total_complexity"])
    assert sum(c["count"] for c in st["slots"][0]["candidates"]) == 5
    big = service.variant_stats((SHEETS / "sem1" / "kontrolnaya.yaml").read_text(encoding="utf-8"),
                                samples=200)
    assert big["variants"] == 200 and big["family_skips"] > 0
    with pytest.raises(ValueError):
        service.variant_stats((SHEETS / "sem2" / "seminar-demo.yaml").read_text(encoding="utf-8"))


def test_render_output_files_unique_slugs():
    from taskgen.core import engine
    from taskgen.core.sheet import parse_sheet

    spec = parse_sheet(SMALL.replace('"A"', '"б 2"'))
    files = render.output_files(engine.generate(spec, 1))
    assert [f for f, _, _ in files] == ["tasks-b-2.tex", "tasks_solutions-b-2.tex",
                                        "tasks-b-2-2.tex", "tasks_solutions-b-2-2.tex"]
