"""Capstone 5, Lenstra's elliptic curve factorization: test vectors and verifier.

``params`` of a size class (``bench/config.yaml``)::

    shape:  semiprime | unbalanced | square | power | multi | prime
    pbits:  bits of the smallest prime factor, an int or a range [lo, hi]
    nbits:  bits of n (ignored by semiprime and power), an int or a range [lo, hi]
    k:      [lo, hi] number of prime factors (multi) or the exponent (power)
    op:     factor | factorize          (the solver's operation; default factorize)

Shapes: ``semiprime`` n = p q with p, q of ``pbits`` bits (the hardest case for ECM at a
given size of n); ``unbalanced`` n = p q with q of ``nbits - pbits`` bits; ``square``
p^2 q or p q^2 (repeated factors); ``power`` n = p^k; ``multi`` k distinct primes, all of
at least ``pbits`` bits; ``prime`` n itself is prime (expected: "n is prime", no factor).

``expected`` = ``{"prime": bool, "factorization": [[p, e], ...]}`` from Sage's ``factor``.
``verify`` accepts the full factorization (it is unique, so it is compared with
``expected``) or, for ``op: factor``, any proper divisor of n.
"""

from __future__ import annotations

import random

VERSION = 1


def _bits(spec, rng: random.Random) -> int:
    if isinstance(spec, (list, tuple)):
        return rng.randint(int(spec[0]), int(spec[1]))
    return int(spec)


def _prime(bits: int, rng: random.Random, avoid=()) -> int:
    """A random prime of exactly ``bits`` bits (randomness from rng, primality from Sage)."""
    from sage.all import next_prime

    while True:
        x = rng.getrandbits(bits) | (1 << (bits - 1))
        p = int(next_prime(x))
        if p.bit_length() == bits and p not in avoid:
            return p


def _split(total: int, parts: int, least: int, rng: random.Random) -> list[int]:
    """``parts`` sizes >= ``least`` summing to ``total`` (>= parts * least)."""
    sizes = [least] * parts
    for _ in range(total - parts * least):
        sizes[rng.randrange(parts)] += 1
    return sizes


def generate(params: dict, rng: random.Random) -> dict:
    from sage.all import factor, is_prime

    shape = params.get("shape", "semiprime")
    op = params.get("op", "factorize")
    pb = _bits(params.get("pbits", 20), rng)
    nb = _bits(params.get("nbits", 2 * pb), rng)
    tags = [shape]
    if shape == "semiprime":
        p = _prime(pb, rng)
        primes = [p, _prime(pb, rng, avoid={p})]
        tags.append("balanced")
    elif shape == "unbalanced":
        primes = [_prime(pb, rng), _prime(max(nb - pb, pb + 1), rng)]
    elif shape == "square":
        p = _prime(pb, rng)
        q = _prime(max(pb, nb - 2 * pb), rng, avoid={p})
        primes = [p, p, q] if rng.random() < 0.5 else [p, q, q]
        tags += ["repeated", "small-repeated" if primes[1] == p else "large-repeated"]
    elif shape == "power":
        k = _bits(params.get("k", [2, 5]), rng)
        primes = [_prime(pb, rng)] * k
        tags += ["repeated", "perfect-power"]
    elif shape == "multi":
        k = _bits(params.get("k", [3, 5]), rng)
        k = max(3, min(k, nb // pb))
        primes = []
        for b in [pb] + _split(nb - pb, k - 1, pb, rng):
            primes.append(_prime(b, rng, avoid=set(primes)))
    elif shape == "prime":
        primes = [_prime(nb, rng)]
        tags.append("prime")
    else:
        raise ValueError(f"unknown shape {shape!r}")
    n = 1
    for p in primes:
        n *= p
    fac = [[int(p), int(e)] for p, e in factor(n)]          # the oracle
    assert sorted(primes) == sorted(p for p, e in fac for _ in range(e))
    prime = bool(is_prime(n))
    smallest = fac[0][0]
    tags += [f"p{smallest.bit_length()}", f"n{n.bit_length()}"]
    if len(fac) >= 3:
        tags.append("several-factors")
    return {"input": {"op": op, "n": n}, "expected": {"prime": prime, "factorization": fac},
            "tags": tags}


def _int(v) -> int | None:
    if isinstance(v, bool):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def verify(vector: dict, output: dict) -> str | None:
    if not isinstance(output, dict):
        return f"output is not an object: {output!r}"
    n = int(vector["input"]["n"])
    op = vector["input"].get("op", "factorize")
    exp = vector["expected"]
    fac = output.get("factorization")
    if exp["prime"]:
        if output.get("factor") not in (None, n, str(n)):
            return f"n = {n} is prime, but the answer gives the factor {output['factor']!r}"
        if fac is not None and _norm(fac) != [[n, 1]]:
            return f"n = {n} is prime, but the answer factors it as {fac!r}"
        if output.get("prime") is not True and fac is None:
            return f"n = {n} is prime, the answer does not say so"
        return None
    if output.get("prime") is True:
        return f"n = {n} is composite, the answer says it is prime"
    if fac is not None:
        got = _norm(fac)
        if got is None:
            return f"malformed factorization {fac!r}"
        if got != exp["factorization"]:
            return f"factorization {got} != {exp['factorization']}"
        return None
    if op == "factor":
        d = _int(output.get("factor"))
        if d is None or not 1 < d < n or n % d:
            return f"{output.get('factor')!r} is not a proper factor of {n}"
        return None
    return "no 'factorization' in the answer"


def _norm(fac) -> list[list[int]] | None:
    """``[[p, e], ...]`` sorted, equal primes merged; None if malformed."""
    acc: dict[int, int] = {}
    try:
        for item in fac:
            p, e = (_int(x) for x in item)
            if p is None or e is None or p < 2 or e < 1:
                return None
            acc[p] = acc.get(p, 0) + e
    except (TypeError, ValueError):
        return None
    return [[p, e] for p, e in sorted(acc.items())]
