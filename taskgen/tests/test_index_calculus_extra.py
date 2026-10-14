"""Index calculus building blocks (taskgen/tasks/dlp/index_calculus_extra.py)."""

import random

import pytest

from taskgen.core.registry import get_task
from taskgen.tasks.dlp import index_calculus_extra as ic


def test_factor_base_helpers():
    fb = ic.factor_base(5, signed=True)
    assert fb == [-1, 2, 3, 5]
    assert ic.fb_exponents(-60, fb) == [1, 2, 1, 1]
    assert ic.fb_exponents(14, fb) is None
    assert ic.mono_tex([1, 2, 1, 1], fb) == r"-2^{2} \cdot 3 \cdot 5"
    assert ic.mono_tex([1, 0, 0, 0], fb) == "-1"
    assert ic.lin_tex([1, 2, 0, 1], fb) == "L_{-1} + 2L_{2} + L_{5}"
    assert ic.lift(100, 101, True) == -1 and ic.lift(100, 101, False) == 100


def test_elimination_lecture_example():
    # p = 701, g = 11 (lecture notes): relations k = 7, 9, 15, 22, 28, 29 over {2, 3, 5, 7}
    rows = [[3, 2, 0, 0, 7], [2, 1, 2, 0, 9], [0, 5, 0, 0, 15], [5, 1, 0, 1, 22],
            [6, 0, 1, 0, 28], [0, 1, 1, 0, 29]]
    sols = {m: ic.eliminate(rows, 4, q, m)["sol"] for q, m in [(2, 4), (5, 25), (7, 7)]}
    assert sols == {4: [3, 3, 2, 0], 25: [12, 23, 6, 14], 7: [5, 3, 5, 1]}
    logs = [ic.crt_pair_list([sols[m][i] for m in (4, 25, 7)], [4, 25, 7]) for i in range(4)]
    assert logs == [187, 423, 306, 64]
    assert all(pow(11, L, 701) == q for L, q in zip(logs, [2, 3, 5, 7]))
    # without the relation k = 9 the system is singular modulo 5
    assert ic.eliminate(rows[:1] + rows[2:], 4, 5, 25) is None


def test_det_and_rank():
    assert ic.int_det([[2, 0, 1], [0, 1, 2], [2, 1, 0]]) == -6
    assert ic.rank_mod_prime([[2, 0], [0, 2]], 2) == 0


@pytest.mark.parametrize("ref", ["dlp.ic_linear_system@singular", "dlp.ic_individual_log@signed",
                                 "dlp.ic_relations@signed"])
def test_corner_presets(ref):
    task = get_task(ref)
    for seed in range(15):
        p = task.generate(random.Random(seed), seed).params
        if ref.endswith("singular"):
            assert p["bad"]
        elif "individual" in ref:
            assert p["trace"][-1]["r"] < 0
        else:
            assert any(t["ex"] and t["r"] < 0 for t in p["rows"])
