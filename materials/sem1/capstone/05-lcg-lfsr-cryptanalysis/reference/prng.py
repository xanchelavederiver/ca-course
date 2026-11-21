from __future__ import annotations

import math


def lcg_generate(a: int, c: int, m: int, state: int, count: int) -> list[int]:
    if m <= 0 or not 0 <= state < m or count < 0:
        raise ValueError("invalid LCG parameters")
    out = []
    for _ in range(count):
        out.append(state)
        state = (a * state + c) % m
    return out


def lcg_next(a: int, c: int, m: int, state: int) -> int:
    return lcg_generate(a, c, m, state, 2)[1]


def lcg_period(a: int, c: int, m: int, state: int, limit: int = 1_000_000) -> dict:
    if m <= 0 or not 0 <= state < m:
        raise ValueError("invalid LCG parameters")
    seen = {}
    x, i = state, 0
    while x not in seen:
        if i >= limit:
            raise ValueError("period search limit exceeded")
        seen[x] = i
        x = (a * x + c) % m
        i += 1
    return {"period": i - seen[x], "tail": seen[x], "repeated_state": x}


def full_period_conditions(a: int, c: int, m: int, factors: list[list[int]]) -> dict:
    if m <= 1 or math.prod(p ** e for p, e in factors) != m:
        raise ValueError("invalid modulus or factorization")
    c_coprime = math.gcd(c, m) == 1
    prime_conditions = {p: (a - 1) % p == 0 for p, _ in factors}
    four_condition = m % 4 != 0 or a % 4 == 1
    full = c_coprime and all(prime_conditions.values()) and four_condition
    return {"full_period": full, "c_coprime": c_coprime,
            "prime_conditions": {str(p): value for p, value in prime_conditions.items()},
            "four_condition": four_condition}


def lcg_recover(outputs: list[int]) -> dict:
    if len(outputs) < 4 or len(set(outputs)) < 2:
        raise ValueError("not enough distinct LCG observations")
    differences = [b - a for a, b in zip(outputs, outputs[1:])]
    determinants = [differences[i + 2] * differences[i] - differences[i + 1] ** 2
                    for i in range(len(differences) - 2)]
    m = math.gcd(*determinants)
    if m <= max(outputs):
        raise ValueError("observations do not determine the modulus uniquely")
    t0 = differences[0] % m
    if math.gcd(t0, m) != 1:
        raise ValueError("observations do not determine a unique multiplier")
    a = differences[1] % m * pow(t0, -1, m) % m
    c = (outputs[1] - a * outputs[0]) % m
    if any((a * x + c) % m != y for x, y in zip(outputs, outputs[1:])):
        raise ValueError("recovered parameters are inconsistent")
    return {"a": a, "c": c, "m": m, "next": (a * outputs[-1] + c) % m}


def lcg_decrypt(ciphertext: list[int], known_plaintext: list[int]) -> dict:
    if not 0 < len(known_plaintext) < len(ciphertext):
        raise ValueError("known plaintext must be a nonempty proper prefix")
    observed = [plain ^ cipher for plain, cipher in zip(known_plaintext, ciphertext)]
    recovered = lcg_recover(observed)
    stream = lcg_generate(recovered["a"], recovered["c"], recovered["m"], observed[0],
                          len(ciphertext))
    if stream[:len(observed)] != observed:
        raise ValueError("recovered LCG does not reproduce the known keystream")
    recovered["plaintext"] = [cipher ^ key for cipher, key in zip(ciphertext, stream)]
    return recovered


def lfsr_generate(coefficients: list[int], state: list[int], count: int) -> list[int]:
    if not coefficients or len(coefficients) != len(state) or count < 0:
        raise ValueError("invalid LFSR dimensions")
    if any(bit not in (0, 1) for bit in coefficients + state):
        raise ValueError("LFSR is defined over GF(2)")
    out = list(state)
    length = len(coefficients)
    while len(out) < count:
        out.append(sum(coefficients[j - 1] * out[-j] for j in range(1, length + 1)) % 2)
    return out[:count]


def lfsr_period(coefficients: list[int], state: list[int], limit: int = 1_000_000) -> dict:
    lfsr_generate(coefficients, state, 0)
    seen = {}
    current = tuple(state)
    while current not in seen:
        if len(seen) >= limit:
            raise ValueError("period search limit exceeded")
        seen[current] = len(seen)
        extended = lfsr_generate(coefficients, list(current), len(current) + 1)
        current = tuple(extended[1:])
    return {"period": len(seen) - seen[current], "tail": seen[current],
            "repeated_state": list(current)}


def polynomial_forms(connection_mask: int, linear_complexity: int) -> dict:
    connection = [connection_mask >> i & 1 for i in range(linear_complexity + 1)]
    characteristic = [connection_mask >> (linear_complexity - i) & 1
                      for i in range(linear_complexity + 1)]
    return {"connection": connection, "characteristic": characteristic,
            "coefficients": connection[1:]}


def berlekamp_massey(sequence: list[int]) -> dict:
    if any(bit not in (0, 1) for bit in sequence):
        raise ValueError("sequence must contain bits")
    c, b, length, m = 1, 1, 0, -1
    trace = []
    for n, bit in enumerate(sequence):
        discrepancy = bit
        for i in range(1, length + 1):
            discrepancy ^= (c >> i & 1) & sequence[n - i]
        row = {"n": n, "discrepancy": discrepancy}
        if discrepancy:
            previous = c
            c ^= b << (n - m)
            row["shift"] = n - m
            if 2 * length <= n:
                length = n + 1 - length
                b = previous
                m = n
                row["new_length"] = length
        trace.append(row)
    if len(sequence) < 2 * length:
        raise ValueError("sequence is too short for unique recovery")
    forms = polynomial_forms(c, length)
    return {"linear_complexity": length, "connection_mask": c, "state": sequence[:length],
            "trace": trace, **forms}


def lfsr_recover(sequence: list[int]) -> dict:
    recovered = berlekamp_massey(sequence)
    coefficients = recovered["coefficients"]
    predicted = lfsr_generate(coefficients, recovered["state"], len(sequence) + 1)
    if predicted[:-1] != sequence:
        raise ValueError("recovered recurrence does not reproduce observations")
    recovered["next"] = predicted[-1]
    return recovered


def xor_stream(coefficients: list[int], state: list[int], data: list[int]) -> list[int]:
    stream = lfsr_generate(coefficients, state, len(data))
    return [bit ^ key for bit, key in zip(data, stream)]


def lfsr_decrypt(ciphertext: list[int], known_plaintext: list[int]) -> dict:
    if not 0 < len(known_plaintext) < len(ciphertext):
        raise ValueError("known plaintext must be a nonempty proper prefix")
    if any(bit not in (0, 1) for bit in ciphertext + known_plaintext):
        raise ValueError("LFSR ciphertext and plaintext must contain bits")
    observed = [plain ^ cipher for plain, cipher in zip(known_plaintext, ciphertext)]
    recovered = lfsr_recover(observed)
    stream = lfsr_generate(recovered["coefficients"], recovered["state"], len(ciphertext))
    recovered["plaintext"] = [cipher ^ key for cipher, key in zip(ciphertext, stream)]
    return recovered
