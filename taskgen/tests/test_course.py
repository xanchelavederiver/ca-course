"""Course map (course.yaml): schema, checks, scaffolding, worked examples, books."""

import shutil
from pathlib import Path

import pytest
import yaml

from taskgen.core import course as c

REPO = Path(__file__).resolve().parents[2]

MINI = {
    "semesters": [{
        "n": 1, "title": "Тест", "exam_questions": 2,
        "lectures": [
            {"n": 1, "slug": "intro", "title": "Введение", "topics": ["arithmetic.multiplication"],
             "exam_questions": ["sem1:1"]},
            {"n": 2, "slug": "more", "title": "Ещё", "exam_questions": ["sem1:2"], "draft": True},
        ],
        "seminars": [{"n": 1, "slug": "first", "title": "Первый", "lectures": [1]}],
    }],
}


@pytest.fixture
def mini_repo(tmp_path):
    """A repo skeleton with the material templates and a small course map."""
    for d in ("materials/sem1/lectures/00-template", "materials/sem1/seminars/00-template"):
        shutil.copytree(REPO / d, tmp_path / d)
    (tmp_path / "course.yaml").write_text(yaml.safe_dump(MINI, allow_unicode=True), encoding="utf-8")
    return tmp_path


def errors(probs):
    return [str(p) for p in probs if p.level == "error"]


def test_real_course_map_loads():
    crs = c.load_course()
    assert [s.n for s in crs.semesters] == [1, 2]
    assert all(s.lectures and s.seminars for s in crs.semesters)
    # every exam question of both lists is covered by a lecture
    probs = c.check(crs, examples_stale=False)
    assert not [p for p in probs if "not covered by any lecture" in p.message and p.level == "error"]


def test_schema_rejects_duplicates_and_bad_slugs():
    bad = yaml.safe_load(yaml.safe_dump(MINI))
    bad["semesters"][0]["lectures"][1]["n"] = 1
    with pytest.raises(ValueError, match="duplicate lecture n"):
        c.Course.model_validate(bad)
    bad = yaml.safe_load(yaml.safe_dump(MINI))
    bad["semesters"][0]["lectures"][0]["slug"] = "Bad Slug"
    with pytest.raises(ValueError):
        c.Course.model_validate(bad)


def test_check_reports_missing_and_scaffold_fixes_it(mini_repo):
    crs = c.load_course(mini_repo / "course.yaml")
    probs = c.check(crs, mini_repo, examples_stale=False)
    errs = errors(probs)
    assert any("01-intro" in e and "directory missing" in e for e in errs)
    assert any("01-first" in e and "handout.tex missing" in e for e in errs)
    # the draft lecture only warns
    assert not any("02-more" in e for e in errs)
    assert any("02-more" in str(p) for p in probs if p.level == "warning")

    created = c.scaffold(crs, mini_repo)
    assert "materials/sem1/lectures/01-intro" in created
    assert "sheets/sem1/seminar-01-first.yaml" in created
    body = (mini_repo / "materials/sem1/lectures/01-intro/notes-body.tex").read_text(encoding="utf-8")
    assert r"\begin{lecture}{1}{Введение}" in body
    handout = (mini_repo / "materials/sem1/seminars/01-first/handout.tex").read_text(encoding="utf-8")
    assert r"\seminar{1}{Первый}" in handout
    sheet = yaml.safe_load((mini_repo / "sheets/sem1/seminar-01-first.yaml").read_text(encoding="utf-8"))
    assert sheet["kind"] == "classroom" and "arithmetic.karatsuba" in sheet["sections"][0]["tasks"]
    assert c.scaffold(crs, mini_repo) == []  # idempotent
    errs = errors(c.check(crs, mini_repo, examples_stale=False))
    assert errs == [], errs


def test_check_questions_topics_and_labels(mini_repo):
    data = yaml.safe_load((mini_repo / "course.yaml").read_text(encoding="utf-8"))
    data["semesters"][0]["exam_questions"] = 3
    data["semesters"][0]["lectures"][0]["topics"] = ["no.such.topic"]
    data["semesters"][0]["lectures"][0]["exam_questions"] = ["sem1:1", "sem1:9", "sem9:1", "q1"]
    crs = c.Course.model_validate(data)
    c.scaffold(crs, mini_repo)
    body = mini_repo / "materials/sem1/lectures/02-more/notes-body.tex"
    body.write_text(body.read_text(encoding="utf-8").replace("l2:fermat", "dup"), encoding="utf-8")
    body1 = mini_repo / "materials/sem1/lectures/01-intro/notes-body.tex"
    body1.write_text(body1.read_text(encoding="utf-8").replace("l1:fermat", "dup"), encoding="utf-8")
    errs = "\n".join(errors(c.check(crs, mini_repo, examples_stale=False)))
    assert "topic 'no.such.topic' not in taxonomy" in errs
    assert "sem1:9" in errs and "out of range" in errs
    assert "sem9:1" in errs and "q1" in errs
    assert "exam question sem1:3 is not covered" in errs
    assert "label 'dup' also used" in errs


def test_worked_examples_roundtrip(mini_repo):
    crs = c.load_course(mini_repo / "course.yaml")
    c.scaffold(crs, mini_repo)
    d = mini_repo / "materials/sem1/lectures/01-intro"
    (d / "examples.yaml").write_text("- {name: kar, task: arithmetic.karatsuba, seed: 3, title: Пример}\n",
                                     encoding="utf-8")
    assert c.examples(crs, mini_repo, write=False) == [("materials/sem1/lectures/01-intro/examples/kar.tex",
                                                        "stale")]
    assert c.examples(crs, mini_repo)[0][1] == "written"
    text = (d / "examples/kar.tex").read_text(encoding="utf-8")
    assert text.startswith("% Generated") and r"\begin{example}[Пример]\label{ex:kar}" in text
    assert c.examples(crs, mini_repo, write=False)[0][1] == "ok"
    probs = c.check(crs, mini_repo)
    assert any("not \\input in notes-body.tex" in p.message for p in probs)
    (d / "examples/kar.tex").write_text("edited", encoding="utf-8")
    assert any("stale" in p.message for p in c.check(crs, mini_repo))


def test_documents_sheets_and_book(mini_repo):
    crs = c.load_course(mini_repo / "course.yaml")
    assert c.documents(crs) == ["materials/sem1/lectures/01-intro/notes.tex",
                                "materials/sem1/lectures/01-intro/slides.tex",
                                "materials/sem1/lectures/02-more/notes.tex",
                                "materials/sem1/lectures/02-more/slides.tex",
                                "materials/sem1/seminars/01-first/handout.tex"]
    assert c.sheets(crs) == ["sheets/sem1/seminar-01-first.yaml"]
    c.scaffold(crs, mini_repo)
    book = c.write_book(crs, 1, mini_repo)
    text = book.read_text(encoding="utf-8")
    assert book == mini_repo / "build/materials/sem1/notes-book.tex"
    assert r"\documentclass[book]{ca-notes}" in text
    assert text.index("01-intro") < text.index("02-more")
    assert r"\subimport{../../../materials/sem1/lectures/01-intro/}{notes-body}" in text
