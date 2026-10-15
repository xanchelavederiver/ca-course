"""Capstone 01 (bigint-arithmetic): vectors for the operations of a bigint library.

One vector = one operation (``input.op``) on hex-string operands (``"-0x1f"``):

    add, sub, mul_school, mul_karatsuba, sqr        -> c
    divmod -> q, r     mod -> r     gcd -> g     xgcd -> g, x, y     inv -> inv | null
    shl, shr (k)                                    -> c
    mont_redc (t, m) -> c, r_bits     mont_mul (a, b, m) -> c = a b mod m
    pow_binary, pow_qary (q)  (a, e)                -> c = a^e
    powmod_binary, powmod_qary (q)  (a, e, m)       -> c = a^e mod m

``input.repeat`` = R asks the solver to repeat the operation R times (per-op time =
wall / R); R comes from a cost model of the reference so that one request takes about
``target_ms`` (default 30 ms).

params::

    bits: 2048          operand size (divmod/mod: dividend 2 bits, divisor bits)
    ops: [..]           the operations to draw from (default: all, uniformly)
    corner: 0.3         probability of a corner case instead of random operands
    exp_bits: 2048      exponent size of powmod (default: bits)
    target_ms: 30       wall time per request the repeat count aims at

``verify`` uses the standard library only (it runs in the ``capstone-c`` image) and
accepts every correct answer: truncated, floored or Euclidean division, any Bezout
coefficients, any inverse representative, floor or truncating right shifts, any
Montgomery radix R = 2^r_bits.
"""

from __future__ import annotations

import math

VERSION = 1

LIMB = 64
B = 1 << LIMB
# Karatsuba thresholds of the reference (reference/src/limbs.h), in limbs: the
# threshold corner cases sit at T - 1, T, T + 1, 2T - 1, 2T, 2T + 1 limbs.
KARATSUBA_THRESHOLD = 24
KARATSUBA_SQR_THRESHOLD = 48

OPS = ("add", "sub", "mul_school", "mul_karatsuba", "sqr", "divmod", "mod", "gcd", "xgcd",
       "inv", "shl", "shr", "mont_redc", "mont_mul", "pow_binary", "pow_qary",
       "powmod_binary", "powmod_qary")
QS = (2, 4, 8, 16)
MAX_REPEAT = 1_000_000


def h(x: int) -> str:
    return hex(x)      # "-0x1f", "0x0"


# ----------------------------------------------------------------- random operands --

def rand_bits(rng, bits: int) -> int:
    """A random number of exactly ``bits`` bits (0 for bits <= 0)."""
    if bits <= 0:
        return 0
    return rng.getrandbits(bits) | (1 << (bits - 1))


def rand_shaped(rng, bits: int) -> int:
    """Mostly uniform; sometimes long runs of 0/1 bits (limbs 0 and B - 1, carries)."""
    if bits <= 0:
        return 0
    if rng.random() < 0.2:
        x, pos = 0, 0
        while pos < bits:
            run = rng.randrange(1, 2 * LIMB)
            if rng.random() < 0.5:
                x |= ((1 << min(run, bits - pos)) - 1) << pos
            pos += run
        return x | (1 << (bits - 1))
    return rand_bits(rng, bits)


def signed(rng, x: int) -> int:
    return -x if rng.random() < 0.5 else x


def rand_odd(rng, bits: int) -> int:
    return rand_bits(rng, bits) | 1


# ----------------------------------------------------------------- Algorithm D model --

def _limbs(x: int, n: int | None = None) -> list[int]:
    out = []
    while x:
        out.append(x & (B - 1))
        x >>= LIMB
    if n is not None:
        out += [0] * (n - len(out))
    return out


def knuth_d_stats(a: int, b: int) -> tuple[int, int]:
    """(add-backs, qhat = B-1 starts) of Algorithm D on |a| / |b| with 64-bit limbs,
    exactly as the reference runs it (used to tag and to check the D6 corner cases)."""
    a, b = abs(a), abs(b)
    if b == 0 or a < b or b < B:
        return 0, 0
    n = (b.bit_length() + LIMB - 1) // LIMB
    s = LIMB * n - b.bit_length()
    v = _limbs(b << s, n)
    m = (a.bit_length() + LIMB - 1) // LIMB - n
    u = _limbs(a << s, m + n + 1)
    addbacks = qmax = 0
    for j in range(m, -1, -1):
        top = u[j + n] * B + u[j + n - 1]
        if u[j + n] >= v[-1]:
            qhat, rhat = B - 1, top - (B - 1) * v[-1]
            qmax += 1
        else:
            qhat, rhat = divmod(top, v[-1])
        while rhat < B and qhat * v[-2] > rhat * B + u[j + n - 2]:
            qhat -= 1
            rhat += v[-1]
        win = sum(u[j + i] << (LIMB * i) for i in range(n + 1))
        bv = sum(v[i] << (LIMB * i) for i in range(n))
        rest = win - qhat * bv
        if rest < 0:
            addbacks += 1
            rest += bv
        for i, limb in enumerate(_limbs(rest, n + 1)):
            u[j + i] = limb
    return addbacks, qmax


def addback_pair(rng, nlimbs: int, qlimbs: int) -> tuple[int, int]:
    """(a, b) with b of nlimbs >= 3 normalized limbs for which the last quotient limb
    estimate of Algorithm D passes the two-limb test of D3 but is one too large (D6).

    v = T B^(n-2) + L (T = the top two limbs, 0 < L); the window u = qd T B^(n-2) + R
    with R < qd L gives qhat = qd while u - qd v = R - qd L < 0. Higher quotient limbs
    X are prepended as a = X v B + u (the window of the last step is then u).
    """
    top = rand_bits(rng, LIMB)                    # top bit set: no normalization shift
    T = top * B + rng.getrandbits(LIMB)
    L = rng.getrandbits(LIMB * (nlimbs - 2)) | 1
    v = T * B ** (nlimbs - 2) + L
    qd = rng.randrange(2, B)
    R = rng.randrange(0, min(qd * L, B ** (nlimbs - 2)))
    u = qd * T * B ** (nlimbs - 2) + R
    X = rand_bits(rng, LIMB * qlimbs) if qlimbs > 0 else 0
    return X * v * B + u, v


def qhat_max_pair(rng, nlimbs: int, qlimbs: int) -> tuple[int, int]:
    """(a, b) whose last Algorithm D step starts with u_n == v_(n-1) (qhat = B - 1)."""
    v = rand_bits(rng, LIMB * nlimbs)
    low = v - (v >> (LIMB * (nlimbs - 1)) << (LIMB * (nlimbs - 1)))   # v without its top limb
    u = (v >> (LIMB * (nlimbs - 1))) * B ** nlimbs + rng.randrange(0, max(1, low * B))
    X = rand_bits(rng, LIMB * qlimbs) if qlimbs > 0 else 0
    return X * v * B + u, v


# ----------------------------------------------------------------- cost model --------
# Per-operation time of the reference (us) on the reference machine, fitted to
# `build/bigint-tune`; only used to choose `repeat` (a 3x error is harmless).

def _n(x: int) -> int:
    return max(1, (abs(x).bit_length() + LIMB - 1) // LIMB)


def _school(n1: int, n2: int) -> float:
    return 0.02 + 0.0011 * n1 * n2


def _kara(n1: int, n2: int, t: int = KARATSUBA_THRESHOLD) -> float:
    lo = min(n1, n2)
    return _school(n1, n2) * (1.0 if lo < t else (lo / t) ** -0.33)


def _sqr(n: int) -> float:
    return 0.65 * _school(n, n) * (1.0 if n < KARATSUBA_SQR_THRESHOLD
                                   else (n / KARATSUBA_SQR_THRESHOLD) ** -0.33)


def _mont(n: int, square: bool = False) -> float:
    return (_sqr(n) if square else _kara(n, n)) + 0.0012 * n * n + 0.05


def _gcd(a: int, b: int) -> float:
    bits = max(abs(a).bit_length(), abs(b).bit_length(), 64)
    return 0.6 * bits * (0.065 + 0.002 * bits / LIMB)


def cost_us(inp: dict) -> float:
    """Estimated time of one operation of ``inp`` (int operands)."""
    op = inp["op"]
    g = lambda k: inp.get(k, 0)  # noqa: E731
    na, nb = _n(g("a")), _n(g("b"))
    if op in ("add", "sub"):
        return 0.02 + 0.0011 * max(na, nb)
    if op in ("shl", "shr"):
        return 0.03 + 0.0015 * (na + g("k") // LIMB)
    if op == "mul_school":
        return _school(na, nb)
    if op == "mul_karatsuba":
        return _kara(na, nb, inp.get("threshold", KARATSUBA_THRESHOLD)) * (
            1.0 if inp.get("threshold", KARATSUBA_THRESHOLD) >= 8 else 3.0)
    if op == "sqr":
        return _sqr(na)
    if op in ("divmod", "mod"):
        qn = max(1, na - nb + 1)
        return 0.1 + 0.0015 * qn * nb + 0.002 * na
    if op == "gcd":
        return _gcd(g("a"), g("b"))
    if op in ("xgcd", "inv"):
        return 2.3 * _gcd(g("a"), g("m") if op == "inv" else g("b"))
    nm = _n(g("m"))
    if op == "mont_redc":
        return 0.3 + 0.0012 * nm * nm
    if op == "mont_mul":
        return _mont(nm)
    eb = max(1, abs(g("e")).bit_length())
    k = int(math.log2(inp.get("q", 2)))
    mults = eb / 2 if k == 1 else eb / k + 2 ** k
    if op.startswith("powmod"):
        return 1.0 + eb * _mont(nm, square=True) + mults * _mont(nm)
    # plain power: the last squarings dominate (geometric series)
    abits = abs(g("a")).bit_length()
    rn = 1 if abits <= 1 else max(1, abits * g("e") // LIMB)
    return 0.5 + 2.0 * _sqr(rn) + mults * _kara(rn, na)


def repeat_for(inp: dict, target_ms: float) -> int:
    return max(1, min(MAX_REPEAT, round(target_ms * 1000.0 / cost_us(inp))))


# ----------------------------------------------------------------- instances ---------

def _two(rng, bits):
    return signed(rng, rand_shaped(rng, bits)), signed(rng, rand_shaped(rng, bits))


def _gen_addsub(rng, bits, corner):
    a, b = _two(rng, bits)
    if corner:
        kind = rng.choice(["zero", "one", "opposite", "equal", "lengths", "carry"])
        if kind == "zero":
            a, b = (0, b) if rng.random() < 0.5 else (a, 0)
        elif kind == "one":
            b = rng.choice([1, -1])
        elif kind == "opposite":
            b = -a
        elif kind == "equal":
            b = a
        elif kind == "lengths":
            b = signed(rng, rand_shaped(rng, rng.choice([1, 64, 65, bits // 4])))
        else:   # 2^bits - 1 + 1 and 2^bits - 1: a carry / borrow through every limb
            a, b = rng.choice([((1 << bits) - 1, 1), (1 << bits, -1), (-(1 << bits), 1)])
        return {"a": a, "b": b}, [kind]
    return {"a": a, "b": b}, []


def _gen_mul(rng, bits, corner, op):
    a, b = _two(rng, bits)
    inp: dict = {}
    if corner:
        kinds = ["zero", "one", "lengths", "ones"]
        if op != "mul_school":
            kinds += ["threshold"] * 3
        if op == "mul_karatsuba":
            kinds += ["small-threshold"]
        kind = rng.choice(kinds)
        if kind == "zero":
            a = 0
        elif kind == "one":
            b = rng.choice([1, -1])
        elif kind == "lengths":
            b = signed(rng, rand_shaped(rng, rng.choice([64, 65, 130, max(66, bits // 3)])))
        elif kind == "ones":
            a, b = (1 << bits) - 1, -((1 << bits) - 1)
        elif kind == "threshold":
            t = KARATSUBA_SQR_THRESHOLD if op == "sqr" else KARATSUBA_THRESHOLD
            na = rng.choice([t - 1, t, t + 1, 2 * t - 1, 2 * t, 2 * t + 1])
            nb = rng.choice([na, na, t - 1, t, 2 * t + 1])
            a = signed(rng, rand_shaped(rng, LIMB * na))
            b = signed(rng, rand_shaped(rng, LIMB * nb))
            kind = f"threshold-{na}x{nb}"
        else:   # Karatsuba down to a few limbs: deep recursion, odd splits
            inp["threshold"] = rng.choice([2, 3, 4, 5])
        tags = [kind.split("-")[0] if kind.startswith("threshold") else kind]
    else:
        tags = []
    inp.update({"a": a} if op == "sqr" else {"a": a, "b": b})
    return inp, tags


def _gen_div(rng, bits, corner, op):
    a = signed(rng, rand_shaped(rng, 2 * bits))
    b = signed(rng, rand_shaped(rng, bits))
    tags = []
    if corner:
        kind = rng.choice(["addback", "addback", "qhat-max", "small-a", "zero", "unit",
                           "exact", "equal", "one-limb", "lengths"])
        nl = max(3, bits // LIMB)
        if kind == "addback":
            a, b = addback_pair(rng, nl, rng.choice([0, 1, nl]))
        elif kind == "qhat-max":
            a, b = qhat_max_pair(rng, nl, rng.choice([0, 1, nl]))
        elif kind == "small-a":
            a = signed(rng, rand_shaped(rng, bits // 2))
        elif kind == "zero":
            a = 0
        elif kind == "unit":
            b = rng.choice([1, -1])
        elif kind == "exact":
            a = b * signed(rng, rand_shaped(rng, bits))
        elif kind == "equal":
            a = rng.choice([b, -b])
        elif kind == "one-limb":
            b = rand_bits(rng, rng.randrange(1, LIMB + 1))
        else:
            b = rand_shaped(rng, rng.choice([65, 128, 129, bits + 64]))
        a, b = signed(rng, a), signed(rng, b)
        tags.append(kind)
        ab, qm = knuth_d_stats(a, b)
        if ab:
            tags.append("knuth-d-addback")
        if qm:
            tags.append("knuth-d-qhat-max")
    return {"a": a, "b": b}, tags


def _fib_pair(bits):
    x, y = 1, 1
    while y.bit_length() < bits:
        x, y = y, x + y
    return y, x


def _gen_gcd(rng, bits, corner, op):
    a, b = _two(rng, bits)
    tags = []
    if op == "inv":
        m = rand_shaped(rng, bits)
        if corner:
            kind = rng.choice(["not-invertible", "zero", "m-one", "big-a", "odd-m", "fib"])
            if kind == "not-invertible":
                g = rand_bits(rng, rng.choice([2, 64, bits // 2]))
                a, m = signed(rng, g * rand_bits(rng, bits // 2)), g * rand_bits(rng, bits // 2)
            elif kind == "zero":
                a = rng.choice([0, m, -m])
            elif kind == "m-one":
                m = 1
            elif kind == "big-a":
                a = signed(rng, rand_bits(rng, 2 * bits))
            elif kind == "odd-m":
                m |= 1
            else:
                a, m = _fib_pair(bits)
            tags.append(kind)
        return {"a": a, "m": max(1, m)}, tags
    if corner:
        kind = rng.choice(["zero", "both-zero", "equal", "divides", "common-factor", "fib", "one",
                           "lengths"])
        if kind == "zero":
            b = 0
        elif kind == "both-zero":
            a = b = 0
        elif kind == "equal":
            b = rng.choice([a, -a])
        elif kind == "divides":
            b = a * signed(rng, rand_bits(rng, bits // 2))
        elif kind == "common-factor":
            g = rand_bits(rng, bits // 2)
            a = signed(rng, g * rand_bits(rng, bits // 2))
            b = signed(rng, g * rand_bits(rng, bits // 2))
        elif kind == "fib":     # consecutive Fibonacci numbers: the most Euclid steps
            a, b = _fib_pair(bits)
        elif kind == "one":
            b = rng.choice([1, -1])
        else:
            b = signed(rng, rand_bits(rng, rng.choice([64, 65, bits // 4])))
        tags.append(kind)
    return {"a": a, "b": b}, tags


def _gen_shift(rng, bits, corner, op):
    a = signed(rng, rand_shaped(rng, bits))
    k = rng.randrange(1, bits)
    tags = []
    if corner:
        kind = rng.choice(["k0", "limb-edges", "beyond", "zero", "minus-one", "exact"])
        if kind == "k0":
            k = 0
        elif kind == "limb-edges":
            k = rng.choice([1, 63, 64, 65, 127, 128, 129])
        elif kind == "beyond":
            k = bits + rng.choice([0, 1, 64, 1000])
        elif kind == "zero":
            a = 0
        elif kind == "minus-one":
            a = -1
        else:   # a negative multiple of 2^k: floor and truncation agree
            a = -(rand_bits(rng, bits - k) << k) if k < bits else -(1 << k)
        tags.append(kind)
    return {"a": a, "k": k}, tags


def _gen_mont(rng, bits, corner, op):
    m = rand_odd(rng, bits)
    tags = []
    if op == "mont_redc":
        t = rng.randrange(0, m * m)
        if corner:
            kind = rng.choice(["zero", "one", "max", "small-m", "m-one", "special-m", "t-multiple"])
            if kind == "zero":
                t = 0
            elif kind == "one":
                t = 1
            elif kind == "max":
                t = m * m - 1
            elif kind == "small-m":
                m = rand_odd(rng, rng.choice([2, 33, 64]))
                t = rng.randrange(0, m * m)
            elif kind == "m-one":
                m, t = 1, 0
            elif kind == "special-m":
                m = rng.choice([(1 << bits) - 1, (1 << (bits - 1)) + 1])
                t = rng.randrange(0, m * m)
            else:
                t = m * rng.randrange(0, m)
            tags.append(kind)
        return {"t": t, "m": m}, tags
    a, b = rng.randrange(0, m), rng.randrange(0, m)
    if corner:
        kind = rng.choice(["a-zero-mod-m", "minus-one", "unreduced", "small-m", "special-m"])
        if kind == "a-zero-mod-m":
            a = rng.choice([0, m, -m, 3 * m])
        elif kind == "minus-one":
            a = b = m - 1
        elif kind == "unreduced":
            a, b = signed(rng, rand_bits(rng, 2 * bits)), -b
        elif kind == "small-m":
            m = rand_odd(rng, rng.choice([2, 33, 64]))
            a, b = rng.randrange(0, m), rng.randrange(0, m)
        else:
            m = rng.choice([(1 << bits) - 1, (1 << (bits - 1)) + 1])
            a, b = rng.randrange(0, m), rng.randrange(0, m)
        tags.append(kind)
    return {"a": a, "b": b, "m": m}, tags


def _gen_pow(rng, bits, corner, op, exp_bits):
    qary = op.endswith("qary")
    inp: dict = {}
    tags = []
    if op.startswith("powmod"):
        m = rand_odd(rng, bits)
        a = rng.randrange(0, m)
        e = rand_bits(rng, exp_bits)
        if corner:
            kind = rng.choice(["e0", "e1", "e2", "a-zero-mod-m", "a-one", "minus-one", "negative-a",
                               "unreduced", "even-m", "even-m", "power-of-two-m", "m-one",
                               "small-m"])
            if kind in ("e0", "e1", "e2"):
                e = int(kind[1])
            elif kind == "a-zero-mod-m":
                a = rng.choice([0, m, -2 * m])
            elif kind == "a-one":
                a = 1
            elif kind == "minus-one":
                a = rng.choice([m - 1, -1])
            elif kind == "negative-a":
                a = -rand_bits(rng, bits)
            elif kind == "unreduced":
                a = rand_bits(rng, 2 * bits)
            elif kind == "even-m":
                m = rand_bits(rng, bits) & ~1
                a = rng.randrange(0, m)
            elif kind == "power-of-two-m":
                m = 1 << (bits - 1)
                a = rand_bits(rng, bits)
            elif kind == "m-one":
                m = 1
            else:
                m = rand_odd(rng, rng.choice([2, 64]))
            tags.append(kind)
        inp = {"a": a, "e": e, "m": m}
    else:
        # plain power: the result has about `bits` bits
        e = rng.randrange(2, 65)
        a = signed(rng, rand_shaped(rng, max(2, bits // e)))
        if corner:
            kind = rng.choice(["e0", "e1", "a-zero", "a-one", "minus-one", "zero-zero", "full-a"])
            if kind in ("e0", "e1"):
                e = int(kind[1])
            elif kind == "a-zero":
                a = 0
            elif kind == "a-one":
                a = 1
            elif kind == "minus-one":
                a = -1
                e = rng.randrange(0, 1 << 40)
            elif kind == "zero-zero":
                a, e = 0, 0
            else:
                a, e = signed(rng, rand_bits(rng, bits)), rng.randrange(2, 9)
            tags.append(kind)
        inp = {"a": a, "e": e}
    if qary:
        inp["q"] = rng.choice(QS)
    return inp, tags


def _powmod(a: int, e: int, m: int) -> int:
    try:
        import gmpy2  # GMP: much faster than pow() for 16384-bit operands
        return int(gmpy2.powmod(a, e, m))
    except ImportError:
        return pow(a, e, m)


def expected(inp: dict) -> dict:
    """The answer (in ints) of a request with int operands; one valid answer for the
    operations whose answer is not unique."""
    op = inp["op"]
    a, b = inp.get("a"), inp.get("b")
    if op == "add":
        return {"c": a + b}
    if op == "sub":
        return {"c": a - b}
    if op in ("mul_school", "mul_karatsuba"):
        return {"c": a * b}
    if op == "sqr":
        return {"c": a * a}
    if op == "divmod":
        q = abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)   # truncated
        return {"q": q, "r": a - q * b}
    if op == "mod":
        return {"r": a % abs(b)}
    if op == "gcd":
        return {"g": math.gcd(a, b)}
    if op == "xgcd":
        g, x, y = _xgcd(a, b)
        return {"g": g, "x": x, "y": y}
    if op == "inv":
        m = inp["m"]
        return {"inv": pow(a, -1, m) if math.gcd(a, m) == 1 else None}
    if op == "shl":
        return {"c": a << inp["k"]}
    if op == "shr":
        return {"c": a >> inp["k"]}
    m = inp.get("m")
    if op == "mont_redc":
        rb = LIMB * _n(m)
        return {"c": inp["t"] * pow(2, -rb, m) % m if m > 1 else 0, "r_bits": rb}
    if op == "mont_mul":
        return {"c": a * b % m}
    if op.startswith("powmod"):
        return {"c": _powmod(a, inp["e"], m)}
    return {"c": a ** inp["e"]}


def _xgcd(a: int, b: int) -> tuple[int, int, int]:
    r0, r1, s0, s1, t0, t1 = abs(a), abs(b), 1, 0, 0, 1
    while r1:
        q = r0 // r1
        r0, r1 = r1, r0 - q * r1
        s0, s1 = s1, s0 - q * s1
        t0, t1 = t1, t0 - q * t1
    return r0, s0 * (-1 if a < 0 else 1), t0 * (-1 if b < 0 else 1)


SMALL_INPUTS = ("k", "q", "repeat", "threshold")   # JSON numbers; every other int is hex


def _encode(d: dict, small: tuple = ()) -> dict:
    return {k: h(v) if isinstance(v, int) and k not in small else v for k, v in d.items()}


def generate(params: dict, rng) -> dict:
    bits = int(params["bits"])
    ops = list(params.get("ops") or OPS)
    op = rng.choice(ops)
    corner = rng.random() < float(params.get("corner", 0.3))
    exp_bits = int(params.get("exp_bits", bits))
    if op in ("add", "sub"):
        inp, tags = _gen_addsub(rng, bits, corner)
    elif op in ("mul_school", "mul_karatsuba", "sqr"):
        inp, tags = _gen_mul(rng, bits, corner, op)
    elif op in ("divmod", "mod"):
        inp, tags = _gen_div(rng, bits, corner, op)
    elif op in ("gcd", "xgcd", "inv"):
        inp, tags = _gen_gcd(rng, bits, corner, op)
    elif op in ("shl", "shr"):
        inp, tags = _gen_shift(rng, bits, corner, op)
    elif op in ("mont_redc", "mont_mul"):
        inp, tags = _gen_mont(rng, bits, corner, op)
    else:
        inp, tags = _gen_pow(rng, bits, corner, op, exp_bits)
    inp = {"op": op, **inp}
    inp["repeat"] = repeat_for(inp, float(params.get("target_ms", 30)))
    tags = [op] + (["corner"] if corner else []) + tags
    if any(isinstance(inp.get(k), int) and inp[k] < 0 for k in ("a", "b", "t")):
        tags.append("negative")
    return {"input": _encode(inp, SMALL_INPUTS), "expected": _encode(expected(inp), ("r_bits",)),
            "tags": sorted(set(tags))}


# ----------------------------------------------------------------- verify ------------

def _int(x, what: str) -> int:
    if isinstance(x, bool) or x is None:
        raise ValueError(f"{what}: missing or not a number ({x!r})")
    if isinstance(x, int):
        return x
    if isinstance(x, str):
        s = x.strip()
        neg = s.startswith("-")
        body = s[1:] if s[:1] in "+-" else s
        if body[:2].lower() == "0x":
            body = body[2:]
        if not body or any(c not in "0123456789abcdefABCDEF" for c in body):
            raise ValueError(f"{what}: not a hex number ({x[:40]!r})")
        v = int(body, 16)
        return -v if neg else v
    raise ValueError(f"{what}: expected a hex string, got {type(x).__name__}")


def verify(vector: dict, output: dict) -> str | None:
    inp = vector["input"]
    op = inp["op"]
    out = output if isinstance(output, dict) else {}
    try:
        val = {k: _int(v, k) if k not in SMALL_INPUTS else v
               for k, v in inp.items() if k != "op"}
        a, b, m = val.get("a"), val.get("b"), val.get("m")
        get = lambda k: _int(out.get(k), k)  # noqa: E731
        if op in ("add", "sub", "mul_school", "mul_karatsuba", "sqr"):
            want = {"add": lambda: a + b, "sub": lambda: a - b, "sqr": lambda: a * a}.get(
                op, lambda: a * b)()
            return None if get("c") == want else f"c != {op}(a, b)"
        if op == "divmod":
            q, r = get("q"), get("r")
            if q * b + r != a:
                return "q b + r != a"
            return None if abs(r) < abs(b) else "|r| >= |b|"
        if op == "mod":
            r = get("r")
            if (a - r) % b:
                return "r is not congruent to a mod b"
            return None if abs(r) < abs(b) else "|r| >= |b|"
        if op == "gcd":
            return None if get("g") == math.gcd(a, b) else "wrong gcd"
        if op == "xgcd":
            g, x, y = get("g"), get("x"), get("y")
            if g != math.gcd(a, b):
                return "wrong gcd"
            return None if a * x + b * y == g else "a x + b y != g"
        if op == "inv":
            inv = out.get("inv", "missing")
            if math.gcd(a, m) != 1:
                return None if inv is None else "a is not invertible mod m: expected null"
            if inv is None or inv == "missing":
                return "a is invertible mod m, got no inverse"
            return None if (a * _int(inv, "inv") - 1) % m == 0 else "a inv != 1 mod m"
        if op == "shl":
            return None if get("c") == a << inp["k"] else "c != a 2^k"
        if op == "shr":
            k, c = inp["k"], get("c")
            trunc = -((-a) >> k) if a < 0 else a >> k
            return None if c in (a >> k, trunc) else "c != floor(a / 2^k) (nor trunc)"
        if op == "mont_redc":
            c, rb, t = get("c"), out.get("r_bits"), val["t"]
            if not isinstance(rb, int) or isinstance(rb, bool) or rb < 0 or (1 << rb) <= m:
                return f"r_bits {rb!r}: need an integer with 2^r_bits > m"
            if not 0 <= c < m and m > 1:
                return "c not in [0, m)"
            return None if (c * pow(2, rb, m) - t) % m == 0 else "c 2^r_bits != t mod m"
        if op == "mont_mul":
            c = get("c")
            return None if 0 <= c < max(m, 1) and (c - a * b) % m == 0 else "c != a b mod m"
        if op.startswith("powmod") or op.startswith("pow_"):
            want = _int(vector["expected"]["c"], "expected c")
            return None if get("c") == want else f"c != a^e{' mod m' if m else ''}"
        return f"unknown op {op!r}"
    except (ValueError, TypeError, ZeroDivisionError) as e:
        return str(e)
