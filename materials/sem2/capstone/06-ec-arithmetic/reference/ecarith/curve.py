"""The group E(F_p) of the curve y^2 = x^3 + a x + b over F_p, p > 3 prime.

Points are ``None`` (the point at infinity O) or a pair ``(x, y)`` of reduced residues
(affine coordinates). The scalar multiplication works in Jacobian coordinates
(X : Y : Z) with x = X/Z^2, y = Y/Z^3 (one inversion per multiplication instead of one
per group operation); a Jacobian point with Z = 0 is O.
"""

from __future__ import annotations

import random

from .field import inv, is_prime, legendre, mpz, sqrt_mod


class CurveError(ValueError):
    """Bad curve or point (singular curve, p not prime, point not on the curve, ...)."""


class Curve:
    def __init__(self, p, a, b, check: bool = True):
        self.p, self.a, self.b = mpz(p), mpz(a) % p, mpz(b) % p
        if check:
            if self.p < 5 or not is_prime(self.p):
                raise CurveError(f"p = {p} is not a prime > 3")
            if (4 * self.a ** 3 + 27 * self.b ** 2) % self.p == 0:
                raise CurveError("the curve is singular: 4a^3 + 27b^2 = 0 (mod p)")
        # a = -3 (NIST curves) and a = 0 (secp256k1) have cheaper doublings
        self.a_kind = "zero" if self.a == 0 else "minus3" if self.a == self.p - 3 else "generic"

    def __repr__(self) -> str:
        return f"Curve(p={self.p}, a={self.a}, b={self.b})"

    # --- points ---------------------------------------------------------------------
    def rhs(self, x):
        """f(x) = x^3 + a x + b mod p."""
        return (x * x * x + self.a * x + self.b) % self.p

    def on_curve(self, P) -> bool:
        if P is None:
            return True
        x, y = P
        return 0 <= x < self.p and 0 <= y < self.p and (y * y - self.rhs(x)) % self.p == 0

    def point(self, P):
        """Validate and convert an input point ([x, y] or None)."""
        if P is None:
            return None
        if len(P) != 2:
            raise CurveError(f"a point is [x, y] or null, got {P!r}")
        x, y = mpz(P[0]) % self.p, mpz(P[1]) % self.p
        if not self.on_curve((x, y)):
            raise CurveError(f"({P[0]}, {P[1]}) is not on {self}")
        return (x, y)

    # --- the group law in affine coordinates ----------------------------------------
    def neg(self, P):
        """-P = (x, -y)."""
        if P is None:
            return None
        return (P[0], (-P[1]) % self.p)

    def double(self, P):
        """2P: the tangent at P, lambda = (3x^2 + a) / 2y; 2P = O when y = 0 (2-torsion)."""
        if P is None or P[1] == 0:
            return None
        p = self.p
        x, y = P
        lam = (3 * x * x + self.a) * inv(2 * y, p) % p
        x3 = (lam * lam - 2 * x) % p
        return (x3, (lam * (x - x3) - y) % p)

    def add(self, P, Q):
        """P + Q by the chord-and-tangent rule, with all the special cases:
        O is neutral, P + (-P) = O, and P + P is a doubling (the chord degenerates)."""
        if P is None:
            return Q
        if Q is None:
            return P
        p = self.p
        (x1, y1), (x2, y2) = P, Q
        if x1 == x2:
            if (y1 + y2) % p == 0:
                return None               # Q = -P (also covers P = Q of order 2)
            return self.double(P)         # Q = P
        lam = (y2 - y1) * inv(x2 - x1, p) % p
        x3 = (lam * lam - x1 - x2) % p
        return (x3, (lam * (x1 - x3) - y1) % p)

    def sub(self, P, Q):
        return self.add(P, self.neg(Q))

    # --- Jacobian coordinates --------------------------------------------------------
    @staticmethod
    def to_jacobian(P):
        return (mpz(1), mpz(1), mpz(0)) if P is None else (P[0], P[1], mpz(1))

    def from_jacobian(self, J):
        X, Y, Z = J
        if Z == 0:
            return None
        p = self.p
        zi = inv(Z, p)
        zi2 = zi * zi % p
        return (X * zi2 % p, Y * zi2 * zi % p)

    def jdouble(self, J):
        """2J in Jacobian coordinates (3M + 5S for generic a; 'dbl-1998-cmo-2' in the EFD)."""
        X, Y, Z = J
        if Z == 0 or Y == 0:
            return (mpz(1), mpz(1), mpz(0))
        p = self.p
        YY = Y * Y % p
        S = 4 * X * YY % p
        if self.a_kind == "zero":
            M = 3 * X * X % p
        elif self.a_kind == "minus3":
            ZZ = Z * Z % p
            M = 3 * (X - ZZ) * (X + ZZ) % p
        else:
            ZZ = Z * Z % p
            M = (3 * X * X + self.a * ZZ * ZZ) % p
        X3 = (M * M - 2 * S) % p
        Y3 = (M * (S - X3) - 8 * YY * YY) % p
        Z3 = 2 * Y * Z % p
        return (X3, Y3, Z3)

    def jadd_affine(self, J, Q):
        """J + Q with J Jacobian and Q affine (the 'mixed' addition, 8M + 3S)."""
        if Q is None:
            return J
        X1, Y1, Z1 = J
        if Z1 == 0:
            return self.to_jacobian(Q)
        p = self.p
        x2, y2 = Q
        Z1Z1 = Z1 * Z1 % p
        U2 = x2 * Z1Z1 % p                 # x2 in the scale of J
        S2 = y2 * Z1 * Z1Z1 % p            # y2 in the scale of J
        H = (U2 - X1) % p
        r = (S2 - Y1) % p
        if H == 0:
            if r == 0:
                return self.jdouble(J)     # J = Q
            return (mpz(1), mpz(1), mpz(0))  # J = -Q
        HH = H * H % p
        HHH = H * HH % p
        V = X1 * HH % p
        X3 = (r * r - HHH - 2 * V) % p
        Y3 = (r * (V - X3) - Y1 * HHH) % p
        Z3 = Z1 * H % p
        return (X3, Y3, Z3)

    # --- generating a point ------------------------------------------------------------
    def random_point(self, rng: random.Random):
        """A random finite point: pick x until f(x) is a square, then y = sqrt(f(x))
        by Tonelli--Shanks (a random sign). About half of the x succeed."""
        p = self.p
        for _ in range(100 * int(p).bit_length() + 1000):
            x = mpz(rng.randrange(int(p)))
            r = self.rhs(x)
            if r == 0:
                return (x, mpz(0))
            if legendre(r, p) == 1:
                y = sqrt_mod(r, p, rng)
                return (x, y if rng.getrandbits(1) else (-y) % p)
        # tiny p: the curve may have few points; scan every x
        for x in range(int(p)):
            y = sqrt_mod(self.rhs(mpz(x)), p, rng)
            if y is not None:
                return (mpz(x), y)
        raise CurveError("no finite point found")  # impossible for p >= 5 (Hasse)
