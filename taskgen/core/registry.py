"""Task registry with auto-discovery of ``taskgen/tasks/**``."""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from taskgen.core.task import Task

_REGISTRY: dict[str, type["Task"]] = {}
_discovered = False


def register(cls: type["Task"]) -> type["Task"]:
    tid = cls.id
    other = _REGISTRY.get(tid)
    if other is not None and other is not cls and \
            (other.__module__, other.__qualname__) != (cls.__module__, cls.__qualname__):
        raise ValueError(f"duplicate task id {tid!r}: {other.__module__} and {cls.__module__}")
    _REGISTRY[tid] = cls
    return cls


def discover() -> None:
    """Import every module under ``taskgen.tasks`` (idempotent)."""
    global _discovered
    if _discovered:
        return
    import taskgen.tasks as pkg

    for mod in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + "."):
        importlib.import_module(mod.name)
    _discovered = True


def parse_ref(ref: str) -> tuple[str, str | None]:
    """``"id@preset"`` -> ``("id", "preset")``; ``"id"`` -> ``("id", None)``."""
    tid, _, preset = ref.partition("@")
    return tid, (preset or None)


def task_class(task_id: str) -> type["Task"]:
    discover()
    try:
        return _REGISTRY[task_id]
    except KeyError:
        raise KeyError(f"unknown task id {task_id!r}") from None


def get_task(ref: str, preset: str | None = None) -> "Task":
    """Instantiate a task from ``"id[@preset]"`` (explicit ``preset`` wins)."""
    tid, ref_preset = parse_ref(ref)
    return task_class(tid)(preset or ref_preset)


def all_tasks() -> list[type["Task"]]:
    discover()
    return [_REGISTRY[k] for k in sorted(_REGISTRY)]


def topic_matches(task_topics: tuple[str, ...] | list[str], wanted: list[str]) -> bool:
    """Hierarchical match: wanted "dlp" matches task topic "dlp.bsgs"."""
    return any(t == w or t.startswith(w + ".") for t in task_topics for w in wanted)


def tasks_matching(topics: list[str], complexity: list[int] | None = None) -> list[type["Task"]]:
    return [c for c in all_tasks()
            if topic_matches(c.topics, topics)
            and (complexity is None or c.complexity in complexity)]
