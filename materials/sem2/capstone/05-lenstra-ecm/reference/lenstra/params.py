"""Choosing the bounds B1, B2 and the number of curves from the expected factor size.

For a prime factor ``p`` the optimal stage-1 bound is asymptotically
``L_p[1/2, 1/sqrt 2] = exp(sqrt(ln p * ln ln p / 2))`` (Lenstra; C&P sec. 7.4.1). A curve
succeeds when ``#E(F_p)`` --- a number of about ``p / t`` after removing the known torsion
factor ``t`` (12 or 16 for the special families) --- is B1-smooth, except for at most one
prime in ``(B1, B2]`` when stage 2 is on. Heuristically ``#E(F_p)`` behaves like a random
integer of that size, so the success probability is the semismooth probability

    G(alpha, beta) = rho(alpha) + integral_1^beta rho(alpha - lam) / lam  d lam,
    alpha = ln(p / t) / ln B1,   beta = ln B2 / ln B1,

with Dickman's function ``rho``, and the expected number of curves is ``1 / G``. Each
level takes the B1 (from a 1-1.5-2-3-5-7 grid; B2 = 100 B1) that minimises the expected
work ``curve_cost(B1, B2) / G``.

The algorithm does not know ``p``. It runs *levels*: factor sizes of 12, 16, 20, ... bits,
each with its B1, B2 and expected number of curves, up to half the size of the number
(a composite has a factor of at most that size), and then repeats the last level.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

TORSION = {"weierstrass": 1, "suyama": 12, "z2z8": 16}
B2_FACTOR = 100            # B2 = 100 * B1, a common choice for the standard stage 2
LEVEL_STEP = 4             # bits between levels
FIRST_LEVEL = 12           # bits of the first level (smaller factors fall out of it too)

_H = 0.01                  # step of the rho table


@lru_cache(maxsize=1)
def _rho_table(umax: int = 30) -> list[float]:
    """rho(u) on a grid of step _H: rho = 1 on [0, 1], u rho'(u) = -rho(u - 1)."""
    m = round(1 / _H)
    r = [1.0] * (m + 1)
    for i in range(m + 1, round(umax / _H) + 1):
        u0, u1 = (i - 1) * _H, i * _H
        # trapezoid rule for rho(u1) = rho(u0) - integral_{u0}^{u1} rho(t - 1) / t dt
        r.append(r[-1] - _H / 2 * (r[i - 1 - m] / u0 + r[i - m] / u1))
    return r


def rho(u: float) -> float:
    """Dickman's function (linear interpolation in the table)."""
    if u <= 1:
        return 1.0
    t = _rho_table()
    x = u / _H
    i = int(x)
    if i + 1 >= len(t):
        return 0.0
    return t[i] + (x - i) * (t[i + 1] - t[i])


def semismooth(alpha: float, beta: float) -> float:
    """G(alpha, beta): probability of B1-smooth times at most one prime in (B1, B2]."""
    g = rho(alpha)
    if beta > 1:
        hi = min(beta, alpha)
        k = 64
        h = (hi - 1) / k
        if h > 0:                    # Simpson's rule
            f = [rho(alpha - (1 + i * h)) / (1 + i * h) for i in range(k + 1)]
            g += h / 3 * (f[0] + f[-1] + 4 * sum(f[1:-1:2]) + 2 * sum(f[2:-1:2]))
    return g


def b1_asymptotic(bits: int) -> float:
    """``L_p[1/2, 1/sqrt 2] = exp(sqrt(ln p ln ln p / 2))`` for a ``bits``-bit prime p."""
    lp = bits * math.log(2)
    return math.exp(math.sqrt(lp * math.log(lp) / 2))


# Candidate bounds: 1-1.5-2-3-5-7 x 10^k (the asymptotic B1 is only a guide: the constants
# matter at these sizes, so the level picks the candidate of least expected work).
B1_GRID = tuple(m * 10 ** k for k in range(1, 8) for m in (1, 1.5, 2, 3, 5, 7) if m * 10 ** k >= 50)


def curve_cost(B1: int, B2: int) -> float:
    """Work of one curve in ladder steps (about 10 modular multiplications each): stage 1
    takes ``log2(prod p^e) ~ 1.44 B1`` steps; stage 2 one multiplication per prime in
    ``(B1, B2]`` (0.14 steps with the +-j pairing) plus the giant steps."""
    c = 1.44 * B1
    if B2 > B1:
        c += 0.14 * (B2 / math.log(B2) - B1 / math.log(B1)) + 0.6 * B2 / 2310
    return c


@dataclass(frozen=True)
class Level:
    bits: int          # target factor size
    B1: int
    B2: int            # = B1 when stage 2 is off
    curves: int        # expected number of curves for a factor of `bits` bits


@lru_cache(maxsize=256)
def level(bits: int, family: str, stage2: bool = True) -> Level:
    """The bounds of least expected work ``curves(B1) * curve_cost(B1)`` for a factor of
    ``bits`` bits, where ``curves = 1 / G`` is the expected number of curves."""
    best = None
    for B1 in B1_GRID:
        B1 = int(B1)
        B2 = B2_FACTOR * B1 if stage2 else B1
        lnB1 = math.log(B1)
        alpha = max(0.0, bits * math.log(2) - math.log(TORSION[family])) / lnB1
        curves = max(1, math.ceil(1 / max(semismooth(alpha, math.log(B2) / lnB1), 1e-300)))
        work = curves * curve_cost(B1, B2)
        if best is None or work < best[0]:
            best = (work, Level(bits, B1, B2, curves))
    return best[1]


def schedule(n_bits: int, family: str, stage2: bool = True, start_bits: int | None = None):
    """Infinite sequence of levels for a composite of ``n_bits`` bits."""
    top = max(FIRST_LEVEL, math.ceil(n_bits / 2))
    t = FIRST_LEVEL if start_bits is None else max(FIRST_LEVEL, start_bits)
    while True:
        yield level(min(t, top), family, stage2)
        t += LEVEL_STEP
