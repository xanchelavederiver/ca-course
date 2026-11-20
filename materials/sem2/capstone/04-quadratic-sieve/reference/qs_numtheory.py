"""Elementary number theory for the quadratic sieve, written by hand.

Everything here works on Python ints (the "big integer library" the spec allows).
Nothing is imported from Sage: the reference must not use Sage's ``factor``,
``is_prime``, ``sqrt`` mod p and so on (they are the oracle of the test vectors).
"""

from __future__ import annotations

import math


def primes_up_to(b: int) -> list[int]:
    """All primes p <= b (sieve of Eratosthenes)."""
    if b < 2:
        return []
    sieve = bytearray([1]) * (b + 1)
    sieve[0] = sieve[1] = 0
    for p in range(2, math.isqrt(b) + 1):
        if sieve[p]:
            sieve[p * p::p] = bytes(len(range(p * p, b + 1, p)))
    return [i for i, v in enumerate(sieve) if v]


def legendre(a: int, p: int) -> int:
    """Legendre symbol (a/p) for an odd prime p, by Euler's criterion: a^((p-1)/2) mod p."""
    a %= p
    if a == 0:
        return 0
    return 1 if pow(a, (p - 1) // 2, p) == 1 else -1


def sqrt_mod_prime(a: int, p: int) -> int:
    """A square root of a quadratic residue a modulo a prime p (Tonelli--Shanks).

    Returns r with r^2 = a (mod p), 0 <= r < p; the other root is p - r.
    """
    a %= p
    if p == 2 or a == 0:
        return a
    if legendre(a, p) != 1:
        raise ValueError(f"{a} is not a square modulo {p}")
    if p % 4 == 3:                       # the easy case: r = a^((p+1)/4)
        return pow(a, (p + 1) // 4, p)
    # p - 1 = q * 2^s with q odd
    q, s = p - 1, 0
    while q % 2 == 0:
        q //= 2
        s += 1
    z = 2                                # a quadratic non-residue
    while legendre(z, p) != -1:
        z += 1
    m, c, t, r = s, pow(z, q, p), pow(a, q, p), pow(a, (q + 1) // 2, p)
    # invariant: r^2 = a * t (mod p), ord(t) | 2^(m-1), c generates the 2^m part
    while t != 1:
        i, t2 = 0, t
        while t2 != 1:                   # least i with t^(2^i) = 1
            t2 = t2 * t2 % p
            i += 1
        b = pow(c, 1 << (m - i - 1), p)
        m, c = i, b * b % p
        t, r = t * c % p, r * b % p
    return r


def lift_root(r: int, n: int, p: int, k: int) -> int:
    """Hensel lifting: from r^2 = n (mod p^k), p odd, p !| n, get r' = r (mod p^k)
    with r'^2 = n (mod p^(k+1))."""
    pk1 = p ** (k + 1)
    # r' = r - (r^2 - n) / (2r)  (mod p^(k+1)); the inverse exists since p !| 2r
    return (r - (r * r - n) * pow(2 * r, -1, pk1)) % pk1


def is_probable_prime(n: int) -> bool:
    """Miller--Rabin with the first 20 prime bases.

    Deterministic for n < 3.3 * 10^24 (the first 13 bases suffice there); for larger n
    the error probability is below 4^-20, far beyond the sizes of this capstone.
    """
    if n < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71)
    for p in small:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in small:
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


def iroot(n: int, k: int) -> int:
    """floor(n^(1/k)) for n >= 0 (Newton's method on integers)."""
    if n < 2 or k == 1:
        return n
    x = 1 << ((n.bit_length() + k - 1) // k)        # x >= n^(1/k)
    while True:
        y = ((k - 1) * x + n // x ** (k - 1)) // k
        if y >= x:
            return x
        x = y


def perfect_power(n: int) -> tuple[int, int] | None:
    """(m, k) with n = m^k, k >= 2 and k as large as possible (m minimal), or None.

    The quadratic sieve cannot split a prime power n = p^k: the group (Z/p^k Z)^* is
    cyclic, so x^2 = y^2 (mod n) with gcd(xy, n) = 1 forces x = +-y and gcd(x - y, n)
    is trivial. Perfect powers are therefore detected before sieving.
    """
    for k in range(n.bit_length(), 1, -1):
        m = iroot(n, k)
        if m > 1 and m ** k == n:
            return m, k
    return None
