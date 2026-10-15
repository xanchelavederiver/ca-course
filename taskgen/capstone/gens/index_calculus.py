"""Capstone 3 (index calculus): DLP instances g^x = h in GF(p)^* for p of a given size.

``params`` of a size class (bench/config.yaml)::

    bits: 60                                   # bit length of p (exact)
    shapes: [random, safe, prime-power, smooth]   # shapes of p - 1 (uniform; repeat = weight)
    bases:  [generator, subgroup, prime-order, small-order]
    xs:     [random, zero, one, max]           # kinds of exponent

Shapes of p - 1:
    random       p a random prime (p - 1 as it comes)
    safe         p = 2q + 1 with q prime: the system is solved modulo 2 and a huge q
    prime-power  2^k or 3^k with k of 25--40 % of the bits divides p - 1 (CRT modulo a
                 large power of a small prime)
    smooth       every prime factor of p - 1 has <= 16 bits (many CRT moduli)
Bases: a primitive root (``generator``, the system can be built on g itself); g of order
(p - 1)/d for a random divisor 1 < d < p - 1 (``subgroup``); g of order the largest prime factor
of p - 1 (``prime-order``); g of a small order: a prime factor of p - 1 below 2^12, or
2 (g = -1) if there is none (``small-order``). In the last three the factor-base primes are
not powers of g, so the method needs a primitive root (see reference/README.md).
Exponents: random in [0, n), 0 (h = 1), 1 (h = g) or n - 1 (h = g^-1), n = ord g.

Tags: the shape and the base kind, ``h-smooth`` / ``h-not-smooth`` (h itself B-smooth for
the B = L(p)^(1/sqrt 2) of the spec's step 1, so that step 4 succeeds at k = 0) and
``small-p`` (p < 2^16: a factor base of a few primes, the group may be smaller than the
number of relations the estimate asks for).

The vector ``input`` is {p, g, h}; ``expected`` is {x, order} with x = log_g h in
[0, ord g) from Sage's (PARI's) discrete logarithm in GF(p), checked against the planted
x. ``verify`` accepts every x with g^x = h (mod p).
"""

from __future__ import annotations

import math

VERSION = 1

SHAPES = ("random", "random", "safe", "prime-power", "smooth")
BASES = ("generator", "generator", "generator", "subgroup", "prime-order", "small-order")
XS = ("random",) * 7 + ("zero", "one", "max")      # repeats = weights


def _rand_prime(b: int, rng) -> int:
    """A random prime of exactly b >= 2 bits (randomness from rng only)."""
    from sage.all import is_prime

    while True:
        n = rng.getrandbits(b) | (1 << (b - 1)) | (1 if b > 2 else 0)
        if is_prime(n):
            return n


def _build_p(bits: int, shape: str, rng) -> int:
    """A prime p of exactly `bits` bits with p - 1 of the given shape."""
    from sage.all import is_prime

    for _ in range(100_000):
        if shape == "safe" and bits >= 4:
            q = _rand_prime(bits - 1, rng)
            p = 2 * q + 1
        elif shape == "prime-power" and bits >= 12:
            ell = rng.choice((2, 3))
            k = max(2, round(rng.uniform(0.25, 0.40) * bits / math.log2(ell)))
            m = ell ** k * (1 if ell == 2 else 2)
            rest = bits - m.bit_length()
            p = m * (rng.getrandbits(rest) | (1 << (rest - 1))) + 1
        elif shape == "smooth" and bits >= 12:
            m = 2
            while bits - m.bit_length() > 16:
                m *= _rand_prime(rng.randint(2, 16), rng)
            rest = bits - m.bit_length()        # the last prime has rest or rest + 1 bits
            lens = [b for b in (rest, rest + 1) if 2 <= b <= 16]
            if not lens:
                continue
            p = m * _rand_prime(rng.choice(lens), rng) + 1
        else:
            p = _rand_prime(bits, rng)
        if p.bit_length() == bits and is_prime(p):
            return p
    raise RuntimeError(f"no {bits}-bit prime of shape {shape}")


def _factor(n: int) -> list[tuple[int, int]]:
    from sage.all import factor

    return [(int(q), int(e)) for q, e in factor(n)]


def _primitive_root(p: int, f: list[tuple[int, int]], rng) -> int:
    if p == 2:
        return 1
    while True:
        r = rng.randrange(2, p) if p > 3 else 2
        if all(pow(r, (p - 1) // q, p) != 1 for q, _ in f):
            return r


def _base_order(p: int, f: list[tuple[int, int]], kind: str, rng) -> tuple[int, str]:
    """The order n | p - 1 of the base, and the kind actually used."""
    n = p - 1
    if kind == "prime-order" and n > 2:
        return max(q for q, _ in f), kind
    if kind == "small-order" and n > 2:
        small = [q ** rng.randint(1, e) for q, e in f if 2 < q < 1 << 12]
        return (rng.choice(small) if small else 2), kind
    if kind == "subgroup" and n > 2:
        while True:
            d = math.prod(q ** rng.randint(0, e) for q, e in f)
            if 1 < d < n:                        # g = 1 would be degenerate
                return n // d, kind
    return n, "generator"


def _is_smooth(h: int, bound: int) -> bool:
    for q in range(2, bound + 1):
        while h % q == 0:
            h //= q
        if h == 1:
            return True
    return h == 1


def _bound(p: int) -> int:
    """B = L(p)^(1/sqrt 2) of the spec's step 1 (as in the reference, for the tags only)."""
    if p < 5:
        return 2
    lp = math.log(p)
    return max(2, min(p - 1, math.ceil(math.exp(math.sqrt(lp * math.log(lp) / 2)))))


def generate(params: dict, rng) -> dict:
    from sage.all import Mod

    bits = int(params["bits"])
    shape = rng.choice(params.get("shapes") or SHAPES)
    kind = rng.choice(params.get("bases") or BASES)
    xkind = rng.choice(params.get("xs") or XS)
    p = _build_p(bits, shape, rng)
    f = _factor(p - 1)
    if shape in ("prime-power", "smooth", "safe") and bits < 12:
        shape = "random"
    n, kind = _base_order(p, f, kind, rng)
    g = pow(_primitive_root(p, f, rng), (p - 1) // n, p)
    x = {"zero": 0, "one": 1 % n, "max": n - 1}.get(xkind, None)
    x = rng.randrange(n) if x is None else x
    h = pow(g, x, p)

    # Oracle: Sage's discrete logarithm in GF(p) (PARI znlog), independent of the planted x.
    x_sage = int(Mod(h, p).log(Mod(g, p))) % n
    if x_sage != x % n or pow(g, x_sage, p) != h:
        raise AssertionError(f"Sage log disagrees: {x_sage} != {x % n} (p = {p})")

    tags = [shape, kind, f"x-{xkind}" if xkind != "random" else "x-random",
            "h-smooth" if _is_smooth(h, _bound(p)) else "h-not-smooth"]
    if h == 1:
        tags.append("h-one")
    if p < 1 << 16:
        tags.append("small-p")
    return {"input": {"p": p, "g": g, "h": h}, "expected": {"x": x_sage, "order": n},
            "tags": tags}


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
