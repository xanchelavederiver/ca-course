"""Factorization by the quadratic sieve (QS), f(t) = t^2 - N, t around sqrt(N).

The four items of «Требуемый функционал»:

1. ``choose_params``: B, the number of B-smooth values needed and the expected sieve
   length, from L(N) = exp(sqrt(ln N ln ln N)) (HPS, section 3.7.1) and the Dickman
   rho estimate of the smoothness probability.
2. ``sieve``: B-smooth values of f(t) by sieving with logarithms over the factor base
   (primes p <= B with (N/p) = 1 and their powers), block by block, alternately to the
   right and to the left of sqrt(N); candidates are confirmed by trial division.
3. ``qs_linalg.dependencies``: subsets of relations whose f(t) multiply to a square
   (Gaussian elimination over GF(2)).
4. ``square_root_step``: x = prod t, y = sqrt(prod f(t)) (mod N), d = gcd(x - y, N).

Allowed tools only: Python ints, ``math.isqrt``/``gcd``, ``pow(.., -1, m)``.
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field

import qs_linalg
import qs_numtheory as nt

BLOCK = 1 << 16          # sieve block length (positions of x)
CHUNK = 1 << 11          # granularity of the threshold inside a block
SMALL_P = 30             # primes below this are not sieved (remark 3), only trial-divided
B_FACTOR = 4.0           # B = B_FACTOR * L(N)^(1/2), tuned on 60--140 bit N
EXTRA_REL = 16           # relations beyond the matrix width: >= 16 dependencies


class QSFailure(Exception):
    """The sieve could not split N with the given limits."""


# --- 1. parameters -----------------------------------------------------------------

def L(n: int, alpha: float = 1.0) -> float:
    """L(N)^alpha, L(N) = exp(sqrt(ln N * ln ln N))."""
    ln = math.log(n)
    return math.exp(alpha * math.sqrt(ln * math.log(ln)))


_RHO_H = 1 / 256
_RHO: list[float] = []


def dickman_rho(u: float) -> float:
    """Dickman's rho: the probability that a random X is X^(1/u)-smooth (u -> oo).

    rho = 1 on [0, 1] and u rho(u) = integral of rho over [u - 1, u] (equivalent to
    u rho'(u) = -rho(u - 1)); tabulated with the trapezoidal rule, solved for rho(u).
    All terms are positive, so the relative error stays small even where rho is tiny.
    """
    if u <= 1:
        return 1.0
    if not _RHO:
        h, k = _RHO_H, round(1 / _RHO_H)
        _RHO.extend([1.0] * (k + 1))
        inner = sum(_RHO[1:k])                  # rho at the interior nodes of [u-1, u]
        for i in range(k + 1, round(30 / h) + 1):
            # running window: interior nodes of [u - 1, u] for u = i h are i-k+1 .. i-1
            inner += _RHO[i - 1] - _RHO[i - k]
            u_i = i * h
            _RHO.append(h * (_RHO[i - k] / 2 + inner) / (u_i - h / 2))
    x = u / _RHO_H
    j = min(int(x), len(_RHO) - 2)
    return _RHO[j] + (_RHO[j + 1] - _RHO[j]) * (x - j)


@dataclass
class Params:
    B: int                    # smoothness bound
    fb_size: int              # primes in the factor base (without -1)
    needed: int               # relations to collect: fb_size + 1 (sign) + EXTRA_REL
    expected_length: int      # expected number of sieved t (Dickman rho estimate)
    B_theory: float           # HPS: L(N)^(1/sqrt 2)
    length_theory: float      # HPS: L(N)^(sqrt 2) values to check


def choose_params(n: int, b_factor: float = B_FACTOR) -> tuple[Params, list[int]]:
    """B = b_factor * L(N)^(1/2), at least 50; the factor base; the expected length.

    The asymptotic optimum of HPS 3.7.1 is B = L(N)^(1/sqrt 2) with about L(N)^(sqrt 2)
    values of f to check; it ignores the sieve (which makes a value cost O(log log B)
    instead of O(pi(B))) and the o(1) terms, and for 40--120 bit N it is far too large.
    The practical choice L(N)^(1/2) (Crandall--Pomerance, 6.1) is what we use; both
    are reported. The expected length l solves l * rho(u) = needed, where
    u = ln(sqrt(N) * l / 2) / ln B: |f(s + x)| ~ 2 sqrt(N) |x| and |x| <= l / 2, less
    the expected excess of small factor-base primes in f(t) over a random number.
    """
    B = max(50, round(b_factor * L(n, 0.5)))
    fb = [2] + [p for p in nt.primes_up_to(B)[1:] if nt.legendre(n, p) == 1]
    needed = len(fb) + 1 + EXTRA_REL
    lnB, half_ln = math.log(B), math.log(n) / 2
    # Knuth--Schroeppel correction: f(t) gets 2 ln p / (p - 1) from each p in the base
    # (two roots), a random number ln p / (p - 1) from every p, on average
    bonus = (sum(2 * math.log(p) / (p - 1) for p in fb[1:]) + 2 * math.log(2)
             - sum(math.log(p) / (p - 1) for p in nt.primes_up_to(B)))
    length = float(needed)
    for _ in range(50):                   # fixed point of l = needed / rho(u(l))
        u = (half_ln + math.log(max(length, 2) / 2) - bonus) / lnB
        new = needed / dickman_rho(u)
        if abs(new - length) <= 1e-3 * length:
            break
        length = new
    return Params(B, len(fb), needed, round(length), L(n, 1 / math.sqrt(2)),
                  L(n, math.sqrt(2))), fb


# --- 2. sieving ----------------------------------------------------------------------

@dataclass
class Relation:
    t: int                        # t^2 = f(t) (mod N)
    exps: dict[int, int]          # column -> exponent of f(t); column 0 = sign (-1)
    mask: int = 0                 # exponent parities as a bit mask

    def __post_init__(self):
        self.mask = sum(1 << c for c, e in self.exps.items() if e & 1)


@dataclass
class SieveStats:
    length: int = 0               # positions x sieved
    blocks: int = 0
    candidates: int = 0           # passed the log threshold
    relations: int = 0            # confirmed B-smooth
    powers: int = 0               # prime powers p^k > p sieved


def factor_base_roots(n: int, s: int, fb: list[int]):
    """Sieve entries (q, log2 p, offsets): x = offset (mod q) <=> q | f(s + x), q = p^k.

    Roots of t^2 = N (mod p) by Tonelli--Shanks, lifted to p^k by Hensel while p^k <= B
    (remark 2: sieve by the primes and their powers). Primes < SMALL_P are skipped
    (remark 3) and found by trial division.
    """
    B = fb[-1]
    entries, roots = [], []                    # roots: (p, o1, o2) for trial division
    for p in fb:
        if p == 2:
            roots.append((2, (1 - s) % 2, (1 - s) % 2))   # N odd: t odd
            continue
        r = nt.sqrt_mod_prime(n, p)
        roots.append((p, (r - s) % p, (-r - s) % p))
        if p < SMALL_P:
            continue
        lp = round(math.log2(p))
        q, k = p, 1
        while True:
            entries.append((q, lp, sorted({(r - s) % q, (-r - s) % q})))
            if q * p > B:
                break
            r = nt.lift_root(r, n, p, k)
            q, k = q * p, k + 1
    return entries, roots


def _block_order():
    """Block indices 0, -1, 1, -2, 2, ...: x in [b * BLOCK, (b + 1) * BLOCK)."""
    b = 0
    while True:
        yield b
        yield -b - 1
        b += 1


_PATTERNS: dict[int, re.Pattern] = {}


def _ge(th: int) -> re.Pattern:
    """A regex matching any byte >= th: fast scan of a bytearray for candidates."""
    th = max(1, min(th, 255))
    if th not in _PATTERNS:
        _PATTERNS[th] = re.compile(b"[\\x%02x-\\xff]" % th)
    return _PATTERNS[th]


def sieve(n: int, fb: list[int], needed: int, fudge: float,
          max_length: int) -> tuple[list[Relation], SieveStats]:
    """Collect ``needed`` relations t^2 = f(t), f(t) = t^2 - N B-smooth, t = s + x.

    For every block a bytearray holds sum log2 p over the prime powers q | f(s + x);
    positions where it reaches log2 |f| - fudge are candidates, checked by trial
    division over the factor base.
    """
    s = nt.iroot(n, 2)
    entries, roots = factor_base_roots(n, s, fb)
    col = {p: j + 1 for j, p in enumerate(fb)}
    rels: list[Relation] = []
    st = SieveStats(powers=sum(1 for q, _, _ in entries if q not in col))
    for b in _block_order():
        if len(rels) >= needed:
            break
        if st.length >= max_length:
            raise QSFailure(f"only {len(rels)} of {needed} relations in {st.length} positions")
        x0 = b * BLOCK
        arr = bytearray(BLOCK)
        for q, lp, offs in entries:
            for o in offs:
                for i in range((o - x0) % q, BLOCK, q):
                    arr[i] += lp
        st.length += BLOCK
        st.blocks += 1
        for c0 in range(0, BLOCK, CHUNK):
            # |f(s + x)| ~ 2 s |x| grows with |x|: take it at the end of the chunk nearer
            # to x = 0 (at most 1 bit below the far end, except for the first chunks)
            xa = x0 + c0 + CHUNK if b < 0 else x0 + c0
            fmin = max(abs((s + xa) ** 2 - n), 2 * s)
            th = math.ceil(math.log2(fmin) - fudge)
            for m in _ge(th).finditer(arr, c0, c0 + CHUNK):
                st.candidates += 1
                rel = _trial_divide(n, s, x0 + m.start(), roots, col)
                if rel is not None:
                    rels.append(rel)
    st.relations = len(rels)
    return rels[:needed], st


def _trial_divide(n, s, x, roots, col) -> Relation | None:
    """The factorization of f(s + x) over the factor base, or None if not B-smooth."""
    t = s + x
    v = t * t - n
    if v == 0:
        return None
    exps = {}
    if v < 0:
        exps[0] = 1
        v = -v
    for p, o1, o2 in roots:
        r = x % p
        if r != o1 and r != o2:
            continue
        e = 0
        while v % p == 0:
            v //= p
            e += 1
        if e:
            exps[col[p]] = e
    return Relation(t, exps) if v == 1 else None


# --- 3, 4. linear algebra and the congruence of squares ----------------------------------

def square_root_step(n: int, fb: list[int], rels: list[Relation], dep: int) -> tuple[int, int]:
    """x = prod t_i, y = sqrt(prod f(t_i)) (mod N) over the relations in ``dep``."""
    x, total = 1, {}
    i = 0
    while dep:
        if dep & 1:
            r = rels[i]
            x = x * r.t % n
            for c, e in r.exps.items():
                total[c] = total.get(c, 0) + e
        dep >>= 1
        i += 1
    y = 1
    for c, e in total.items():
        assert e % 2 == 0, "not a square: the dependency is wrong"
        if c:                              # column 0 is the sign: (-1)^even = 1
            y = y * pow(fb[c - 1], e // 2, n) % n
    return x, y


@dataclass
class Result:
    factor: int
    method: str                            # qs | trial-division | perfect-power
    extra: dict = field(default_factory=dict)


def qs_split(n: int, b_factor: float = B_FACTOR, fudge: float | None = None,
             linalg: str = "gauss", trace: bool = False) -> Result:
    """A non-trivial factor of an odd composite N that is not a perfect power and has
    no prime factor <= B (``split`` checks both)."""
    times = {}
    t0 = time.perf_counter()
    par, fb = choose_params(n, b_factor)
    if fudge is None:
        fudge = 0.5 * math.log2(par.B) + 4
    extra = {"B": par.B, "fb_size": par.fb_size, "relations_needed": par.needed,
             "expected_length": par.expected_length,
             "B_theory": round(par.B_theory), "length_theory": float(f"{par.length_theory:.3g}"),
             "L_N": float(f"{L(n):.4g}"), "fudge_bits": round(fudge, 2)}
    times["params"] = time.perf_counter() - t0
    attempts = 0
    needed = par.needed
    while True:
        attempts += 1
        t1 = time.perf_counter()
        rels, st = sieve(n, fb, needed, fudge, max_length=200 * max(par.expected_length, BLOCK))
        times["sieve"] = times.get("sieve", 0) + time.perf_counter() - t1
        t1 = time.perf_counter()
        rows = [r.mask for r in rels]
        deps = (qs_linalg.dependencies(rows) if linalg == "gauss"
                else qs_linalg.dependencies_sage(rows, par.fb_size + 1))
        times["linalg"] = times.get("linalg", 0) + time.perf_counter() - t1
        t1 = time.perf_counter()
        gcds, found = [], None
        for dep in deps:
            x, y = square_root_step(n, fb, rels, dep)
            assert (x * x - y * y) % n == 0
            d = math.gcd(x - y, n)
            gcds.append(d)
            if 1 < d < n:
                found = (dep, x, y, d)
                break
        times["sqrt_gcd"] = times.get("sqrt_gcd", 0) + time.perf_counter() - t1
        extra.update({"sieve_length": st.length, "blocks": st.blocks, "candidates": st.candidates,
                      "relations": len(rels), "prime_powers_sieved": st.powers,
                      "matrix": [len(rows), par.fb_size + 1], "dependencies": len(deps),
                      "dependencies_tried": len(gcds), "gcds": gcds[:8], "attempts": attempts})
        if found:
            break
        if attempts >= 4:
            raise QSFailure(f"no dependency split N after {attempts} attempts")
        needed += par.needed // 2          # rare: collect more relations and retry
    dep, x, y, d = found
    members = [i for i in range(len(rels)) if dep >> i & 1]
    extra.update({"dependency_size": len(members), "x": x, "y": y})
    if trace:
        extra["factor_base"] = fb
        extra["smooth"] = [[r.t, {("-1" if c == 0 else str(fb[c - 1])): e for c, e in r.exps.items()}]
                           for r in rels]
        extra["dependency"] = members
    extra["times_s"] = {k: round(v, 4) for k, v in times.items()}
    return Result(d, "qs", extra)


def split(n: int, **kw) -> Result:
    """A non-trivial factor of a composite n (raises ValueError for primes and n < 4)."""
    if n < 4 or nt.is_probable_prime(n):
        raise ValueError(f"n = {n} is not composite")
    pp = nt.perfect_power(n)
    if pp:
        return Result(pp[0], "perfect-power", {"power": list(pp)})
    # trial division up to B: QS needs gcd(N, p) = 1 for the factor base
    B = max(50, round(kw.get("b_factor", B_FACTOR) * L(n, 0.5)))
    for p in nt.primes_up_to(B):
        if n % p == 0:
            return Result(p, "trial-division", {"B": B})
    # here n > B^2 (a composite n <= B^2 has a prime factor <= B), so B < sqrt(n)
    return qs_split(n, **kw)


def factorize(n: int, **kw) -> tuple[dict[int, int], list[tuple[int, Result]]]:
    """The full factorization {p: e} by recursive splitting, and the splits made
    (composite m, its Result) in order; the first split is the one of n itself."""
    out: dict[int, int] = {}
    splits: list[tuple[int, Result]] = []
    stack = [(n, 1)]
    while stack:
        m, e = stack.pop()
        if m == 1:
            continue
        if nt.is_probable_prime(m):
            out[m] = out.get(m, 0) + e
            continue
        r = split(m, **kw)
        splits.append((m, r))
        if r.method == "perfect-power":
            stack.append((r.extra["power"][0], e * r.extra["power"][1]))
        else:
            stack += [(r.factor, e), (m // r.factor, e)]
    return dict(sorted(out.items())), splits
