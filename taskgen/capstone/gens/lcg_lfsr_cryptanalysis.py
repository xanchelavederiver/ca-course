"""Unique-recovery LCG/LFSR vectors; ambiguous observations are not generated."""

from __future__ import annotations

import math

VERSION = 1
OPS = ("lcg_generate", "lcg_period", "lcg_full_period", "lcg_next", "lcg_recover",
       "lfsr_generate", "berlekamp_massey", "lfsr_recover", "lfsr_polynomial", "lfsr_decrypt")


def _lfsr_case(rng, max_length=12):
    from sage.all import GF
    from sage.matrix.berlekamp_massey import berlekamp_massey as sage_bm
    from taskgen.tasks.crypto.lfsr import berlekamp_massey, lfsr_bits

    for _ in range(100):
        length = rng.randrange(2, max_length + 1)
        coefficients = [rng.randrange(2) for _ in range(length)]
        state = [rng.randrange(2) for _ in range(length)]
        sequence = lfsr_bits(coefficients, state, 2 * length + 4)
        oracle = berlekamp_massey(sequence)
        sage_degree = sage_bm([GF(2)(bit) for bit in sequence]).degree()
        if oracle["L"] >= max(2, length - 1) and sage_degree == oracle["L"]:
            return coefficients, state, sequence, oracle
    raise RuntimeError("failed to draw a nondegenerate unique LFSR")


def generate(params: dict, rng) -> dict:
    bits = int(params["bits"])
    op = rng.choice(params.get("ops") or OPS)
    if op in ("lcg_generate", "lcg_next"):
        m = rng.getrandbits(bits) | (1 << (bits - 1))
        a, c, state = rng.randrange(m), rng.randrange(m), rng.randrange(m)
        if op == "lcg_next":
            return {"input": {"op": op, "a": a, "c": c, "m": m, "state": state},
                    "expected": {"next": (a * state + c) % m}, "tags": [op]}
        count = 12
        outputs = []
        x = state
        for _ in range(count):
            outputs.append(x)
            x = (a * x + c) % m
        return {"input": {"op": op, "a": a, "c": c, "m": m, "state": state, "count": count},
                "expected": {"outputs": outputs}, "tags": [op]}
    if op == "lcg_period":
        m = rng.randrange(2, 1 << min(bits, 12))
        a, c, state = rng.randrange(m), rng.randrange(m), rng.randrange(m)
        return {"input": {"op": op, "a": a, "c": c, "m": m, "state": state},
                "expected": {}, "tags": [op, "bounded-period"]}
    if op == "lcg_full_period":
        if rng.randrange(2):
            m = 1 << rng.randrange(2, min(bits, 12) + 1)
            factors = [[2, m.bit_length() - 1]]
            good_a = 1 + (4 if m >= 4 else 2) * rng.randrange(1, 8)
            a = good_a if rng.randrange(2) else good_a + 2
        else:
            m, factors = 15, [[3, 1], [5, 1]]
            a = 6 if rng.randrange(2) else 4
        c = rng.randrange(1, m)
        full = (math.gcd(c, m) == 1 and all((a - 1) % p == 0 for p, _ in factors)
                and (m % 4 != 0 or a % 4 == 1))
        return {"input": {"op": op, "a": a, "c": c, "m": m, "factors": factors},
                "expected": {"full_period": full}, "tags": [op, "full" if full else "not-full"]}
    if op == "lcg_recover":
        for _ in range(1000):
            m = rng.getrandbits(bits) | (1 << (bits - 1))
            a, c, state = rng.randrange(2, m), rng.randrange(m), rng.randrange(m)
            outputs = []
            x = state
            for _ in range(7):
                outputs.append(x)
                x = (a * x + c) % m
            differences = [y - x for x, y in zip(outputs, outputs[1:])]
            determinants = [differences[i + 2] * differences[i] - differences[i + 1] ** 2
                            for i in range(len(differences) - 2)]
            if math.gcd(*determinants) == m and math.gcd(differences[0] % m, m) == 1:
                return {"input": {"op": op, "outputs": outputs},
                        "expected": {"a": a, "c": c, "m": m}, "tags": [op, "unique"]}
        raise RuntimeError("failed to draw a uniquely recoverable LCG")
    if op == "lfsr_polynomial":
        length = rng.randrange(1, max(2, bits // 2))
        mask = 1
        for i in range(1, length + 1):
            mask |= rng.randrange(2) << i
        return {"input": {"op": op, "connection_mask": mask, "linear_complexity": length},
                "expected": {}, "tags": [op]}
    coefficients, state, sequence, oracle = _lfsr_case(rng, min(12, max(3, bits // 2)))
    if op in ("berlekamp_massey", "lfsr_recover"):
        return {"input": {"op": op, "sequence": sequence},
                "expected": {"linear_complexity": oracle["L"]},
                "tags": [op, "unique", "length-2L-plus"]}
    if op == "lfsr_generate":
        return {"input": {"op": op, "coefficients": coefficients, "state": state, "count": len(sequence)},
                "expected": {"bits": sequence}, "tags": [op]}
    plaintext = [rng.randrange(2) for _ in range(len(sequence))]
    key = sequence
    ciphertext = [x ^ y for x, y in zip(plaintext, key)]
    return {"input": {"op": "lfsr_decrypt", "coefficients": coefficients, "state": state,
                      "ciphertext": ciphertext},
            "expected": {"plaintext": plaintext}, "tags": [op, "xor-stream"]}


def verify(vector: dict, output: dict) -> str | None:
    inp, op, expected = vector["input"], vector["input"]["op"], vector["expected"]
    out = output or {}
    if op in ("lcg_generate", "lcg_next"):
        key = "outputs" if op == "lcg_generate" else "next"
        return None if out.get(key) == expected[key] else "incorrect LCG output"
    if op == "lcg_period":
        m, x = inp["m"], inp["state"]
        seen = {}
        while x not in seen:
            seen[x] = len(seen)
            x = (inp["a"] * x + inp["c"]) % m
        period, tail = len(seen) - seen[x], seen[x]
        return None if (out.get("period"), out.get("tail")) == (period, tail) else "incorrect period or tail"
    if op == "lcg_full_period":
        return None if bool(out.get("full_period")) == expected["full_period"] else "incorrect full-period verdict"
    if op == "lcg_recover":
        a, c, m = out.get("a"), out.get("c"), out.get("m")
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in (a, c, m)):
            return "invalid recovered parameter types"
        if any((a * x + c) % m != y for x, y in zip(inp["outputs"], inp["outputs"][1:])):
            return "recovered parameters do not reproduce observations"
        return None
    if op == "lfsr_generate":
        return None if out.get("bits") == expected["bits"] else "incorrect LFSR output"
    if op in ("berlekamp_massey", "lfsr_recover"):
        from sage.all import GF, PolynomialRing
        from sage.matrix.berlekamp_massey import berlekamp_massey as sage_bm
        from taskgen.tasks.crypto.lfsr import lfsr_bits
        sequence = inp["sequence"]
        length = out.get("linear_complexity")
        oracle = sage_bm([GF(2)(bit) for bit in sequence])
        if length != oracle.degree():
            return "incorrect linear complexity"
        ring = PolynomialRing(GF(2), "x")
        if ring(out.get("characteristic") or []) != oracle:
            return "incorrect characteristic polynomial"
        coefficients, state = out.get("coefficients"), out.get("state")
        if not isinstance(coefficients, list) or not isinstance(state, list):
            return "missing recurrence or state"
        if lfsr_bits(coefficients, state, len(sequence)) != sequence:
            return "recurrence does not reproduce observations"
        if op == "lfsr_recover":
            predicted = lfsr_bits(coefficients, state, len(sequence) + 1)
            if out.get("next") != predicted[-1]:
                return "incorrect next-bit prediction"
        return None
    if op == "lfsr_polynomial":
        mask, length = inp["connection_mask"], inp["linear_complexity"]
        connection = [mask >> i & 1 for i in range(length + 1)]
        characteristic = [mask >> (length - i) & 1 for i in range(length + 1)]
        if out.get("connection") != connection or out.get("characteristic") != characteristic:
            return "incorrect polynomial conversion"
        return None
    if op == "lfsr_decrypt":
        plaintext = out.get("plaintext")
        if not isinstance(plaintext, list) or len(plaintext) != len(inp["ciphertext"]):
            return "invalid plaintext"
        from taskgen.tasks.crypto.lfsr import lfsr_bits
        key = lfsr_bits(inp["coefficients"], inp["state"], len(plaintext))
        if [x ^ y for x, y in zip(plaintext, key)] != inp["ciphertext"]:
            return "decryption does not reproduce ciphertext"
        return None
    return f"unknown operation {op}"
