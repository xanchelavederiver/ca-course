"""Elliptic curves modulo a composite n, by hand.

Two models:

* **Weierstrass, affine** (Lenstra's original method): ``y^2 = x^3 + a x + b`` over Z/nZ.
  Points are ``(x, y)`` tuples, ``None`` is the point at infinity. Every addition
  inverts an element of Z/nZ; if the inversion fails, :class:`~lenstra.arith.NotInvertible`
  carries ``gcd(., n)`` up to the caller, and that gcd is the factor.
* **Montgomery, projective x-only** (Crandall--Pomerance, sec. 7.4.2, alg. 7.4.4):
  ``B y^2 = x^3 + A x^2 + x``, points as ``(X : Z)`` without ``y``. No inversions at all;
  the factor is ``gcd(Z, n)`` at the end. Only ``a24 = (A + 2) / 4`` enters the formulas.

Curve generators, all driven by the caller's seeded ``random.Random``:

* :func:`random_weierstrass` --- pick ``a, x0, y0`` at random and put
  ``b = y0^2 - x0^3 - a x0`` (answer to the spec's footnote "как это сделать?": choose the
  point first, then the curve through it; no square roots modulo n needed);
* :func:`suyama` --- Suyama's parametrisation (C&P theorem 7.4.3): ``12 | #E(F_p)``;
* :func:`z2z8` --- curves with rational torsion Z/2 x Z/8, so ``16 | #E(F_p)``. The family
  and its non-torsion point are derived in reference/README.md: an auxiliary curve
  ``T: Y^2 = Z^3 + 4 Z - 16`` of rank 1 with generator ``G = (4, 8)``; each multiple ``k G``
  (computed modulo n) gives a parameter ``u``, the curve ``A(u)`` and a point ``x0(u)``.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from lenstra.arith import NotInvertible, inv

Point = tuple[int, int] | None


# --- Weierstrass, affine -------------------------------------------------------------

def w_add(P: Point, Q: Point, a: int, n: int) -> Point:
    """``P + Q`` on ``y^2 = x^3 + a x + b`` modulo n (b is not needed)."""
    if P is None:
        return Q
    if Q is None:
        return P
    x1, y1 = P
    x2, y2 = Q
    if x1 == x2:
        if (y1 + y2) % n == 0:
            return None                                   # Q = -P
        lam = (3 * x1 * x1 + a) * inv(2 * y1, n) % n      # tangent
    else:
        lam = (y2 - y1) * inv(x2 - x1, n) % n             # chord
    x3 = (lam * lam - x1 - x2) % n
    return x3, (lam * (x1 - x3) - y1) % n


def w_mul(k: int, P: Point, a: int, n: int) -> Point:
    """``k P`` by left-to-right double-and-add (``k >= 0``)."""
    R: Point = None
    for bit in bin(k)[2:]:
        R = w_add(R, R, a, n)
        if bit == "1":
            R = w_add(R, P, a, n)
    return R


# --- Montgomery, x-only -------------------------------------------------------------

def m_dbl(X: int, Z: int, a24: int, n: int) -> tuple[int, int]:
    """``x(2P)`` from ``x(P) = X/Z``: 2M + 2S."""
    s, d = (X + Z) ** 2 % n, (X - Z) ** 2 % n
    t = s - d                                             # 4 X Z
    return s * d % n, t * (d + a24 * t) % n


def m_add(X1: int, Z1: int, X2: int, Z2: int, Xd: int, Zd: int, n: int) -> tuple[int, int]:
    """``x(P + Q)`` from ``x(P), x(Q)`` and ``x(P - Q) = Xd/Zd`` (differential addition)."""
    u = (X1 - Z1) * (X2 + Z2)
    v = (X1 + Z1) * (X2 - Z2)
    return Zd * (u + v) ** 2 % n, Xd * (u - v) ** 2 % n


def m_mul(k: int, X: int, Z: int, a24: int, n: int) -> tuple[int, int]:
    """``x(k P)`` by the Montgomery ladder (``k >= 1``): invariant ``R1 - R0 = P``."""
    X0, Z0, X1, Z1 = X, Z, *m_dbl(X, Z, a24, n)
    for bit in bin(k)[3:]:
        if bit == "1":
            X0, Z0 = m_add(X1, Z1, X0, Z0, X, Z, n)
            X1, Z1 = m_dbl(X1, Z1, a24, n)
        else:
            X1, Z1 = m_add(X1, Z1, X0, Z0, X, Z, n)
            X0, Z0 = m_dbl(X0, Z0, a24, n)
    return X0, Z0


# --- curves ----------------------------------------------------------------------------

@dataclass
class Curve:
    """A curve modulo n with a starting point.

    ``form`` is ``"weierstrass"`` (fields ``a, b, P``) or ``"montgomery"`` (fields
    ``A, B, a24`` and the point ``P = (x0, y0)``; the algorithm uses only ``a24`` and
    ``x0``). ``params`` records how the curve was drawn (``sigma`` for Suyama,
    ``k`` and ``u`` for Z/2 x Z/8).
    """

    form: str
    n: int
    family: str
    a: int = 0
    b: int = 0
    P: Point = None
    A: int = 0
    B: int = 1
    a24: int = 0
    params: dict = field(default_factory=dict)

    def describe(self) -> dict:
        """The equation and the point, for the "extra" output (the spec asks to keep them)."""
        if self.form == "weierstrass":
            return {"family": self.family, "equation": "y^2 = x^3 + a*x + b", "a": self.a,
                    "b": self.b, "point": {"x": self.P[0], "y": self.P[1]}, **self.params}
        return {"family": self.family, "equation": "B*y^2 = x^3 + A*x^2 + x", "A": self.A,
                "B": self.B, "point": {"x": self.P[0], "y": self.P[1]}, **self.params}


class CurveFound(Exception):
    """Building the curve already hit a non-invertible element: a factor for free."""

    def __init__(self, d: int, family: str, params: dict):
        super().__init__(f"factor {d} while building a {family} curve")
        self.d, self.family, self.params = d, family, params


def random_weierstrass(n: int, rng: random.Random) -> Curve:
    """A random curve ``y^2 = x^3 + a x + b`` through a random point ``(x0, y0)``."""
    while True:
        a, x0, y0 = (rng.randrange(n) for _ in range(3))
        b = (y0 * y0 - x0 ** 3 - a * x0) % n
        g = math.gcd(4 * a ** 3 + 27 * b * b, n)          # discriminant (up to -16)
        if g == 1:
            return Curve("weierstrass", n, "random", a=a, b=b, P=(x0, y0))
        if g < n:
            raise CurveFound(g, "random", {"a": a, "b": b})
        # g == n: singular modulo every prime factor; draw again


def suyama(n: int, rng: random.Random, sigma: int | None = None) -> Curve:
    """Suyama's curve for ``sigma`` (C&P theorem 7.4.3): ``u = sigma^2 - 5``, ``v = 4 sigma``,
    ``A = (v - u)^3 (3u + v) / (4 u^3 v) - 2``, ``x0 = u^3 / v^3``; ``12 | #E(F_p)``.

    The point is on ``B y^2 = x^3 + A x^2 + x`` with ``B = (sigma^2 - 5) / sigma^3`` and
    ``y0 = (sigma^2 - 1)(sigma^2 - 25)(sigma^4 - 25) / (512 sigma^3)`` (checked with Sage).
    """
    s = rng.randrange(6, n) if sigma is None else sigma % n
    u, v = (s * s - 5) % n, 4 * s % n
    params = {"sigma": s}
    try:
        a24 = (v - u) ** 3 * (3 * u + v) * inv(16 * u ** 3 * v, n) % n   # (A + 2) / 4
        _check_montgomery(a24, n)
        x0 = u ** 3 * inv(v ** 3, n) % n
        s3 = inv(s ** 3, n)
    except NotInvertible as e:
        raise CurveFound(e.d, "suyama", params) from None
    B = u * s3 % n
    y0 = (s * s - 1) * (s * s - 25) * (s ** 4 - 25) * inv(512, n) * s3 % n
    return Curve("montgomery", n, "suyama", A=(4 * a24 - 2) % n, B=B, a24=a24, P=(x0, y0),
                 params=params)


# Auxiliary curve T: Y^2 = Z^3 + 4 Z - 16, rank 1, generator G = (4, 8).
T_A, T_G = 4, (4, 8)


def z2z8(n: int, rng: random.Random, k: int | None = None) -> Curve:
    """A Montgomery curve with torsion Z/2 x Z/8 and a point of infinite order (``16 | #E(F_p)``).

    ``(Z, Y) = k G`` on ``T``; ``u = (8 + Y) / (2 (Z - 4))``,
    ``Q = (u^2 + 2u + 2)^2 / (2 u (u + 1)(u + 2))``, ``A = Q^2 - 2`` (so ``a24 = Q^2 / 4``),
    ``B = 1``, ``x0 = -2 (u + 1)^2 / u^2`` and
    ``y0 = (u + 1)(u^2 + 4u + 2) (u^2 - (Z + 2)/2) / ((u + 2) u^3)``.
    """
    k = rng.randrange(2, 1 << 32) if k is None else k
    params = {"k": k}
    try:
        R = w_mul(k, T_G, T_A, n)
        if R is None:                                     # k G = O modulo n: no curve
            raise NotInvertible(n, n)
        Zt, Yt = R
        u = (8 + Yt) * inv(2 * (Zt - 4), n) % n
        u1, u2 = u + 1, u + 2
        Q = (u * u + 2 * u + 2) ** 2 * inv(2 * u * u1 * u2, n) % n
        a24 = Q * Q * inv(4, n) % n
        _check_montgomery(a24, n)
        x0 = -2 * u1 * u1 * inv(u * u, n) % n
        y0 = u1 * (u * u + 4 * u + 2) * (u * u - (Zt + 2) * inv(2, n)) * inv(u2 * u ** 3, n) % n
    except NotInvertible as e:
        raise CurveFound(e.d, "z2z8", params) from None
    params["u"] = u
    return Curve("montgomery", n, "z2z8", A=(4 * a24 - 2) % n, a24=a24, P=(x0, y0),
                 params=params)


def _check_montgomery(a24: int, n: int) -> None:
    """``A^2 != 4``: ``a24 = (A + 2)/4`` and ``a24 - 1 = (A - 2)/4`` must be invertible."""
    for t in (a24, a24 - 1):
        g = math.gcd(t, n)
        if g != 1:
            raise NotInvertible(g, n)


FAMILIES = {"weierstrass": random_weierstrass, "suyama": suyama, "z2z8": z2z8}
