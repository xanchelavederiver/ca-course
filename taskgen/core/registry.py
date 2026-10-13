"""Task registry with auto-discovery of ``taskgen/tasks/**``."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import traceback
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from taskgen.core.task import Task

_REGISTRY: dict[str, type["Task"]] = {}
_discovered = False
# module name -> formatted traceback of modules that failed to import
# (only collected by ``discover(strict=False)``).
IMPORT_ERRORS: dict[str, str] = {}


def register(cls: type["Task"]) -> type["Task"]:
    tid = cls.id
    other = _REGISTRY.get(tid)
    if other is not None and other is not cls and \
            (other.__module__, other.__qualname__) != (cls.__module__, cls.__qualname__):
        raise ValueError(f"duplicate task id {tid!r}: {other.__module__} and {cls.__module__}")
    _REGISTRY[tid] = cls
    return cls


def discover(strict: bool = True) -> None:
    """Import every module under ``taskgen.tasks`` (idempotent).

    With ``strict=False`` a module that fails to import is recorded in
    ``IMPORT_ERRORS`` and skipped, so one broken task module does not hide
    the others (used by the web app's engine worker).
    """
    global _discovered
    if _discovered:
        return
    import taskgen.tasks as pkg

    def failed(name: str) -> None:
        IMPORT_ERRORS[name] = traceback.format_exc()
        # classes defined before the error was raised registered themselves
        for tid in [t for t, c in _REGISTRY.items()
                    if c.__module__ == name or c.__module__.startswith(name + ".")]:
            del _REGISTRY[tid]

    def onerror(name: str) -> None:
        if strict:
            raise
        failed(name)

    for mod in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + ".", onerror=onerror):
        try:
            importlib.import_module(mod.name)
        except Exception:
            if strict:
                raise
            failed(mod.name)
    _discovered = True


def source_location(cls: type["Task"]) -> tuple[str | None, int | None, int | None]:
    """``(file, first line, last line)`` of a task class definition (1-based)."""
    try:
        file = inspect.getsourcefile(cls)
        lines, start = inspect.getsourcelines(cls)
    except (OSError, TypeError):
        return None, None, None
    return file, start, start + len(lines) - 1


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
