"""Primality, pseudoprime, Korselt and Lucas--Lehmer vectors."""

from __future__ import annotations

import math

VERSION = 1
OPS = ("fermat", "miller_rabin", "solovay_strassen", "korselt", "lucas_lehmer",
       "mersenne_reduce", "wilson")
CARMICHAEL = (561, 1105, 1729, 41041, 8911, 6601)
PSEUDOPRIMES = (2047, 11305, 1373653, 25326001)


def generate(params: dict, rng) -> dict:
    from sage.all import factor, is_prime, next_prime

    bits = int(params["bits"])
    op = rng.choice(params.get("ops") or OPS)
    if op in ("fermat", "miller_rabin", "solovay_strassen"):
        kind = rng.choice(("random", "prime", "carmichael", "pseudoprime"))
        if kind == "carmichael":
            n = rng.choice(CARMICHAEL)
        elif kind == "pseudoprime":
            n = rng.choice(PSEUDOPRIMES)
        elif kind == "prime":
            n = int(next_prime(rng.getrandbits(bits) | (1 << (bits - 1)) | 1))
        else:
            n = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
        bases = [2, 3, 5, rng.randrange(2, max(3, n))]
        return {"input": {"op": op, "n": n, "bases": bases},
                "expected": {"prime": bool(is_prime(n))}, "tags": [op, kind]}
    if op == "wilson":
        n = rng.randrange(0, 25)
        return {"input": {"op": op, "n": n}, "expected": {"prime": bool(is_prime(n))},
                "tags": [op, "small-only"]}
    if op == "korselt":
        n = rng.choice(CARMICHAEL + PSEUDOPRIMES + (45, 225, 325))
        factors = [[int(p), int(e)] for p, e in factor(n)]
        squarefree = all(e == 1 for _, e in factors)
        liars = math.prod(math.gcd(n - 1, p - 1) for p, _ in factors) if squarefree else None
        return {"input": {"op": op, "n": n, "factors": factors},
                "expected": {"liars": liars}, "tags": [op, "squarefree" if squarefree else "non-squarefree"]}
    if op == "lucas_lehmer":
        exponent = rng.choice((2, 3, 5, 7, 11, 13, 17, 19, 31))
        prime = bool(is_prime((1 << exponent) - 1))
        return {"input": {"op": op, "exponent": exponent}, "expected": {"prime": prime},
                "tags": [op, "mersenne-prime" if prime else "mersenne-composite"]}
    exponent = rng.choice((3, 5, 7, 11, 17, 31))
    x = rng.getrandbits(3 * exponent)
    return {"input": {"op": op, "x": x, "exponent": exponent},
            "expected": {"value": x % ((1 << exponent) - 1)}, "tags": [op]}


def _valid_witness(n, op, witness):
    base, kind = witness.get("base"), witness.get("kind")
    if not isinstance(base, int):
        return False
    a = base % n
    if kind == "gcd":
        return math.gcd(a, n) > 1 and witness.get("value") == math.gcd(a, n)
    if math.gcd(a, n) != 1:
        return False
    if op == "fermat":
        value = pow(a, n - 1, n)
        return value != 1 and witness.get("value") == value
    if op == "solovay_strassen":
        from sage.all import kronecker
        value = pow(a, (n - 1) // 2, n)
        j = int(kronecker(a, n))
        return (j == 0 or value != j % n) and witness.get("value") == value and witness.get("jacobi") == j
    if op == "miller_rabin":
        d, s = n - 1, 0
        while d % 2 == 0:
            d //= 2
            s += 1
        sequence = [pow(a, d, n)]
        if sequence[0] in (1, n - 1):
            return False
        for _ in range(1, s):
            sequence.append(sequence[-1] * sequence[-1] % n)
            if sequence[-1] == n - 1:
                return False
        return witness.get("sequence") == sequence
    return False


def verify(vector: dict, output: dict) -> str | None:
    inp, op, expected = vector["input"], vector["input"]["op"], vector["expected"]
    out = output or {}
    if op in ("fermat", "miller_rabin", "solovay_strassen"):
        verdict = out.get("verdict")
        if expected["prime"]:
            return None if verdict == "probable_prime" else "prime input was not accepted"
        witnesses = out.get("witnesses")
        if verdict == "probable_prime":
            return None if witnesses == [] else "a passing round must not report witnesses"
        if verdict != "composite":
            return "invalid probabilistic-test verdict"
        if not isinstance(witnesses, list) or not witnesses:
            return "missing compositeness witnesses"
        if not all(_valid_witness(inp["n"], op, w) for w in witnesses):
            return "invalid compositeness witness"
        return None
    if op == "wilson":
        return None if (out.get("verdict") == "prime") == expected["prime"] else "incorrect Wilson verdict"
    if op == "lucas_lehmer":
        if (out.get("verdict") == "prime") != expected["prime"]:
            return "incorrect Lucas-Lehmer verdict"
        return None if (out.get("residue") == 0) == expected["prime"] else "incorrect final residue"
    if op == "mersenne_reduce":
        return None if out.get("value") == expected["value"] else "incorrect Mersenne reduction"
    if op == "korselt":
        factors = inp["factors"]
        squarefree = all(e == 1 for _, e in factors)
        want = squarefree and all((inp["n"] - 1) % (p - 1) == 0 for p, _ in factors)
        if bool(out.get("carmichael")) != want or bool(out.get("squarefree")) != squarefree:
            return "incorrect Korselt classification"
        if out.get("liars") != expected["liars"]:
            return "incorrect Fermat liar count"
        return None
    return f"unknown operation {op}"
