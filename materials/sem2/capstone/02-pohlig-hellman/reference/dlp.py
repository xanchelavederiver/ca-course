"""Discrete logarithms in (Z/pZ)^* by the Pohlig--Hellman reduction.

Problem: given a prime p, a base g and an element h of (Z/pZ)^*, find x with
g^x = h (mod p).  Let n = ord(g) = q_1^e_1 ... q_t^e_t.  The reduction has three levels,
one per item of the spec's «Требуемый функционал»:

1. prime order q: brute force (:func:`dlog_brute`) or Shanks' baby-step giant-step
   (:func:`dlog_bsgs`, O(sqrt q) time and memory);
2. prime-power order q^e: reduction to e problems in the subgroup of order q
   (:func:`dlog_prime_power`), the x_i = d_0 + d_1 q + ... + d_{e-1} q^{e-1} digit by digit;
3. composite order n: one problem of order q_i^e_i per prime (g_i = g^(n/q_i^e_i),
   h_i = h^(n/q_i^e_i)), glued by the CRT (:func:`pohlig_hellman`).

Only Python integers are used (the spec allows big-integer libraries): ``pow`` for modular
powers and inverses.  No CAS discrete-log or factorization routine is called.  The
factorization of p - 1 is normally part of the input; :func:`factor` (trial division +
Pollard--Brent rho + Miller--Rabin) is a fallback for inputs that omit it.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

# Below this subgroup order, brute force beats building a baby-step table.
BRUTE_MAX = 64


class DlogError(ValueError):
    """The instance is malformed or has no solution."""


# --- level 1: prime order ---------------------------------------------------------------

def dlog_brute(g: int, h: int, q: int, p: int) -> int:
    """x in [0, q) with g^x = h (mod p), by trying x = 0, 1, ..., q - 1."""
    e = 1
    for x in range(q):
        if e == h:
            return x
        e = e * g % p
    raise DlogError(f"{h} is not a power of {g} modulo {p}")


class BabySteps:
    """Shanks' baby-step table {g^j: j} for 0 <= j < m, m = ceil(sqrt(q)).

    The table depends only on the base, so in the prime-power reduction it is built once
    per prime q and reused for every digit (all digits are logs to the same base
    gamma = g^(n/q) of order q).
    """

    def __init__(self, g: int, q: int, p: int):
        self.p, self.q = p, q
        self.m = math.isqrt(q - 1) + 1          # m^2 >= q
        table: dict[int, int] = {}
        e = 1
        for j in range(self.m):
            table.setdefault(e, j)              # keep the smallest j (g may have order < m)
            e = e * g % p
        self.table = table
        self.giant = pow(g, -self.m, p)         # g^(-m)

    def log(self, h: int) -> int:
        """x in [0, q) with g^x = h: write x = i m + j and look up h g^(-i m)."""
        y = h
        for i in range(self.m):
            j = self.table.get(y)
            if j is not None:
                return (i * self.m + j) % self.q
            y = y * self.giant % self.p
        raise DlogError(f"{h} is not in the subgroup of order {self.q} modulo {self.p}")


def dlog_bsgs(g: int, h: int, q: int, p: int) -> int:
    """x in [0, q) with g^x = h (mod p), g of order q, by baby-step giant-step."""
    return BabySteps(g, q, p).log(h)


def prime_solver(gamma: int, q: int, p: int, method: str = "auto"):
    """A function h -> log_gamma h in the subgroup of prime order q, and its name."""
    if method == "brute" or (method == "auto" and q <= BRUTE_MAX):
        return (lambda h: dlog_brute(gamma, h, q, p)), "brute"
    if method in ("auto", "bsgs"):
        return BabySteps(gamma, q, p).log, "bsgs"
    raise DlogError(f"unknown prime-order method {method!r} (auto | brute | bsgs)")


# --- level 2: prime-power order ---------------------------------------------------------

@dataclass
class Subproblem:
    """One prime-power subproblem g_i^{x_i} = h_i of order q^e and how it was solved."""
    q: int
    e: int
    g: int
    h: int
    x: int = 0
    digits: list[int] = field(default_factory=list)   # x = sum digits[k] q^k (reduction only)
    method: str = ""

    def as_dict(self) -> dict:
        return {"q": self.q, "e": self.e, "modulus": self.q ** self.e, "g": self.g,
                "h": self.h, "x": self.x, "digits": self.digits, "method": self.method}


def dlog_prime_power(g: int, h: int, q: int, e: int, p: int, prime_method: str = "auto",
                     reduce: bool = True) -> Subproblem:
    """x in [0, q^e) with g^x = h (mod p), g of order exactly q^e.

    With ``reduce`` (the spec's «сведение к собственным подгруппам»): write
    x = d_0 + d_1 q + ... + d_{e-1} q^{e-1}.  With gamma = g^(q^(e-1)) of order q,
    raising g^x = h to the power q^(e-1-k) after removing the known digits gives
    gamma^{d_k} = (h g^{-(d_0 + ... + d_{k-1} q^{k-1})})^(q^(e-1-k)),
    a DLP of prime order q for each digit.  Without ``reduce``, the whole problem of order
    q^e goes to the prime-order method directly (the fallback of the spec's remark 2).
    """
    sp = Subproblem(q, e, g, h)
    n = q ** e
    if not reduce or e == 1:
        if e == 1:
            solve, sp.method = prime_solver(g, q, p, prime_method)
        else:
            # BSGS / brute force work for any cyclic group order, not only primes.
            solve, sp.method = prime_solver(g, n, p, prime_method)
            sp.method += "-direct"
        sp.x = solve(h)
        sp.digits = [sp.x] if e == 1 else []
        return sp
    gamma = pow(g, n // q, p)                   # order q
    solve, sp.method = prime_solver(gamma, q, p, prime_method)
    g_inv = pow(g, -1, p)
    x, qk = 0, 1                                # x = d_0 + ... + d_{k-1} q^{k-1}, qk = q^k
    for k in range(e):
        # h * g^(-x) = g^(d_k q^k + ...) lies in the subgroup of order q^(e-k)
        hk = pow(h * pow(g_inv, x, p) % p, n // (qk * q), p)
        d = solve(hk)
        sp.digits.append(d)
        x += d * qk
        qk *= q
    sp.x = x
    return sp


# --- level 3: composite order, CRT ------------------------------------------------------

def crt(residues: list[int], moduli: list[int]) -> int:
    """The x in [0, prod moduli) with x = r_i (mod m_i), pairwise coprime m_i (Garner)."""
    x, m = 0, 1
    for r, mi in zip(residues, moduli):
        # x + m t = r (mod mi)  =>  t = (r - x) m^{-1} (mod mi)
        t = (r - x) * pow(m, -1, mi) % mi
        x, m = x + m * t, m * mi
    return x % m


def element_order(g: int, p: int, group_factors: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Factorization of ord(g) in (Z/pZ)^*, given that of the group order p - 1.

    Start from n = p - 1 and, for every prime q, divide n by q while g^(n/q) = 1.
    """
    n = 1
    for q, e in group_factors:
        n *= q ** e
    out = []
    for q, e in group_factors:
        while e and pow(g, n // q, p) == 1:
            n //= q
            e -= 1
        if e:
            out.append((q, e))
    return out


@dataclass
class Solution:
    x: int
    order: int
    order_factors: list[tuple[int, int]]
    subproblems: list[Subproblem]
    factorization: str                         # "input" | "solver"

    def extra(self) -> dict:
        return {
            "order": self.order,
            "order_factors": [[q, e] for q, e in self.order_factors],
            "factorization": self.factorization,
            # the reduced system x = x_i (mod q_i^e_i)
            "congruences": [[s.x, s.q ** s.e] for s in self.subproblems],
            "subproblems": [s.as_dict() for s in self.subproblems],
        }


def pohlig_hellman(p: int, g: int, h: int, group_factors: list[tuple[int, int]] | None = None,
                   prime_method: str = "auto", reduce: bool = True) -> Solution:
    """The smallest x >= 0 with g^x = h (mod p), by the Pohlig--Hellman reduction.

    ``group_factors``: the factorization [(q, e), ...] of p - 1 (factored here if None).
    """
    source = "input"
    if group_factors is None:
        group_factors, source = factor(p - 1), "solver"
    g, h = g % p, h % p
    if g == 0 or h == 0:
        raise DlogError("g and h must be invertible modulo p")
    of = element_order(g, p, group_factors)
    n = math.prod(q ** e for q, e in of)
    # (Z/pZ)^* is cyclic, so h lies in <g> iff h^ord(g) = 1.
    if pow(h, n, p) != 1:
        raise DlogError(f"h is not in the subgroup <g> of order {n}: no solution")
    subs = []
    for q, e in of:
        c = n // q ** e                         # g_i = g^c has order q^e
        subs.append(dlog_prime_power(pow(g, c, p), pow(h, c, p), q, e, p, prime_method, reduce))
    x = crt([s.x for s in subs], [s.q ** s.e for s in subs])
    assert pow(g, x, p) == h, "internal error: the CRT solution does not check"
    return Solution(x, n, of, subs, source)


# --- factorization of p - 1 (fallback when the input does not carry it) -----------------

_SMALL_PRIMES = [q for q in range(2, 1000) if all(q % d for d in range(2, math.isqrt(q) + 1))]


def is_probable_prime(n: int, rounds: int = 32) -> bool:
    """Miller--Rabin with fixed small-prime bases plus seeded random ones."""
    if n < 2:
        return False
    for q in _SMALL_PRIMES[:25]:
        if n % q == 0:
            return n == q
    d, s = n - 1, 0
    while d % 2 == 0:
        d, s = d // 2, s + 1
    rng = random.Random(n)                      # deterministic for a given n
    bases = _SMALL_PRIMES[:12] + [rng.randrange(2, n - 1) for _ in range(rounds - 12)]
    for a in bases:
        y = pow(a, d, n)
        if y in (1, n - 1):
            continue
        for _ in range(s - 1):
            y = y * y % n
            if y == n - 1:
                break
        else:
            return False
    return True


def _rho(n: int, rng: random.Random) -> int:
    """A non-trivial factor of the odd composite n (Pollard--Brent rho, batched gcd)."""
    while True:
        c, y, m = rng.randrange(1, n), rng.randrange(n), 128
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
        if g == n:                              # the batch overshot: redo it step by step
            g = 1
            while g == 1:
                ys = (ys * ys + c) % n
                g = math.gcd(abs(x - ys), n)
        if g != n:
            return g


def factor(n: int) -> list[tuple[int, int]]:
    """Factorization [(q, e), ...] of n >= 1 with q increasing."""
    out: dict[int, int] = {}
    for q in _SMALL_PRIMES:
        while n % q == 0:
            out[q] = out.get(q, 0) + 1
            n //= q
    stack, rng = [n] if n > 1 else [], random.Random(n)
    while stack:
        m = stack.pop()
        if is_probable_prime(m):
            out[m] = out.get(m, 0) + 1
            continue
        d = _rho(m, rng)
        stack += [d, m // d]
    return sorted(out.items())
