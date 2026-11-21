"""Unique-recovery LCG/LFSR vectors; ambiguous observations are not generated."""

from __future__ import annotations

import math

VERSION = 2
OPS = ("lcg_generate", "lcg_period", "lcg_full_period", "lcg_next", "lcg_recover", "lcg_decrypt",
       "lfsr_generate", "lfsr_period", "berlekamp_massey", "lfsr_recover", "lfsr_polynomial",
       "lfsr_decrypt")


def _lcg_recovery_case(bits, rng):
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
            return a, c, m, outputs
    raise RuntimeError("failed to draw a uniquely recoverable LCG")


def _lfsr_case(rng, max_length=12, extra=0):
    from sage.all import GF
    from sage.matrix.berlekamp_massey import berlekamp_massey as sage_bm
    from taskgen.tasks.crypto.lfsr import berlekamp_massey, lfsr_bits

    for _ in range(100):
        length = rng.randrange(2, max_length + 1)
        coefficients = [rng.randrange(2) for _ in range(length)]
        state = [rng.randrange(2) for _ in range(length)]
        known_length = 2 * length + 4
        sequence = lfsr_bits(coefficients, state, known_length + extra)
        oracle = berlekamp_massey(sequence[:known_length])
        sage_degree = sage_bm([GF(2)(bit) for bit in sequence[:known_length]]).degree()
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
    if op in ("lcg_recover", "lcg_decrypt"):
        a, c, m, outputs = _lcg_recovery_case(bits, rng)
        if op == "lcg_recover":
            return {"input": {"op": op, "outputs": outputs},
                    "expected": {"a": a, "c": c, "m": m}, "tags": [op, "unique"]}
        known_length = len(outputs)
        while len(outputs) < known_length + 8:
            outputs.append((a * outputs[-1] + c) % m)
        plaintext = [rng.randrange(m) for _ in outputs]
        ciphertext = [plain ^ key for plain, key in zip(plaintext, outputs)]
        return {"input": {"op": op, "ciphertext": ciphertext,
                          "known_plaintext": plaintext[:known_length]},
                "expected": {"plaintext": plaintext},
                "tags": [op, "known-plaintext", "unique", "xor-stream"]}
    if op == "lfsr_period":
        length = rng.randrange(1, min(bits, 8) + 1)
        coefficients = [rng.randrange(2) for _ in range(length)]
        state = [rng.randrange(2) for _ in range(length)]
        if rng.randrange(4) == 0:
            coefficients[-1] = 0
        if rng.randrange(4) == 0:
            state = [0] * length
        return {"input": {"op": op, "coefficients": coefficients, "state": state},
                "expected": {}, "tags": [op, "bounded-period"]}
    if op == "lfsr_polynomial":
        length = rng.randrange(1, max(2, bits // 2))
        mask = 1
        for i in range(1, length + 1):
            mask |= rng.randrange(2) << i
        return {"input": {"op": op, "connection_mask": mask, "linear_complexity": length},
                "expected": {}, "tags": [op]}
    coefficients, state, sequence, oracle = _lfsr_case(
        rng, min(12, max(3, bits // 2)), extra=8 if op == "lfsr_decrypt" else 0)
    if op in ("berlekamp_massey", "lfsr_recover"):
        return {"input": {"op": op, "sequence": sequence},
                "expected": {"linear_complexity": oracle["L"]},
                "tags": [op, "unique", "length-2L-plus"]}
    if op == "lfsr_generate":
        return {"input": {"op": op, "coefficients": coefficients, "state": state, "count": len(sequence)},
                "expected": {"bits": sequence}, "tags": [op]}
    known_length = len(sequence) - 8
    plaintext = [rng.randrange(2) for _ in sequence]
    ciphertext = [plain ^ key for plain, key in zip(plaintext, sequence)]
    return {"input": {"op": "lfsr_decrypt", "ciphertext": ciphertext,
                      "known_plaintext": plaintext[:known_length]},
            "expected": {"plaintext": plaintext},
            "tags": [op, "known-plaintext", "unique", "xor-stream"]}


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
    if op == "lcg_decrypt":
        a, c, m = out.get("a"), out.get("c"), out.get("m")
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in (a, c, m)):
            return "invalid recovered parameter types"
        if m <= 0 or not 0 <= a < m or not 0 <= c < m:
            return "invalid recovered LCG parameters"
        known = [plain ^ cipher for plain, cipher in zip(inp["known_plaintext"], inp["ciphertext"])]
        if not 0 <= known[0] < m or any((a * x + c) % m != y for x, y in zip(known, known[1:])):
            return "recovered parameters do not reproduce the known keystream"
        stream = []
        x = known[0]
        for _ in inp["ciphertext"]:
            stream.append(x)
            x = (a * x + c) % m
        plaintext = [cipher ^ key for cipher, key in zip(inp["ciphertext"], stream)]
        return None if out.get("plaintext") == plaintext else "incorrect LCG known-plaintext attack"
    if op == "lfsr_generate":
        return None if out.get("bits") == expected["bits"] else "incorrect LFSR output"
    if op == "lfsr_period":
        state = tuple(inp["state"])
        seen = {}
        while state not in seen:
            seen[state] = len(seen)
            nxt = sum(inp["coefficients"][j - 1] * state[-j]
                      for j in range(1, len(state) + 1)) % 2
            state = state[1:] + (nxt,)
        period, tail = len(seen) - seen[state], seen[state]
        return None if (out.get("period"), out.get("tail")) == (period, tail) else \
            "incorrect LFSR period or tail"
    if op in ("berlekamp_massey", "lfsr_recover", "lfsr_decrypt"):
        from sage.all import GF, PolynomialRing
        from sage.matrix.berlekamp_massey import berlekamp_massey as sage_bm
        from taskgen.tasks.crypto.lfsr import lfsr_bits
        sequence = inp.get("sequence")
        if sequence is None:
            sequence = [plain ^ cipher
                        for plain, cipher in zip(inp["known_plaintext"], inp["ciphertext"])]
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
        if op == "lfsr_decrypt":
            stream = lfsr_bits(coefficients, state, len(inp["ciphertext"]))
            plaintext = [cipher ^ key for cipher, key in zip(inp["ciphertext"], stream)]
            if out.get("plaintext") != plaintext:
                return "incorrect LFSR known-plaintext attack"
        return None
    if op == "lfsr_polynomial":
        mask, length = inp["connection_mask"], inp["linear_complexity"]
        connection = [mask >> i & 1 for i in range(length + 1)]
        characteristic = [mask >> (length - i) & 1 for i in range(length + 1)]
        if out.get("connection") != connection or out.get("characteristic") != characteristic:
            return "incorrect polynomial conversion"
        return None
    return f"unknown operation {op}"
