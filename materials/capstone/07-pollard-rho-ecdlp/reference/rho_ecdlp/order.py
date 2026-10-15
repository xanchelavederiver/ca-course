"""ord(P) by the Shanks-Mestre baby-step giant-step method (item 2 of the spec).

Hasse: #E(F_p) = p + 1 - t with |t| <= 2 sqrt(p), and [#E]P = O. A BSGS over the
Hasse interval [L, H] = [p + 1 - 2 sqrt(p), p + 1 + 2 sqrt(p)] finds some M in it
with [M]P = O in O(p^{1/4}) group operations, so ord(P) divides M. Then factor M and
strip prime factors q while [M/q]P = O: what is left is exactly ord(P).

(M need not be #E when ord(P) is small, since several multiples of ord(P) may lie in
the interval; ord(P) is still correct, and that is all the rho algorithm needs. The
answer to the footnote: rho solves the final congruence modulo n = ord(P).)
"""

from __future__ import annotations

import math

from .ec import Curve, Point
from .ntheory import factor


def multiple_in_hasse_interval(E: Curve, P: Point) -> tuple[int, dict]:
    """Some M in the Hasse interval with [M]P = O, by baby steps / giant steps."""
    p = E.p
    r = math.isqrt(4 * p) + 1           # ceil(2 sqrt(p)) or one more: a safe radius
    lo, hi = max(1, p + 1 - r), p + 1 + r
    m = math.isqrt(hi - lo) + 1         # m^2 > hi - lo: the giant steps cover [lo, hi]
    # Baby steps: [j]P -> j for j = 0..m-1 (the first j wins if [j]P repeats).
    baby: dict = {}
    R: Point = None
    for j in range(m):
        baby.setdefault(R, j)
        R = E.add(R, P)
    # Giant steps: [lo + i m]P = -[j]P  <=>  [lo + i m + j]P = O.
    step = E.neg(E.mul(m, P))           # -[m]P: walk -[lo + i m]P downwards
    G = E.neg(E.mul(lo, P))
    for i in range(m + 1):
        j = baby.get(G)
        if j is not None:
            M = lo + i * m + j
            return M, {"interval": [lo, hi], "baby_steps": m, "giant_steps": i + 1}
        G = E.add(G, step)
    raise ArithmeticError("no multiple of ord(P) in the Hasse interval: is the curve valid?")


def point_order(E: Curve, P: Point) -> tuple[int, dict]:
    """(ord(P), intermediate data)."""
    if P is None:
        return 1, {"method": "trivial"}
    if E.p < 1000:                      # tiny fields: just count
        n, R = 1, P
        while R is not None:
            R, n = E.add(R, P), n + 1
        return n, {"method": "naive"}
    M, info = multiple_in_hasse_interval(E, P)
    fac = factor(M)
    n = M
    for q in fac:
        while n % q == 0 and E.mul(n // q, P) is None:
            n //= q
    return n, {"method": "shanks-mestre", "M": M, "M_factors": [[q, e] for q, e in fac.items()], **info}
