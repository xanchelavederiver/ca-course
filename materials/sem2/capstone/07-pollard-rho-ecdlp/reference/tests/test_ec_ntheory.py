"""Curve arithmetic and number theory of the reference vs Sage."""

import random

import pytest
from conftest import sage_curve, sage_point, xy

from rho_ecdlp.ec import Curve, CurveError
from rho_ecdlp.ntheory import factor, is_prime, solve_linear_congruence


@pytest.mark.parametrize("bits", [8, 16, 32, 64, 100])
def test_add_mul_vs_sage(rng, bits):
    for _ in range(10):
        S, p, a, b = sage_curve(rng, bits)
        E = Curve.checked(p, a, b)
        P, Q = sage_point(S, rng), sage_point(S, rng)
        for A, B in [(P, Q), (P, P), (P, -P), (P, S(0)), (S(0), Q)]:
            assert E.add(xy(A), xy(B)) == xy(A + B)
        k = rng.randrange(-2 ** bits, 2 ** bits)
        assert E.mul(k, xy(P)) == xy(k * P)
        assert E.mul(0, xy(P)) is None
        assert E.neg(xy(P)) == xy(-P)


def test_two_torsion_doubling():
    # b = 0: (0, 0) has order 2, so (0, 0) + (0, 0) = O (tangent is vertical)
    E = Curve.checked(10007, 3, 0)
    assert E.add((0, 0), (0, 0)) is None
    assert E.mul(2, (0, 0)) is None


@pytest.mark.parametrize("p,a,b", [(9, 1, 1), (2, 1, 1), (10007, 0, 0), (10007, 10004, 2)])
def test_bad_curves(p, a, b):
    # 10004 = -3: 4(-3)^3 + 27 * 2^2 = 0
    with pytest.raises(CurveError):
        Curve.checked(p, a, b)


def test_bad_points():
    E = Curve.checked(10007, 1, 1)
    for bad in ([1, 2], [1], "P", [1.0, 2.0]):
        with pytest.raises(CurveError):
            E.point(bad)
    assert E.point(None) is None


def test_is_prime_vs_sage(rng):
    from sage.all import is_prime as sage_is_prime

    carmichael = [561, 1105, 1729, 2465, 2821, 6601, 8911, 41041, 825265, 321197185]
    xs = carmichael + [rng.getrandbits(b) | 1 for b in (8, 20, 40, 64, 80) for _ in range(200)]
    xs += [0, 1, 2, 3, 4, 2 ** 61 - 1, (2 ** 31 - 1) ** 2]
    for x in xs:
        assert is_prime(x) == bool(sage_is_prime(x)), x


def test_factor_vs_sage(rng):
    from sage.all import factor as sage_factor, next_prime

    cases = [1, 2, 1024, 3 ** 7, 997 * 1009, int(next_prime(2 ** 30)) ** 2,
             int(next_prime(2 ** 31)) * int(next_prime(2 ** 35)) * 4]
    cases += [rng.getrandbits(b) + 1 for b in (16, 32, 48, 64, 70) for _ in range(20)]
    for m in cases:
        assert factor(m, random.Random(m)) == {int(q): int(e) for q, e in sage_factor(m)}, m


def test_linear_congruence_brute_force(rng):
    for n in list(range(1, 60)) + [rng.randrange(60, 400) for _ in range(20)]:
        for _ in range(10):
            u, v = rng.randrange(-n, 2 * n), rng.randrange(-n, 2 * n)
            d, xs = solve_linear_congruence(u, v, n, limit=10 ** 6)
            assert xs == [x for x in range(n) if (u * x - v) % n == 0]
            assert d == __import__("math").gcd(u, n)
    # more than `limit` solutions: degenerate, not listed
    assert solve_linear_congruence(0, 0, 101, limit=16) == (101, None)
    assert solve_linear_congruence(0, 5, 101, limit=16) == (101, [])
