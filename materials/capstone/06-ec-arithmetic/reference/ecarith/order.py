"""#E(F_p): the naive count and the Shanks--Mestre method (Crandall--Pomerance, 7.5.1).

By Hasse, #E = p + 1 - t with |t| <= 2 sqrt(p), so #E lies in the interval
[p + 1 - 2 sqrt(p), p + 1 + 2 sqrt(p)] of length about 4 sqrt(p). For a point P,
baby steps / giant steps (Shanks) find every m in the interval with [m]P = O in
O(p^(1/4)) group operations. If exactly one m is found, #E = m. If P has a small
order there are several m, and we try another point.

Mestre's theorem: for p > 229, the curve E or its quadratic twist E' has a point
whose order has a unique multiple in the Hasse interval. A random x gives a point on
E if f(x) = x^3 + a x + b is a square and a point on the twist otherwise, and
#E + #E' = 2p + 2, so a unique answer for either curve gives #E.
"""

from __future__ import annotations

import random

import gmpy2

from .curve import Curve, CurveError
from .field import legendre, mpz, nonresidue, sqrt_mod
from .scalar import mul_binary

MESTRE_BOUND = 229        # Mestre's theorem needs p > 229; below it, count naively
MAX_ATTEMPTS = 1000


def hasse_interval(p) -> tuple[int, int]:
    """[p + 1 - floor(2 sqrt p), p + 1 + floor(2 sqrt p)] (floor(2 sqrt p) = isqrt(4p))."""
    w = gmpy2.isqrt(4 * mpz(p))
    return int(p + 1 - w), int(p + 1 + w)


def order_naive(E: Curve) -> int:
    """#E = 1 + sum_x (1 + (f(x)/p)) = p + 1 + sum_x (f(x)/p), O(p) Legendre symbols."""
    p = E.p
    return int(p + 1 + sum(legendre(E.rhs(mpz(x)), p) for x in range(int(p))))


def multiples_in_interval(E: Curve, P, lo: int, hi: int) -> list[int] | None:
    """All m in [lo, hi] with [m]P = O, by baby steps / giant steps.

    Baby steps: [j]P for j = 1..W, stored by x-coordinate. Giant steps: G = [c]P for the
    centres c = lo + W, lo + W + (2W+1), ... A baby step with x([j]P) = x(G) means
    [j]P = -G (then m = c + j) or [j]P = G (then m = c - j), so each giant step covers
    the 2W + 1 values c - W..c + W. Returns None if P has order <= 2W (then a window
    may contain several m, and the point is useless for counting anyway).
    """
    span = hi - lo + 1
    W = max(1, int(gmpy2.isqrt(span // 2)) + 1)
    table: dict = {}
    Q = None
    for j in range(1, W + 1):
        Q = E.add(Q, P)
        if Q is None or Q[0] in table:
            return None                   # [j]P = O or [j]P = +-[i]P: ord(P) <= 2W
        table[Q[0]] = (j, Q[1])
    step = 2 * W + 1
    S = mul_binary(E, P, step)
    c = lo + W
    G = mul_binary(E, P, c)
    found = []
    while c - W <= hi:
        if G is None:
            m = c
        else:
            hit = table.get(G[0])
            m = None
            if hit is not None:
                j, y = hit
                m = c + j if (y + G[1]) % E.p == 0 else c - j
        if m is not None and lo <= m <= hi:
            found.append(m)
        G = E.add(G, S)
        c += step
    return found


def twist(E: Curve):
    """The quadratic twist E': y^2 = x^3 + a d^2 x + b d^3 with a non-residue d.
    The point of E' over x is (d x, d sqrt(d f(x))) when f(x) is a non-residue."""
    p = E.p
    d = nonresidue(p)
    return Curve(p, E.a * d * d, E.b * d * d * d, check=False), d


def order_shanks_mestre(E: Curve, rng: random.Random | None = None) -> tuple[int, dict]:
    """#E by Shanks--Mestre; returns (order, extra data on how it was found)."""
    p = E.p
    if p <= MESTRE_BOUND:
        return order_naive(E), {"method": "naive", "reason": f"p <= {MESTRE_BOUND}"}
    rng = rng or random.Random(int(p) ^ int(E.a) ^ int(E.b))
    lo, hi = hasse_interval(p)
    Et, d = twist(E)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        x = mpz(rng.randrange(int(p)))
        r = E.rhs(x)
        chi = legendre(r, p)
        if chi == 0:
            continue                       # (x, 0) has order 2
        if chi == 1:
            P, curve = (x, sqrt_mod(r, p, rng)), E
        else:
            # d f(x) is a square; d^3 f(x) = d^2 (d f(x)) is the twist's right-hand side at d x
            P, curve = (d * x % p, d * sqrt_mod(d * r, p, rng) % p), Et
        ms = multiples_in_interval(curve, P, lo, hi)
        if ms is not None and len(ms) == 1:
            m = ms[0]
            order = m if curve is E else 2 * int(p) + 2 - m
            return order, {"method": "shanks-mestre", "attempts": attempt,
                           "curve": "E" if curve is E else "twist", "point": [int(P[0]), int(P[1])],
                           "trace": int(p) + 1 - order}
    raise CurveError(f"Shanks--Mestre failed after {MAX_ATTEMPTS} points")
