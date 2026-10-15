"""Capstone 4 (quadratic sieve): composite n to factor.

Vector: ``input = {"n": n}`` (``"full": true`` asks for the complete factorization),
``expected = {"factorization": [[p, e], ...]}`` from Sage's ``factor`` (the oracle).

``params``:

- ``bits``: the size of n;
- ``shape``: ``balanced`` (n = pq, p and q of bits/2 bits) or a list of shapes to draw
  from (each vector draws one with ``rng``):

  - ``unbalanced``: n = pq with p of ``small_bits`` (default bits/4) bits, still above
    the factor base bound, so the sieve has to find it;
  - ``small-factor``: a prime factor of 2--12 bits (n may be even); trial division up
    to B finds it before any sieving;
  - ``square``: n = p^2; ``perfect-square``: n = m^2, m = pq; ``cube``: n = p^3.
    QS cannot split prime powers (the solver must detect perfect powers);
  - ``repeated``: n = p^2 q (not a perfect power; QS splits it);
  - ``close``: n = pq with |p - q| tiny (Fermat would win; f(t) at t = (p+q)/2 is a
    square);
  - ``multi``: 3 or 4 primes of similar size, with ``full: true``.

``verify`` accepts any non-trivial divisor 1 < d < n as ``factor``; a
``factorization``, when given (required with ``full``), must be the factorization.
"""

from __future__ import annotations

VERSION = 1

SHAPES = ("balanced", "unbalanced", "small-factor", "square", "perfect-square", "cube",
          "repeated", "close", "multi")


def _prime(rng, bits: int) -> int:
    """A prime of exactly ``bits`` bits, >= 1.5 * 2^(bits-1): a product of such primes
    of a + b bits has a + b bits."""
    from sage.all import Integer, next_prime

    while True:
        x = rng.getrandbits(bits) | (1 << (bits - 1)) | (1 << (bits - 2))
        p = int(next_prime(Integer(x - 1)))      # the least prime >= x
        if p.bit_length() == bits:
            return p


def _split_bits(bits: int, k: int) -> list[int]:
    base = [bits // k] * k
    for i in range(bits - sum(base)):
        base[i] += 1
    return base


def _compose(shape: str, bits: int, params: dict, rng) -> tuple[int, list[str]]:
    if shape == "balanced":
        a, b = _split_bits(bits, 2)
        while True:
            p, q = _prime(rng, a), _prime(rng, b)
            if p != q:
                return p * q, ["balanced", "semiprime"]
    if shape == "unbalanced":
        a = int(params.get("small_bits") or max(bits // 4, 16))
        return _prime(rng, a) * _prime(rng, bits - a), ["unbalanced", "semiprime"]
    if shape == "small-factor":
        a = rng.randrange(2, 13)
        p = 2 if a == 2 and rng.getrandbits(1) else _prime(rng, a)
        return p * _prime(rng, bits - (1 if p == 2 else p.bit_length())), ["small-factor"]
    if shape == "square":
        return _prime(rng, (bits + 1) // 2) ** 2, ["square", "prime-power"]
    if shape == "perfect-square":
        a, b = _split_bits((bits + 1) // 2, 2)
        return (_prime(rng, a) * _prime(rng, b)) ** 2, ["perfect-square"]
    if shape == "cube":
        return _prime(rng, (bits + 2) // 3) ** 3, ["cube", "prime-power"]
    if shape == "repeated":
        a = bits // 3
        return _prime(rng, a) ** 2 * _prime(rng, bits - 2 * a), ["repeated-factor"]
    if shape == "close":
        from sage.all import Integer, next_prime

        a = (bits + 1) // 2
        p = _prime(rng, a)
        q = int(next_prime(Integer(p) + rng.randrange(1, 1 << 12)))
        return p * q, ["close-factors", "semiprime"]
    if shape == "multi":
        k = 3 + rng.getrandbits(1)
        n = 1
        for b in _split_bits(bits, k):
            n *= _prime(rng, b)
        return n, ["multi-factor", f"{k}-primes"]
    raise ValueError(f"unknown shape {shape!r} (have {', '.join(SHAPES)})")


def generate(params: dict, rng) -> dict:
    from sage.all import Integer, factor

    bits = int(params["bits"])
    shapes = params.get("shape", "balanced")
    shape = shapes if isinstance(shapes, str) else shapes[rng.randrange(len(shapes))]
    n, tags = _compose(shape, bits, params, rng)
    fac = [[int(p), int(e)] for p, e in factor(Integer(n))]
    inp = {"n": n}
    if shape == "multi" or params.get("full"):
        inp["full"] = True
    return {"input": inp, "expected": {"factorization": fac},
            "tags": tags + [f"bits{n.bit_length()}"]}


def verify(vector: dict, output: dict) -> str | None:
    n = vector["input"]["n"]
    out = output if isinstance(output, dict) else {}
    d = out.get("factor")
    if not isinstance(d, int) or isinstance(d, bool) or not 1 < d < n or n % d:
        return f"factor = {d!r} is not a non-trivial divisor of n = {n}"
    fac = out.get("factorization")
    if fac is None:
        return "full factorization was asked for but not given" if vector["input"].get("full") else None
    try:
        got = sorted([int(p), int(e)] for p, e in fac)
    except (TypeError, ValueError):
        return f"malformed factorization {fac!r}"
    want = vector["expected"]["factorization"]
    return None if got == want else f"factorization {got} != {want}"
