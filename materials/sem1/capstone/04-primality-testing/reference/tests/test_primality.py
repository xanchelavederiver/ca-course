import math
import random
import sys
from pathlib import Path

import pytest
from sage.all import factor, is_prime, kronecker

sys.path.insert(0, str(Path(__file__).parents[1]))

from primality import (fermat, jacobi, korselt, lucas_lehmer, mersenne_reduce, miller_rabin,
                       solovay_strassen, wilson)


@pytest.mark.parametrize("n", range(0, 40))
def test_wilson(n):
    assert (wilson(n)["verdict"] == "prime") == bool(is_prime(n))


@pytest.mark.parametrize("function", [fermat, miller_rabin, solovay_strassen])
@pytest.mark.parametrize("n", [2, 3, 5, 17, 97, 101, 561, 1105, 1729, 2047, 41041])
def test_probable_prime_tests(function, n):
    result = function(n, [2, 3, 5, 7, 11])
    if is_prime(n):
        assert result["verdict"] == "probable_prime"
    else:
        assert result["verdict"] == "composite"
        assert result["witnesses"]


def test_known_pseudoprime_distinctions():
    assert not fermat(561, [2])["witnesses"]
    assert miller_rabin(561, [2])["witnesses"]
    assert not fermat(41041, [2])["witnesses"]
    assert solovay_strassen(11305, [2, 3])["witnesses"]
    assert not miller_rabin(2047, [2])["witnesses"]
    assert miller_rabin(2047, [3])["witnesses"]


def test_jacobi_against_sage():
    rng = random.Random(551)
    for _ in range(100):
        n = rng.randrange(1, 1000) | 1
        a = rng.randrange(-2000, 2000)
        assert jacobi(a, n) == int(kronecker(a, n))


@pytest.mark.parametrize("n", [45, 225, 325, 561, 1105, 1729, 41041, 8911, 6601])
def test_korselt_and_liar_count(n):
    factors = [[p, e] for p, e in factor(n)]
    result = korselt(n, factors)
    squarefree = all(e == 1 for _, e in factors)
    want = squarefree and all((n - 1) % (p - 1) == 0 for p, _ in factors)
    assert result["carmichael"] == want
    if squarefree:
        assert result["liars"] == math.prod(math.gcd(n - 1, p - 1) for p, _ in factors)
        assert result["phi"] == math.prod(p - 1 for p, _ in factors)
    else:
        assert result["liars"] is None


def test_mersenne_reduction():
    rng = random.Random(771)
    for exponent in (3, 5, 7, 11, 17, 31):
        m = (1 << exponent) - 1
        for _ in range(20):
            x = rng.getrandbits(3 * exponent)
            assert mersenne_reduce(x, exponent) == x % m
        assert mersenne_reduce(m, exponent) == 0


@pytest.mark.parametrize("exponent", [2, 3, 5, 7, 11, 13, 17, 19, 31])
def test_lucas_lehmer(exponent):
    m = (1 << exponent) - 1
    result = lucas_lehmer(exponent)
    assert (result["verdict"] == "prime") == bool(is_prime(m))
    assert (result["residue"] == 0) == bool(is_prime(m))
    assert result["residue"] < m


def test_witnesses_are_reproducible():
    first = miller_rabin(41041, [2, 3, 5])
    second = miller_rabin(41041, [2, 3, 5])
    assert first == second
    assert first["witnesses"] == second["witnesses"]
