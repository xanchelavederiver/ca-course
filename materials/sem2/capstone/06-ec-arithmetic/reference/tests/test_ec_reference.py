"""Unit tests of the EC-arithmetic reference against Sage's EllipticCurve (the oracle).

Run: make test-capstones CAPSTONE=ec-arithmetic
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path

import pytest
from sage.all import GF, ZZ, EllipticCurve, legendre_symbol

REF = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REF))

from ecarith import (Curve, CurveError, mul, order_naive, order_schoof,  # noqa: E402
                     order_shanks_mestre, ternary_expansion)
from ecarith.field import legendre, sqrt_mod  # noqa: E402
from ecarith.poly import Modulus, PolyRing  # noqa: E402
from ecarith.schoof import DivisionPolynomials  # noqa: E402

from taskgen.capstone.gens import ec_arithmetic as gen  # noqa: E402


def rand_prime(rng, bits, shape=None):
    while True:
        n = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
        if shape == "ts-hard":
            s = bits // 2
            n = (n >> s << s) | 1
        if ZZ(n).is_pseudoprime() and (shape != "3mod4" or n % 4 == 3):
            return n


def rand_curve(rng, bits, kind="generic"):
    p = rand_prime(rng, bits)
    while True:
        a, b = rng.randrange(p), rng.randrange(p)
        if kind == "a0":
            a = 0
        if kind == "b0":
            b = 0
        if (4 * a ** 3 + 27 * b ** 2) % p:
            return p, a, b


def sage_point(Es, P):
    return Es(0) if P is None else Es(P[0], P[1])


# --- the field ------------------------------------------------------------------------
@pytest.mark.parametrize("shape", [None, "3mod4", "ts-hard"])
def test_sqrt_mod(shape):
    rng = random.Random(1)
    for bits in (8, 64, 256, 1024):
        p = rand_prime(rng, bits, shape)
        for _ in range(20):
            a = rng.randrange(p)
            assert legendre(a, p) == legendre_symbol(a, p)
            r = sqrt_mod(a, p, rng)
            if legendre_symbol(a, p) == -1:
                assert r is None
            else:
                assert r * r % p == a


# --- the group law --------------------------------------------------------------------
@pytest.mark.parametrize("bits", [16, 64, 256, 521, 1024])
@pytest.mark.parametrize("kind", ["generic", "a0", "b0"])
def test_group_law(bits, kind):
    rng = random.Random(bits)
    p, a, b = rand_curve(rng, bits, kind)
    E, Es = Curve(p, a, b), EllipticCurve(GF(p, proof=False), [a, b])
    for _ in range(10):
        P, Q = E.random_point(rng), E.random_point(rng)
        Ps, Qs = sage_point(Es, P), sage_point(Es, Q)
        assert E.on_curve(P)
        assert sage_point(Es, E.add(P, Q)) == Ps + Qs
        assert sage_point(Es, E.sub(P, Q)) == Ps - Qs
        assert sage_point(Es, E.add(P, P)) == 2 * Ps            # P + P via add
        assert sage_point(Es, E.double(P)) == 2 * Ps
        assert sage_point(Es, E.neg(P)) == -Ps
        assert E.add(P, E.neg(P)) is None                       # P + (-P) = O
        assert E.add(None, P) == P and E.add(P, None) == P and E.add(None, None) is None
        J = E.jadd_affine(E.jdouble(E.to_jacobian(P)), Q)       # Jacobian 2P + Q
        assert sage_point(Es, E.from_jacobian(J)) == 2 * Ps + Qs


def test_two_torsion():
    rng = random.Random(5)
    p = rand_prime(rng, 128)
    a, x0 = rng.randrange(p), rng.randrange(p)
    b = (-x0 ** 3 - a * x0) % p
    E = Curve(p, a, b)
    T = (x0, 0)
    assert E.on_curve(T) and E.double(T) is None and E.add(T, T) is None
    assert E.from_jacobian(E.jdouble(E.to_jacobian(T))) is None
    for k in (1, 2, 3, 10 ** 20, -7):
        for m in ("binary", "ternary"):
            assert mul(E, T, k, m) == (T if k % 2 else None)


def test_bad_input():
    with pytest.raises(CurveError):
        Curve(15, 1, 1)                                  # p not prime
    with pytest.raises(CurveError):
        Curve(23, 0, 0)                                  # singular
    with pytest.raises(CurveError):
        Curve(23, 1, 1).point([1, 1])                    # not on the curve


# --- scalar multiplication --------------------------------------------------------------
def test_ternary_expansion():
    rng = random.Random(2)
    assert ternary_expansion(0) == []
    for n in list(range(1, 300)) + [rng.getrandbits(k) for k in range(1, 3000, 37)]:
        d = ternary_expansion(n)
        assert set(d) <= {-1, 0, 1} and d[-1] == 1
        assert sum(x << i for i, x in enumerate(d)) == n
        assert all(d[i] == 0 or d[i + 1] == 0 for i in range(len(d) - 1))   # NAF
        assert d == gen._naf(n)


@pytest.mark.parametrize("bits", [8, 64, 192, 521, 1024])
@pytest.mark.parametrize("method", ["binary", "ternary"])
@pytest.mark.parametrize("coords", ["affine", "jacobian"])
def test_mul(bits, method, coords):
    rng = random.Random(bits * 7 + len(method) + len(coords))
    for kind in ("generic", "a0"):
        p, a, b = rand_curve(rng, bits, kind)
        E, Es = Curve(p, a, b), EllipticCurve(GF(p, proof=False), [a, b])
        P = E.random_point(rng)
        Ps = sage_point(Es, P)
        ks = [0, 1, -1, 2, 3, rng.getrandbits(bits), -rng.getrandbits(bits), rng.getrandbits(2 * bits)]
        if bits <= 192:
            n = int(Es.order())
            ks += [n, n - 1, n + 1, -n, 2 * n + 3]
        for k in ks:
            assert sage_point(Es, mul(E, P, k, method, coords)) == k * Ps, k
        assert mul(E, None, 12345, method, coords) is None


@pytest.mark.parametrize("name", sorted(gen.STD))
def test_standard_curves(name):
    p, a, b, gx, gy, n = gen.STD[name]
    assert ZZ(p).is_pseudoprime() and ZZ(n).is_pseudoprime()
    E = Curve(p, a, b)
    G = E.point([gx, gy])
    for method in ("binary", "ternary"):
        assert mul(E, G, n, method) is None                   # n G = O
        assert mul(E, G, n - 1, method) == E.neg(G)
    Es = EllipticCurve(GF(p, proof=False), [a, b])
    k = random.Random(3).randrange(n)
    assert sage_point(Es, mul(E, G, k)) == k * Es(gx, gy)


# --- the order ------------------------------------------------------------------------
def test_order_naive_tiny():
    for p in (5, 7, 11, 13, 101, 229):
        for a in range(0, p, max(1, p // 7)):
            for b in range(0, p, max(1, p // 5)):
                if (4 * a ** 3 + 27 * b ** 2) % p:
                    n = int(EllipticCurve(GF(p), [a, b]).order())
                    E = Curve(p, a, b)
                    assert order_naive(E) == n
                    assert order_shanks_mestre(E)[0] == n
                    assert order_schoof(E)[0] == n


@pytest.mark.parametrize("bits", [10, 20, 32, 48])
@pytest.mark.parametrize("kind", ["generic", "a0", "b0"])
def test_order(bits, kind):
    rng = random.Random(bits + len(kind))
    for _ in range(3):
        p, a, b = rand_curve(rng, bits, kind)
        n = int(EllipticCurve(GF(p), [a, b]).order())
        E = Curve(p, a, b)
        assert order_shanks_mestre(E, rng)[0] == n
        assert order_schoof(E)[0] == n


def test_order_supersingular_and_full_2_torsion():
    rng = random.Random(9)
    for _ in range(3):
        p = rand_prime(rng, 40, "3mod4")
        E = Curve(p, 1, 0)                                  # #E = p + 1
        assert order_shanks_mestre(E, rng)[0] == p + 1 == order_schoof(E)[0]
        r1, r2 = rng.randrange(p), rng.randrange(p)
        r3 = (-r1 - r2) % p
        a, b = (r1 * r2 + r1 * r3 + r2 * r3) % p, (-r1 * r2 * r3) % p
        if (4 * a ** 3 + 27 * b ** 2) % p:
            n = int(EllipticCurve(GF(p), [a, b]).order())
            assert order_shanks_mestre(Curve(p, a, b), rng)[0] == n == order_schoof(Curve(p, a, b))[0]


def test_division_polynomials():
    rng = random.Random(4)
    p, a, b = rand_curve(rng, 40)
    Es = EllipticCurve(GF(p), [a, b])
    psi = DivisionPolynomials(Curve(p, a, b), PolyRing(p))
    for l in (3, 5, 7, 11, 13):
        assert psi(l) == [int(c) for c in Es.division_polynomial(l).list()]


def test_poly_mulmod():
    rng = random.Random(6)
    p = rand_prime(rng, 64)
    R = PolyRing(p)
    Fx = GF(p)["x"]
    for n in (1, 2, 5, 40, 300):
        g = [rng.randrange(p) for _ in range(n)] + [1]
        M = Modulus(R, g)
        a = R.norm([rng.randrange(p) for _ in range(n)])
        b = R.norm([rng.randrange(p) for _ in range(n)])
        G, A, B = Fx(g), Fx(a), Fx(b)
        assert M.mul(a, b) == [int(c) for c in (A * B % G).list()]
        assert M.x_pow(p) == [int(c) for c in pow(Fx.gen(), p, G).list()]
        d, s = R.xgcd_inverse(a, g)
        assert d == [int(c) for c in A.gcd(G).list()]
        if d == [1]:
            assert M.mul(s, a) == [1]


# --- the CLI against the generator's vectors ---------------------------------------------
def test_cli_on_generated_vectors():
    rng = random.Random(8)
    params = [{"kind": "misc"}] * 12 + [{"kind": "add", "bits": 64}] * 12 + \
             [{"kind": "mul", "bits": 128}] * 12 + [{"kind": "mul", "bits": 256, "std": ["P-256", "secp256k1"]}] * 6 + \
             [{"kind": "point", "bits": 128}] * 6 + \
             [{"kind": "order", "bits": 32, "method": m} for m in ("shanks-mestre", "schoof")] * 4
    vecs = [gen.generate(dict(p), rng) for p in params]
    reqs = "".join(json.dumps({"id": i, "input": v["input"]}) + "\n" for i, v in enumerate(vecs))
    reqs += '{"id": "bad", "input": {"op": "add", "curve": {"p": 23, "a": 1, "b": 1}, "P": [1, 1], "Q": null}}\n'
    out = subprocess.run([sys.executable, str(REF / "main.py")], input=reqs, capture_output=True,
                         text=True, check=True).stdout.splitlines()
    assert len(out) == len(vecs) + 1
    for line, v in zip(out, vecs):
        ans = json.loads(line)
        assert "error" not in ans, ans
        assert gen.verify(v, ans["output"]) is None, (v, ans)
    assert "error" in json.loads(out[-1])


def test_verify_normalizes_coordinates():
    p, a, b = 10007, 3, 7
    Es = EllipticCurve(GF(p), [a, b])
    P = Es.lift_x(GF(p)(5)) if Es.is_x_coord(5) else Es.gens()[0]
    v = {"input": {"op": "double", "curve": {"p": p, "a": a, "b": b}, "P": [int(P[0]), int(P[1])]},
         "expected": {"point": [int((2 * P)[0]), int((2 * P)[1])]}}
    x, y = v["expected"]["point"]
    z = 1234
    assert gen.verify(v, {"point": [x, y]}) is None
    assert gen.verify(v, {"point": [x * z % p, y * z % p, z], "coords": "projective"}) is None
    assert gen.verify(v, {"point": [x * z * z % p, y * z ** 3 % p, z], "coords": "jacobian"}) is None
    assert gen.verify(v, {"point": [x * z * z % p, y * z ** 3 % p, z]}) is None
    assert gen.verify(v, {"point": [x, (y + 1) % p]}) is not None
    assert gen.verify(v, {"point": None}) is not None
    v0 = dict(v, expected={"point": None})
    assert gen.verify(v0, {"point": None}) is None and gen.verify(v0, {"point": [1, 0, 0]}) is None
