"""#E(F_p) by Schoof's algorithm (Crandall--Pomerance, 7.5.2).

The Frobenius endomorphism phi(x, y) = (x^p, y^p) satisfies phi^2 - t phi + p = 0 on
E, where #E = p + 1 - t. For small primes l != p we find t mod l by testing this
equation on the l-torsion E[l], i.e. computing in the ring

    A_l = F_p[x, y] / (psi_l(x), y^2 - f(x)),

where psi_l is the l-th division polynomial (its roots are the x-coordinates of the
points of E[l] \\ {O}). The "generic point" (x, y) of A_l stands for every point
of E[l] at once. When prod l > 4 sqrt(p), the Chinese remainder theorem gives t
(|t| <= 2 sqrt p by Hasse).

Points of A_l are written (a(x), b(x) y) and stored as fractions
(a_num, a_den, b_num, b_den) of polynomials modulo the current modulus g, so a
group operation needs no inversion. That is valid as long as every operation is
"generic" at every root of g (no P = +-Q, no O), which holds for multiples [k]P,
k < l, and for multiples of phi(P). The one test that may differ between roots,
x(phi^2 P) = x([p mod l] P), is decided by a gcd: if the gcd with g is a proper
factor h, we continue with h (or g / h) as the modulus. Any factor of psi_l over
F_p describes a Frobenius-stable set of l-torsion points, and the characteristic
equation, and so t mod l, can be read off any non-empty such set.
"""

from __future__ import annotations

from math import isqrt

from .curve import Curve
from .poly import Modulus, PolyRing


class Split(Exception):
    """A test was not uniform over the roots of the modulus: restart with ``factor``."""

    def __init__(self, factor):
        super().__init__()
        self.factor = factor


# --- division polynomials -----------------------------------------------------------
class DivisionPolynomials:
    """psi_n for the curve y^2 = f(x), as polynomials in x only: for odd n psi_n itself,
    for even n psi_n / y (written psi~_n). With this convention the standard
    recurrences become (f^2 = y^4 enters where an even-index product appears twice):

        psi_{2m+1} = psi_{m+2} psi_m^3 - psi_{m-1} psi_{m+1}^3   (times f^2 on the even side)
        psi~_{2m}  = psi_m (psi_{m+2} psi_{m-1}^2 - psi_{m-2} psi_{m+1}^2) / 2
    """

    def __init__(self, E: Curve, R: PolyRing):
        p, a, b = int(E.p), int(E.a), int(E.b)
        self.R = R
        self.f = R.norm([b, a, 0, 1])
        self.ff = R.sqr(self.f)
        self.cache = {
            0: [], 1: [1], 2: [2 % p],
            3: R.norm([(-a * a) % p, 12 * b % p, 6 * a % p, 0, 3 % p]),
            4: R.scale(R.norm([(-8 * b * b - a ** 3) % p, (-4 * a * b) % p, (-5 * a * a) % p,
                               20 * b % p, 5 * a % p, 0, 1]), 4),
        }

    def __call__(self, n: int):
        if n in self.cache:
            return self.cache[n]
        R = self.R
        m = n // 2
        if n % 2:                                       # n = 2m + 1
            u = R.mul(self(m + 2), R.mul(R.sqr(self(m)), self(m)))
            v = R.mul(self(m - 1), R.mul(R.sqr(self(m + 1)), self(m + 1)))
            if m % 2 == 0:
                u = R.mul(u, self.ff)                   # psi_{m+2} psi_m^3 has y^4
            else:
                v = R.mul(v, self.ff)                   # psi_{m-1} psi_{m+1}^3 has y^4
            res = R.sub(u, v)
        else:                                           # n = 2m
            u = R.mul(self(m + 2), R.sqr(self(m - 1)))
            v = R.mul(self(m - 2), R.sqr(self(m + 1)))
            res = R.scale(R.mul(self(m), R.sub(u, v)), pow(2, -1, R.p))
        self.cache[n] = res
        return res


# --- points of A_l as fractions -----------------------------------------------------
class TorsionArithmetic:
    """Group operations on points (a/a', (b/b') y) of A_l modulo g."""

    def __init__(self, E: Curve, M: Modulus):
        self.M, self.R = M, M.R
        self.A = int(E.a)
        self.f = self.R.mod(self.R.norm([int(E.b), int(E.a), 0, 1]), M.g)

    def _fsub(self, n1, d1, n2, d2):
        M, R = self.M, self.R
        return R.sub(M.mul(n1, d2), M.mul(n2, d1)), M.mul(d1, d2)

    def add(self, P, Q):
        """P + Q for P != +-Q at every root (the chord)."""
        M, R = self.M, self.R
        xn1, xd1, yn1, yd1 = P
        xn2, xd2, yn2, yd2 = Q
        dyn, dyd = self._fsub(yn2, yd2, yn1, yd1)
        dxn, dxd = self._fsub(xn2, xd2, xn1, xd1)
        ln, ld = M.mul(dyn, dxd), M.mul(dyd, dxn)                # lambda = dy / dx
        # x3 = lambda^2 f - x1 - x2
        l2n, l2d = M.mul(M.sqr(ln), self.f), M.sqr(ld)
        sxn, sxd = R.add(M.mul(xn1, xd2), M.mul(xn2, xd1)), M.mul(xd1, xd2)
        x3n, x3d = self._fsub(l2n, l2d, sxn, sxd)
        return self._finish(ln, ld, xn1, xd1, yn1, yd1, x3n, x3d)

    def double(self, P):
        """2P for P of odd order (b != 0 at every root): lambda = (3x^2 + a) / (2 b f)."""
        M, R = self.M, self.R
        xn, xd, yn, yd = P
        xn2, xd2 = M.sqr(xn), M.sqr(xd)
        ln = M.mul(R.add(R.scale(xn2, 3), R.scale(xd2, self.A)), yd)
        ld = M.mul(M.mul(R.scale(yn, 2), self.f), xd2)
        l2n, l2d = M.mul(M.sqr(ln), self.f), M.sqr(ld)
        x3n, x3d = self._fsub(l2n, l2d, R.scale(xn, 2), xd)
        return self._finish(ln, ld, xn, xd, yn, yd, x3n, x3d)

    def _finish(self, ln, ld, xn1, xd1, yn1, yd1, x3n, x3d):
        """b3 = lambda (x1 - x3) - b1."""
        M = self.M
        tn, td = self._fsub(xn1, xd1, x3n, x3d)
        y3n, y3d = self._fsub(M.mul(ln, tn), M.mul(ld, td), yn1, yd1)
        return (x3n, x3d, y3n, y3d)

    def mul(self, P, k: int):
        """[k]P for 1 <= k < l (all steps generic)."""
        Q = P
        for bit in bin(k)[3:]:
            Q = self.double(Q)
            if bit == "1":
                Q = self.add(Q, P)
        return Q

    def x_diff(self, P, Q):
        """Numerator of x(P) - x(Q)."""
        return self._fsub(P[0], P[1], Q[0], Q[1])[0]

    def y_diff(self, P, Q, sign: int = 1):
        """Numerator of b(P) - sign b(Q)."""
        M, R = self.M, self.R
        u, v = M.mul(P[2], Q[3]), M.mul(Q[2], P[3])
        return R.sub(u, v) if sign == 1 else R.add(u, v)

    def uniform_zero(self, h) -> bool:
        """Is h = 0 at every root of g? False if at none; Split if at some only.
        (A gcd, i.e. quadratic in deg g: used only where the answer may vary.)"""
        if not h:
            return True
        d = self.R.gcd(self.M.g, h)
        if len(d) == 1:
            return False
        raise Split(d)


def _trace_mod_l(E: Curve, l: int, M: Modulus, frob) -> int:
    """t mod l, computing modulo the factor M.g of psi_l (may raise Split)."""
    T = TorsionArithmetic(E, M)
    one = [1]
    P = ([0, 1], one, one, one)                       # the generic point (x, y)
    xp, bp, xp2, bp2 = frob
    Phi = (xp, one, bp, one)                          # (x^p, y^p) = (x^p, f^((p-1)/2) y)
    Phi2 = (xp2, one, bp2, one)                       # (x^(p^2), y^(p^2))
    q = int(E.p) % l
    Qq = T.mul(P, q)
    # The only test whose answer may vary over the roots of g. All the later ones are
    # uniform (they follow from phi^2 - t phi + q = 0 with one t), so "= 0 at every
    # root" is just "= 0 mod g", i.e. the reduced numerator is the zero polynomial.
    if T.uniform_zero(T.x_diff(Phi2, Qq)):
        # phi^2 P = +- [q] P on all of the current torsion set
        if not T.y_diff(Phi2, Qq, -1):
            return 0                                  # phi^2 P = -[q] P  =>  t phi P = O
        if T.y_diff(Phi2, Qq, 1):
            raise ArithmeticError("Schoof: inconsistent signs")
        # phi^2 P = [q] P: phi P = [lambda] P with lambda^2 = q, and t = 2 lambda
        w = next((w for w in range(1, l) if w * w % l == q), None)
        if w is None:
            raise ArithmeticError(f"Schoof: {q} is not a square mod {l}")
        Wp = T.mul(P, w)
        if T.x_diff(Phi, Wp):
            raise ArithmeticError("Schoof: no eigenvalue +-w")
        return 2 * w % l if not T.y_diff(Phi, Wp, 1) else (-2 * w) % l
    Rp = T.add(Phi2, Qq)                              # (phi^2 + q) P, generic at every root
    Tt = Phi
    for tau in range(1, (l - 1) // 2 + 1):
        if tau == 2:
            Tt = T.double(Phi)
        elif tau > 2:
            Tt = T.add(Tt, Phi)
        if not T.x_diff(Rp, Tt):
            return tau if not T.y_diff(Rp, Tt, 1) else (-tau) % l
    raise ArithmeticError(f"Schoof: no tau found for l = {l}")


def trace_mod_l(E: Curve, l: int, psi: DivisionPolynomials) -> tuple[int, int]:
    """(t mod l, degree of the factor of psi_l used)."""
    R = psi.R
    g = R.monic(psi(l))
    M = Modulus(R, g)
    p = int(E.p)
    f = R.mod(psi.f, g)
    xp = M.x_pow(p)
    bp = M.pow(f, (p - 1) // 2)                       # y^p = f^((p-1)/2) y
    xp2 = M.pow(xp, p)                                # x^(p^2) = (x^p)^p
    bp2 = M.mul(M.pow(bp, p), bp)                     # y^(p^2) = b^p y^p = b^p b y
    frob = [xp, bp, xp2, bp2]
    while True:
        try:
            return _trace_mod_l(E, l, M, frob), M.n
        except Split as s:
            h = s.factor
            other = R.divmod(M.g, h)[0]
            g = min(h, R.monic(other), key=len)       # either factor works; take the smaller
            M = Modulus(R, g)
            frob = [R.mod(c, g) for c in frob]


def trace_mod_2(E: Curve, R: PolyRing) -> int:
    """t = #E - p - 1 = #E (mod 2): #E is even iff E has a point of order 2,
    i.e. f has a root in F_p, i.e. gcd(x^p - x, f) != 1."""
    f = R.norm([int(E.b), int(E.a), 0, 1])
    M = Modulus(R, f)
    xp = M.x_pow(int(E.p))
    return 0 if len(R.gcd(f, R.sub(xp, [0, 1]))) > 1 else 1


def order_schoof(E: Curve) -> tuple[int, dict]:
    p = int(E.p)
    R = PolyRing(p)
    psi = DivisionPolynomials(E, R)
    residues = {2: trace_mod_2(E, R)}
    degrees = {}
    t, m = residues[2], 2
    l = 2
    while m * m <= 16 * p:                            # until prod l > 4 sqrt(p)
        l += 1
        if any(l % d == 0 for d in range(2, isqrt(l) + 1)) or l == p:
            continue
        r, deg = trace_mod_l(E, l, psi)
        residues[l], degrees[l] = r, deg
        # CRT: t = t (mod m), t = r (mod l)
        t = t + m * ((r - t) * pow(m, -1, l) % l)
        m *= l
    if t > m // 2:
        t -= m
    return p + 1 - t, {"method": "schoof", "trace": t,
                       "t_mod_l": {str(k): v for k, v in residues.items()},
                       "factor_degree": {str(k): v for k, v in degrees.items()}}
