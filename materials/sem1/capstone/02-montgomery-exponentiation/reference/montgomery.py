from __future__ import annotations


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


def validate(a: int, e: int, n: int) -> None:
    if n <= 0:
        raise ValueError("modulus must be positive")
    if e < 0:
        raise ValueError("exponent must be nonnegative")


def binary_lr(a: int, e: int, n: int, stats: dict | None = None) -> int:
    validate(a, e, n)
    result = 1 % n
    base = a % n
    for bit in bin(e)[2:]:
        result = result * result % n
        if stats is not None:
            stats["squarings"] += 1
        if bit == "1":
            result = result * base % n
            if stats is not None:
                stats["multiplications"] += 1
    return result


def validate_qary(q: int) -> None:
    if q < 2 or q & (q - 1):
        raise ValueError("q must be a power of two >= 2")


def qary_digits(e: int, q: int) -> list[int]:
    if e == 0:
        return [0]
    out = []
    while e:
        out.append(e % q)
        e //= q
    return out[::-1]


def prepare_qary(a: int, n: int, q: int) -> dict:
    validate_qary(q)
    table = [1 % n]
    for _ in range(1, q):
        table.append(table[-1] * (a % n) % n)
    return {"base": a % n, "n": n, "q": q, "table": table}


def eval_qary(prepared: dict, e: int, stats: dict) -> int:
    n, q, table = prepared["n"], prepared["q"], prepared["table"]
    validate(table[1] if q > 1 else 0, e, n)
    result = 1 % n
    q_steps = q.bit_length() - 1
    for digit in qary_digits(e, q):
        for _ in range(q_steps):
            result = result * result % n
            stats["squarings"] += 1
        if digit:
            result = result * table[digit] % n
            stats["multiplications"] += 1
    return result


def prepare_sliding(a: int, n: int, width: int) -> dict:
    if not 1 <= width <= 16:
        raise ValueError("window width must be in 1..16")
    base = a % n
    table = [0] * (1 << width)
    table[0], table[1] = 1 % n, base
    square = base * base % n
    for exponent in range(3, 1 << width, 2):
        table[exponent] = table[exponent - 2] * square % n
    return {"base": base, "n": n, "width": width, "table": table}


def eval_sliding(prepared: dict, e: int, stats: dict) -> int:
    n, k, table = prepared["n"], prepared["width"], prepared["table"]
    validate(table[1], e, n)
    result = 1 % n
    bits = bin(e)[2:]
    i = 0
    while i < len(bits):
        if bits[i] == "0":
            result = result * result % n
            stats["squarings"] += 1
            i += 1
            continue
        last = min(i + k, len(bits))
        j = last - 1
        while bits[j] == "0":
            j -= 1
        window = int(bits[i:j + 1], 2)
        for _ in range(j - i + 1):
            result = result * result % n
            stats["squarings"] += 1
        result = result * table[window] % n
        stats["multiplications"] += 1
        i = j + 1
    return result


class Montgomery:
    def __init__(self, n: int, r_bits: int | None = None):
        if n <= 0 or n % 2 == 0:
            raise ValueError("Montgomery modulus must be positive and odd")
        self.n = n
        self.r_bits = r_bits or max(1, n.bit_length())
        self.r = 1 << self.r_bits
        if self.r <= n:
            raise ValueError("R must exceed n")
        g, _, inv_n = xgcd(self.r, n)
        if g != 1:
            raise ValueError("R and n must be coprime")
        self.n_prime = (-inv_n) % self.r
        self.one = self.to_montgomery(1)
        self.redc_count = 0

    def to_montgomery(self, a: int) -> int:
        return a * self.r % self.n

    def redc(self, t: int) -> int:
        m = (t % self.r) * self.n_prime % self.r
        u = (t + m * self.n) // self.r
        if u >= self.n:
            u -= self.n
        self.redc_count += 1
        return u

    def from_montgomery(self, a: int) -> int:
        return self.redc(a)

    def mul(self, a: int, b: int) -> int:
        return self.redc(a * b)

    def pow(self, a: int, e: int, stats: dict) -> int:
        validate(a, e, self.n)
        result = self.one
        base = self.to_montgomery(a)
        for bit in bin(e)[2:]:
            result = self.mul(result, result)
            stats["squarings"] += 1
            if bit == "1":
                result = self.mul(result, base)
                stats["multiplications"] += 1
        value = self.from_montgomery(result)
        stats["redc"] = self.redc_count
        return value


def prepare(a: int, n: int, method: str, parameter: int | None = None) -> dict:
    if n <= 0:
        raise ValueError("modulus must be positive")
    if method == "binary":
        return {"base": a % n, "n": n}
    if method == "qary":
        return prepare_qary(a, n, 4 if parameter is None else parameter)
    if method == "sliding":
        return prepare_sliding(a, n, 4 if parameter is None else parameter)
    if method == "montgomery":
        return {"context": Montgomery(n), "base": a % n, "n": n}
    raise ValueError(f"unknown exponentiation method {method!r}")


def evaluate(prepared: dict, a: int, e: int, n: int, method: str) -> tuple[int, dict]:
    stats = {"squarings": 0, "multiplications": 0}
    if prepared["base"] != a % n or prepared["n"] != n:
        raise ValueError("stale precomputation")
    if method == "binary":
        return binary_lr(a, e, n, stats), stats
    if method == "qary":
        return eval_qary(prepared, e, stats), stats
    if method == "sliding":
        return eval_sliding(prepared, e, stats), stats
    if method == "montgomery":
        return prepared["context"].pow(a, e, stats), stats
    raise ValueError(f"unknown exponentiation method {method!r}")
