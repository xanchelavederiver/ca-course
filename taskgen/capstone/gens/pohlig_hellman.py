"""Capstone 2 (Pohlig--Hellman): DLP instances g^x = h in (Z/pZ)^* with a chosen shape of p - 1.

``params`` of a size class (bench/config.yaml)::

    bits: 100            # bit length of p (exact)
    qmax_bits: 40        # every prime factor of p - 1 (hence of ord g) has <= qmax_bits bits;
                         # keeps the BSGS subproblems feasible (about 2^(qmax_bits/2) steps)
    smooth_bits: 16      # optional: prime bound of the "smooth" shape
    shapes: [smooth, prime-power, max-prime, random]           # p - 1 shapes to draw from
                                                               # (uniformly; repeat = weight)
    bases:  [generator, subgroup, prime-order, prime-power-order]   # kinds of base g
    xs:     [random, zero, max]                                # kinds of exponent

Shapes of p - 1 = 2^k * (odd part):
    smooth       all prime factors <= smooth_bits bits
    prime-power  one factor q^e (q of 2..12 bits, e >= 2) of 30--60 % of the bits
    max-prime    one prime factor of exactly qmax_bits bits (the hardest BSGS case)
    random       prime factors of random sizes <= qmax_bits bits
Bases: a primitive root, or g of order n | p - 1 where n is a random proper divisor
(``subgroup``, it keeps the largest prime of p - 1), the largest prime factor
(``prime-order``) or the largest prime power q^e with e >= 2 (``prime-power-order``).
Exponents: random in [0, n), 0 (so h = 1) or n - 1.

The vector ``input`` is {p, g, h, factors} -- ``factors`` is the factorization of p - 1,
which the task gives (see reference/README.md); ``expected`` is {x, order} with
x = log_g h in [0, ord g) from Sage's ``discrete_log`` (checked against the planted x).
``verify`` accepts every x with g^x = h (mod p).
"""

from __future__ import annotations

import math
from collections import Counter

VERSION = 1

SHAPES = ("smooth", "prime-power", "max-prime", "max-prime", "random")
BASES = ("generator", "subgroup", "prime-order", "prime-power-order")
XS = ("random", "random", "random", "random", "zero", "max")   # repeats = weights


def _rand_prime(b: int, rng) -> int:
    """A uniform-ish random odd prime of exactly b >= 2 bits (randomness from rng only)."""
    from sage.all import is_prime

    while True:
        n = rng.getrandbits(b) | (1 << (b - 1)) | 1
        if is_prime(n):
            return n


def _build_p(bits: int, qmax: int, shape: str, smooth: int, rng) -> tuple[int, Counter]:
    """A prime p of exactly ``bits`` bits with p - 1 of the given shape, and the
    factorization of p - 1 (a Counter q -> e)."""
    from sage.all import is_prime

    cap = min(smooth, qmax) if shape == "smooth" else qmax
    for _ in range(10_000):
        f: Counter = Counter({2: rng.choice((1, 1, 1, 1, 2, 2, 3, 4, 6))})
        if shape == "prime-power":
            q = _rand_prime(rng.randint(2, max(2, min(12, qmax))), rng)
            target = rng.randint(3 * bits // 10, 6 * bits // 10)
            f[q] += max(2, round(target / math.log2(q)))
        elif shape == "max-prime":
            f[_rand_prime(qmax, rng)] += 1
        m = math.prod(q ** e for q, e in f.items())
        # p = m * q_last + 1 with q_last of r or r + 1 bits; fill until r fits under cap
        r = bits - m.bit_length()
        while r > cap:
            q = _rand_prime(rng.randint(2, min(cap, r - 2)), rng)
            f[q] += 1
            m *= q
            r = bits - m.bit_length()
        lens = [b for b in (r, r + 1) if 2 <= b <= cap]
        if not lens:
            continue
        for _ in range(200):
            q = _rand_prime(rng.choice(lens), rng)
            p = m * q + 1
            if p.bit_length() == bits and is_prime(p):
                f[q] += 1
                return p, f
    raise RuntimeError(f"no {bits}-bit prime of shape {shape} found")


def _primitive_root(p: int, f: Counter, rng) -> int:
    while True:
        r = rng.randrange(2, p - 1) if p > 3 else p - 1
        if all(pow(r, (p - 1) // q, p) != 1 for q in f):
            return r


def _base_order(f: Counter, kind: str, rng) -> tuple[int, str]:
    """The order n | p - 1 of the base, and the kind actually used."""
    full = math.prod(q ** e for q, e in f.items())
    if kind == "prime-power-order":
        powers = [(q, e) for q, e in f.items() if e >= 2]
        if powers:
            q, e = max(powers, key=lambda qe: qe[0] ** qe[1])
            return q ** e, kind
        kind = "prime-order"                     # p - 1 is squarefree: fall back
    if kind == "prime-order":
        return max(f), kind
    if kind == "subgroup" and full > 2:
        # a random proper divisor that keeps the largest prime (the hard subproblem)
        top = max(f)
        while True:
            n = math.prod(q ** (f[q] if q == top else rng.randint(0, f[q])) for q in sorted(f))
            if n < full:
                return n, kind
    return full, "generator"


def _factor_of(n: int, f: Counter) -> list[tuple[int, int]]:
    out = []
    for q in sorted(f):
        e = 0
        while n % q == 0:
            n //= q
            e += 1
        if e:
            out.append((q, e))
    return out


def generate(params: dict, rng) -> dict:
    from sage.all import GF, discrete_log

    bits, qmax = int(params["bits"]), int(params.get("qmax_bits", 40))
    qmax = min(qmax, bits - 2)
    shape = rng.choice(params.get("shapes") or SHAPES)
    kind = rng.choice(params.get("bases") or BASES)
    xkind = rng.choice(params.get("xs") or XS)
    p, f = _build_p(bits, qmax, shape, int(params.get("smooth_bits", 16)), rng)
    n, kind = _base_order(f, kind, rng)
    g = pow(_primitive_root(p, f, rng), (p - 1) // n, p)
    x = {"zero": 0, "max": n - 1}.get(xkind) if xkind != "random" else rng.randrange(n)
    h = pow(g, x, p)

    # Oracle: Sage's own discrete log (independent of the planted x and of the reference).
    F = GF(p)
    x_sage = int(discrete_log(F(h), F(g), ord=n))
    if x_sage != x % n:
        raise AssertionError(f"Sage discrete_log disagrees: {x_sage} != {x % n} (p = {p})")

    of = _factor_of(n, f)
    lpf = max((q for q, _ in of), default=1)
    tags = [shape, kind, f"qmax-{qmax}", f"lpf-{lpf.bit_length()}"]
    tags += {"zero": ["x-zero", "h-one"], "max": ["x-max"]}.get(xkind, [])
    if bits <= 24:
        tags.append("small-p")
    if any(e >= 2 and q > 2 for q, e in of):
        tags.append("odd-prime-power")
    return {"input": {"p": p, "g": g, "h": h, "factors": [[q, e] for q, e in sorted(f.items())]},
            "expected": {"x": x_sage, "order": n}, "tags": tags}


def verify(vector: dict, output: dict) -> str | None:
    inp = vector["input"]
    x = (output or {}).get("x")
    if isinstance(x, str) and x.lstrip("-").isdigit():
        x = int(x)
    if not isinstance(x, int) or isinstance(x, bool):
        return f"x = {x!r} is not an integer"
    p, g, h = inp["p"], inp["g"], inp["h"]
    if pow(g, x, p) != h % p:
        return f"g^x != h (mod p) for x = {x}"
    return None
