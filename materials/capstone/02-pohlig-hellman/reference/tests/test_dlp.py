"""Tests of the Pohlig--Hellman reference against Sage's oracles (discrete_log, factor,
multiplicative_order, crt) on seeded random instances, plus the corner cases.

Run: ``make test-capstones CAPSTONE=pohlig-hellman``.
"""

from __future__ import annotations

import json
import math
import random
import subprocess
import sys
from pathlib import Path

import pytest
from sage.all import CRT_list, GF, discrete_log, factor as sage_factor, is_prime, next_prime

REF = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REF))

import dlp  # noqa: E402
from taskgen.capstone.gens import pohlig_hellman as gen  # noqa: E402


def sage_factors(n: int) -> list[tuple[int, int]]:
    return [(int(q), int(e)) for q, e in sage_factor(n)]


def instance(bits: int, rng: random.Random, qmax: int = 24):
    """A random instance with p - 1 B-smooth (via the capstone's generator)."""
    v = gen.generate({"bits": bits, "qmax_bits": qmax}, rng)
    i = v["input"]
    return i["p"], i["g"], i["h"], [tuple(qe) for qe in i["factors"]], v


# --- level 1 -----------------------------------------------------------------------------

@pytest.mark.parametrize("seed", range(20))
def test_prime_order_brute_and_bsgs(seed):
    rng = random.Random(seed)
    q = int(next_prime(rng.randrange(2, 1 << rng.choice((5, 12, 20)))))
    # p = k q + 1 prime, g of order q
    k = 2
    while not is_prime(k * q + 1):
        k += 2 if q > 2 else 1
    p = k * q + 1
    g = pow(int(GF(p).multiplicative_generator()), k, p)
    x = rng.randrange(q)
    h = pow(g, x, p)
    assert dlp.dlog_bsgs(g, h, q, p) == x
    if q < 5000:
        assert dlp.dlog_brute(g, h, q, p) == x
    assert int(discrete_log(GF(p)(h), GF(p)(g), ord=q)) == x


def test_bsgs_tiny_orders():
    p = 23
    for g in range(2, p):
        n = int(GF(p)(g).multiplicative_order())
        for x in range(n):
            h = pow(g, x, p)
            assert dlp.dlog_bsgs(g, h, n, p) == x      # BSGS is fine for any cyclic order
            assert dlp.dlog_brute(g, h, n, p) == x


def test_not_in_subgroup():
    p, g = 23, 2                                      # ord 2 = 11; 5 is a non-residue
    with pytest.raises(dlp.DlogError):
        dlp.dlog_bsgs(g, 5, 11, p)
    with pytest.raises(dlp.DlogError):
        dlp.dlog_brute(g, 5, 11, p)
    with pytest.raises(dlp.DlogError):
        dlp.pohlig_hellman(p, g, 5, [(2, 1), (11, 1)])


# --- level 2 -----------------------------------------------------------------------------

@pytest.mark.parametrize("q,e", [(2, 1), (2, 12), (3, 9), (5, 6), (7, 3), (101, 3), (65537, 2)])
@pytest.mark.parametrize("reduce", [True, False])
def test_prime_power(q, e, reduce):
    rng = random.Random(q * 100 + e)
    n = q ** e
    k = 2
    while not is_prime(k * n + 1):
        k += 2 if q != 2 else 1
    p = k * n + 1
    g = pow(int(GF(p).multiplicative_generator()), k, p)
    for x in (0, 1, n - 1, rng.randrange(n)):
        h = pow(g, x, p)
        sp = dlp.dlog_prime_power(g, h, q, e, p, reduce=reduce)
        assert sp.x == x
        if reduce:
            assert len(sp.digits) == e and all(0 <= d < q for d in sp.digits)
            assert sum(d * q ** i for i, d in enumerate(sp.digits)) == x


# --- level 3 -----------------------------------------------------------------------------

@pytest.mark.parametrize("seed", range(40))
def test_pohlig_hellman_vs_sage(seed):
    rng = random.Random(1000 + seed)
    p, g, h, fs, v = instance(rng.choice((20, 32, 48, 64)), rng)
    assert fs == sage_factors(p - 1)
    sol = dlp.pohlig_hellman(p, g, h, fs)
    F = GF(p)
    n = int(F(g).multiplicative_order())
    assert sol.order == n and sol.order_factors == sage_factors(n)
    assert sol.x == int(discrete_log(F(h), F(g), ord=n)) == v["expected"]["x"]
    # the recorded congruence system is the one the CRT glues
    res = [r for r, _ in sol.extra()["congruences"]]
    mods = [m for _, m in sol.extra()["congruences"]]
    assert math.prod(mods) == n
    assert sol.x == (int(CRT_list(res, mods)) if mods else 0)
    for (r, m), s in zip(sol.extra()["congruences"], sol.subproblems):
        assert pow(s.g, r, p) == s.h and m == s.q ** s.e


@pytest.mark.parametrize("prime_method", ["brute", "bsgs", "auto"])
@pytest.mark.parametrize("reduce", [True, False])
def test_methods_agree(prime_method, reduce):
    rng = random.Random(7)
    for _ in range(10):
        p, g, h, fs, _ = instance(28, rng, qmax=14)
        assert pow(g, dlp.pohlig_hellman(p, g, h, fs, prime_method, reduce).x, p) == h


def test_corner_cases():
    p = 1000003                                       # p - 1 = 2 * 3 * 166667
    fs = sage_factors(p - 1)
    assert dlp.pohlig_hellman(p, 1, 1, fs).x == 0     # g = 1: order 1
    assert dlp.pohlig_hellman(p, p - 1, p - 1, fs).x == 1   # order 2
    assert dlp.pohlig_hellman(p, p - 1, 1, fs).x == 0
    g = int(GF(p).multiplicative_generator())
    assert dlp.pohlig_hellman(p, g, 1, fs).x == 0     # h = 1
    assert dlp.pohlig_hellman(p, g, pow(g, -1, p), fs).x == p - 2
    assert dlp.pohlig_hellman(p, g + p, g, fs).x == 1  # unreduced g
    assert dlp.pohlig_hellman(3, 2, 2, [(2, 1)]).x == 1
    assert dlp.pohlig_hellman(2, 1, 1, []).x == 0       # the trivial group
    with pytest.raises(dlp.DlogError):
        dlp.pohlig_hellman(p, 0, 1, fs)


def test_crt():
    rng = random.Random(3)
    for _ in range(50):
        ms = [int(next_prime(rng.randrange(2, 10 ** 6))) ** rng.randint(1, 3) for _ in range(4)]
        if len({math.gcd(a, b) for a in ms for b in ms if a != b} - {1}):
            continue
        rs = [rng.randrange(m) for m in ms]
        assert dlp.crt(rs, ms) == int(CRT_list(rs, ms))


# --- factorization fallback --------------------------------------------------------------

@pytest.mark.parametrize("seed", range(15))
def test_factor_vs_sage(seed):
    rng = random.Random(seed)
    n = math.prod(int(next_prime(rng.randrange(2, 1 << rng.choice((8, 20, 32)))))
                  ** rng.randint(1, 3) for _ in range(rng.randint(1, 4)))
    assert dlp.factor(n) == sage_factors(n)
    p, g, h, fs, _ = instance(60, rng, qmax=30)
    assert dlp.factor(p - 1) == fs
    sol = dlp.pohlig_hellman(p, g, h)                 # no factorization in the input
    assert sol.factorization == "solver" and pow(g, sol.x, p) == h


def test_is_probable_prime():
    for n in range(-5, 3000):
        assert dlp.is_probable_prime(n) == (n > 1 and bool(is_prime(n)))
    for n in (561, 41041, 3215031751, 3825123056546413051, 2 ** 89 - 1, 2 ** 89 + 1):
        assert dlp.is_probable_prime(n) == bool(is_prime(n))


# --- the CLI (JSON-lines contract) -------------------------------------------------------

def run_cli(lines: list[str]) -> list[dict]:
    out = subprocess.run([sys.executable, str(REF / "solver.py")], input="\n".join(lines) + "\n",
                         capture_output=True, text=True, check=True, timeout=120).stdout
    return [json.loads(x) for x in out.splitlines()]


def test_cli_contract():
    rng = random.Random(11)
    p, g, h, fs, v = instance(40, rng)
    reqs = [
        {"id": "a", "input": {"p": p, "g": g, "h": h, "factors": fs}},
        {"id": "b", "input": {"p": str(p), "g": str(g), "h": str(h)}},       # no factors, strings
        {"id": "c", "input": {"p": p, "g": g, "h": h, "factors": fs,
                              "prime_method": "brute", "prime_power_method": "direct"}},
        {"id": "d", "input": {"p": p + 1, "g": 2, "h": 3}},                 # p not prime
        {"id": "e", "input": {"p": p, "g": g, "h": h, "factors": [[2, 1]]}},  # wrong factors
        {"id": "f", "input": {"p": 23, "g": 2, "h": 5}},                    # no solution
        {"id": "g", "input": {"g": 2}},
    ]
    lines = [json.dumps(r) for r in reqs] + ["not json"]
    ans = run_cli(lines)
    assert [a["id"] for a in ans] == ["a", "b", "c", "d", "e", "f", "g", None]
    for a in ans[:3]:
        assert gen.verify(v, a["output"]) is None and a["output"]["x"] == v["expected"]["x"]
    ex = ans[0]["extra"]
    assert ex["order"] == v["expected"]["order"] and ex["factorization"] == "input"
    assert ans[1]["extra"]["factorization"] == "solver"
    assert all("error" in a for a in ans[3:])


# --- the generator / verifier ------------------------------------------------------------

def test_generator_shapes_and_verify():
    rng = random.Random(5)
    for shape in gen.SHAPES:
        for kind in gen.BASES:
            v = gen.generate({"bits": 56, "qmax_bits": 24, "shapes": [shape], "bases": [kind]}, rng)
            i, e = v["input"], v["expected"]
            assert i["p"].bit_length() == 56 and is_prime(i["p"])
            assert all(q.bit_length() <= 24 for q, _ in i["factors"])
            assert shape in v["tags"] and int(GF(i["p"])(i["g"]).multiplicative_order()) == e["order"]
            assert gen.verify(v, {"x": e["x"]}) is None
            assert gen.verify(v, {"x": e["x"] + 3 * e["order"]}) is None    # any correct x
            if e["order"] > 1:
                assert gen.verify(v, {"x": e["x"] + 1}) is not None
            assert gen.verify(v, {"x": "abc"}) is not None and gen.verify(v, None) is not None
    v = gen.generate({"bits": 40, "qmax_bits": 20, "xs": ["zero"]}, rng)
    assert v["input"]["h"] == 1 and v["expected"]["x"] == 0 and "h-one" in v["tags"]
