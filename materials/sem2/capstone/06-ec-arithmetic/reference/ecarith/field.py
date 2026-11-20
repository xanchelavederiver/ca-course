"""Arithmetic in the prime field F_p on top of the bigint library (gmpy2 / GMP).

The spec allows a bigint library (GMP or its gmpy2 wrapper), so modular inversion,
modular powering and the primality test come from gmpy2. Everything specific to the
course is written by hand: the quadratic character and the square root (Tonelli--Shanks).
"""

from __future__ import annotations

import random

import gmpy2
from gmpy2 import mpz

__all__ = ["mpz", "inv", "is_prime", "legendre", "sqrt_mod", "nonresidue"]


def inv(a, p):
    """a^{-1} mod p; raises ZeroDivisionError for a = 0 mod p."""
    return gmpy2.invert(a, p)


def is_prime(n) -> bool:
    return bool(gmpy2.is_prime(n, 30))


def legendre(a, p) -> int:
    """Legendre symbol (a/p) for an odd prime p by Euler's criterion: a^((p-1)/2)."""
    a %= p
    if a == 0:
        return 0
    return 1 if gmpy2.powmod(a, (p - 1) // 2, p) == 1 else -1


def nonresidue(p, rng: random.Random | None = None):
    """A quadratic non-residue mod p (random search: half of the elements are)."""
    if p % 4 == 3:
        return p - 1                      # -1 is a non-residue
    if p % 8 == 5:
        return mpz(2)                     # (2/p) = -1 for p = 3, 5 mod 8
    rng = rng or random.Random(int(p))
    while True:
        z = mpz(rng.randrange(2, int(p)))
        if legendre(z, p) == -1:
            return z


def sqrt_mod(a, p, rng: random.Random | None = None):
    """A square root of a mod an odd prime p, or None if a is a non-residue.

    p = 3 (mod 4): r = a^((p+1)/4). Otherwise Tonelli--Shanks: write p - 1 = 2^s q with q
    odd, take a non-residue z; r = a^((q+1)/2), t = a^q, c = z^q. The invariant is
    r^2 = a t, and the order of t in F_p^* is a power of 2 that strictly decreases each
    step, so at most s steps of at most s squarings each are needed.
    """
    a = mpz(a) % p
    if a == 0:
        return mpz(0)
    if legendre(a, p) != 1:
        return None
    if p % 4 == 3:
        return gmpy2.powmod(a, (p + 1) // 4, p)
    q, s = p - 1, 0
    while q % 2 == 0:
        q //= 2
        s += 1
    c = gmpy2.powmod(nonresidue(p, rng), q, p)
    r = gmpy2.powmod(a, (q + 1) // 2, p)
    t = gmpy2.powmod(a, q, p)
    m = s
    while t != 1:
        # the least i with t^(2^i) = 1; 0 < i < m
        i, t2 = 0, t
        while t2 != 1:
            t2 = t2 * t2 % p
            i += 1
        b = c
        for _ in range(m - i - 1):
            b = b * b % p
        r = r * b % p
        c = b * b % p
        t = t * c % p
        m = i
    return r
