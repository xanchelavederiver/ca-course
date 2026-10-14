"""Small pure-Python number theory helpers.

Used for *sampling* (Sage's own random functions use a global RNG and would
break determinism) and for *independent* self-checks of answers that the
tasks compute with Sage.
"""

from __future__ import annotations

import random
from functools import lru_cache
from math import gcd, isqrt


@lru_cache(maxsize=None)
def first_primes(n: int) -> tuple[int, ...]:
    """The first ``n`` primes (``first_primes(100)[-1] == 541``)."""
    out: list[int] = []
    k = 2
    while len(out) < n:
        if all(k % p for p in out if p * p <= k):
            out.append(k)
        k += 1
    return tuple(out)


_MR_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)


def is_prime(n: int) -> bool:
    """Deterministic Miller–Rabin for n < 3.18e23 (bases 2..37; the least counterexample is
    318665857834031151167461)."""
    if n < 2:
        return False
    for p in _MR_BASES:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
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


def random_prime(rng: random.Random, lo: int, hi: int) -> int:
    """Uniformly random prime in ``[lo, hi]`` (rejection sampling)."""
    for _ in range(100_000):
        k = rng.randint(lo, hi)
        if is_prime(k):
            return k
    raise ValueError(f"no prime found in [{lo}, {hi}]")


def factorize(n: int) -> dict[int, int]:
    """Trial-division factorization (small n only)."""
    f: dict[int, int] = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            f[d] = f.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        f[n] = f.get(n, 0) + 1
    return f


def is_order(g: int, o: int, p: int) -> bool:
    """True iff the multiplicative order of g mod p is exactly o."""
    if pow(g, o, p) != 1:
        return False
    return all(pow(g, o // q, p) != 1 for q in factorize(o))


def is_square_mod(a: int, p: int) -> bool:
    a %= p
    return a == 0 or pow(a, (p - 1) // 2, p) == 1


def inverse(a: int, m: int) -> int:
    return pow(a, -1, m)


__all__ = ["first_primes", "is_prime", "random_prime", "factorize", "is_order",
           "is_square_mod", "inverse", "gcd", "isqrt"]
