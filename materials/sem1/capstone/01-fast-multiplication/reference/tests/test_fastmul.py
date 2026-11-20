import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from fastmul import (METHODS, fft, finite_field_convolution, karatsuba, schoolbook,
                     select_finite_field, toom3)


def naive_convolution(x, y, cyclic=False):
    n = max(len(x), len(y)) if cyclic else len(x) + len(y) - 1
    out = [0] * n
    for i, a in enumerate(x):
        for j, b in enumerate(y):
            out[(i + j) % n if cyclic else i + j] += a * b
    return out


@pytest.mark.parametrize("method", sorted(METHODS))
@pytest.mark.parametrize("a,b", [
    (0, 0), (0, 123), (-1, 1), (1, -999), (-999, -888),
    (2**30 - 1, 2**30 - 1), (2**64 + 1, 2**64 - 1),
    (2**127 - 1, 2**127 + 1), (2**200 + 2**100 + 1, -(2**190 + 3)),
])
def test_corners(method, a, b):
    assert METHODS[method](a, b) == a * b


@pytest.mark.parametrize("method", sorted(METHODS))
def test_random(method):
    rng = random.Random(712367)
    for _ in range(25):
        a = rng.getrandbits(rng.randrange(0, 350))
        b = rng.getrandbits(rng.randrange(0, 350))
        if rng.randrange(2):
            a = -a
        if rng.randrange(2):
            b = -b
        assert METHODS[method](a, b) == a * b


def test_unbalanced_and_carry_heavy():
    for method in METHODS.values():
        assert method((1 << 600) - 1, (1 << 37) - 1) == ((1 << 600) - 1) * ((1 << 37) - 1)
        assert method(1 << 900, (1 << 33) + 1) == (1 << 933) + (1 << 900)


def test_prime_and_root_selection():
    n, p, omega = select_finite_field(100, 10_000)
    assert n == 128 and p > 10_000 and p % n == 1
    assert pow(omega, n, p) == 1 and pow(omega, n // 2, p) != 1


def test_fft_rejects_bad_root():
    with pytest.raises(ValueError):
        fft([1, 2], 17, 1)


@pytest.mark.parametrize("cyclic", [False, True])
def test_finite_field_convolution(cyclic):
    rng = random.Random(991)
    for _ in range(10):
        x = [rng.randrange(20) for _ in range(rng.randrange(1, 15))]
        y = [rng.randrange(20) for _ in range(rng.randrange(1, 15))]
        got, info = finite_field_convolution(x, y, cyclic=cyclic)
        want = naive_convolution(x, y, cyclic=cyclic)
        if cyclic:
            n = info["n"]
            padded = naive_convolution(x + [0] * (n - len(x)), y + [0] * (n - len(y)), cyclic=True)
            assert got == padded
        else:
            assert got == want
        assert all(0 <= c < info["p"] for c in got)


def test_toom_interpolation_negative_evaluations():
    rng = random.Random(81)
    for _ in range(10):
        a = rng.getrandbits(200)
        b = rng.getrandbits(180)
        assert toom3(a, b) == karatsuba(a, b) == schoolbook(a, b) == a * b
