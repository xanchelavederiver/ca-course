"""Lenstra's elliptic curve method: one curve (stage 1 + stage 2), a factor, a factorization.

Stage 1 multiplies the starting point by every prime power ``p^e <= B1`` (or, in the
textbook variant of HPS sec. 6.6, by ``2, 3, ..., B1`` in turn, i.e. computes ``j! P``).
If ``#E(F_p)`` is B1-smooth for a prime ``p | n``, the point becomes the identity modulo
``p`` and a gcd with ``n`` reveals ``p``.

Stage 2 (the "standard continuation", C&P alg. 7.4.4) catches the case
``#E(F_p) = (B1-smooth) * q`` with one prime ``q in (B1, B2]``: write ``q = m D +- j``
with ``gcd(j, D) = 1, j < D/2``; then ``q Q = O`` modulo p iff ``x(m D Q) = x(j Q)``, so
it accumulates ``prod (x(m D Q) - x(j Q))`` over all such q and takes one gcd.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from functools import lru_cache

from lenstra import curves as C
from lenstra.arith import (NotInvertible, batch_inv, is_prime, perfect_power, primes_up_to)
from lenstra.params import Level, schedule

TRACE_CAP = 24                 # intermediate points kept for the successful curve


@dataclass
class Options:
    family: str = "z2z8"           # weierstrass | suyama | z2z8
    stage1: str = "primepowers"    # primepowers | factorial (weierstrass only)
    stage2: bool = True
    B1: int | None = None          # fixed bounds instead of the schedule
    B2: int | None = None
    curves: int | None = None      # with B1: the number of curves; else a cap per factor
    factor_bits: int | None = None # expected size of the factor: first level of the schedule
    trial: int = 100               # trial division bound before ECM
    max_curves: int = 200_000      # give up on one composite after this many curves
    trace: bool = False            # keep the intermediate points of the successful curve


@dataclass
class Stats:
    curves: int = 0
    levels: list = field(default_factory=list)   # {"bits", "B1", "B2", "curves_planned", "curves_run"}


# --- plans (cached per bound) -----------------------------------------------------------

@lru_cache(maxsize=16)
def stage1_plan(B1: int) -> tuple[tuple[int, int], ...]:
    """``(p, p^e)`` with ``p^e <= B1 < p^(e+1)`` for every prime ``p <= B1``."""
    out = []
    for p in primes_up_to(B1):
        pe = p
        while pe * p <= B1:
            pe *= p
        out.append((p, pe))
    return tuple(out)


@dataclass(frozen=True)
class Stage2Plan:
    D: int
    js: tuple[int, ...]                       # baby steps: odd j < D/2, gcd(j, D) = 1
    m0: int
    giants: tuple[tuple[int, ...], ...]       # giants[m - m0] = indices into js


@lru_cache(maxsize=16)
def stage2_plan(B1: int, B2: int) -> Stage2Plan | None:
    if B2 <= B1:
        return None
    # D = a primorial <= B1 (so every q > B1 has m >= 1) minimising #baby + #giant steps
    D = min((d for d in (30, 210, 2310, 30030) if d <= B1), default=6,
            key=lambda d: d * _phi_frac(d) / 2 + (B2 - B1) / d)
    js = tuple(j for j in range(1, D // 2, 2) if math.gcd(j, D) == 1)
    index = {j: i for i, j in enumerate(js)}
    m0 = max(1, (B1 + D // 2) // D)
    m1 = (B2 + D // 2) // D
    giants: list[set[int]] = [set() for _ in range(m1 - m0 + 1)]
    for q in primes_up_to(B2):
        if q <= B1:
            continue
        m = (q + D // 2) // D
        j = abs(q - m * D)
        if j in index:                # always, except q in {2, 3} when B1 < 3
            giants[m - m0].add(index[j])
    return Stage2Plan(D, js, m0, tuple(tuple(sorted(g)) for g in giants))


def _phi_frac(d: int) -> float:
    return math.prod(1 - 1 / p for p in (2, 3, 5, 7, 11, 13) if d % p == 0)


# --- one curve ------------------------------------------------------------------------

@dataclass
class Hit:
    """A gcd > 1 on a curve. ``d == n`` means every prime factor at once: useless."""
    d: int
    stage: int | str                 # 1, 2 or "setup"
    prime: int | None = None         # the stage-1 prime after which the gcd appeared
    trace: list | None = None


def run_curve(c: C.Curve, B1: int, B2: int, opts: Options) -> Hit | None:
    if c.form == "weierstrass":
        return _run_weierstrass(c, B1, B2, opts)
    return _run_montgomery(c, B1, B2, opts)


def _run_weierstrass(c: C.Curve, B1: int, B2: int, opts: Options) -> Hit | None:
    n, a, P = c.n, c.a, c.P
    trace = [] if opts.trace else None
    steps = ([(j, j) for j in range(2, B1 + 1)] if opts.stage1 == "factorial"
             else stage1_plan(B1))
    for p, k in steps:
        try:
            P = C.w_mul(k, P, a, n)
        except NotInvertible as e:
            return Hit(e.d, 1, p, trace)
        if trace is not None:
            _keep(trace, {"after": p, "x": P[0], "y": P[1]} if P else {"after": p, "point": "O"})
        if P is None:                 # identity modulo every p | n: gcd would be n
            return Hit(n, 1, p)
    plan = stage2_plan(B1, B2)
    if plan is None:
        return None
    try:
        baby = [P]
        P2 = C.w_add(P, P, a, n)
        R = P
        for j in range(3, plan.D // 2, 2):
            R = C.w_add(R, P2, a, n)
            baby.append(R)
        xs = {j: baby[(j - 1) // 2] for j in plan.js}
        xj = [xs[j][0] if xs[j] else None for j in plan.js]
        DP = C.w_mul(plan.D, P, a, n)
        R = C.w_mul(plan.m0, DP, a, n)
        g = 1
        for idx in plan.giants:
            if R is not None:
                xr = R[0]
                for i in idx:
                    if xj[i] is not None:
                        g = g * (xr - xj[i]) % n
            R = C.w_add(R, DP, a, n)
    except NotInvertible as e:
        return Hit(e.d, 2, None, trace)
    d = math.gcd(g, n)
    return Hit(d, 2, None, trace) if d > 1 else None


def _run_montgomery(c: C.Curve, B1: int, B2: int, opts: Options) -> Hit | None:
    n, a24, X, Z = c.n, c.a24, c.P[0], 1
    trace = [] if opts.trace else None
    for p, pe in stage1_plan(B1):
        X, Z = C.m_mul(pe, X, Z, a24, n)
        if trace is not None:
            _keep(trace, {"after": p, "X": X, "Z": Z})
        d = math.gcd(Z, n)
        if d > 1:
            return Hit(d, 1, p, trace)
    plan = stage2_plan(B1, B2)
    if plan is None:
        return None
    # baby steps x(jQ), j odd < D/2: jQ + 2Q with difference (j - 2)Q
    X2, Z2 = C.m_dbl(X, Z, a24, n)
    pts = [(X, Z)]
    prev, cur = (X, Z), C.m_add(X2, Z2, X, Z, X, Z, n)            # Q, 3Q
    for _ in range(3, plan.D // 2, 2):
        pts.append(cur)
        prev, cur = cur, C.m_add(cur[0], cur[1], X2, Z2, prev[0], prev[1], n)
    sel = [pts[(j - 1) // 2] for j in plan.js]
    try:
        zinv = batch_inv([z for _, z in sel], n)
    except NotInvertible as e:
        return Hit(e.d, 2, None, trace)
    xj = [x * zi % n for (x, _), zi in zip(sel, zinv)]
    # giant steps x(m D Q), m = m0, m0 + 1, ...: R_{m+1} = R_m + DQ, difference R_{m-1}
    DX, DZ = C.m_mul(plan.D, X, Z, a24, n)
    R0 = C.m_mul(plan.m0, DX, DZ, a24, n)
    R1 = C.m_mul(plan.m0 + 1, DX, DZ, a24, n)
    g = 1
    for idx in plan.giants:
        RX, RZ = R0
        for i in idx:
            g = g * (RX - xj[i] * RZ) % n
        R0, R1 = R1, C.m_add(R1[0], R1[1], DX, DZ, R0[0], R0[1], n)
    d = math.gcd(g, n)
    return Hit(d, 2, None, trace) if d > 1 else None


def _keep(trace: list, item: dict) -> None:
    """Keep the first and the most recent TRACE_CAP/2 intermediate points."""
    if len(trace) >= TRACE_CAP:
        del trace[TRACE_CAP // 2]
    trace.append(item)


# --- a factor of n ------------------------------------------------------------------------

def _levels(n: int, opts: Options, start: int | None):
    if opts.B1:
        B2 = opts.B2 if opts.B2 is not None else (100 * opts.B1 if opts.stage2 else opts.B1)
        while True:
            yield Level(0, opts.B1, B2, opts.curves or 10 ** 9)
    yield from schedule(n.bit_length(), opts.family, opts.stage2, start)


def find_factor(n: int, rng: random.Random, opts: Options, stats: Stats,
                start_bits: int | None = None) -> dict | None:
    """A proper factor of the composite ``n`` (not a prime power, ``gcd(n, 6) = 1``) by ECM.

    Returns the provenance record (factor, curve, point, bounds, stage...) or None when the
    curve budget (``opts.curves`` with fixed bounds, else ``opts.max_curves``) runs out.
    """
    make = C.FAMILIES[opts.family]
    budget = opts.curves if (opts.B1 and opts.curves) else opts.max_curves
    used = 0
    for lv in _levels(n, opts, start_bits if start_bits is not None else opts.factor_bits):
        rec = {"bits": lv.bits, "B1": lv.B1, "B2": lv.B2, "curves_planned": lv.curves,
               "curves_run": 0}
        stats.levels.append(rec)
        for _ in range(lv.curves):
            if used >= budget:
                return None
            used += 1
            stats.curves += 1
            rec["curves_run"] += 1
            try:
                c = make(n, rng)
            except C.CurveFound as e:
                if 1 < e.d < n:
                    return {"factor": e.d, "of": n, "stage": "setup",
                            "curve": {"family": e.family, **e.params}, "B1": lv.B1,
                            "B2": lv.B2, "level_bits": lv.bits, "curve_no": stats.curves}
                continue
            hit = run_curve(c, lv.B1, lv.B2, opts)
            if hit is None or hit.d == n:
                continue
            out = {"factor": hit.d, "of": n, "stage": hit.stage, "curve": c.describe(),
                   "B1": lv.B1, "B2": lv.B2, "level_bits": lv.bits, "curve_no": stats.curves}
            if hit.prime is not None:
                out["after_prime"] = hit.prime
            if opts.trace:
                out["trace"] = hit.trace
            return out
    return None


# --- full factorization -----------------------------------------------------------------

def factorize(n: int, rng: random.Random, opts: Options, stats: Stats,
              one: bool = False) -> tuple[dict[int, int], list[dict], bool]:
    """Prime factorization of ``n >= 2`` as ``{p: e}``, plus the provenance of each split.

    Trial division by primes < ``opts.trial`` (always 2 and 3: the curve formulas need
    ``gcd(n, 6) = 1``), then a stack of cofactors: a prime goes to the result, a perfect
    power ``r^k`` is replaced by ``r`` with multiplicity ``k``, anything else is split by
    :func:`find_factor`. With ``one`` it stops at the first proper factor (the result is
    then ``{d: 1}``). The third value is False if ECM gave up (the result has a composite).
    """
    found: list[dict] = []
    res: dict[int, int] = {}
    m = n
    for p in primes_up_to(max(3, opts.trial - 1)):
        if p * p > m:
            break
        while m % p == 0:
            if one:                       # p * p <= n, so p is a proper factor
                return {p: 1}, [{"factor": p, "of": n, "stage": "trial"}], True
            res[p] = res.get(p, 0) + 1
            found.append({"factor": p, "of": m, "stage": "trial"})
            m //= p
    stack = [(m, 1)] if m > 1 else []
    level_bits = None                     # resume the schedule where the last split stopped
    complete = True
    while stack:
        m, e = stack.pop()
        if is_prime(m, rng):
            if one and m == n:
                return {}, found, True    # n itself is prime
            res[m] = res.get(m, 0) + e
            continue
        pw = perfect_power(m)
        if pw:
            r, k = pw
            found.append({"factor": r, "of": m, "stage": "power", "exponent": k})
            if one:
                return {r: 1}, found, True
            stack.append((r, e * k))
            continue
        hit = find_factor(m, rng, opts, stats, level_bits)
        if hit is None:
            res[m] = res.get(m, 0) + e
            complete = False
            continue
        found.append(hit)
        if one:
            return {hit["factor"]: 1}, found, True
        level_bits = hit["level_bits"] or None
        d = hit["factor"]
        stack += [(m // d, e), (d, e)]
    return dict(sorted(res.items())), found, complete
