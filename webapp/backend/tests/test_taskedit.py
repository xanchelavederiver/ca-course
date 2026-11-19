"""ast/libcst metadata round trip: edits touch only the edited attribute."""

import ast
import difflib

import pytest

from taskgen_web import taskedit

from .conftest import REPO

DLP = (REPO / "taskgen/tasks/dlp/dlp_mod_p.py").read_text(encoding="utf-8")
MUL = (REPO / "taskgen/tasks/arithmetic/multiplication.py").read_text(encoding="utf-8")


def changed_lines(a: str, b: str) -> list[str]:
    return [line for line in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
            if line[:1] in "+-" and not line.startswith(("+++", "---"))]


def test_read_meta_literal_and_computed():
    m = taskedit.read_meta(DLP, "dlp.shanks")
    f = m["fields"]
    assert m["class_name"] == "Shanks"
    assert f["id"]["value"] == "dlp.shanks" and f["complexity"]["value"] == 1
    assert f["topics"]["value"] == ["dlp.generic"]
    assert f["solution_detail"] == {"defined": True, "editable": True, "value": "full",
                                    "expr": "SolutionDetail.FULL"}
    assert not f["statement"]["editable"] and "STATEMENT_HEAD" in f["statement"]["expr"]
    assert not f["presets"]["editable"]
    assert f["family"]["defined"] is False and f["family"]["editable"]


def test_apply_meta_changes_only_that_line():
    out = taskedit.apply_meta(DLP, "dlp.shanks", {"complexity": 2, "title_ru": "Шенкс"})
    assert sorted(changed_lines(DLP, out)) == sorted([
        '-    title_ru = "Алгоритм Шенкса (baby-step giant-step)"',
        '-    complexity = 1',
        '+    title_ru = r"Шенкс"',
        '+    complexity = 2',
    ])
    # other tasks in the same module untouched
    assert taskedit.read_meta(out, "dlp.pohlig_hellman") == taskedit.read_meta(DLP, "dlp.pohlig_hellman")


def test_apply_meta_noop_returns_identical_source():
    assert taskedit.apply_meta(DLP, "dlp.shanks", {"complexity": 1, "topics": ["dlp.generic"]}) == DLP


def test_apply_meta_inserts_inherited_field():
    out = taskedit.apply_meta(DLP, "dlp.shanks", {"family": "dlp-generic", "notes": "x"})
    lines = changed_lines(DLP, out)
    assert lines == ['+    family = "dlp-generic"', '+    notes = r"x"']
    assert taskedit.read_meta(out, "dlp.shanks")["fields"]["family"]["value"] == "dlp-generic"


def test_apply_meta_refuses_computed_field():
    with pytest.raises(taskedit.TaskEditError, match="Code tab"):
        taskedit.apply_meta(DLP, "dlp.shanks", {"statement": "x"})


def test_apply_meta_validates_values():
    for values in ({"complexity": 0}, {"topics": []}, {"id": "Bad Id"},
                   {"solution_detail": "partial"}, {"presets": {"x": {}}}):
        with pytest.raises(taskedit.TaskEditError):
            taskedit.apply_meta(DLP, "dlp.shanks", values)


def test_templates_round_trip_long_and_multiline():
    tid = next(t for t in ("arithmetic.karatsuba",) if t)
    meta = taskedit.read_meta(MUL, tid)["fields"]
    assert meta["statement"]["editable"]
    long = r"Вычислить \VAR{a} \cdot \VAR{b} методом Карацубы; " * 6 + r"ответ: $\VAR{answer}$\\"
    multi = "Строка 1\n\\[x = \\VAR{answer}\\]\n"
    for value in (long, multi, 'с "кавычками" и \\', "a\\"):
        out = taskedit.apply_meta(MUL, tid, {"statement": value})
        assert taskedit.read_meta(out, tid)["fields"]["statement"]["value"] == value
        added = (line[1:] for line in changed_lines(MUL, out) if line.startswith("+"))
        assert all(len(line) < 100 for line in added if "Карацубы" in line)


def test_presets_with_arithmetic_are_editable_and_keep_expressions():
    tid = "arithmetic.karatsuba"
    f = taskedit.read_meta(MUL, tid)["fields"]["presets"]
    assert f["editable"] and f["value"] == {"default": {"lo": 10**6 + 1, "hi": 10**8}}
    presets = {"default": {"lo": 10**6 + 1, "hi": 10**9}}
    out = taskedit.apply_meta(MUL, tid, {"presets": presets})
    assert changed_lines(MUL, out) == [
        '-    presets = {"default": {"lo": 10**6 + 1, "hi": 10**8}}',
        '+    presets = {"default": {"lo": 10**6 + 1, "hi": 1000000000}}',
    ]
    big = {"default": {"lo": 10**6 + 1, "hi": 10**8, "list": list(range(30))}, "sem2": {"lo": 5}}
    out = taskedit.apply_meta(MUL, tid, {"presets": big})
    assert taskedit.read_meta(out, tid)["fields"]["presets"]["value"] == big
    assert '"lo": 10**6 + 1' in out and all(len(line) <= 99 for line in out.splitlines()
                                             if "presets" in line or '"list"' in line)
    ast.parse(out)


def test_const_eval_is_safe():
    for src in ("10**10000", "__import__('os')", "len([1])", "x", "2**-1"):
        with pytest.raises((ValueError, TypeError)):
            taskedit.const_eval(ast.parse(src, mode="eval").body)
    assert taskedit.const_eval(ast.parse("-(2**31) + 1", mode="eval").body) == -(2**31) + 1


def test_scaffold_new_and_append():
    new = taskedit.scaffold(None, task_id="dlp.toy", class_name="Toy", title="Игрушка",
                            topic="dlp.generic")
    assert taskedit.read_meta(new, "dlp.toy")["fields"]["topics"]["value"] == ["dlp.generic"]
    appended = taskedit.scaffold(DLP, task_id="dlp.toy", class_name="Toy", title="T", topic="dlp")
    assert appended.startswith(DLP.rstrip("\n"))
    with pytest.raises(taskedit.TaskEditError):
        taskedit.scaffold(DLP, task_id="dlp.toy", class_name="Shanks", title="T", topic="dlp")


def test_index_finds_tasks_and_survives_syntax_errors(tmp_path):
    root = tmp_path / "taskgen" / "tasks" / "x"
    root.mkdir(parents=True)
    f = root / "m.py"
    f.write_text('class A:\n    id = "x.a"\n')
    idx = taskedit.TaskIndex(tmp_path)
    assert idx.find("x.a").file == "taskgen/tasks/x/m.py"
    f.write_text('class A:\n    id = "x.a"\n    def broken(:\n')
    assert idx.find("x.a").class_name == "A"  # last known location kept
    assert "taskgen/tasks/x/m.py" in idx.syntax_errors
