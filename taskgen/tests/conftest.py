from pathlib import Path

import pytest

from taskgen.core import registry

REPO = Path(__file__).resolve().parents[2]
SHEETS = REPO / "sheets"


def all_task_presets():
    return [(cls.id, p) for cls in registry.all_tasks() for p in cls.presets]


@pytest.fixture
def repo() -> Path:
    return REPO
