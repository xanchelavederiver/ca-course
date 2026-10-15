"""icalc.nt and icalc.params against Sage's built-ins (the oracle)."""

import random

import pytest
from sage.all import factor, is_prime, primes_first_n, primitive_root, prime_range

from icalc import nt, params

RNG = random.Random(20261014)


def test_primes_up_to():
    for n in (0, 1, 2, 3, 10, 97, 1000, 7919):
        assert nt.primes_up_to(n) == list(prime_range(n + 1))


@pytest.mark.parametrize("bits", [8, 20, 40, 64, 90])
def test_is_probable_prime(bits):
    for _ in range(200):
        n = RNG.getrandbits(bits) | 1
        assert nt.is_probable_prime(n) == bool(is_prime(n)), n
    # Carmichael numbers and strong pseudoprimes to small bases
    for n in (561, 1105, 1729, 2047, 3215031751, 3825123056546413051):
        assert not nt.is_probable_prime(n)


@pytest.mark.parametrize("bits", [2, 10, 30, 60, 80])
def test_factorize(bits):
    for _ in range(20):
        n = RNG.getrandbits(bits) + 1
        assert nt.factorize(n) == {int(q): int(e) for q, e in factor(n)}
    q = 1000003
    assert nt.factorize(q ** 2) == {q: 2}
    assert nt.factorize(q ** 3 * 4) == {2: 2, q: 3}
    assert nt.factorize(1) == {}


def test_crt():
    ms = [8, 9, 5, 7, 1000003]
    x = RNG.randrange(8 * 9 * 5 * 7 * 1000003)
    assert nt.crt([x % m for m in ms], ms) == (x, 8 * 9 * 5 * 7 * 1000003)


def test_primitive_root_and_order():
    for p in [int(q) for q in primes_first_n(60)] + [1000003, 2 ** 61 - 1]:
        f = nt.factorize(p - 1)
        assert nt.primitive_root(p, f) == int(primitive_root(p))
        a = RNG.randrange(1, p)
        from sage.all import Mod
        assert nt.element_order(a, p, f) == int(Mod(a, p).multiplicative_order())


def test_dickman_rho():
    # rho(2) = 1 - ln 2, rho(3) = 0.0486..., rho(4) = 0.0049109..., rho(5) = 0.00035472...
    for u, want in [(1, 1.0), (2, 0.306853), (3, 0.048608), (4, 0.0049109), (5, 0.00035472)]:
        assert params.dickman_rho(u) == pytest.approx(want, rel=1e-3)


def test_choose():
    p = 2 ** 61 - 1
    par = params.choose(p)
    assert par["B"] == pytest.approx(params.L(p) ** (2 ** -0.5), rel=1e-6, abs=1)
    params.finish(par, len(nt.primes_up_to(par["B"])))
    assert par["relations_needed"] > len(nt.primes_up_to(par["B"]))
    assert par["expected_trials"] == pytest.approx(par["relations_needed"] / par["smooth_prob_rho"])
    # the optimum c = 1/sqrt 2 minimises the asymptotic L^(c + 1/(2c))
    assert params.choose(p, b=100)["B"] == 100
    for p in (2, 3, 5, 7):
        assert 2 <= params.choose(p)["B"] <= max(2, p - 1)
