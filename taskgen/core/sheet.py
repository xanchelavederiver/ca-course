"""Sheet specifications (YAML), see ``sheets/`` and README.

Two kinds:

* ``classroom`` — a single sheet: ordered sections of explicit task refs.
* ``individual`` — homework/exam: one variant per student; each variant
  fills every slot with one task chosen from the slot's pool (explicit task
  refs or topics), subject to the complexity budget and family-collision
  rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from taskgen.core import registry
from taskgen.core.taxonomy import check_topic

SLUG = r"^[a-z0-9][a-z0-9._-]*$"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskRef(_Model):
    id: str
    preset: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _from_str(cls, v: Any) -> Any:
        if isinstance(v, str):
            tid, preset = registry.parse_ref(v)
            return {"id": tid, "preset": preset}
        return v

    def __str__(self) -> str:
        return self.id if not self.preset else f"{self.id}@{self.preset}"


class Section(_Model):
    title: str
    intro: str | None = None
    tasks: list[TaskRef]


class Slot(_Model):
    title: str | None = None
    tasks: list[TaskRef] | None = None
    topics: list[str] | None = None
    complexity: list[int] | None = None

    @model_validator(mode="after")
    def _one_source(self) -> "Slot":
        if (self.tasks is None) == (self.topics is None):
            raise ValueError("slot needs exactly one of 'tasks' or 'topics'")
        return self


class Group(_Model):
    name: str
    count: int | None = Field(default=None, ge=1)
    students: list[str] | None = None

    @model_validator(mode="after")
    def _one_source(self) -> "Group":
        if (self.count is None) == (self.students is None):
            raise ValueError("group needs exactly one of 'count' or 'students'")
        return self

    @property
    def size(self) -> int:
        return self.count if self.count is not None else len(self.students or [])


class Budget(_Model):
    min: int | None = None
    max: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _from_int(cls, v: Any) -> Any:
        return {"min": v, "max": v} if isinstance(v, int) else v

    def ok(self, total: int) -> bool:
        return (self.min is None or total >= self.min) and (self.max is None or total <= self.max)


class SlotRule(_Model):
    when_slot: int = Field(ge=0)
    when_families: list[str]
    require_slot: int = Field(ge=0)
    tasks: list[TaskRef]


class Document(_Model):
    """LaTeX document options."""
    font_size: str = "14pt"
    toc: bool = True
    # Text for the solution manual's title suffix.
    solutions_suffix: str = "Решения"


class _SheetBase(_Model):
    id: str = Field(pattern=SLUG)
    title: str
    semester: int | None = None
    # Default task preset (used when a task has it, e.g. "sem2").
    preset: str | None = None
    intro: str = ""
    document: Document = Document()
    template: str | None = None


class ClassroomSheet(_SheetBase):
    kind: Literal["classroom"]
    sections: list[Section]


class IndividualSheet(_SheetBase):
    kind: Literal["individual"]
    groups: list[Group]
    slots: list[Slot]
    rules: list[SlotRule] = Field(default_factory=list)
    budget: Budget | None = None
    distinct_families: bool = True


Sheet = Annotated[Union[ClassroomSheet, IndividualSheet], Field(discriminator="kind")]
_adapter: TypeAdapter[Any] = TypeAdapter(Sheet)


@dataclass(frozen=True)
class VariantKey:
    group: str | None
    number: int
    student: str | None = None

    @property
    def key(self) -> str:
        return f"{self.group}/{self.number}" if self.group is not None else str(self.number)


def variants(spec: ClassroomSheet | IndividualSheet) -> list[VariantKey]:
    if isinstance(spec, ClassroomSheet):
        return [VariantKey(group=None, number=1)]
    out = []
    for g in spec.groups:
        for i in range(g.size):
            out.append(VariantKey(group=g.name, number=i + 1,
                                  student=g.students[i] if g.students else None))
    return out


def parse_sheet(text: str) -> ClassroomSheet | IndividualSheet:
    spec = _adapter.validate_python(yaml.safe_load(text))
    problems = check_sheet(spec)
    if problems:
        raise ValueError("invalid sheet spec:\n  " + "\n  ".join(problems))
    return spec


def load_sheet(path: str | Path) -> tuple[ClassroomSheet | IndividualSheet, str]:
    """Load and check a sheet spec; returns ``(spec, raw_yaml_text)``."""
    text = Path(path).read_text(encoding="utf-8")
    return parse_sheet(text), text


def _resolve_preset(cls: type, ref_preset: str | None, sheet_preset: str | None) -> str:
    if ref_preset:
        return ref_preset
    if sheet_preset and sheet_preset in cls.presets:  # type: ignore[attr-defined]
        return sheet_preset
    return "default"


def resolve_ref(ref: TaskRef, sheet_preset: str | None):
    cls = registry.task_class(ref.id)
    return cls(_resolve_preset(cls, ref.preset, sheet_preset))


def slot_candidates(slot: Slot, sheet_preset: str | None) -> list:
    """Task objects a slot may be filled with (deterministic order)."""
    if slot.tasks is not None:
        tasks = [resolve_ref(r, sheet_preset) for r in slot.tasks]
    else:
        tasks = [cls(_resolve_preset(cls, None, sheet_preset))
                 for cls in registry.tasks_matching(slot.topics or [], slot.complexity)]
    if slot.complexity is not None:
        tasks = [t for t in tasks if t.complexity in slot.complexity]
    return tasks


def check_sheet(spec: ClassroomSheet | IndividualSheet) -> list[str]:
    problems: list[str] = []

    def check_ref(where: str, ref: TaskRef) -> None:
        if not re.match(SLUG, ref.id):
            problems.append(f"{where}: bad task id {ref.id!r}")
        try:
            resolve_ref(ref, spec.preset)
        except Exception as e:  # unknown id / preset
            problems.append(f"{where}: {e}")

    if isinstance(spec, ClassroomSheet):
        for i, sec in enumerate(spec.sections):
            for ref in sec.tasks:
                check_ref(f"sections[{i}]", ref)
    else:
        names = [g.name for g in spec.groups]
        if len(set(names)) != len(names):
            problems.append("duplicate group names")
        for i, slot in enumerate(spec.slots):
            for ref in slot.tasks or []:
                check_ref(f"slots[{i}]", ref)
            for t in slot.topics or []:
                for m in check_topic(t):
                    problems.append(f"slots[{i}]: topic {m!r} not in taxonomy")
            if not problems and not slot_candidates(slot, spec.preset):
                problems.append(f"slots[{i}]: no candidate tasks")
        for i, rule in enumerate(spec.rules):
            if rule.when_slot >= len(spec.slots) or rule.require_slot >= len(spec.slots):
                problems.append(f"rules[{i}]: slot index out of range")
                continue
            if rule.when_slot == rule.require_slot:
                problems.append(f"rules[{i}]: source and target slots must differ")
            for ref in rule.tasks:
                check_ref(f"rules[{i}]", ref)
            candidates = {str(t.ref) for t in slot_candidates(spec.slots[rule.require_slot], spec.preset)}
            for ref in rule.tasks:
                if str(ref) not in candidates:
                    problems.append(f"rules[{i}]: task {ref} is not in the target slot's pool")
    return problems
