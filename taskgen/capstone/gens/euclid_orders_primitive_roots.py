"""Vectors for Euclid, CRT/Garner, orders and primitive roots."""

from __future__ import annotations

import math

VERSION = 1
OPS = ("binary_gcd", "xgcd", "inverse", "batch_inverse", "crt", "garner",
       "order_sequential", "order_product_tree", "primitive_root")


def field_instance(bits, rng):
    from sage.all import factor, next_prime

    start = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
    p = int(next_prime(start))
    factors = [[int(q), int(e)] for q, e in factor(p - 1)]
    return p, factors


def generate(params: dict, rng) -> dict:
    bits = int(params["bits"])
    op = rng.choice(params.get("ops") or OPS)
    if op in ("binary_gcd", "xgcd"):
        a = rng.getrandbits(bits) * rng.choice((-1, 1))
        b = rng.getrandbits(bits) * rng.choice((-1, 1))
        if rng.randrange(5) == 0:
            a = 0
        return {"input": {"op": op, "a": a, "b": b},
                "expected": {"g": math.gcd(a, b)}, "tags": [op, "signed"]}
    if op == "inverse":
        n = rng.getrandbits(bits) | 1 | (1 << (bits - 1))
        a = rng.randrange(2, n)
        while math.gcd(a, n) != 1:
            a += 1
        return {"input": {"op": op, "a": a, "n": n},
                "expected": {"inverse": pow(a, -1, n)}, "tags": [op]}
    if op == "batch_inverse":
        n = rng.getrandbits(bits) | 1 | (1 << (bits - 1))
        values = [rng.randrange(-2 * n, 2 * n) for _ in range(12)]
        values[0], values[1] = 0, n
        expected = [pow(v, -1, n) if math.gcd(v, n) == 1 else None for v in values]
        return {"input": {"op": op, "values": values, "n": n},
                "expected": {"inverses": expected}, "tags": [op, "nonunits", "zero"]}
    if op in ("crt", "garner"):
        primes = (3, 5, 7, 11, 13, 17, 19, 23)
        moduli = sorted(rng.sample(primes, 4))
        residues = [rng.randrange(m) for m in moduli]
        expected = {}
        return {"input": {"op": op, "residues": residues, "moduli": moduli},
                "expected": expected, "tags": [op, "permuted-moduli"]}
    p, factors = field_instance(bits, rng)
    if op == "primitive_root":
        from sage.all import primitive_root as oracle
        return {"input": {"op": op, "p": p, "factors": factors},
                "expected": {"root": int(oracle(p))}, "tags": [op, f"bits-{bits}"]}
    from sage.all import Mod
    g = rng.randrange(1, p)
    if rng.randrange(3) == 0:
        g = pow(g, rng.randrange(2, 8), p)
    order = int(Mod(g, p).multiplicative_order())
    return {"input": {"op": op, "g": g, "p": p, "factors": factors},
            "expected": {"order": order}, "tags": [op, f"bits-{bits}"]}


def _integer(value):
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def verify(vector: dict, output: dict) -> str | None:
    inp, op = vector["input"], vector["input"]["op"]
    out = output or {}
    if op in ("binary_gcd", "xgcd"):
        g = _integer(out.get("g"))
        if g != math.gcd(inp["a"], inp["b"]):
            return "incorrect gcd"
        if op == "xgcd":
            x, y = _integer(out.get("x")), _integer(out.get("y"))
            if x is None or y is None or inp["a"] * x + inp["b"] * y != g:
                return "invalid Bézout coefficients"
        return None
    if op == "inverse":
        inv = _integer(out.get("inverse"))
        if inv is None or inp["a"] * inv % inp["n"] != 1:
            return "invalid inverse"
        return None
    if op == "batch_inverse":
        inverses = out.get("inverses")
        if not isinstance(inverses, list) or len(inverses) != len(inp["values"]):
            return "incorrect inverse list length"
        for value, inv in zip(inp["values"], inverses):
            if math.gcd(value, inp["n"]) == 1:
                if _integer(inv) is None or value * inv % inp["n"] != 1:
                    return "invalid batch inverse"
            elif inv is not None:
                return "non-unit must have null inverse"
        return None
    if op in ("crt", "garner"):
        x, modulus = _integer(out.get("x")), _integer(out.get("modulus"))
        if modulus != math.prod(inp["moduli"]):
            return "incorrect combined modulus"
        if x is None or any(x % m != r % m for r, m in zip(inp["residues"], inp["moduli"])):
            return "CRT solution has an incorrect residue"
        return None
    if op in ("order_sequential", "order_product_tree"):
        order = _integer(out.get("order"))
        if not order or order <= 0 or pow(inp["g"], order, inp["p"]) != 1:
            return "not an order"
        for q, _ in inp["factors"]:
            if order % q == 0 and pow(inp["g"], order // q, inp["p"]) == 1:
                return "order is not minimal"
        return None
    if op == "primitive_root":
        root = _integer(out.get("root"))
        if root is None or not 1 <= root < inp["p"]:
            return "invalid primitive root range"
        if any(pow(root, (inp["p"] - 1) // q, inp["p"]) == 1 for q, _ in inp["factors"]):
            return "element is not a primitive root"
        return None
    return f"unknown operation {op}"
