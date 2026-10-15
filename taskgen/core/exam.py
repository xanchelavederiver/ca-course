"""Exam question lists (``materials/semN/exam/questions.yaml``), Plan 4.

The YAML is the source of the question sheets; ``render`` writes
``questions-body.tex``, which both ``questions.tex`` (plain list) and
``questions-refs.tex`` (with references, class option ``refs``) ``\\input``::

    title: Вопросы на зачёт
    genitive: вопросов на зачёт          # «Ссылки на источники для <genitive> ...»
    date: декабрь 2026
    sheet: sheets/sem1/zachet.yaml       # optional: the written exam task sheet
    literature: [knuth-taocp2, welschenbach]   # ca-refs.bib keys, in list order
    topics:
      - title: Арифметика больших чисел и операции в $\\Zn{n}$
        questions:
          - id: sem1:1
            text: Школьные алгоритмы ...
            refs: [{key: knuth-taocp2, loc: Раздел 4.3}, {text: не скажу ☺}]
            topics: [arithmetic.division]   # task taxonomy (sheet coverage)
          - id: sem1:14
            text: [part for 14, part for 15]  # a combined question «14-15» (span 2)
            lectures: [7]                     # optional, checked against course.yaml

The literature numbers are not typed anywhere: the class cites the entries
with biblatex (``\\nocite`` in the order of ``literature``, ``\\cite[loc]{key}``
in the references), so the list and the citation labels come from one source.

``coverage`` maps the questions to the slots of the exam task sheet (by
taxonomy topics), and ``check`` reports problems (used by ``taskgen course check``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

REPO_ROOT = Path(__file__).resolve().parents[2]
BIB_FILE = REPO_ROOT / "latex" / "ca-refs.bib"
QID = re.compile(r"^sem(\d+):(\d+)$")


def questions_path(sem: int) -> str:
    return f"materials/sem{sem}/exam/questions.yaml"


def body_path(sem: int) -> str:
    return f"materials/sem{sem}/exam/questions-body.tex"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Ref(_Model):
    key: str | None = None
    loc: str | None = None
    text: str | None = None
    sep: str = ", "      # printed before this reference (not before the first one)

    @model_validator(mode="after")
    def _one(self) -> "Ref":
        if (self.key is None) == (self.text is None):
            raise ValueError("a reference needs exactly one of 'key' or 'text'")
        if self.loc is not None and self.key is None:
            raise ValueError("'loc' needs 'key'")
        return self

    def tex(self) -> str:
        if self.text is not None:
            return self.text
        return f"\\cite[{self.loc}]{{{self.key}}}" if self.loc else f"\\cite{{{self.key}}}"


class Question(_Model):
    id: str = Field(pattern=QID.pattern)
    text: str | list[str]
    span: int | None = Field(default=None, ge=1)
    refs: list[Ref] = []
    lectures: list[int] | None = None
    topics: list[str] | None = None
    new: bool = False

    @model_validator(mode="after")
    def _span(self) -> "Question":
        if isinstance(self.text, list):
            if not self.text:
                raise ValueError(f"{self.id}: empty text")
            if self.span is None:
                self.span = len(self.text)
            elif self.span != len(self.text):
                raise ValueError(f"{self.id}: span {self.span} != {len(self.text)} text parts")
        elif self.span is None:
            self.span = 1
        return self

    @property
    def sem(self) -> int:
        return int(QID.match(self.id).group(1))  # type: ignore[union-attr]

    @property
    def first(self) -> int:
        return int(QID.match(self.id).group(2))  # type: ignore[union-attr]

    @property
    def numbers(self) -> list[int]:
        return list(range(self.first, self.first + (self.span or 1)))

    @property
    def label(self) -> str:
        """«7» or «14-15» (plain text)"""
        n = self.numbers
        return str(n[0]) if len(n) == 1 else f"{n[0]}-{n[-1]}"

    def ids(self) -> list[str]:
        return [f"sem{self.sem}:{k}" for k in self.numbers]


class Topic(_Model):
    title: str
    new: bool = False
    questions: list[Question]


class ExamQuestions(_Model):
    title: str
    genitive: str | None = None
    date: str
    sheet: str | None = None
    literature: list[str] = []
    topics: list[Topic]

    @model_validator(mode="after")
    def _numbering(self) -> "ExamQuestions":
        expect = 1
        sems = {q.sem for q in self.questions()}
        if len(sems) > 1:
            raise ValueError(f"questions of several semesters: {sorted(sems)}")
        for q in self.questions():
            if q.first != expect:
                raise ValueError(f"question {q.id}: expected number {expect} (numbering must be "
                                 f"consecutive, a combined question takes `span` numbers)")
            expect += q.span or 1
        dup = sorted({k for k in self.literature if self.literature.count(k) > 1})
        if dup:
            raise ValueError(f"duplicate literature keys: {', '.join(dup)}")
        for q in self.questions():
            for r in q.refs:
                if r.key is not None and r.key not in self.literature:
                    raise ValueError(f"question {q.id}: reference {r.key!r} is not in `literature`")
        return self

    def questions(self) -> list[Question]:
        return [q for t in self.topics for q in t.questions]

    @property
    def count(self) -> int:
        return sum(q.span or 1 for q in self.questions())


def load(path: str | Path) -> ExamQuestions:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return ExamQuestions.model_validate(data)


def load_sem(sem: int, repo: Path = REPO_ROOT) -> ExamQuestions | None:
    p = repo / questions_path(sem)
    return load(p) if p.exists() else None


def bib_keys(path: Path = BIB_FILE) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"^\s*@\w+\s*\{\s*([^,\s]+)\s*,", text, flags=re.M))


# --- rendering -------------------------------------------------------------------------

def _refs_tex(refs: list[Ref]) -> str:
    out = ""
    for i, r in enumerate(refs):
        out += ("" if i == 0 else r.sep) + r.tex()
    return out


def render(exam: ExamQuestions, source: str = "questions.yaml") -> str:
    """The shared body of questions.tex / questions-refs.tex."""
    lines = [
        f"% Generated by `taskgen exam render` from {source}.",
        "% Do not edit: change questions.yaml and run `taskgen exam render` (or `make exams`).",
        f"\\examtitle[{exam.genitive or exam.title}]{{{exam.title}}}{{{exam.date}}}",
    ]
    if exam.literature:
        lines.append(f"\\examliterature{{{','.join(exam.literature)}}}")
    for t in exam.topics:
        lines += ["", f"\\topic{{{t.title}}}"]
        for q in t.questions:
            refs = _refs_tex(q.refs)
            tag = f"  % {q.id}" + (" (new)" if q.new else "")
            if isinstance(q.text, list):
                n = q.numbers
                lines.append(f"\\begin{{questiongroup}}{{{n[0]}}}{{{n[-1]}}}{{{refs}}}{tag}")
                lines += [f"  \\qpart{{{part}}}" for part in q.text]
                lines.append("\\end{questiongroup}")
            else:
                num = q.label.replace("-", "--")
                lines.append(f"\\question{{{num}}}{{{q.text}}}{{{refs}}}{tag}")
    return "\n".join(lines) + "\n"


@dataclass
class RenderResult:
    sem: int
    path: str
    status: str   # ok | written | stale | missing


def render_all(course, repo: Path = REPO_ROOT, sem: int | None = None,
               write: bool = True) -> list[RenderResult]:
    """Render every semester's questions.yaml (``write=False``: only compare)."""
    out = []
    for s in course.semesters:
        if sem is not None and s.n != sem:
            continue
        exam = load_sem(s.n, repo)
        if exam is None:
            if sem is not None:
                out.append(RenderResult(s.n, questions_path(s.n), "missing"))
            continue
        text = render(exam, questions_path(s.n))
        p = repo / body_path(s.n)
        if p.exists() and p.read_text(encoding="utf-8") == text:
            status = "ok"
        elif write:
            p.write_text(text, encoding="utf-8")
            status = "written"
        else:
            status = "stale"
        out.append(RenderResult(s.n, body_path(s.n), status))
    return out


# --- coverage by the exam task sheet ---------------------------------------------------

def question_topics(q: Question, course_sem) -> list[str]:
    """Explicit ``topics``, else the topics of the lectures covering the question."""
    if q.topics is not None:
        return q.topics
    ids = set(q.ids())
    out: list[str] = []
    for lec in course_sem.lectures:
        if ids & set(lec.exam_questions):
            out += [t for t in lec.topics if t not in out]
    return out


@dataclass
class QuestionCoverage:
    question: Question
    topics: list[str]
    slots: list[str] = field(default_factory=list)   # titles of the slots covering it
    tasks: list[str] = field(default_factory=list)   # task ids (of those slots) on its topics

    @property
    def covered(self) -> bool:
        return bool(self.slots)


def coverage(exam: ExamQuestions, course_sem, repo: Path = REPO_ROOT) -> list[QuestionCoverage]:
    """For every question: the slots of ``exam.sheet`` whose pools contain a task on one
    of the question's topics."""
    from taskgen.core import registry
    from taskgen.core.sheet import IndividualSheet, load_sheet, slot_candidates

    spec, _ = load_sheet(repo / exam.sheet) if exam.sheet else (None, "")
    pools: list[tuple[str, list]] = []
    if isinstance(spec, IndividualSheet):
        for i, slot in enumerate(spec.slots):
            pools.append((slot.title or f"slot {i + 1}", slot_candidates(slot, spec.preset)))
    out = []
    for q in exam.questions():
        qc = QuestionCoverage(q, question_topics(q, course_sem))
        for title, tasks in pools:
            hit = [t.id for t in tasks if qc.topics and registry.topic_matches(t.topics, qc.topics)]
            if hit:
                qc.slots.append(title)
                qc.tasks += [t for t in hit if t not in qc.tasks]
        out.append(qc)
    return out


# --- checks ----------------------------------------------------------------------------

def check(course, repo: Path = REPO_ROOT) -> list[tuple[str, str, str]]:
    """``(level, where, message)`` problems of the exam question lists vs course.yaml,
    the bibliography, the taxonomy, the tasks and the exam task sheets."""
    from taskgen.core import registry
    from taskgen.core.taxonomy import check_topic

    probs: list[tuple[str, str, str]] = []
    keys = bib_keys(repo / "latex" / "ca-refs.bib") if (repo / "latex" / "ca-refs.bib").exists() else None
    for s in course.semesters:
        where = questions_path(s.n)
        try:
            exam = load_sem(s.n, repo)
        except Exception as e:
            probs.append(("error", where, f"invalid: {e}"))
            continue
        if exam is None:
            if s.exam_questions:
                probs.append(("warning", where, "missing (the exam question list)"))
            continue
        if exam.count != s.exam_questions:
            probs.append(("error", where, f"{exam.count} question numbers, course.yaml says "
                                          f"exam_questions: {s.exam_questions}"))
        if keys is not None:
            for k in exam.literature:
                if k not in keys:
                    probs.append(("error", where, f"literature key {k!r} not in latex/ca-refs.bib"))
        # lectures: course.yaml exam_questions vs questions.yaml `lectures`
        by_q: dict[str, set[int]] = {}
        for lec in s.lectures:
            for qid in lec.exam_questions:
                by_q.setdefault(qid, set()).add(lec.n)
        for q in exam.questions():
            # (numbers no lecture covers are reported by course.check itself)
            mapped = set().union(*(by_q.get(i, set()) for i in q.ids()))
            if q.lectures is not None and set(q.lectures) != mapped:
                probs.append(("error", where, f"question {q.label}: lectures {sorted(q.lectures)} "
                                              f"!= course.yaml {sorted(mapped)}"))
            for t in q.topics or []:
                if check_topic(t):
                    probs.append(("error", where, f"question {q.label}: topic {t!r} not in taxonomy"))
            topics = question_topics(q, s)
            if not topics:
                probs.append(("warning", where, f"question {q.label}: no task topics"))
            elif not any(registry.tasks_matching([t]) for t in topics if not check_topic(t)):
                probs.append(("warning", where, f"question {q.label}: topics {', '.join(topics)} "
                                                f"have no tasks"))
        for lec in s.lectures:
            if not lec.exam_questions and not lec.draft and lec.topics:
                probs.append(("warning", lec.dir(s.n), "lecture has no exam questions"))
        # generated body up to date
        bp = repo / body_path(s.n)
        if not bp.exists() or bp.read_text(encoding="utf-8") != render(exam, questions_path(s.n)):
            probs.append(("error", body_path(s.n), "stale or missing (taskgen exam render)"))
        # coverage of the questions by the exam task sheet
        if exam.sheet:
            if not (repo / exam.sheet).exists():
                probs.append(("warning", where, f"exam sheet {exam.sheet} missing"))
                continue
            try:
                cov = coverage(exam, s, repo)
            except Exception as e:
                probs.append(("error", exam.sheet, f"invalid sheet: {e}"))
                continue
            for qc in cov:
                if not qc.covered and qc.topics:
                    probs.append(("warning", exam.sheet, f"no slot covers question {qc.question.label} "
                                                         f"({', '.join(qc.topics)})"))
    return probs
