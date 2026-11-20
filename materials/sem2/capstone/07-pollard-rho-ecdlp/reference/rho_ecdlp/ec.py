"""Affine arithmetic on E: y^2 = x^3 + a*x + b over F_p, by hand over Python ints.

A point is a tuple ``(x, y)`` of ints in [0, p); the point at infinity O is ``None``.
The spec allows students to use a library for the points; the reference does not, so
that its timings stay the cost of the rho algorithm itself, comparable across
languages (and Sage's EllipticCurve is the oracle of the test vectors).

The rho walks in :mod:`rho` inline the addition formulas below for speed; the
functions here are the readable version used everywhere else.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ntheory import is_prime

Point = tuple[int, int] | None
O: Point = None


class CurveError(ValueError):
    """Invalid curve or point in the input."""


@dataclass(frozen=True)
class Curve:
    p: int
    a: int
    b: int

    @classmethod
    def checked(cls, p: int, a: int, b: int) -> "Curve":
        """The curve, after checking that p > 3 is prime and 4a^3 + 27b^2 != 0 mod p."""
        if not all(isinstance(t, int) for t in (p, a, b)):
            raise CurveError("p, a, b must be integers")
        if p <= 3 or not is_prime(p):
            raise CurveError(f"p = {p} is not a prime > 3")
        a, b = a % p, b % p
        if (4 * a ** 3 + 27 * b * b) % p == 0:
            raise CurveError("singular curve: 4a^3 + 27b^2 = 0 (mod p)")
        return cls(p, a, b)

    def point(self, xy) -> Point:
        """Parse a JSON point: ``null`` (or ``"O"``) for O, else ``[x, y]`` on the curve."""
        if xy is None or xy == "O":
            return O
        if (not isinstance(xy, (list, tuple)) or len(xy) != 2
                or not all(isinstance(t, int) for t in xy)):
            raise CurveError(f"bad point {xy!r}: expected [x, y] or null")
        P = (xy[0] % self.p, xy[1] % self.p)
        if not self.on_curve(P):
            raise CurveError(f"point {list(xy)} is not on the curve")
        return P

    def on_curve(self, P: Point) -> bool:
        if P is None:
            return True
        x, y = P
        return (y * y - (x * x * x + self.a * x + self.b)) % self.p == 0

    def neg(self, P: Point) -> Point:
        return None if P is None else (P[0], -P[1] % self.p)

    def add(self, P: Point, Q: Point) -> Point:
        """P + Q by the chord-and-tangent formulas."""
        if P is None:
            return Q
        if Q is None:
            return P
        p = self.p
        x1, y1 = P
        x2, y2 = Q
        if x1 == x2:
            if (y1 + y2) % p == 0:      # Q = -P (this includes 2-torsion doubling)
                return None
            lam = (3 * x1 * x1 + self.a) * pow(2 * y1, -1, p) % p
        else:
            lam = (y2 - y1) * pow(x2 - x1, -1, p) % p
        x3 = (lam * lam - x1 - x2) % p
        return x3, (lam * (x1 - x3) - y1) % p

    def mul(self, k: int, P: Point) -> Point:
        """[k]P by left-to-right double-and-add (k may be negative)."""
        if k < 0:
            k, P = -k, self.neg(P)
        R: Point = None
        for bit in bin(k)[2:]:
            R = self.add(R, R)
            if bit == "1":
                R = self.add(R, P)
        return R

    def lin(self, u: int, P: Point, v: int, Q: Point) -> Point:
        """[u]P + [v]Q."""
        return self.add(self.mul(u, P), self.mul(v, Q))


def to_json(P: Point):
    return None if P is None else [P[0], P[1]]
