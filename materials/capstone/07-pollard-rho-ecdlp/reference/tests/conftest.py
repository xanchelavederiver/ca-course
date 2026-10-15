"""pytest setup: import the reference package (rho_ecdlp) from ../ and Sage helpers."""

import random
import sys
from pathlib import Path

import pytest

REF = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REF))


def sage_curve(rng: random.Random, bits: int, a=None, b=None):
    """A random non-singular Sage curve over a random `bits`-bit prime field (rng only)."""
    from sage.all import GF, EllipticCurve, next_prime

    while True:
        p = int(next_prime(rng.getrandbits(bits - 1) | (1 << (bits - 1))))
        aa = rng.randrange(p) if a is None else a
        bb = rng.randrange(p) if b is None else b
        if (4 * aa ** 3 + 27 * bb ** 2) % p:
            return EllipticCurve(GF(p), [aa, bb]), p, aa, bb


def sage_point(E, rng: random.Random):
    """A random affine point of the Sage curve E (rng only)."""
    F = E.base_field()
    p = int(F.order())
    while True:
        x = F(rng.randrange(p))
        if E.is_x_coord(x):
            P = E.lift_x(x)
            return -P if rng.getrandbits(1) else P


def xy(P):
    return None if P.is_zero() else (int(P[0]), int(P[1]))


@pytest.fixture
def rng(request):
    return random.Random(request.node.name)
