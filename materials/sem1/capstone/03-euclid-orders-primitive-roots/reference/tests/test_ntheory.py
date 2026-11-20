import math
import random
import sys
from pathlib import Path

import pytest
from sage.all import Mod, factor, primitive_root as sage_primitive_root

sys.path.insert(0, str(Path(__file__).parents[1]))

from ntheory import (batch_inverse, binary_gcd, crt, garner, inverse, order_product_tree,
                     order_sequential, primitive_root, xgcd)


def test_gcd_and_xgcd():
    rng = random.Random(7712)
    for _ in range(100):
        a = rng.randrange(-10**12, 10**12)
        b = rng.randrange(-10**12, 10**12)
        assert binary_gcd(a, b) == math.gcd(a, b)
        g, x, y = xgcd(a, b)
        assert g == math.gcd(a, b) and a * x + b * y == g


def test_inverse_and_batch_with_nonunits():
    n = 60
    values = [0, 1, 7, 12, 13, 25, 49, 60, -7]
    got = batch_inverse(values, n)
    for i, value in enumerate(values):
        if math.gcd(value, n) == 1:
            assert got["inverses"][i] * value % n == 1
        else:
            assert got["inverses"][i] is None
    assert got["nonunits"] == [0, 3, 5, 7]
    assert inverse(-7, 60) == pow(-7, -1, 60)
    with pytest.raises(ValueError):
        inverse(12, 60)


def test_batch_matches_repeated_inversion_random():
    rng = random.Random(19)
    for _ in range(30):
        n = rng.randrange(2, 500)
        values = [rng.randrange(-500, 500) for _ in range(20)]
        got = batch_inverse(values, n)
        for value, inv in zip(values, got["inverses"]):
            if math.gcd(value, n) == 1:
                assert inv == pow(value, -1, n)
            else:
                assert inv is None


@pytest.mark.parametrize("function", [crt, lambda r, m: garner(r, m)[:2]])
def test_crt_and_garner(function):
    residues = [2, 3, 4, 8]
    moduli = [5, 7, 11, 17]
    x, modulus = function(residues, moduli)
    assert modulus == math.prod(moduli)
    assert [x % m for m in moduli] == residues
    assert function([0, 0], [3, 4])[0] == 0
    with pytest.raises(ValueError):
        function([1, 2], [6, 9])


def test_garner_coefficients_reconstruct():
    residues, moduli = [4, 2, 10], [7, 9, 11]
    x, modulus, coefficients = garner(residues, moduli)
    product = 1
    reconstructed = 0
    for coefficient, m in zip(coefficients, moduli):
        reconstructed += product * coefficient
        product *= m
    assert reconstructed % modulus == x


@pytest.mark.parametrize("p", [101, 211, 4093, 65537, 2**61 - 1])
def test_orders_and_primitive_root(p):
    factors = [[q, e] for q, e in factor(p - 1)]
    expected_root = int(sage_primitive_root(p))
    root = primitive_root(p, factors)
    assert all(pow(root, (p - 1) // q, p) != 1 for q, _ in factors)
    for g in {1, 2, root, pow(root, 2, p), pow(root, (p - 1) // 2, p)}:
        sequential, trace = order_sequential(g, p, factors)
        tree, tree_trace = order_product_tree(g, p, factors)
        assert sequential == tree == int(Mod(g, p).multiplicative_order())
        assert pow(g, sequential, p) == 1
        assert tree_trace


def test_product_tree_prime_power_and_non_generator():
    p = 271
    factors = [[q, e] for q, e in factor(p - 1)]
    root = primitive_root(p, factors)
    for divisor in (2, 3, 5, 9, 27, 30, 45, 135, 270):
        g = pow(root, (p - 1) // divisor, p)
        assert order_sequential(g, p, factors)[0] == divisor
        assert order_product_tree(g, p, factors)[0] == divisor


def test_invalid_factorization_rejected():
    with pytest.raises(ValueError):
        order_sequential(2, 101, [[2, 1], [5, 2]])
