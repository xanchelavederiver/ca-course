from __future__ import annotations

DIGIT_BITS = 30
BASE = 1 << DIGIT_BITS
MASK = BASE - 1
FFT_DIGIT_BITS = 16
FFT_BASE = 1 << FFT_DIGIT_BITS


def digits(a: int, bits: int = DIGIT_BITS) -> list[int]:
    base = 1 << bits
    mask = base - 1
    out = []
    while a:
        out.append(a & mask)
        a >>= bits
    return out


def from_digits(ds: list[int], bits: int = DIGIT_BITS) -> int:
    out = 0
    for d in reversed(ds):
        out = (out << bits) | d
    return out


def schoolbook_positive(a: int, b: int) -> int:
    x, y = digits(a), digits(b)
    if not x or not y:
        return 0
    out = [0] * (len(x) + len(y) + 1)
    for i, xi in enumerate(x):
        carry = 0
        for j, yj in enumerate(y):
            cur = out[i + j] + xi * yj + carry
            out[i + j] = cur & MASK
            carry = cur >> DIGIT_BITS
        k = i + len(y)
        while carry:
            cur = out[k] + carry
            out[k] = cur & MASK
            carry = cur >> DIGIT_BITS
            k += 1
    return from_digits(out)


def schoolbook(a: int, b: int) -> int:
    sign = -1 if (a < 0) != (b < 0) else 1
    return sign * schoolbook_positive(abs(a), abs(b))


def karatsuba_positive(a: int, b: int) -> int:
    if max(a.bit_length(), b.bit_length()) <= 64:
        return a * b
    m = max(a.bit_length(), b.bit_length()) // 2
    mask = (1 << m) - 1
    a0, a1 = a & mask, a >> m
    b0, b1 = b & mask, b >> m
    z0 = karatsuba_positive(a0, b0)
    z2 = karatsuba_positive(a1, b1)
    z1 = karatsuba_positive(a0 + a1, b0 + b1) - z0 - z2
    return z0 + (z1 << m) + (z2 << (2 * m))


def karatsuba(a: int, b: int) -> int:
    sign = -1 if (a < 0) != (b < 0) else 1
    return sign * karatsuba_positive(abs(a), abs(b))


def toom3_positive(a: int, b: int) -> int:
    if max(a.bit_length(), b.bit_length()) <= 96:
        return schoolbook_positive(a, b)
    k = (max(a.bit_length(), b.bit_length()) + 2) // 3
    mask = (1 << k) - 1
    a0, a1, a2 = a & mask, (a >> k) & mask, a >> (2 * k)
    b0, b1, b2 = b & mask, (b >> k) & mask, b >> (2 * k)

    def evaluate(x0: int, x1: int, x2: int, point: int) -> int:
        return x0 + point * x1 + point * point * x2

    v0 = toom3_positive(a0, b0)
    v1 = toom3(evaluate(a0, a1, a2, 1), evaluate(b0, b1, b2, 1))
    vm1 = toom3(evaluate(a0, a1, a2, -1), evaluate(b0, b1, b2, -1))
    vm2 = toom3(evaluate(a0, a1, a2, -2), evaluate(b0, b1, b2, -2))
    vinf = toom3_positive(a2, b2)

    r0 = v0
    r4 = vinf
    r3 = (vm2 - v1) // 3
    r1 = (v1 - vm1) // 2
    r2 = vm1 - v0
    r3 = (r2 - r3) // 2 + 2 * r4
    r2 = r2 + r1 - r4
    r1 = r1 - r3
    return r0 + (r1 << k) + (r2 << (2 * k)) + (r3 << (3 * k)) + (r4 << (4 * k))


def toom3(a: int, b: int) -> int:
    sign = -1 if (a < 0) != (b < 0) else 1
    return sign * toom3_positive(abs(a), abs(b))


def next_power_of_two(n: int) -> int:
    if n < 1:
        raise ValueError("transform length must be positive")
    return 1 << (n - 1).bit_length()


def select_finite_field(length: int, coefficient_bound: int) -> tuple[int, int, int]:
    from sage.all import is_prime

    n = next_power_of_two(length)
    if coefficient_bound < 1:
        raise ValueError("coefficient bound must be positive")
    k = max(1, coefficient_bound // n)
    while True:
        p = k * n + 1
        if p > coefficient_bound and is_prime(p):
            break
        k += 1
    if n == 1:
        return n, p, 1
    h = 2
    while True:
        omega = pow(h, k, p)
        if pow(omega, n // 2, p) != 1:
            return n, p, omega
        h += 1


def fft(values: list[int], p: int, omega: int) -> list[int]:
    n = len(values)
    if n < 1 or n & (n - 1) or pow(omega, n, p) != 1:
        raise ValueError("invalid FFT length or root")
    if n > 1 and pow(omega, n // 2, p) == 1:
        raise ValueError("root does not have exact order n")
    a = [x % p for x in values]
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        wlen = pow(omega, n // length, p)
        for start in range(0, n, length):
            w = 1
            half = length // 2
            for i in range(start, start + half):
                u = a[i]
                v = a[i + half] * w % p
                a[i] = (u + v) % p
                a[i + half] = (u - v) % p
                w = w * wlen % p
        length <<= 1
    return a


def finite_field_convolution(x: list[int], y: list[int], cyclic: bool = False,
                             coefficient_bound: int | None = None) -> tuple[list[int], dict]:
    if not x or not y:
        raise ValueError("convolution inputs must be nonempty")
    length = max(len(x), len(y)) if cyclic else len(x) + len(y) - 1
    peak = max(max(x), max(y))
    bound = coefficient_bound or next_power_of_two(length) * peak * peak
    n, p, omega = select_finite_field(length, bound)
    a = fft(x + [0] * (n - len(x)), p, omega)
    b = fft(y + [0] * (n - len(y)), p, omega)
    omega_inv = pow(omega, -1, p)
    n_inv = pow(n, -1, p)
    c = fft([u * v % p for u, v in zip(a, b)], p, omega_inv)
    c = [v * n_inv % p for v in c]
    out_len = n if cyclic else length
    return c[:out_len], {"n": n, "p": p, "omega": omega, "coefficient_bound": bound}


def fft_positive_with_info(a: int, b: int) -> tuple[int, dict]:
    if not a or not b:
        return 0, {}
    x, y = digits(a, FFT_DIGIT_BITS), digits(b, FFT_DIGIT_BITS)
    length = len(x) + len(y) - 1
    bound = next_power_of_two(length) * (FFT_BASE - 1) ** 2
    c, info = finite_field_convolution(x, y, coefficient_bound=bound)
    product = sum(coefficient << (FFT_DIGIT_BITS * i) for i, coefficient in enumerate(c))
    return product, info


def fft_multiply(a: int, b: int) -> int:
    sign = -1 if (a < 0) != (b < 0) else 1
    return sign * fft_positive_with_info(abs(a), abs(b))[0]


METHODS = {
    "schoolbook": schoolbook,
    "karatsuba": karatsuba,
    "toom3": toom3,
    "fft": fft_multiply,
}


def multiply(a: int, b: int, method: str) -> tuple[int, dict]:
    if method not in METHODS:
        raise ValueError(f"unknown multiplication method {method!r}")
    extra = {}
    if method == "fft":
        sign = -1 if (a < 0) != (b < 0) else 1
        product, extra["fft"] = fft_positive_with_info(abs(a), abs(b))
        return sign * product, extra
    return METHODS[method](a, b), extra
