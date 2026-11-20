"""Tests of the ECM reference against Sage (the oracle), on seeded random inputs.

Run: ``make test-capstones CAPSTONE=lenstra-ecm`` (Sage's python, taskgen image).
"""

import json
import os
import random
import subprocess
import sys

import pytest
from sage.all import GF, EllipticCurve, Integer, factor, is_prime as sage_is_prime, next_prime

REF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REF)

from lenstra import curves as C                                           # noqa: E402
from lenstra.arith import (NotInvertible, batch_inv, inv, iroot, is_prime,  # noqa: E402
                           perfect_power, primes_up_to)
from lenstra.ecm import Options, Stats, factorize, stage2_plan               # noqa: E402
from lenstra.params import level, rho, semismooth                           # noqa: E402
from main import solve                                                     # noqa: E402

FAMILIES = ("weierstrass", "suyama", "z2z8")


def rprime(bits, rng):
    while True:
        p = int(next_prime(rng.getrandbits(bits) | (1 << (bits - 1))))
        if p.bit_length() == bits:
            return p


def sage_factorization(n):
    return [[int(p), int(e)] for p, e in factor(n)]


# --- arithmetic ---------------------------------------------------------------------------

def test_is_prime_vs_sage():
    rng = random.Random(1)
    nums = [rng.getrandbits(rng.randint(2, 128)) for _ in range(3000)]
    nums += [rprime(b, rng) for b in (8, 32, 64, 81, 82, 100, 127, 200) for _ in range(5)]
    # Carmichael numbers and strong pseudoprimes to several small bases
    nums += [561, 1105, 1729, 2465, 2821, 6601, 8911, 3215031751, 2152302898747,
             3474749660383, 341550071728321, 3825123056546413051,
             318665857834031151167461, 3317044064679887385961981]
    nums += [rprime(60, rng) * rprime(60, rng) for _ in range(20)]
    for n in nums:
        assert is_prime(n) == bool(sage_is_prime(n)), n


def test_iroot_and_perfect_power():
    rng = random.Random(2)
    for _ in range(500):
        n, k = rng.getrandbits(rng.randint(1, 200)), rng.randint(2, 9)
        assert iroot(n, k) == int(Integer(n).nth_root(k, truncate_mode=True)[0])
    for r, k in [(3, 2), (5, 3), (7, 4), (2 ** 61 - 1, 2), (6, 6), (10, 5), (1000003, 3)]:
        assert perfect_power(r ** k) == (r, k)
    assert perfect_power(4) == (2, 2) and perfect_power(2 ** 12) == (2, 12)
    assert perfect_power(36) == (6, 2) and perfect_power(64) == (2, 6)
    for n in (2, 3, 6, 12, 1000001, 2 * 3 ** 5, rprime(64, rng) * rprime(64, rng)):
        assert perfect_power(n) is None


def test_inv_reports_the_gcd():
    n = 101 * 103
    assert inv(5, n) * 5 % n == 1
    with pytest.raises(NotInvertible) as e:
        inv(101 * 7, n)
    assert e.value.d == 101
    with pytest.raises(NotInvertible) as e:
        inv(0, n)
    assert e.value.d == n
    xs = [3, 5, 7, 11]
    assert [x * y % n for x, y in zip(xs, batch_inv(xs, n))] == [1] * 4
    with pytest.raises(NotInvertible) as e:
        batch_inv([3, 103 * 2, 5], n)
    assert e.value.d == 103


def test_primes():
    assert primes_up_to(1000) == [int(p) for p in __import__("sage.all", fromlist=["primes"]).primes(1001)]


# --- curve arithmetic vs Sage over F_p --------------------------------------------------------

def test_weierstrass_vs_sage():
    rng = random.Random(3)
    for _ in range(40):
        p = rprime(rng.randint(10, 60), rng)
        c = C.random_weierstrass(p, rng)
        E = EllipticCurve(GF(p), [c.a, c.b])
        P = E(c.P)
        for _ in range(5):
            k = rng.randrange(1, 2 * p)
            R = C.w_mul(k, c.P, c.a, p)
            S = k * P
            assert (R is None and S.is_zero()) or R == tuple(int(t) for t in S.xy())
        Q = E.random_element()
        if not Q.is_zero():
            R = C.w_add(c.P, tuple(int(t) for t in Q.xy()), c.a, p)
            S = P + Q
            assert (R is None and S.is_zero()) or R == tuple(int(t) for t in S.xy())


@pytest.mark.parametrize("family", ["suyama", "z2z8"])
def test_montgomery_ladder_vs_sage(family):
    rng = random.Random(4)
    for _ in range(30):
        p = rprime(rng.randint(12, 64), rng)
        try:
            c = C.FAMILIES[family](p, rng)
        except C.CurveFound:
            continue
        E = EllipticCurve(GF(p), [0, c.A * c.B, 0, c.B ** 2, 0])   # (x, y) -> (B x, B^2 y)
        P = E(c.B * c.P[0], c.B ** 2 * c.P[1])
        for _ in range(5):
            k = rng.randrange(1, 4 * p)
            X, Z = C.m_mul(k, c.P[0], 1, c.a24, p)
            S = k * P
            if S.is_zero():
                assert Z % p == 0
            else:
                assert Z % p and X * inv(Z, p) * c.B % p == S.xy()[0]


@pytest.mark.parametrize("family,torsion", [("suyama", 12), ("z2z8", 16)])
def test_special_families_group_order(family, torsion):
    """Theorem 7.4.3 of C&P (Suyama, 12) and the Z/2 x Z/8 family (16): the curve order
    is divisible by the torsion for every good prime, and the point lies on the curve."""
    rng = random.Random(5)
    seen = 0
    while seen < 60:
        p = rprime(rng.randint(10, 40), rng)
        try:
            c = C.FAMILIES[family](p, rng)
        except C.CurveFound:
            continue
        x, y = c.P
        assert (c.B * y * y - (x ** 3 + c.A * x * x + x)) % p == 0
        E = EllipticCurve(GF(p), [0, c.A * c.B, 0, c.B ** 2, 0])
        assert E.order() % torsion == 0
        seen += 1


def test_curve_point_modulo_composite():
    rng = random.Random(6)
    for family in FAMILIES:
        for _ in range(10):
            n = rprime(40, rng) * rprime(50, rng)
            out, _ = solve({"op": "curve", "n": n, "family": family, "seed": rng.random()}, Options())
            cu, pt = out["curve"], out["point"]
            x, y = pt["x"], pt["y"]
            if family == "weierstrass":
                assert (y * y - x ** 3 - cu["a"] * x - cu["b"]) % n == 0
            else:
                assert (cu["B"] * y * y - x ** 3 - cu["A"] * x * x - x) % n == 0


def test_z2z8_rational_family():
    """Over Q the multiples k G give curves with torsion Z/2 x Z/8 and a point of infinite order."""
    from sage.all import QQ
    T = EllipticCurve(QQ, [C.T_A, -16])
    G = T(C.T_G)
    assert not G.has_finite_order()
    for k in (2, 3, 5):
        Zt, Yt = (k * G).xy()
        u = (8 + Yt) / (2 * (Zt - 4))
        Q = (u ** 2 + 2 * u + 2) ** 2 / (2 * u * (u + 1) * (u + 2))
        E = EllipticCurve(QQ, [0, Q ** 2 - 2, 0, 1, 0])
        assert E.torsion_subgroup().invariants() == (2, 8)
        x0 = -2 * (u + 1) ** 2 / u ** 2
        y0 = (u + 1) * (u ** 2 + 4 * u + 2) * (u ** 2 - (Zt + 2) / 2) / ((u + 2) * u ** 3)
        P = E(x0, y0)
        assert not P.has_finite_order()


# --- parameters -------------------------------------------------------------------------

def test_rho_and_levels():
    assert rho(1) == 1 and abs(rho(2) - 0.3068528) < 1e-4
    assert abs(rho(3) - 0.0486084) < 2e-4 and abs(rho(4) - 0.0049109) < 5e-5
    assert semismooth(3, 1) == pytest.approx(rho(3))
    assert semismooth(3, 2) > rho(3)
    prev = None
    for bits in range(12, 101, 4):
        lv = level(bits, "z2z8")
        assert lv.B2 == 100 * lv.B1
        if prev:
            assert lv.B1 >= prev.B1 and lv.curves >= prev.curves * 0.5
        prev = lv


@pytest.mark.parametrize("B1,B2", [(50, 5000), (130, 13000), (700, 70000), (3000, 300000)])
def test_stage2_plan_covers_every_prime(B1, B2):
    plan = stage2_plan(B1, B2)
    covered = set()
    for i, idx in enumerate(plan.giants):
        m = plan.m0 + i
        for t in idx:
            j = plan.js[t]
            covered |= {m * plan.D - j, m * plan.D + j}
    for q in primes_up_to(B2):
        if q > B1:
            assert q in covered, q


# --- factoring vs Sage's factor ---------------------------------------------------------------

def _numbers(rng):
    out = []
    for b in (10, 16, 20, 24):
        out.append(rprime(b, rng) * rprime(b, rng))                       # balanced
        out.append(rprime(b, rng) * rprime(2 * b + 10, rng))              # unbalanced
        p, q = rprime(b, rng), rprime(b + 5, rng)
        out += [p * p * q, p * q * q, p ** 3]                             # repeated
        out.append(rprime(b, rng) * rprime(b, rng) * rprime(b + 3, rng))  # several
    out += [4, 6, 8, 9, 12, 15, 25, 35, 49, 2 ** 20, 3 ** 13, 2 * 3 * 5 * 7 * 11 * 13,
            97 * 89, 101 * 103, 1009 * 1013, (2 ** 31 - 1) * (2 ** 61 - 1), 1000003 ** 2 * 101]
    return out


@pytest.mark.parametrize("family", FAMILIES)
def test_factorize_vs_sage(family):
    rng = random.Random(7)
    for n in _numbers(rng):
        out, extra = solve({"op": "factorize", "n": n, "family": family}, Options())
        assert out["factorization"] == sage_factorization(n), n
        assert out["prime"] is False and extra["complete"]


def test_factor_op_and_primes():
    rng = random.Random(8)
    for n in _numbers(rng):
        out, _ = solve({"op": "factor", "n": n}, Options())
        d = out["factor"]
        assert 1 < d < n and n % d == 0 and out["prime"] is False
    for n in [2, 3, 5, 101, 65537, rprime(64, rng), rprime(128, rng), 2 ** 127 - 1]:
        for op in ("factor", "factorize"):
            out, _ = solve({"op": op, "n": n}, Options())
            assert out["prime"] is True
            assert out.get("factor") is None
            if op == "factorize":
                assert out["factorization"] == [[n, 1]]


def test_variants_factorial_no_stage2_fixed_bounds():
    rng = random.Random(9)
    for _ in range(4):
        n = rprime(22, rng) * rprime(26, rng)
        for inp in ({"family": "weierstrass", "stage1": "factorial", "trace": True},
                    {"family": "weierstrass", "stage2": False},
                    {"family": "suyama", "stage2": False},
                    {"family": "z2z8", "B1": 400, "B2": 40000},
                    {"family": "z2z8", "factor_bits": 24}):
            out, extra = solve({"op": "factorize", "n": n, **inp}, Options())
            assert out["factorization"] == sage_factorization(n), (n, inp)
    # a curve budget that is too small: no factor, no crash
    n = rprime(40, rng) * rprime(40, rng)
    out, extra = solve({"op": "factor", "n": n, "B1": 10, "curves": 2, "stage2": False}, Options())
    assert out["factor"] is None or n % out["factor"] == 0


def test_provenance_matches_group_order():
    """The recorded curve and point really explain the factor: modulo the prime factor p
    that was found, the order of the point is B1-smooth (stage 1, with the reported prime
    the largest) or B1-smooth times one prime <= B2 (stage 2)."""
    rng = random.Random(10)
    checked = 0
    for family in FAMILIES:
        for _ in range(8):
            p, q = rprime(28, rng), rprime(30, rng)
            out, extra = solve({"op": "factor", "n": p * q, "family": family, "trial": 3}, Options())
            hit = extra["found"][-1]
            if hit["stage"] not in (1, 2):
                continue
            f = hit["factor"]
            assert f in (p, q)
            cu, pt = hit["curve"], hit["curve"]["point"]
            K = GF(f)
            if family == "weierstrass":
                E = EllipticCurve(K, [cu["a"], cu["b"]])
                P = E(pt["x"], pt["y"])
            else:
                B = cu["B"]
                E = EllipticCurve(K, [0, cu["A"] * B, 0, B ** 2, 0])
                P = E(B * pt["x"], B ** 2 * pt["y"])
            primes = [int(r) for r, _ in factor(P.order())]
            if hit["stage"] == 1:
                assert max(primes) == hit["after_prime"] <= hit["B1"]
            else:
                big = [r for r in primes if r > hit["B1"]]
                assert len(big) <= 1 and all(r <= hit["B2"] for r in big)
            checked += 1
    assert checked >= 12


def test_deterministic():
    n = 1000000007 * 998244353 * 1000003
    a = solve({"op": "factorize", "n": n}, Options())
    b = solve({"op": "factorize", "n": str(n)}, Options())
    assert a == b
    c = solve({"op": "factorize", "n": n, "seed": 5}, Options())
    assert c[0] == a[0]


# --- CLI ----------------------------------------------------------------------------------------

def test_cli_contract():
    reqs = [{"id": "a", "input": {"op": "factor", "n": 1000000007 * 1000000009}},
            {"id": "b", "input": {"n": 360}},
            {"id": "c", "input": {"n": "x"}},
            {"id": "d", "input": {"op": "nope", "n": 15}},
            {"id": "e", "input": {"n": 1}},
            {"id": "f", "input": {"n": 77, "family": "edwards"}},
            {"id": "g", "input": None}]
    text = "".join(json.dumps(r) + "\n" for r in reqs) + "not json\n"
    res = subprocess.run([sys.executable, os.path.join(REF, "main.py")], input=text,
                         capture_output=True, text=True, timeout=120, check=True)
    ans = [json.loads(line) for line in res.stdout.splitlines()]
    assert [a["id"] for a in ans] == ["a", "b", "c", "d", "e", "f", "g", None]
    assert ans[0]["output"]["factor"] in (1000000007, 1000000009)
    assert ans[0]["extra"]["found"][0]["curve"]["point"]
    assert ans[1]["output"]["factorization"] == [[2, 3], [3, 2], [5, 1]]
    assert all("error" in a for a in ans[2:])


# --- generator / verifier ---------------------------------------------------------------------

def test_generator_and_verify():
    from taskgen.capstone.gens import lenstra_ecm as G
    rng = random.Random(11)
    for shape in ("semiprime", "unbalanced", "square", "power", "multi", "prime"):
        for _ in range(4):
            v = G.generate({"shape": shape, "pbits": [12, 20], "nbits": [60, 80],
                            "op": "factor" if shape == "semiprime" else "factorize"}, rng)
            v["id"] = "t"
            n = v["input"]["n"]
            assert v["expected"]["factorization"] == sage_factorization(n)
            out, _ = solve(v["input"], Options())
            assert G.verify(v, out) is None, (v, out)
            exp = v["expected"]
            if exp["prime"]:
                assert G.verify(v, {"prime": False, "factor": 3}) is not None
                assert G.verify(v, {"prime": True}) is None
                continue
            assert G.verify(v, {"prime": True}) is not None
            assert G.verify(v, {"factorization": exp["factorization"]}) is None
            bad = [list(x) for x in exp["factorization"]]
            bad[0][1] += 1
            assert G.verify(v, {"factorization": bad}) is not None
            d = exp["factorization"][0][0]
            if v["input"]["op"] == "factor":
                assert G.verify(v, {"factor": n // d}) is None
                assert G.verify(v, {"factor": str(d)}) is None
                assert G.verify(v, {"factor": n}) is not None
                assert G.verify(v, {"factor": 1}) is not None
            else:
                assert G.verify(v, {"factor": d}) is not None
