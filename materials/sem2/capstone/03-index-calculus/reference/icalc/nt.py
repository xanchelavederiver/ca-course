"""Elementary number theory by hand: primes, primality, factoring p - 1, CRT, primitive roots.

Nothing here calls Sage: the index-calculus reference may use bigints (Python ints,
gmpy2) and linear algebra, but not Sage's ``factor``/``discrete_log``/``primitive_root``.
"""

from __future__ import annotations

import math
import random

SMALL_PRIMES = None  # filled lazily by _small_primes()


def primes_up_to(n: int) -> list[int]:
    """All primes <= n (sieve of Eratosthenes on a bytearray)."""
    if n < 2:
        return []
    sieve = bytearray([1]) * (n + 1)
    sieve[0] = sieve[1] = 0
    for i in range(2, math.isqrt(n) + 1):
        if sieve[i]:
            sieve[i * i:: i] = bytes(len(range(i * i, n + 1, i)))
    return [i for i in range(n + 1) if sieve[i]]


def _small_primes() -> list[int]:
    global SMALL_PRIMES
    if SMALL_PRIMES is None:
        SMALL_PRIMES = primes_up_to(10_000)
    return SMALL_PRIMES


def is_probable_prime(n: int) -> bool:
    """Miller--Rabin with the first 20 prime bases (deterministic below 3.3e24, and
    an error probability below 4^-20 above that)."""
    if n < 2:
        return False
    for q in _small_primes()[:20]:
        if n % q == 0:
            return n == q
    d, s = n - 1, 0
    while d % 2 == 0:
        d, s = d // 2, s + 1
    for a in _small_primes()[:20]:
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
    """A non-trivial factor of the odd composite n (Pollard rho, Brent's variant)."""
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
        if g == n:                      # overshot: redo the last block one step at a time
            g = 1
            while g == 1:
                ys = (ys * ys + c) % n
                g = math.gcd(abs(x - ys), n)
        if g != n:
            return g


def factorize(n: int, seed: int = 1) -> dict[int, int]:
    """{prime: exponent} of n >= 1: trial division by primes < 10^4, then Pollard rho."""
    out: dict[int, int] = {}
    for q in _small_primes():
        if q * q > n:
            break
        while n % q == 0:
            out[q] = out.get(q, 0) + 1
            n //= q
    rng = random.Random(seed)
    stack = [n] if n > 1 else []
    while stack:
        m = stack.pop()
        if is_probable_prime(m):
            out[m] = out.get(m, 0) + 1
            continue
        r = math.isqrt(m)
        if r * r == m:                  # rho cannot split a perfect square of a prime
            stack += [r, r]
            continue
        d = _pollard_brent(m, rng)
        stack += [d, m // d]
    return dict(sorted(out.items()))


def crt(residues: list[int], moduli: list[int]) -> tuple[int, int]:
    """x mod M with x = r_i (mod m_i) for pairwise coprime m_i; returns (x, M)."""
    x, mod = 0, 1
    for r, m in zip(residues, moduli):
        # x + mod*t = r (mod m)  =>  t = (r - x) * mod^{-1} (mod m)
        t = (r - x) * pow(mod, -1, m) % m
        x, mod = x + mod * t, mod * m
    return x % mod, mod


def element_order(a: int, p: int, n_factors: dict[int, int]) -> int:
    """Multiplicative order of a mod p, given the factorization of p - 1."""
    order = p - 1
    for q, e in n_factors.items():
        for _ in range(e):
            if pow(a, order // q, p) == 1:
                order //= q
            else:
                break
    return order


def is_primitive_root(a: int, p: int, n_factors: dict[int, int]) -> bool:
    return a % p != 0 and all(pow(a, (p - 1) // q, p) != 1 for q in n_factors)


def primitive_root(p: int, n_factors: dict[int, int]) -> int:
    """The least primitive root modulo the prime p."""
    for a in range(2, p):
        if is_primitive_root(a, p, n_factors):
            return a
    return 1                            # p = 2: the group is trivial
