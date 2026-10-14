"""Seeding, sampler invariants, engine determinism, sheet specs."""

import random

import pytest

from taskgen.core import engine, registry, sampler
from taskgen.core.rng import derive_seed, make_rng
from taskgen.core.sheet import Budget, load_sheet, parse_sheet, slot_candidates, variants

from .conftest import SHEETS


def test_derive_seed_is_stable():
    # Golden values: changing them breaks regeneration of archived runs.
    assert derive_seed(1, "sheet", "6411/1", 0) == 7062519819433524466
    assert derive_seed("x") == 1637211439935739938
    assert make_rng(5).randrange(10**9) == 454673762


def _sem2():
    return load_sheet(SHEETS / "sem2" / "kontrolnaya.yaml")[0]


def _sem1():
    return load_sheet(SHEETS / "sem1" / "kontrolnaya.yaml")[0]


def test_sem2_budget_and_families():
    spec = _sem2()
    pools = [slot_candidates(s, spec.preset) for s in spec.slots]
    seen = set()
    for k in range(300):
        tasks = sampler.select(pools, random.Random(k), spec.budget, spec.distinct_families)
        assert sum(t.complexity for t in tasks) == 8
        # the legacy tier rule (3 + 2 + 1 + 1 + 1), or three complexity-2 tasks (Plan 3 pools)
        assert sorted(t.complexity for t in tasks) in ([1, 1, 1, 2, 3], [1, 1, 2, 2, 2])
        assert len({t.family_name() for t in tasks}) == len(tasks)
        for t, pool in zip(tasks, pools):
            assert t.ref in {c.ref for c in pool}
        seen.update(t.id for t in tasks)
    # every task of every pool is reachable
    assert seen == {t.id for pool in pools for t in pool}


def test_sem2_uses_sem2_presets():
    spec = _sem2()
    pools = [slot_candidates(s, spec.preset) for s in spec.slots]
    by_id = {t.id: t for pool in pools for t in pool}
    assert by_id["powmod.binary_mod"].preset == "sem2"
    assert by_id["dlp.shanks"].preset == "default"  # no sem2 preset -> default


def test_sem1_montgomery_collision():
    spec = _sem1()
    pools = [slot_candidates(s, spec.preset) for s in spec.slots]
    for k in range(300):
        tasks = sampler.select(pools, random.Random(k), None, True)
        assert sum(t.family_name() == "montgomery" for t in tasks) <= 1


def test_impossible_budget_raises():
    spec = _sem2()
    pools = [slot_candidates(s, spec.preset) for s in spec.slots]
    with pytest.raises(sampler.SamplingError):
        sampler.select(pools, random.Random(0), Budget(min=100, max=100))


def test_run_determinism_and_variant_independence():
    spec = _sem2()
    a = engine.generate(spec, 1234)
    b = engine.generate(spec, 1234)
    assert [v.instances for v in a.variants] == [v.instances for v in b.variants]
    assert len(a.variants) == 126
    c = engine.generate(spec, 1235)
    assert [v.instances for v in a.variants] != [v.instances for v in c.variants]
    one = engine.generate(spec, 1234, only={"6412/7"})
    (v,) = one.variants
    assert v.instances == next(x for x in a.variants if x.key == "6412/7").instances


def test_unknown_variant():
    with pytest.raises(KeyError):
        engine.generate(_sem2(), 1, only={"9999/1"})


@pytest.mark.parametrize("path", sorted(SHEETS.glob("*/*.yaml")), ids=lambda p: p.name)
def test_all_sheets_generate(path):
    spec, _ = load_sheet(path)
    keys = variants(spec)
    run = engine.generate(spec, 7, only={keys[0].key, keys[-1].key})
    assert run.variants and all(v.instances for v in run.variants)


def test_sheet_validation_errors():
    with pytest.raises(ValueError, match="unknown task id"):
        parse_sheet("id: x\nkind: classroom\ntitle: t\nsections: [{title: s, tasks: [nope.task]}]")
    with pytest.raises(ValueError, match="no preset"):
        parse_sheet("id: x\nkind: classroom\ntitle: t\nsections: [{title: s, tasks: [dlp.shanks@sem9]}]")
    with pytest.raises(ValueError):
        parse_sheet("id: x\nkind: individual\ntitle: t\ngroups: [{name: a, count: 1}]\n"
                    "slots: [{topics: [no_such_topic]}]")


def test_topic_matching_is_hierarchical():
    ids = {c.id for c in registry.tasks_matching(["dlp"])}
    assert {"dlp.shanks", "dlp.pohlig_hellman", "dlp.index_calculus", "dlp.rho"} <= ids
    assert ids == {c.id for c in registry.all_tasks()
                   if any(t == "dlp" or t.startswith("dlp.") for t in c.topics)}
    assert {c.id for c in registry.tasks_matching(["dlp.generic"])} >= {"dlp.shanks"}
    assert "dlp.rho" not in {c.id for c in registry.tasks_matching(["dlp.generic"])}
    assert not registry.tasks_matching(["dl"])
