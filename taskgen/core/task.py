"""Task model.

A task is a class with declarative metadata, LaTeX templates for the
statement and the solution, and a ``sample(rng)`` method that draws the
input values and computes everything the templates need::

    class Karatsuba(Task):
        id = "arithmetic.karatsuba"
        title_ru = "Умножение методом Карацубы"
        topics = ("arithmetic.multiplication",)
        complexity = 1
        presets = {"default": {"lo": 10**6 + 1, "hi": 10**8}}
        statement = r"Вычислить \\[\\VAR{a} \\cdot \\VAR{b}\\] ..."
        solution = r"\\[\\VAR{answer}.\\]"

        def sample(self, rng):
            a = rng.randrange(self.cfg.lo, self.cfg.hi)
            ...
            return {"a": a, "b": b, "answer": a * b}

        def check(self, p):             # optional self-check on the params
            assert p["answer"] == p["a"] * p["b"]

``presets`` hold value-generation settings; the "default" preset is always
present and other presets override it (e.g. "sem2" ranges). A task is
referenced from sheets as ``"<id>"`` or ``"<id>@<preset>"``.
"""

from __future__ import annotations

import numbers
import random
from dataclasses import asdict, dataclass, field
from enum import Enum
from fractions import Fraction
from types import SimpleNamespace
from typing import Any, ClassVar

from taskgen.core import tex


class SolutionDetail(str, Enum):
    ANSWER_ONLY = "answer_only"
    FULL = "full"


class TaskError(Exception):
    pass


class TaskValidationError(TaskError):
    pass


@dataclass(frozen=True)
class TaskInstance:
    task_id: str
    preset: str
    seed: int | None
    params: dict[str, Any]
    statement: str
    solution: str
    answer: Any
    complexity: int = 1
    title_ru: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def ref(self) -> str:
        return self.task_id if self.preset == "default" else f"{self.task_id}@{self.preset}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def jsonable(x: Any) -> Any:
    """Convert Sage/Python values to JSON-serializable data (deterministically)."""
    if x is None or isinstance(x, (bool, str)):
        return x
    if isinstance(x, int):
        return int(x)
    if isinstance(x, float):
        return x
    if isinstance(x, Fraction):
        return str(x)
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    # Sage objects: Integer -> int, residues -> int, vectors/points -> list, else str
    if isinstance(x, numbers.Integral):
        return int(x)
    if hasattr(x, "lift") and callable(x.lift):
        try:
            return jsonable(x.lift())
        except Exception:
            pass
    if hasattr(x, "list") and callable(x.list):
        try:
            return [jsonable(v) for v in x.list()]
        except Exception:
            pass
    return str(x)


class Task:
    # --- metadata (override in subclasses) ---
    id: ClassVar[str]
    title_ru: ClassVar[str]
    topics: ClassVar[tuple[str, ...]] = ()
    complexity: ClassVar[int] = 1
    # Tasks of the same family never appear together in one variant
    # (e.g. Montgomery multiplication vs Montgomery exponentiation).
    family: ClassVar[str | None] = None
    solution_detail: ClassVar[SolutionDetail] = SolutionDetail.ANSWER_ONLY
    presets: ClassVar[dict[str, dict[str, Any]]] = {"default": {}}
    statement: ClassVar[str]
    solution: ClassVar[str]
    # Free-form notes for maintainers (shown by `taskgen list -v`).
    notes: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "id" in cls.__dict__:
            from taskgen.core.registry import register

            register(cls)

    def __init__(self, preset: str | None = None) -> None:
        preset = preset or "default"
        if preset not in self.presets:
            raise TaskError(f"task {self.id!r} has no preset {preset!r} "
                            f"(available: {', '.join(sorted(self.presets))})")
        self.preset = preset
        cfg = dict(self.presets.get("default", {}))
        cfg.update(self.presets[preset])
        self.cfg = SimpleNamespace(**cfg)

    # --- API -------------------------------------------------------------------
    @classmethod
    def family_name(cls) -> str:
        return cls.family or cls.id

    @property
    def ref(self) -> str:
        return self.id if self.preset == "default" else f"{self.id}@{self.preset}"

    def sample(self, rng: random.Random) -> dict[str, Any]:
        """Draw inputs and compute the template context (must contain 'answer')."""
        raise NotImplementedError

    def check(self, p: dict[str, Any]) -> None:
        """Task-specific self-check of an instance's (JSON) params.

        Raise ``AssertionError``/``TaskValidationError`` on failure. Prefer
        verifying the answer by an independent route and checking that the
        values stay in sane, pedagogically useful bounds.
        """

    def generate(self, rng: random.Random, seed: int | None = None) -> TaskInstance:
        ctx = self.sample(rng)
        if "answer" not in ctx:
            raise TaskError(f"{self.id}: sample() must return an 'answer'")
        context = {**ctx, "cfg": self.cfg}
        inst = TaskInstance(
            task_id=self.id,
            preset=self.preset,
            seed=seed,
            params=jsonable(ctx),
            statement=tex.render(self.statement, **context),
            solution=tex.render(self.solution, **context),
            answer=jsonable(ctx["answer"]),
            complexity=self.complexity,
            title_ru=self.title_ru,
        )
        self.validate(inst)
        return inst

    def validate(self, inst: TaskInstance) -> None:
        for name in ("statement", "solution"):
            problems = tex.latex_problems(getattr(inst, name))
            if problems:
                raise TaskValidationError(f"{self.id}: {name}: {'; '.join(problems)}")
        if inst.answer is None:
            raise TaskValidationError(f"{self.id}: answer is None")
        try:
            self.check(inst.params)
        except AssertionError as e:
            raise TaskValidationError(f"{self.id}: self-check failed: {e}") from e
