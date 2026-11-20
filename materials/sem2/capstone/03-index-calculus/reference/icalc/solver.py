"""The index-calculus method for g^x = h (mod p): the four steps of the spec.

1. params.choose: B = L(p)^(1/sqrt 2), the number of relations, the expected trials.
2. relations.collect: B-smooth residues gamma^k mod p -> congruences k = sum e_i log q_i.
3. linalg.solve: the logarithms of the factor base modulo every prime power of p - 1.
4. relations.individual_log: a B-smooth h * gamma^-k, then log h.

The base of the system. If g is a primitive root, the system is built on gamma = g
exactly as in the spec. Otherwise the factor-base primes need not be powers of g at
all, so the system is built on a primitive root gamma (the least one; finding it takes
the factorization of p - 1, which the CRT of step 3 needs anyway), step 4 is run for
both h and g, and x is recovered from the linear congruence

    x * log_gamma g = log_gamma h   (mod p - 1),

which is solvable iff gcd(log_gamma g, p - 1) divides log_gamma h (i.e. h is in <g>);
x is then unique modulo ord(g) = (p - 1) / gcd(log_gamma g, p - 1).
"""

from __future__ import annotations

import math
import random
import time

from icalc import linalg, nt, params
from icalc.relations import FactorBase, collect, individual_log

MAX_ROUNDS = 10                 # rounds of "collect more relations"
MIN_KNOWN = 0.5                 # ... while fewer than this fraction of logarithms is known


class InputError(ValueError):
    pass


def _seed(p: int, g: int, h: int) -> int:
    return (p * 1_000_003 + g * 10_007 + h) % (1 << 64)


def solve(p: int, g: int, h: int, *, b: int | None = None, c: float | None = None,
          margin: float = 0.05, seed: int | None = None, full: bool = False,
          smooth: str = "powmod") -> tuple[dict, dict]:
    """Solve g^x = h (mod p). Returns (output, extra): output = {"x": x mod ord(g)} or
    {"x": None} when h is not a power of g; extra = the intermediate data of every step."""
    if not (isinstance(p, int) and p >= 2 and nt.is_probable_prime(p)):
        raise InputError(f"p = {p!r} is not a prime")
    g, h = g % p, h % p
    if g == 0 or h == 0:
        raise InputError("g and h must be nonzero modulo p")
    rng = random.Random(_seed(p, g, h) if seed is None else seed)
    n_order = p - 1
    n_factors = nt.factorize(n_order) if n_order > 1 else {}
    ord_g = nt.element_order(g, p, n_factors)
    extra: dict = {"order": str(n_order), "order_factors": {str(q): e for q, e in n_factors.items()},
                   "ord_g": str(ord_g)}
    if h == 1:
        return {"x": 0}, {**extra, "trivial": "h = 1"}
    if ord_g == 1:
        return {"x": None}, {**extra, "trivial": "g = 1 != h"}

    clock = [time.perf_counter()]
    seconds: dict[str, float] = {}

    def lap(name: str) -> None:
        now = time.perf_counter()
        seconds[name] = round(now - clock[0], 4)
        clock[0] = now

    # --- step 1: parameters --------------------------------------------------------
    par = params.choose(p, **({} if c is None else {"c": c}), b=b, margin=margin)
    fb = FactorBase(nt.primes_up_to(par["B"]), p, smooth)
    params.finish(par, len(fb.primes))
    gamma = g if ord_g == n_order else nt.primitive_root(p, n_factors)
    extra.update(params=par, factor_base_size=len(fb.primes), gamma=gamma, seconds=seconds)
    lap("params")

    # --- step 2 + 3: relations and the linear system ----------------------------------
    # Primes that occur in no relation, or that the relations do not pin down modulo some
    # l | p - 1, keep an unknown logarithm; step 4 only uses primes of known logarithm.
    # Should fewer than MIN_KNOWN of the factor base be known, more relations are collected.
    small = n_order <= 4 * par["relations_needed"]   # tiny groups: enumerate every k once
    relations, trials = collect(p, gamma, n_order, fb, par["relations_needed"], rng,
                                max_trials=n_order if small else None)
    lap("relations")
    rounds = 0
    while True:
        logs, la = linalg.solve(relations, len(fb.primes), n_order, n_factors)
        if small or rounds >= MAX_ROUNDS or sum(x is not None for x in logs) >= \
                MIN_KNOWN * len(fb.primes):
            break
        rounds += 1
        _, t = collect(p, gamma, n_order, fb, max(10, len(fb.primes) // 10), rng, relations)
        trials += t
    lap("linalg")
    # every logarithm is checked: gamma^log q = q (mod p)
    bad = [i for i, x in enumerate(logs) if x is not None and pow(gamma, x, p) != fb.primes[i]]
    for i in bad:
        logs[i] = None
    known = sum(x is not None for x in logs)
    extra.update(relations_found=len(relations), trials=trials, extra_rounds=rounds,
                 linalg=la, logs_known=known, logs_rejected=len(bad),
                 factor_base_logs={str(q): x for q, x in zip(fb.primes, logs) if x is not None}
                 if full or len(fb.primes) <= 200 else
                 {str(q): x for q, x in list(zip(fb.primes, logs))[:20] if x is not None},
                 relations_sample=[{"k": k, "factors": {str(fb.primes[i]): e for i, e in f.items()}}
                                   for k, f in (relations if full else relations[:10])])

    # --- step 4: individual logarithms -----------------------------------------------
    log_h, expr_h = individual_log(p, gamma, n_order, h, fb, logs, rng)
    extra["individual_h"] = expr_h
    if gamma == g:
        log_g = 1
    else:
        log_g, expr_g = individual_log(p, gamma, n_order, g, fb, logs, rng)
        extra["individual_g"] = expr_g
    lap("individual")
    extra.update(log_gamma_h=log_h, log_gamma_g=log_g)
    d = math.gcd(log_g, n_order)
    if log_h % d:
        return {"x": None}, {**extra, "reason": "h is not in <g>"}
    m = n_order // d                     # = ord(g)
    x = (log_h // d) * pow(log_g // d, -1, m) % m if m > 1 else 0
    return {"x": x}, extra
