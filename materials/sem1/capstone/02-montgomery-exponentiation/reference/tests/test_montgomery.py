import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from montgomery import (Montgomery, binary_lr, evaluate, prepare, qary_digits, xgcd)

METHODS = ("binary", "qary", "sliding", "montgomery")


@pytest.mark.parametrize("a,b", [(1, 1), (12, 18), (-12, 18), (30, -18), (0, 17), (2**64, 2**63 + 1)])
def test_xgcd(a, b):
    g, x, y = xgcd(a, b)
    assert g == __import__("math").gcd(a, b)
    assert a * x + b * y == g


@pytest.mark.parametrize("n", [1, 3, 5, 17, 2**61 - 1, 2**127 - 1])
def test_montgomery_arithmetic(n):
    ctx = Montgomery(n)
    one = ctx.to_montgomery(1)
    assert ctx.from_montgomery(one) == 1 % n
    for a in (0, 1, 2, n - 1, n, n + 3, 10 * n + 7):
        am = ctx.to_montgomery(a)
        assert ctx.from_montgomery(am) == a % n
        assert ctx.from_montgomery(ctx.mul(am, am)) == a * a % n


@pytest.mark.parametrize("n", [2, 4, 18, 0, -3])
def test_montgomery_rejects_invalid_modulus(n):
    with pytest.raises(ValueError):
        Montgomery(n)


@pytest.mark.parametrize("method", METHODS)
def test_exponentiation_corners(method):
    for n in (1, 2, 3, 17, 100, 2**61 - 1):
        if method == "montgomery" and n % 2 == 0:
            continue
        for a, e in ((0, 0), (0, 9), (1, 0), (12, 0), (12, 1), (12, 63), (100, 64)):
            prepared = prepare(a, n, method, 4)
            got, stats = evaluate(prepared, a, e, n, method)
            assert got == pow(a, e, n)
            assert stats["squarings"] >= 0


@pytest.mark.parametrize("method", METHODS)
def test_exponentiation_random(method):
    rng = random.Random(8131)
    for _ in range(30):
        n = rng.getrandbits(80) | 1 | (1 << 79)
        a = rng.getrandbits(100)
        e = rng.getrandbits(rng.randrange(0, 100))
        parameter = rng.choice((2, 4, 8, 16)) if method == "qary" else rng.randrange(1, 7)
        prepared = prepare(a, n, method, parameter)
        got, _ = evaluate(prepared, a, e, n, method)
        assert got == pow(a, e, n)


def test_precomputation_is_reused_but_base_is_checked():
    a, n = 17, 101
    prepared = prepare(a, n, "sliding", 4)
    for e in (1, 2, 3, 127, 255, 1024):
        assert evaluate(prepared, a, e, n, "sliding")[0] == pow(a, e, n)
    with pytest.raises(ValueError, match="stale"):
        evaluate(prepared, a + 1, 10, n, "sliding")


def test_qary_digits_and_parameters():
    assert qary_digits(0, 4) == [0]
    assert qary_digits(255, 4) == [3, 3, 3, 3]
    with pytest.raises(ValueError):
        prepare(2, 17, "qary", 3)
    with pytest.raises(ValueError):
        prepare(2, 17, "sliding", 0)


def test_montgomery_redc_count():
    ctx = Montgomery(101)
    stats = {"squarings": 0, "multiplications": 0}
    assert ctx.pow(17, 100, stats) == pow(17, 100, 101)
    assert stats["redc"] == stats["squarings"] + stats["multiplications"] + 1
