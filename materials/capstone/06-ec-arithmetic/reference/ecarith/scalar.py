"""Scalar multiplication [k]P ("возведение в степень" in the additive notation).

* ``mul_binary``  — the doubling-and-adding ladder over the binary digits of k
  (left to right: Q <- 2Q, and Q <- Q + P for every 1 bit).
* ``mul_ternary`` — the addition--subtraction ladder over the *ternary* (signed binary)
  expansion of k: digits in {-1, 0, 1}, Q <- 2Q, then Q <- Q + P or Q <- Q - P.
  Subtraction is as cheap as addition on a curve (-P = (x, -y)), and the expansion
  has on average n/3 non-zero digits instead of n/2 (Crandall--Pomerance, Alg. 7.2.4).

Both work either in affine coordinates (an inversion per group operation) or in
Jacobian coordinates (one inversion at the end). A negative k multiplies -P by |k|.
"""

from __future__ import annotations

import operator

from .curve import Curve


def ternary_expansion(n: int) -> list[int]:
    """The signed-binary ("ternary") expansion of n >= 0: digits d_i in {-1, 0, 1},
    least significant first, with n = sum d_i 2^i (the empty list for n = 0).

    The trick of Crandall--Pomerance (Alg. 7.2.4): with m = 3n, the bits of m and n
    satisfy 2n = m - n = sum_j (m_j - n_j) 2^j, so d_{j-1} = m_j - n_j. The result is
    the non-adjacent form (NAF): no two adjacent digits are non-zero.
    """
    if n < 0:
        raise ValueError("the ternary expansion is defined here for n >= 0")
    n = int(n)
    m = 3 * n
    return [((m >> j) & 1) - ((n >> j) & 1) for j in range(1, m.bit_length())]


def _check_k(k) -> int:
    if not isinstance(k, bool):
        try:
            return operator.index(k)      # int or mpz
        except TypeError:
            pass
    raise ValueError(f"the scalar must be an integer, got {k!r}")


def mul_binary(E: Curve, P, k: int, coords: str = "jacobian"):
    """[k]P by doubling and adding (left-to-right binary method)."""
    k = _check_k(k)
    if k < 0:
        P, k = E.neg(P), -k
    if k == 0 or P is None:
        return None
    bits = bin(k)[3:]                     # the leading 1 is the starting Q = P
    if coords == "affine":
        Q = P
        for bit in bits:
            Q = E.double(Q)
            if bit == "1":
                Q = E.add(Q, P)
        return Q
    J = E.to_jacobian(P)
    for bit in bits:
        J = E.jdouble(J)
        if bit == "1":
            J = E.jadd_affine(J, P)
    return E.from_jacobian(J)


def mul_ternary(E: Curve, P, k: int, coords: str = "jacobian", digits: list[int] | None = None):
    """[k]P by the addition--subtraction ladder over ``ternary_expansion(|k|)``."""
    k = _check_k(k)
    if k < 0:
        P, k = E.neg(P), -k
    if k == 0 or P is None:
        return None
    d = digits if digits is not None else ternary_expansion(k)
    mP = E.neg(P)
    # the top digit is 1: start with Q = P and walk down the remaining digits
    if coords == "affine":
        Q = P
        for di in reversed(d[:-1]):
            Q = E.double(Q)
            if di == 1:
                Q = E.add(Q, P)
            elif di == -1:
                Q = E.add(Q, mP)
        return Q
    J = E.to_jacobian(P)
    for di in reversed(d[:-1]):
        J = E.jdouble(J)
        if di == 1:
            J = E.jadd_affine(J, P)
        elif di == -1:
            J = E.jadd_affine(J, mP)
    return E.from_jacobian(J)


METHODS = {"binary": mul_binary, "ternary": mul_ternary}


def mul(E: Curve, P, k: int, method: str = "ternary", coords: str = "jacobian"):
    try:
        f = METHODS[method]
    except KeyError:
        raise ValueError(f"unknown method {method!r} (binary | ternary)") from None
    if coords not in ("affine", "jacobian"):
        raise ValueError(f"unknown coordinates {coords!r} (affine | jacobian)")
    return f(E, P, k, coords)
