"""Step 1 of the spec: B, the number of B-smooth numbers needed, the expected number of trials.

Hoffstein--Pipher--Silverman, section 3.7.1 (and 3.6.3 for psi(X, B)):

    L(X) = exp(sqrt(ln X * ln ln X)),        psi(X, L(X)^c) / X ~ L(X)^(-1/(2c))

The relation search tests random g^k mod p (numbers of size about p) for B-smoothness
and needs about pi(B) of them, so the expected number of trials is

    T(B) = pi(B) / (psi(p, B) / p)  ~  L(p)^(c + 1/(2c))   (pi(B) ~ B = L(p)^c),

which is minimal for c = 1/sqrt(2):  B = L(p)^(1/sqrt 2),  T = L(p)^(sqrt 2).

Besides the asymptotic value we report a sharper estimate: psi(p, B)/p ~ rho(u), the
Dickman function at u = ln p / ln B (the crude u^-u underestimates it by a factor ~u^u/rho(u)
that grows with u; we tabulate rho by integrating its delay differential equation).
"""

from __future__ import annotations

import math
from functools import lru_cache


def L(x: int, c: float = 1.0) -> float:
    """L(x)^c = exp(c * sqrt(ln x * ln ln x))."""
    lx = math.log(x)
    return math.exp(c * math.sqrt(lx * math.log(lx)))


@lru_cache(maxsize=1)
def _rho_table(step: float = 1e-3, umax: float = 30.0) -> list[float]:
    """Dickman rho on [0, umax] with step `step`: rho = 1 on [0, 1],
    u rho'(u) = -rho(u - 1); trapezoidal rule (fine for an estimate)."""
    n1 = round(1 / step)
    rho = [1.0] * (n1 + 1)
    for i in range(n1 + 1, round(umax / step) + 1):
        u0, u1 = (i - 1) * step, i * step
        d0, d1 = rho[i - 1 - n1] / u0, rho[i - n1] / u1
        rho.append(rho[i - 1] - step * (d0 + d1) / 2)
    return rho


def dickman_rho(u: float, step: float = 1e-3) -> float:
    if u <= 1:
        return 1.0
    t = _rho_table(step)
    i = min(len(t) - 1, round(u / step))
    return max(t[i], 1e-300)


def prime_count_estimate(b: float) -> float:
    return b / math.log(b) if b > 2 else 1.0


def choose(p: int, c: float = 1 / math.sqrt(2), b: int | None = None,
           margin: float = 0.05) -> dict:
    """The parameters of the method for the prime p.

    c: B = L(p)^c (the optimum is 1/sqrt 2); b: an explicit B overriding c;
    margin: extra relations beyond the number of unknowns (the system must be
    overdetermined to have full rank modulo every prime factor of p - 1).
    """
    if b is not None:
        bound = int(b)
    elif p < 5:
        bound = 2
    else:
        bound = math.ceil(L(p, c))
    bound = max(2, min(bound, p - 1))           # factor-base primes are residues mod p
    u = math.log(p) / math.log(bound) if p > 2 else 1.0
    smooth_prob = dickman_rho(u)
    pi_b = prime_count_estimate(bound)
    lp = L(p) if p > 3 else 1.0                 # ln ln p < 0 for p < 3
    return {
        "L": lp,
        "c": math.log(bound) / math.log(lp) if lp > 1 else c,   # the c actually used
        "B": bound,
        "u": u,
        "smooth_prob_rho": smooth_prob,       # psi(p, B)/p ~ rho(u)
        "smooth_prob_uu": u ** -u,            # the cruder u^-u of HPS
        "margin": margin,
        # filled in by the solver once the factor base is known (pi(B) exactly):
        "relations_needed": None,
        "expected_trials": None,
        "expected_trials_asymptotic": L(p, math.sqrt(2)) if p > 3 else 1.0,
        "pi_B_estimate": pi_b,
    }


def finish(par: dict, fb_size: int) -> dict:
    """Fill in the counts once pi(B) = len(factor base) is known."""
    need = fb_size + max(10, math.ceil(par["margin"] * fb_size))
    par["relations_needed"] = need
    par["expected_trials"] = need / par["smooth_prob_rho"]
    return par
