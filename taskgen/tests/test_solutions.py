"""Step-by-step solutions and task-specific behaviour."""

import random

import pytest

from taskgen.core import registry, steps
from taskgen.core.rng import make_rng
from taskgen.core.task import SolutionDetail
from taskgen.tasks.modular.fermat_mersenne import from_2f, integer_to_2f

from .conftest import all_task_presets


@pytest.mark.parametrize("task_id,preset", all_task_presets())
def test_every_task_has_full_solution(task_id, preset):
    cls = registry.task_class(task_id)
    assert cls.solution_detail is SolutionDetail.FULL
    inst = cls(preset).generate(make_rng("full", task_id, preset))
    # a full solution is more than the final answer line
    assert len(inst.solution) > 150, inst.solution


def test_diminished_one_code():
    for t in (4, 8):
        seen = set()
        for b in range(2**t + 1):
            bits = integer_to_2f(b, t)
            assert len(bits) == t + 1 and from_2f(bits) == b
            seen.add(tuple(bits))
        assert len(seen) == 2**t + 1
    assert integer_to_2f(0, 8) == [0] * 8 + [1]
    assert integer_to_2f(1, 8) == [0] * 9
    assert integer_to_2f(256, 8) == [1] * 8 + [0]


@pytest.mark.parametrize("task_id", ["arithmetic.montgomery_mul_even", "powmod.montgomery_even"])
def test_montgomery_even_versions(task_id):
    task = registry.get_task(task_id)
    assert task.complexity == 3 and task.family_name() == "montgomery"
    for k in range(30):
        p = task.generate(make_rng("even", task_id, k)).params
        assert p["m"] % 2 == 0 and p["s"] % 2 == 1 and p["s"] > 1


@pytest.mark.parametrize("task_id", ["arithmetic.montgomery_mul", "powmod.montgomery"])
def test_montgomery_odd_versions(task_id):
    task = registry.get_task(task_id)
    for k in range(30):
        assert task.generate(make_rng("odd", task_id, k)).params["m"] % 2 == 1


@pytest.mark.parametrize("task_id", ["number_theory.solovay_strassen", "number_theory.miller_rabin"])
@pytest.mark.parametrize("preset", ["default", "sem2"])
def test_primality_gives_primes_and_composites(task_id, preset):
    task = registry.get_task(task_id, preset)
    answers = {task.generate(make_rng("prim", task_id, preset, k)).answer for k in range(60)}
    assert answers == {"prime", "composite"}


@pytest.mark.parametrize("task_id,preset", [("number_theory.order", "default"),
                                            ("number_theory.order", "sem2"),
                                            ("number_theory.order_product_tree", "default")])
def test_order_allows_primitive_roots(task_id, preset):
    task = registry.get_task(task_id, preset)
    insts = [task.generate(make_rng("ord", task_id, preset, k)) for k in range(200)]
    assert any(i.answer == i.params["p"] - 1 for i in insts)


def test_ternary_expansion_is_nontrivial():
    task = registry.get_task("ecc.double_and_add_ternary")
    for k in range(20):
        p = task.generate(make_rng("naf", k)).params
        assert -1 in p["digits"]
        assert all(not (a and b) for a, b in zip(p["digits"], p["digits"][1:]))


def test_congruential_vector_decrypts():
    task = registry.get_task("crypto.congruential")
    for k in range(20):
        p = task.generate(make_rng("cong", k)).params
        f, g = p["dk"]["f"], p["dk"]["g"]
        assert (p["h"] * f - g) % p["q"] == 0 and p["dk"]["b"] == p["answer"]


def test_step_helpers():
    rng = random.Random(1)
    for _ in range(300):
        m = rng.randrange(3, 10**6) | 1
        a, b, e = rng.randrange(m), rng.randrange(m), rng.randrange(1, 300)
        assert steps.montgomery_mul(a, b, m)["result"] == a * b % m
        assert steps.montgomery_pow(a, e, m)["result"] == pow(a, e, m)
        assert steps.qary_pow_steps(a, e, m)["result"] == pow(a, e, m)
    # textbook examples (Hoffstein–Pipher–Silverman)
    assert steps.jacobi(1001, 9907) == -1
    assert steps.gauss_reduce([66586820, 65354729], [6513996, 6393464])["v1"] == [2280, -1001]
    assert steps.babai([[137, 312], [215, -187]], [53172, 81743])["r"] == [53159, 81818]
    assert steps.crt([3, 4, 1], [8, 9, 5])["x"] == 211
