"""Integer helpers: small primes, modular inversion that reports a factor, primality, roots.

Only Python integers (bigints) are used. The one operation that matters for ECM is
:func:`inv`: when an element of Z/nZ is not invertible, it raises :class:`NotInvertible`
carrying ``gcd(x, n)``, which is exactly how Lenstra's algorithm finds a factor.
"""

from __future__ import annotations

import math
import random

# Miller-Rabin with these bases is deterministic for n < 3.3 * 10^24 (about 2^81).
MR_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41)
MR_DETERMINISTIC_BOUND = 3_317_044_064_679_887_385_961_981
MR_EXTRA_ROUNDS = 24          # random bases on top of MR_BASES above that bound


class NotInvertible(ArithmeticError):
    """``x`` has no inverse modulo ``n``; ``d = gcd(x, n) > 1`` (possibly ``d == n``)."""

    def __init__(self, d: int, n: int):
        super().__init__(f"not invertible modulo {n}: gcd = {d}")
        self.d, self.n = d, n


def inv(x: int, n: int) -> int:
    """Inverse of ``x`` modulo ``n``, or :class:`NotInvertible` with ``gcd(x, n)``."""
    try:
        return pow(x, -1, n)
    except ValueError:
        raise NotInvertible(math.gcd(x, n), n) from None


def batch_inv(xs: list[int], n: int) -> list[int]:
    """Inverses of all ``xs`` modulo ``n`` with one inversion (Montgomery's trick).

    If some ``x`` is not invertible, raises :class:`NotInvertible` with the gcd of the
    first such element (so a proper factor is reported whenever one element yields it).
    """
    prefix = [1] * (len(xs) + 1)
    for i, x in enumerate(xs):
        prefix[i + 1] = prefix[i] * x % n
    try:
        t = inv(prefix[-1], n)
    except NotInvertible:
        # Find the culprit: a proper factor if any single x gives one.
        gs = [math.gcd(x, n) for x in xs]
        proper = [g for g in gs if 1 < g < n]
        raise NotInvertible(proper[0] if proper else n, n) from None
    out = [0] * len(xs)
    for i in range(len(xs) - 1, -1, -1):
        out[i] = prefix[i] * t % n
        t = t * xs[i] % n
    return out


def primes_up_to(limit: int) -> list[int]:
    """All primes ``<= limit`` (sieve of Eratosthenes)."""
    if limit < 2:
        return []
    sieve = bytearray([1]) * (limit + 1)
    sieve[0:2] = b"\0\0"
    for p in range(2, math.isqrt(limit) + 1):
        if sieve[p]:
            sieve[p * p:: p] = bytes(len(range(p * p, limit + 1, p)))
    return [i for i, f in enumerate(sieve) if f]


SMALL_PRIMES = primes_up_to(1000)


def _strong_probable_prime(n: int, a: int, d: int, s: int) -> bool:
    x = pow(a, d, n)
    if x in (1, n - 1):
        return True
    for _ in range(s - 1):
        x = x * x % n
        if x == n - 1:
            return True
    return False


def is_prime(n: int, rng: random.Random | None = None) -> bool:
    """Miller-Rabin: deterministic below ``MR_DETERMINISTIC_BOUND``; above it, the 13
    fixed bases plus ``MR_EXTRA_ROUNDS`` random ones (error < 4^-37 for composites)."""
    if n < 2:
        return False
    for p in SMALL_PRIMES[:30]:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d, s = d // 2, s + 1
    if not all(_strong_probable_prime(n, a, d, s) for a in MR_BASES):
        return False
    if n < MR_DETERMINISTIC_BOUND:
        return True
    rng = rng or random.Random(n)
    return all(_strong_probable_prime(n, rng.randrange(2, n - 1), d, s)
               for _ in range(MR_EXTRA_ROUNDS))


def iroot(n: int, k: int) -> int:
    """``floor(n ** (1/k))`` for ``n >= 0`` (Newton's method on integers)."""
    if n < 2:
        return n
    x = 1 << ((n.bit_length() + k - 1) // k)      # an upper bound for the root
    while True:
        y = ((k - 1) * x + n // x ** (k - 1)) // k
        if y >= x:
            return x
        x = y


def perfect_power(n: int) -> tuple[int, int] | None:
    """``(r, k)`` with ``n = r^k``, ``k >= 2`` maximal, or None if ``n`` is not a power."""
    best = None
    for k in primes_up_to(max(2, n.bit_length())):
        r = iroot(n, k)
        if r > 1 and r ** k == n:
            best = (r, k)
    if best is None:
        return None
    r, k = best
    sub = perfect_power(r)                        # n = (s^j)^k
    return (sub[0], sub[1] * k) if sub else best
