"""Committed topic taxonomy (``taskgen/tasks/taxonomy.yaml``).

Topics are dotted slugs; every prefix of a topic must itself be a topic.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

TAXONOMY_FILE = Path(__file__).resolve().parent.parent / "tasks" / "taxonomy.yaml"


@lru_cache(maxsize=1)
def taxonomy() -> dict[str, str]:
    """topic slug -> Russian title"""
    data = yaml.safe_load(TAXONOMY_FILE.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in data.items()}


def check_topic(topic: str) -> list[str]:
    tax = taxonomy()
    parts = topic.split(".")
    return [p for p in (".".join(parts[:i]) for i in range(1, len(parts) + 1)) if p not in tax]


def check_taxonomy() -> list[str]:
    """Problems with the taxonomy itself and with every registered task's topics."""
    from taskgen.core.registry import all_tasks

    problems = [f"taxonomy: parent of {t!r} missing: {m}"
                for t in taxonomy() for m in check_topic(t)]
    for cls in all_tasks():
        if not cls.topics:
            problems.append(f"{cls.id}: no topics")
        for t in cls.topics:
            for m in check_topic(t):
                problems.append(f"{cls.id}: topic {m!r} not in taxonomy")
    return problems
