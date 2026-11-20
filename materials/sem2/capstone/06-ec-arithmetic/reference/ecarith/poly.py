"""Dense polynomials over F_p for Schoof's algorithm (written by hand on top of bigints).

A polynomial is a list of ints in [0, p), least significant coefficient first, without
trailing zeros (the zero polynomial is []).

Multiplication uses Kronecker substitution: a polynomial with coefficients < p and
degree < n is packed into one big integer with w-bit slots, w >= 2 log2 p + log2 n,
so that the coefficients of the product do not overlap; one bigint multiplication
(GMP, asymptotically fast) then multiplies the polynomials. Reduction modulo a fixed
monic g uses a precomputed inverse of the reversed g (Newton iteration), i.e. two
more multiplications instead of a quadratic long division. Long division and the
extended Euclidean algorithm stay schoolbook: they run only a few times per prime l.
"""

from __future__ import annotations

from gmpy2 import mpz


class PolyRing:
    """F_p[x]."""

    def __init__(self, p):
        self.p = int(p)
        self.pbits = self.p.bit_length()

    # --- basics -----------------------------------------------------------------------
    @staticmethod
    def norm(a: list[int]) -> list[int]:
        while a and a[-1] == 0:
            a.pop()
        return a

    def add(self, a, b):
        p = self.p
        if len(a) < len(b):
            a, b = b, a
        return self.norm([(x + y) % p for x, y in zip(a, b)] + a[len(b):])

    def sub(self, a, b):
        p = self.p
        n = max(len(a), len(b))
        a = a + [0] * (n - len(a))
        b = b + [0] * (n - len(b))
        return self.norm([(x - y) % p for x, y in zip(a, b)])

    def neg(self, a):
        p = self.p
        return [(-x) % p for x in a]

    def scale(self, a, c):
        p, c = self.p, int(c) % self.p
        return self.norm([x * c % p for x in a]) if c else []

    def monic(self, a):
        return self.scale(a, pow(a[-1], -1, self.p)) if a else []

    # --- Kronecker multiplication ---------------------------------------------------
    def _slot(self, n: int) -> int:
        """Slot width in bytes for products of polynomials with <= n coefficients."""
        return (2 * self.pbits + n.bit_length() + 8) // 8

    @staticmethod
    def _pack(a, wb: int) -> mpz:
        return mpz(int.from_bytes(b"".join(c.to_bytes(wb, "little") for c in a), "little"))

    def _unpack(self, z, wb: int, n: int) -> list[int]:
        data = int(z).to_bytes(n * wb, "little")
        p = self.p
        return self.norm([int.from_bytes(data[i:i + wb], "little") % p
                          for i in range(0, n * wb, wb)])

    def mul(self, a, b):
        if not a or not b:
            return []
        if len(a) <= 8 or len(b) <= 8:          # schoolbook for tiny factors
            p = self.p
            out = [0] * (len(a) + len(b) - 1)
            for i, x in enumerate(a):
                if x:
                    for j, y in enumerate(b):
                        out[i + j] += x * y
            return self.norm([c % p for c in out])
        wb = self._slot(min(len(a), len(b)))
        return self._unpack(self._pack(a, wb) * self._pack(b, wb), wb, len(a) + len(b) - 1)

    def sqr(self, a):
        if len(a) <= 8:
            return self.mul(a, a)
        wb = self._slot(len(a))
        z = self._pack(a, wb)
        return self._unpack(z * z, wb, 2 * len(a) - 1)

    def mul_trunc(self, a, b, n: int):
        """a b mod x^n."""
        return self.norm(self.mul(a[:n], b[:n])[:n])

    def inv_series(self, a, n: int):
        """a^{-1} mod x^n (a[0] != 0) by Newton's iteration h <- h (2 - a h)."""
        h = [pow(a[0], -1, self.p)]
        k = 1
        while k < n:
            k = min(2 * k, n)
            e = self.mul_trunc(a, h, k)
            e = self.sub([2], e)
            h = self.mul_trunc(h, e, k)
        return h

    # --- division -----------------------------------------------------------------------
    def divmod(self, a, b):
        """Schoolbook long division: a = q b + r, deg r < deg b."""
        if not b:
            raise ZeroDivisionError("polynomial division by zero")
        p = self.p
        r = list(a)
        db = len(b) - 1
        if len(r) <= db:
            return [], r
        il = pow(b[-1], -1, p)
        q = [0] * (len(r) - db)
        for i in range(len(r) - 1 - db, -1, -1):
            c = r[i + db] * il % p
            q[i] = c
            if c:
                for j in range(db + 1):
                    r[i + j] = (r[i + j] - c * b[j]) % p
        return self.norm(q), self.norm(r[:db])

    def mod(self, a, b):
        return self.divmod(a, b)[1]

    def gcd(self, a, b):
        """Monic gcd by Euclid's algorithm."""
        while b:
            a, b = b, self.mod(a, b)
        return self.monic(a)

    def xgcd_inverse(self, a, g):
        """(d, s) with d = gcd(a, g) monic and s a = d (mod g) (extended Euclid)."""
        r0, r1 = list(g), self.mod(a, g)
        s0, s1 = [], [1]
        while r1:
            q, r = self.divmod(r0, r1)
            r0, r1 = r1, r
            s0, s1 = s1, self.sub(s0, self.mul(q, s1))
        if not r0:
            return [], []
        c = pow(r0[-1], -1, self.p)
        return self.scale(r0, c), self.mod(self.scale(s0, c), g)


class Modulus:
    """Arithmetic in F_p[x] / (g) for a monic g of degree n >= 1, with fast reduction."""

    def __init__(self, R: PolyRing, g):
        if not g or g[-1] != 1:
            raise ValueError("the modulus must be monic and non-constant")
        self.R, self.g, self.n = R, list(g), len(g) - 1
        # inverse of rev(g) modulo x^(n-1): the quotient of a degree <= 2n-2 dividend
        self.ginv = R.inv_series(g[::-1], max(1, self.n - 1))

    def reduce(self, a):
        """a mod g for deg a <= 2n - 2 (larger inputs fall back to long division)."""
        n = self.n
        m = len(a) - 1
        if m < n:
            return a
        if m > 2 * n - 2:
            return self.R.mod(a, self.g)
        R = self.R
        k = m - n + 1                              # number of quotient coefficients
        qrev = R.mul_trunc(a[::-1][:k], self.ginv, k)
        q = qrev[::-1] if len(qrev) == k else ([0] * (k - len(qrev)) + qrev[::-1])
        q = R.norm(q)
        qg = R.mul(q, self.g)[:n]
        return R.sub(a[:n], qg)

    def mul(self, a, b):
        return self.reduce(self.R.mul(a, b))

    def sqr(self, a):
        return self.reduce(self.R.sqr(a))

    def pow(self, a, e: int):
        """a^e mod g, left-to-right binary powering."""
        e = int(e)
        if e == 0:
            return [1] if self.n > 0 else []
        r = list(a)
        for bit in bin(e)[3:]:
            r = self.sqr(r)
            if bit == "1":
                r = self.mul(r, a)
        return r

    def x_pow(self, e: int):
        """x^e mod g; multiplying by x is a shift, so only the squarings cost."""
        e = int(e)
        r = self.reduce([0, 1]) if self.n > 1 else self.R.mod([0, 1], self.g)
        for bit in bin(e)[3:]:
            r = self.sqr(r)
            if bit == "1":
                r = self.reduce([0] + r)
        return r
