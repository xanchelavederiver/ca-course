"""Elementary number theory over Python ints: primality, factorization, congruences.

Everything here is written by hand (the capstone allows "bigints and linear algebra",
not Sage's ``factor`` or ``discrete_log``). The sizes involved are small: the group
orders that :mod:`order` factors have at most ~70 bits.
"""

from __future__ import annotations

import math
import random

# Miller-Rabin with the first 13 prime bases is deterministic below 3.3 * 10^24
# (Sorenson & Webster, 2015); above that it is a strong probable-prime test.
_MR_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41)
_SMALL_PRIMES = [q for q in range(2, 1000) if all(q % d for d in range(2, math.isqrt(q) + 1))]


def is_prime(n: int) -> bool:
    """Miller-Rabin test with fixed bases (deterministic for n < 3.3e24)."""
    if n < 2:
        return False
    for q in _SMALL_PRIMES[:13]:
        if n % q == 0:
            return n == q
    d, s = n - 1, 0
    while d % 2 == 0:
        d, s = d // 2, s + 1
    for a in _MR_BASES:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _pollard_brent(n: int, rng: random.Random) -> int:
    """A non-trivial factor of the odd composite n (Pollard's rho, Brent's variant)."""
    while True:
        y, c, m = rng.randrange(1, n), rng.randrange(1, n), 128
        g = r = q = 1
        while g == 1:
            x = y
            for _ in range(r):
                y = (y * y + c) % n
            k = 0
            while k < r and g == 1:
                ys = y
                for _ in range(min(m, r - k)):
                    y = (y * y + c) % n
                    q = q * abs(x - y) % n
                g = math.gcd(q, n)
                k += m
            r *= 2
        if g == n:                      # the batched gcd overshot: redo it step by step
            g = 1
            while g == 1:
                ys = (ys * ys + c) % n
                g = math.gcd(abs(x - ys), n)
        if g != n:
            return g


def factor(n: int, rng: random.Random | None = None) -> dict[int, int]:
    """Prime factorization {q: e} of n >= 1: trial division by primes < 1000, then rho."""
    rng = rng or random.Random(n)
    out: dict[int, int] = {}
    for q in _SMALL_PRIMES:
        while n % q == 0:
            out[q] = out.get(q, 0) + 1
            n //= q
    stack = [n] if n > 1 else []
    while stack:
        m = stack.pop()
        if is_prime(m):
            out[m] = out.get(m, 0) + 1
            continue
        r = math.isqrt(m)
        if r * r == m:                  # rho cannot split a square of a prime: do it here
            stack += [r, r]
            continue
        d = _pollard_brent(m, rng)
        stack += [d, m // d]
    return dict(sorted(out.items()))


def solve_linear_congruence(u: int, v: int, n: int, limit: int) -> tuple[int, list[int] | None]:
    """All x in [0, n) with u*x = v (mod n).

    Returns ``(d, xs)`` with d = gcd(u, n). There are d solutions when d | v, none
    otherwise. If there are more than ``limit`` of them (a degenerate collision, e.g.
    u = 0 mod n), ``xs`` is None: listing (and checking) them would be pointless.
    """
    u, v = u % n, v % n
    d = math.gcd(u, n)
    if v % d:
        return d, []
    if d > limit:
        return d, None
    n1 = n // d
    x0 = (v // d) * pow(u // d, -1, n1) % n1 if n1 > 1 else 0
    return d, [x0 + t * n1 for t in range(d)]
