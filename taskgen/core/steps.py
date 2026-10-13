"""Algorithm traces for step-by-step solutions.

Each function runs an algorithm the way it is done by hand and returns the
intermediate values as plain (JSON-able) data that solution templates render
(see ``render/templates/macros.tex.j2``).
"""

from __future__ import annotations

import math
from math import gcd

from taskgen.core.nt import factorize, inverse

# --- extended Euclid / CRT -------------------------------------------------------------


def xgcd_rows(a: int, b: int) -> list[dict]:
    """Rows r_i = u_i a + v_i b of the extended Euclidean algorithm (last row: r = 0)."""
    rows = [{"r": a, "q": None, "u": 1, "v": 0}, {"r": b, "q": None, "u": 0, "v": 1}]
    while rows[-1]["r"] != 0:
        p, c = rows[-2], rows[-1]
        q = p["r"] // c["r"]
        rows.append({"r": p["r"] - q * c["r"], "q": q, "u": p["u"] - q * c["u"],
                     "v": p["v"] - q * c["v"]})
    return rows


def inverse_rows(a: int, m: int) -> dict:
    """a^{-1} mod m via extended Euclid on (m, a)."""
    rows = xgcd_rows(m, a % m)
    g = rows[-2]
    assert g["r"] == 1, "not invertible"
    return {"a": a % m, "m": m, "rows": rows, "inv": g["v"] % m, "v": g["v"]}


def crt(residues: list[int], moduli: list[int]) -> dict:
    """x = sum r_i M_i y_i mod M with M_i = M/m_i, y_i = M_i^{-1} mod m_i."""
    M = math.prod(moduli)
    eqs = []
    for r, m in zip(residues, moduli):
        Mi = M // m
        eqs.append({"r": r, "m": m, "Mi": Mi, "Mi_mod": Mi % m, "y": inverse(Mi % m, m) if m > 1 else 0})
    x = sum(e["r"] * e["Mi"] * e["y"] for e in eqs) % M
    return {"M": M, "eqs": eqs, "x": x}


# --- exponentiation -------------------------------------------------------------------


def binary_pow_steps(a: int, e: int, m: int | None = None) -> list[dict]:
    """Left-to-right square-and-multiply; m=None for exact integers."""
    red = (lambda x: x % m) if m else (lambda x: x)
    r, ex, steps = 1, 0, []
    for bit in format(e, "b"):
        sq, ex = red(r * r), 2 * ex
        r = red(sq * a) if bit == "1" else sq
        ex += bit == "1"
        steps.append({"bit": bit, "sq": sq, "r": r, "e": ex})
    return steps


def qary_pow_steps(a: int, e: int, m: int | None = None, q_bits: int = 2) -> dict:
    """Left-to-right 2^k-ary exponentiation (k = q_bits; 4-ary by default)."""
    q = 1 << q_bits
    red = (lambda x: x % m) if m else (lambda x: x)
    table = [1]
    for _ in range(1, q):
        table.append(red(table[-1] * a))
    digits = []
    n = e
    while n:
        digits.append(n % q)
        n //= q
    digits.reverse()
    r, ex, steps = 1, 0, []
    for i, d in enumerate(digits):
        pw = r
        for _ in range(q_bits if i else 0):
            pw = red(pw * pw)
        ex = ex * q if i else 0
        r = red(pw * table[d]) if i else table[d]
        ex += d
        steps.append({"digit": d, "pow": pw, "r": r, "e": ex, "first": i == 0})
    return {"table": table, "digits": digits, "steps": steps, "result": r}


# --- Montgomery -----------------------------------------------------------------------


class Montgomery:
    """Montgomery arithmetic modulo odd m with R = 2^k, the least power of two > m."""

    def __init__(self, m: int) -> None:
        assert m % 2 == 1 and m > 1
        self.m = m
        self.k = m.bit_length()
        self.R = 1 << self.k
        self.mp = (-inverse(m, self.R)) % self.R  # m' = -m^{-1} mod R
        self.R2 = self.R * self.R % m
        self.rows: list[dict] = []

    def redc(self, T: int, label: str) -> int:
        assert 0 <= T < self.m * self.R
        u = (T % self.R) * self.mp % self.R
        t = (T + u * self.m) // self.R
        res = t - self.m if t >= self.m else t
        self.rows.append({"label": label, "T": T, "u": u, "t": t, "res": res, "sub": t >= self.m})
        return res

    def info(self) -> dict:
        return {"m": self.m, "k": self.k, "R": self.R, "mp": self.mp, "R2": self.R2,
                "rows": self.rows}


def montgomery_mul(a: int, b: int, m: int) -> dict:
    mo = Montgomery(m)
    a_r, b_r = a % m, b % m
    x = mo.redc(a_r * b_r, r"a \cdot b")
    y = mo.redc(x * mo.R2, r"x \cdot (R^2 \bmod m)")
    return {**mo.info(), "a_r": a_r, "b_r": b_r, "x": x, "result": y}


def montgomery_pow(a: int, e: int, m: int) -> dict:
    mo = Montgomery(m)
    a_r = a % m
    abar = mo.redc(a_r * mo.R2, r"\bar a = a \cdot R^2")
    xbar = abar
    bits = format(e, "b")
    for bit in bits[1:]:
        xbar = mo.redc(xbar * xbar, r"\text{бит " + bit + r"}: \bar x^2")
        if bit == "1":
            xbar = mo.redc(xbar * abar, r"\bar x \cdot \bar a")
    res = mo.redc(xbar, r"\bar x \to x")
    return {**mo.info(), "a_r": a_r, "abar": abar, "bits": bits, "result": res}


def split_even(m: int) -> tuple[int, int]:
    """m = 2^t * s with s odd."""
    t = (m & -m).bit_length() - 1
    return t, m >> t


# --- Jacobi symbol ----------------------------------------------------------------------


def jacobi_chain(a: int, n: int) -> dict:
    """Jacobi symbol (a/n) as a chain of equal terms ``[(sign, num, den), ...]``.

    Rules used: reduction a mod n; (2/n) = (-1)^{(n^2-1)/8}; reciprocity for odd
    coprime a, n with sign (-1)^{(a-1)(n-1)/4}.
    """
    assert n % 2 == 1 and n > 0
    s, terms = 1, []
    a %= n
    terms.append((s, a, n))
    while a not in (0, 1):
        while a % 2 == 0:
            a //= 2
            if n % 8 in (3, 5):
                s = -s
            terms.append((s, a, n))
        if a == 1:
            break
        if gcd(a, n) != 1:
            return {"terms": terms, "value": 0}
        if a % 4 == 3 and n % 4 == 3:
            s = -s
        terms.append((s, n, a))
        a, n = n % a, a
        terms.append((s, a, n))
    value = s if a == 1 else 0
    return {"terms": [list(t) for t in terms], "value": value}


def jacobi(a: int, n: int) -> int:
    return jacobi_chain(a, n)["value"]


# --- lattices -----------------------------------------------------------------------------


def gauss_reduce(v1: list[int], v2: list[int]) -> dict:
    """Gauss (Lagrange) reduction of a 2-dim basis, with the trace."""
    def dot(x, y):
        return x[0] * y[0] + x[1] * y[1]

    v1, v2, rows = list(v1), list(v2), []
    while True:
        swap = dot(v2, v2) < dot(v1, v1)
        if swap:
            v1, v2 = v2, v1
        mu = dot(v1, v2) / dot(v1, v1)
        m = math.floor(mu + 0.5)
        row = {"swap": swap, "v1": list(v1), "v2": list(v2), "n1": dot(v1, v1), "n2": dot(v2, v2),
               "dot": dot(v1, v2), "m": m}
        rows.append(row)
        if m == 0:
            return {"rows": rows, "v1": v1, "v2": v2}
        v2 = [v2[0] - m * v1[0], v2[1] - m * v1[1]]


def babai(v: list[list[int]], w: list[int]) -> dict:
    """Babai rounding: w = t1 v1 + t2 v2 (Cramer), r = round(t1) v1 + round(t2) v2."""
    from fractions import Fraction

    det = v[0][0] * v[1][1] - v[0][1] * v[1][0]
    t1 = Fraction(w[0] * v[1][1] - w[1] * v[1][0], det)
    t2 = Fraction(v[0][0] * w[1] - v[0][1] * w[0], det)
    c1, c2 = math.floor(t1 + Fraction(1, 2)), math.floor(t2 + Fraction(1, 2))
    r = [c1 * v[0][0] + c2 * v[1][0], c1 * v[0][1] + c2 * v[1][1]]
    return {"det": det, "t1": f"{float(t1):.3f}", "t2": f"{float(t2):.3f}",
            "t1_frac": [t1.numerator, t1.denominator], "t2_frac": [t2.numerator, t2.denominator],
            "c1": c1, "c2": c2, "r": r, "dist": f"{math.dist(r, w):.3f}"}


# --- elliptic curves -----------------------------------------------------------------------


def ec_add_step(P, Q, a: int, p: int) -> dict:
    """Affine P + Q (or 2P) with the slope; None = point at infinity."""
    if P is None or Q is None:
        return {"lam": None, "R": Q if P is None else P}
    (x1, y1), (x2, y2) = P, Q
    if x1 == x2 and (y1 + y2) % p == 0:
        return {"lam": None, "R": None}
    if (x1, y1) == (x2, y2):
        lam = (3 * x1 * x1 + a) * inverse(2 * y1 % p, p) % p
    else:
        lam = (y2 - y1) * inverse((x2 - x1) % p, p) % p
    x3 = (lam * lam - x1 - x2) % p
    return {"lam": lam, "R": [x3, (lam * (x1 - x3) - y1) % p]}


def naf(n: int) -> list[int]:
    """Non-adjacent form (digits -1, 0, 1), most significant first."""
    out = []
    while n:
        if n % 2:
            d = 2 - (n % 4)
            n -= d
        else:
            d = 0
        out.append(d)
        n //= 2
    return out[::-1]


# --- misc -------------------------------------------------------------------------------------


def primitive_root(p: int) -> int:
    fs = factorize(p - 1)
    g = 2
    while any(pow(g, (p - 1) // q, p) == 1 for q in fs):
        g += 1
    return g


def factor_tex(n: int) -> str:
    return r" \cdot ".join(f"{q}^{{{e}}}" if e > 1 else str(q) for q, e in sorted(factorize(n).items()))
