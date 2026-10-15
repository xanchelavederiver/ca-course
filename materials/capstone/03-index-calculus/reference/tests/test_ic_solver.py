"""The index-calculus reference against Sage's discrete logarithm (PARI znlog)."""

import json
import random
import subprocess
import sys
from pathlib import Path

import pytest
from sage.all import Mod, next_prime

from icalc import linalg, nt, params
from icalc.relations import FactorBase, collect
from icalc.solver import InputError, solve

REF = Path(__file__).resolve().parents[1]
RNG = random.Random(314159)


def rand_prime(bits):
    return int(next_prime(RNG.getrandbits(bits) | (1 << (bits - 1))))


def check(p, g, h):
    out, extra = solve(p, g, h)
    x = out["x"]
    want = int(Mod(h, p).log(Mod(g, p)))           # the oracle
    n = int(Mod(g, p).multiplicative_order())
    assert x is not None and pow(g, x, p) == h % p, (p, g, h, x)
    assert x % n == want % n and 0 <= x < n
    return extra


def test_relations_hold():
    p = rand_prime(40)
    f = nt.factorize(p - 1)
    gamma = nt.primitive_root(p, f)
    fb = FactorBase(nt.primes_up_to(300), p)
    rels, trials = collect(p, gamma, p - 1, fb, 50, random.Random(1))
    assert len(rels) == 50 and trials >= 50
    for k, fac in rels:
        prod = 1
        for i, e in fac.items():
            prod *= fb.primes[i] ** e
        assert pow(gamma, k, p) == prod


def test_linalg_logs_are_correct():
    for bits in (24, 36, 48):
        p = rand_prime(bits)
        f = nt.factorize(p - 1)
        gamma = nt.primitive_root(p, f)
        par = params.choose(p)
        fb = FactorBase(nt.primes_up_to(par["B"]), p)
        params.finish(par, len(fb.primes))
        rels, _ = collect(p, gamma, p - 1, fb, par["relations_needed"], random.Random(bits))
        logs, info = linalg.solve(rels, len(fb.primes), p - 1, f)
        known = [(q, x) for q, x in zip(fb.primes, logs) if x is not None]
        assert len(known) >= len(fb.primes) // 2
        for q, x in known:                           # vs the oracle, not just gamma^x = q
            assert x == int(Mod(q, p).log(Mod(gamma, p)))
        assert info["core_rows"] + info["singletons"] == len(rels)


def test_prune_singletons():
    rows = [{0: 1, 1: 1}, {0: 2, 2: 1}, {0: 1, 1: 3}, {3: 1, 2: 1}]
    core, removed = linalg.prune_singletons(rows)
    # column 3 is a singleton (row 3); then column 2 (row 1); the core is rows 0 and 2
    assert core == [0, 2] and removed == [(3, 3), (1, 2)]


@pytest.mark.parametrize("bits", [12, 16, 20, 28, 36, 44, 52])
def test_random_generators(bits):
    for _ in range(3):
        p = rand_prime(bits)
        f = nt.factorize(p - 1)
        g = nt.primitive_root(p, f)
        g = pow(g, RNG.choice([q for q in range(1, 50) if all(q % r for r, _ in f.items())]), p)
        check(p, g, RNG.randrange(1, p))


@pytest.mark.parametrize("bits", [14, 24, 40])
def test_non_generators(bits):
    for _ in range(3):
        p = rand_prime(bits)
        f = nt.factorize(p - 1)
        gamma = nt.primitive_root(p, f)
        for q in f:                                  # g of index q, g of order q
            for g in (pow(gamma, q, p), pow(gamma, (p - 1) // q, p)):
                check(p, g, pow(g, RNG.randrange(p), p))


def test_vectors_of_the_generator():
    from taskgen.capstone.gens import index_calculus as gen

    for bits in (10, 16, 24, 32, 40):
        for i in range(6):
            v = gen.generate({"bits": bits}, random.Random(1000 * bits + i))
            out, _ = solve(**v["input"])
            assert gen.verify(v, out) is None, v


def test_safe_prime_and_prime_power():
    # p = 2q + 1: the system is solved modulo 2 and a 40-bit q
    q = rand_prime(40)
    while not nt.is_probable_prime(2 * q + 1):
        q = int(next_prime(q))
    p = 2 * q + 1
    check(p, nt.primitive_root(p, {2: 1, q: 1}), RNG.randrange(2, p))
    # 2^24 | p - 1: the system modulo a large power of 2
    k = 2 ** 24
    m = next(m for m in range(2 ** 17 + 1, 2 ** 20, 2) if nt.is_probable_prime(k * m + 1))
    p = k * m + 1
    check(p, nt.primitive_root(p, nt.factorize(p - 1)), RNG.randrange(2, p))
    # 3^15 | p - 1
    k = 2 * 3 ** 15
    m = next(m for m in range(2 ** 16, 2 ** 20) if nt.is_probable_prime(k * m + 1))
    p = k * m + 1
    check(p, nt.primitive_root(p, nt.factorize(p - 1)), RNG.randrange(2, p))


def test_corner_cases():
    p = rand_prime(30)
    g = nt.primitive_root(p, nt.factorize(p - 1))
    assert solve(p, g, 1)[0] == {"x": 0}               # h = 1
    assert solve(p, g, g)[0] == {"x": 1}               # h = g
    assert solve(p, g, pow(g, -1, p))[0] == {"x": p - 2}
    assert solve(p, p - 1, p - 1)[0] == {"x": 1}       # g = -1 of order 2
    assert solve(p, p - 1, 1)[0] == {"x": 0}
    assert solve(p, 1, 1)[0] == {"x": 0}
    assert solve(p, 1, 5)[0] == {"x": None}            # h not in <g>
    sq = pow(g, 2, p)
    assert solve(p, sq, g)[0] == {"x": None}           # a non-residue is not a power of a square
    h = RNG.randrange(2, p)
    assert pow(g, solve(p, g + p, h + 3 * p)[0]["x"], p) == h   # inputs are reduced mod p
    for p in (2, 3, 5, 7, 11, 13):
        for g in range(1, p):
            for h in range(1, p):
                out, _ = solve(p, g, h)
                if out["x"] is None:
                    assert all(pow(g, x, p) != h for x in range(p))
                else:
                    assert pow(g, out["x"], p) == h


def test_bad_input():
    for p, g, h in [(15, 2, 3), (1, 1, 1), (101, 0, 3), (101, 3, 0), (101, 3, 101)]:
        with pytest.raises(InputError):
            solve(p, g, h)


def test_extra_records_the_steps():
    p = rand_prime(40)
    g = nt.primitive_root(p, nt.factorize(p - 1))
    _, extra = solve(p, g, RNG.randrange(2, p))
    par = extra["params"]
    assert par["B"] > 2 and par["relations_needed"] > extra["factor_base_size"]
    assert extra["relations_found"] >= par["relations_needed"]
    assert extra["gamma"] == g and "individual_g" not in extra
    ih = extra["individual_h"]
    prod = 1
    for q, e in ih["factors"].items():
        prod *= int(q) ** e
    assert prod == ih["residue"]
    for r in extra["relations_sample"]:
        prod = 1
        for q, e in r["factors"].items():
            prod *= int(q) ** e
        assert pow(g, r["k"], p) == prod


def test_cli():
    p = rand_prime(32)
    g = nt.primitive_root(p, nt.factorize(p - 1))
    h = RNG.randrange(2, p)
    lines = [json.dumps({"id": "a", "input": {"p": p, "g": g, "h": h}}), "not json",
             json.dumps({"id": "b", "input": {"p": 15, "g": 2, "h": 3}}),
             json.dumps({"id": "c", "input": {"p": p, "g": g}}),
             json.dumps({"id": "d", "input": {"p": p, "g": g, "h": h, "B": 500, "seed": 7}})]
    res = subprocess.run([sys.executable, str(REF / "main.py")], input="\n".join(lines) + "\n",
                         capture_output=True, text=True, timeout=300, check=True)
    out = [json.loads(s) for s in res.stdout.splitlines()]
    assert [o["id"] for o in out] == ["a", None, "b", "c", "d"]
    assert pow(g, out[0]["output"]["x"], p) == h and "params" in out[0]["extra"]
    assert "error" in out[1] and "error" in out[2] and "error" in out[3]
    assert pow(g, out[4]["output"]["x"], p) == h and out[4]["extra"]["params"]["B"] == 500


def test_trial_division_mode():
    p = rand_prime(36)
    g = nt.primitive_root(p, nt.factorize(p - 1))
    h = RNG.randrange(2, p)
    a, ea = solve(p, g, h, smooth="trial")
    b, eb = solve(p, g, h)
    assert a == b and pow(g, a["x"], p) == h
    assert ea["relations_sample"] == eb["relations_sample"]   # same relations, other test
    with pytest.raises(ValueError):
        solve(p, g, h, smooth="sieve")
