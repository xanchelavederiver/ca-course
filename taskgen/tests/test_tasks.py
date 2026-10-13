"""Every task x preset: instances validate, are deterministic, render sane LaTeX."""

import json

import pytest

from taskgen.core import registry, tex
from taskgen.core.rng import derive_seed, make_rng
from taskgen.core.task import SolutionDetail
from taskgen.core.taxonomy import check_taxonomy

from .conftest import all_task_presets

N_SEEDS = 20


def test_registry_has_legacy_corpus():
    # main-1sem.py + main-2sem.py, deduplicated: 29 tasks, + 2 even-modulus Montgomery tasks.
    assert len(registry.all_tasks()) >= 31


def test_taxonomy_consistent():
    assert check_taxonomy() == []


@pytest.mark.parametrize("task_id,preset", all_task_presets())
def test_task_instances(task_id, preset):
    task = registry.get_task(task_id, preset)
    for k in range(N_SEEDS):
        seed = derive_seed("test", task_id, preset, k)
        inst = task.generate(make_rng(seed), seed=seed)  # validates internally
        assert inst == task.generate(make_rng(seed), seed=seed), "non-deterministic"
        assert tex.latex_problems(inst.statement) == []
        assert tex.latex_problems(inst.solution) == []
        json.dumps(inst.to_dict())  # manifest-serialisable
        task.validate(inst)


@pytest.mark.parametrize("task_id,preset", all_task_presets())
def test_metadata(task_id, preset):
    cls = registry.task_class(task_id)
    assert cls.title_ru and cls.topics
    assert cls.complexity in (1, 2, 3)
    assert isinstance(cls.solution_detail, SolutionDetail)
    assert "default" in cls.presets


def test_latex_problems_detects_errors():
    assert tex.latex_problems(r"\[x") == [r"unbalanced \[ \]"]
    assert "unbalanced '{'" in tex.latex_problems("{a")
    assert "odd number of '$'" in tex.latex_problems("$a")
    assert tex.latex_problems(r"\{ $a$ \}") == []
