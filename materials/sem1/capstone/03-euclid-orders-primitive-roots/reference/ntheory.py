from __future__ import annotations

import math


def binary_gcd(a: int, b: int) -> int:
    a, b = abs(a), abs(b)
    if not a:
        return b
    if not b:
        return a
    shift = 0
    while a % 2 == 0 and b % 2 == 0:
        a //= 2
        b //= 2
        shift += 1
    while a % 2 == 0:
        a //= 2
    while b:
        while b % 2 == 0:
            b //= 2
        if a > b:
            a, b = b, a
        b -= a
    return a << shift


def xgcd(a: int, b: int) -> tuple[int, int, int]:
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    if old_r < 0:
        return -old_r, -old_s, -old_t
    return old_r, old_s, old_t


def inverse(a: int, n: int) -> int:
    if n <= 1:
        raise ValueError("modulus must exceed 1")
    g, x, _ = xgcd(a, n)
    if g != 1:
        raise ValueError("element is not invertible")
    return x % n


def batch_inverse(values: list[int], n: int) -> dict:
    if n <= 1:
        raise ValueError("modulus must exceed 1")
    units = []
    nonunits = []
    for i, value in enumerate(values):
        if binary_gcd(value, n) == 1:
            units.append((i, value % n))
        else:
            nonunits.append(i)
    inverses = [None] * len(values)
    if units:
        prefixes = []
        product = 1
        for _, value in units:
            prefixes.append(product)
            product = product * value % n
        inv_product = inverse(product, n)
        for j in range(len(units) - 1, -1, -1):
            index, value = units[j]
            inverses[index] = inv_product * prefixes[j] % n
            inv_product = inv_product * value % n
    return {"inverses": inverses, "nonunits": nonunits}


def validate_crt(residues: list[int], moduli: list[int]) -> None:
    if len(residues) != len(moduli) or not moduli:
        raise ValueError("residue and modulus lists must be nonempty and equally long")
    if any(m <= 1 for m in moduli):
        raise ValueError("moduli must exceed 1")
    for i, m in enumerate(moduli):
        for other in moduli[:i]:
            if binary_gcd(m, other) != 1:
                raise ValueError("moduli must be pairwise coprime")


def crt(residues: list[int], moduli: list[int]) -> tuple[int, int]:
    validate_crt(residues, moduli)
    x, modulus = residues[0] % moduli[0], moduli[0]
    for residue, m in zip(residues[1:], moduli[1:]):
        step = (residue - x) % m * inverse(modulus, m) % m
        x += modulus * step
        modulus *= m
        x %= modulus
    return x, modulus


def garner(residues: list[int], moduli: list[int]) -> tuple[int, int, list[int]]:
    validate_crt(residues, moduli)
    coefficients = [residues[0] % moduli[0]]
    for i in range(1, len(moduli)):
        product = 1
        value = coefficients[0]
        for j in range(1, i):
            product = product * moduli[j - 1] % moduli[i]
            value += coefficients[j] * product
        product = product * moduli[i - 1] % moduli[i]
        step = (residues[i] - value) % moduli[i] * inverse(product, moduli[i]) % moduli[i]
        coefficients.append(step)
    x, modulus = 0, 1
    for coefficient, m in zip(coefficients, moduli):
        x += modulus * coefficient
        modulus *= m
    return x % modulus, modulus, coefficients


def validate_field_input(g: int, p: int, factors: list[list[int]]) -> list[tuple[int, int]]:
    if p <= 2 or math.gcd(g, p) != 1:
        raise ValueError("g must be a unit modulo an odd prime p")
    normalized = [(int(q), int(e)) for q, e in factors]
    if not normalized or any(q <= 1 or e <= 0 for q, e in normalized):
        raise ValueError("invalid factorization")
    if math.prod(q ** e for q, e in normalized) != p - 1:
        raise ValueError("factorization does not multiply to p - 1")
    return normalized


def order_sequential(g: int, p: int, factors: list[list[int]]) -> tuple[int, list[dict]]:
    factors = validate_field_input(g, p, factors)
    order = p - 1
    trace = []
    for q, _ in factors:
        while order % q == 0:
            candidate = order // q
            if pow(g, candidate, p) != 1:
                break
            trace.append({"q": q, "from": order, "to": candidate})
            order = candidate
    return order, trace


def order_product_tree(g: int, p: int, factors: list[list[int]]) -> tuple[int, list[dict]]:
    factors = validate_field_input(g, p, factors)
    leaves = [(q, q ** e) for q, e in factors]
    trace = []

    def visit(h: int, part: list[tuple[int, int]]) -> int:
        if len(part) == 1:
            q, prime_power = part[0]
            sequence = [h]
            k = 0
            while h != 1:
                h = pow(h, q, p)
                sequence.append(h)
                k += 1
                if k > prime_power.bit_length():
                    raise ValueError("invalid group input")
            trace.append({"prime": q, "prime_power": prime_power, "exponent": k,
                          "sequence": sequence})
            return q ** k
        middle = len(part) // 2
        left, right = part[:middle], part[middle:]
        left_product = math.prod(power for _, power in left)
        right_product = math.prod(power for _, power in right)
        return (visit(pow(h, right_product, p), left)
                * visit(pow(h, left_product, p), right))

    return visit(g % p, leaves), trace


def primitive_root(p: int, factors: list[list[int]], start: int = 2) -> int:
    factors = validate_field_input(1, p, factors)
    for candidate in range(max(2, start), p):
        if math.gcd(candidate, p) != 1:
            continue
        if all(pow(candidate, (p - 1) // q, p) != 1 for q, _ in factors):
            return candidate
    raise ValueError("no primitive root in the requested range")
