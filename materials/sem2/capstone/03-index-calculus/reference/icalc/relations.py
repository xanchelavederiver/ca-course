"""Step 2 (and the search of step 4): B-smooth residues and the system of congruences.

A residue r (an integer 1 <= r < p) is B-smooth iff every prime of r is <= B, i.e. iff r
divides P^(2^s), where P is the product of the factor base and 2^s >= log2 r (no
exponent of r exceeds log2 r). One modular exponentiation P^(2^s) mod r (with gmpy2,
on numbers of the size of p) replaces |factor base| trial divisions for the vast
majority of candidates, which are not smooth. Only the smooth ones are then factored
by trial division over the factor base, as the spec suggests.

``FactorBase(..., method="trial")`` tests every candidate by plain trial division over
the factor base instead (what the spec suggests and most students will do); the bench
README compares the two.
"""

from __future__ import annotations

import math
import random

try:                                    # gmpy2 (the spec's reference [2]); plain ints otherwise
    from gmpy2 import mpz, powmod
except ImportError:                     # pragma: no cover
    mpz = int

    def powmod(a, e, m):
        return pow(a, e, m)


METHODS = ("powmod", "trial")


class FactorBase:
    def __init__(self, primes: list[int], p: int, method: str = "powmod"):
        if method not in METHODS:
            raise ValueError(f"smoothness test {method!r} is not one of {METHODS}")
        self.method = method
        self.primes = primes
        self.index = {q: i for i, q in enumerate(primes)}
        prod = mpz(1)
        for q in primes:
            prod *= q
        self.product = prod
        self.exp = mpz(1) << max(1, p.bit_length()).bit_length()   # 2^s >= log2 p

    def is_smooth(self, r) -> bool:
        return powmod(self.product, self.exp, r) == 0 if r > 1 else True

    def factor(self, r: int) -> dict[int, int] | None:
        """{factor-base index: exponent} of r, or None if r is not B-smooth."""
        if self.method == "trial":
            return self.trial_factor(int(r))
        if not self.is_smooth(r):
            return None
        return self.factor_smooth(int(r))

    def trial_factor(self, r: int) -> dict[int, int] | None:
        """Trial division by every prime of the factor base; None if a cofactor > 1 remains."""
        out = {}
        for i, q in enumerate(self.primes):
            if r == 1:
                break
            if r % q == 0:
                e = 0
                while r % q == 0:
                    r //= q
                    e += 1
                out[i] = e
        return out if r == 1 else None

    def factor_smooth(self, r: int) -> dict[int, int]:
        out = self.trial_factor(r)
        assert out is not None, "not smooth"
        return out


def _step(order: int, rng: random.Random) -> int:
    """A step coprime to the order (so that k0 + i*s runs through every residue)."""
    if order <= 2:
        return 1
    while True:
        s = rng.randrange(1, order)
        if math.gcd(s, order) == 1:
            return s


def collect(p: int, gamma: int, order: int, fb: FactorBase, count: int,
            rng: random.Random, relations: list | None = None,
            max_trials: int | None = None) -> tuple[list[tuple[int, dict[int, int]]], int]:
    """Collect `count` (more) relations gamma^k = prod q_i^e_i (mod p), i.e. the congruences
    k = sum e_i log q_i (mod order). Returns (relations, number of trials).

    Exponents k run through an arithmetic progression k0, k0 + s, k0 + 2s, ... with random
    k0 and s: the next residue is one modular multiplication (by gamma^s) away. A step
    s = 1 would be a mistake for a small gamma such as 2: r smooth => r * 2 smooth, and the
    relations would come in near-duplicate runs that add almost no rank.
    """
    relations = [] if relations is None else relations
    k0, step = rng.randrange(order), _step(order, rng)
    r, mult, pm = mpz(pow(gamma, k0, p)), mpz(pow(gamma, step, p)), mpz(p)
    prod, exp = fb.product, fb.exp          # locals: this is the hot loop of the method
    limit = max_trials if max_trials is not None else 1 << 62
    seen = {k for k, _ in relations}
    trial = fb.method == "trial"
    trials = found = 0
    while found < count and trials < limit:
        trials += 1
        r = r * mult % pm                   # r = gamma^(k0 + trials * step)
        if trial:
            f = fb.trial_factor(int(r))
            if f is None:
                continue
        elif powmod(prod, exp, r):          # nonzero: r is not B-smooth (the usual case)
            continue
        else:
            f = None
        k = (k0 + trials * step) % order
        if k in seen or r == 1:             # wrapped around a small group / k = 0: nothing new
            continue
        seen.add(k)
        relations.append((k, f if f is not None else fb.factor_smooth(int(r))))
        found += 1
    return relations, trials


def individual_log(p: int, gamma: int, order: int, t: int, fb: FactorBase,
                   logs: list[int | None], rng: random.Random,
                   max_trials: int = 10 ** 8) -> tuple[int, dict]:
    """Step 4: find k with t * gamma^(-k) mod p B-smooth over the primes of known logarithm;
    then log t = k + sum e_i log q_i (mod order). Returns (log t, the found expression)."""
    k0, step = rng.randrange(order), _step(order, rng)
    pm = mpz(p)
    mult = mpz(pow(gamma, -step, p))            # k runs through k0 + i*step, as in collect
    r = mpz(t) * mpz(pow(gamma, -k0, p)) % pm
    for i in range(max_trials):
        f = fb.factor(r)
        if f is not None:
            if all(logs[j] is not None for j in f):
                k = (k0 + i * step) % order
                x = (k + sum(e * logs[j] for j, e in f.items())) % order
                expr = {"k": k, "residue": int(r),
                        "factors": {str(fb.primes[j]): e for j, e in f.items()},
                        "trials": i + 1}
                return x, expr
        r = r * mult % pm
    raise RuntimeError("individual logarithm: no smooth h*g^-k found")
