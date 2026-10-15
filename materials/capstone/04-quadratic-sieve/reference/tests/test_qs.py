"""Quadratic sieve reference vs independent oracles (Sage built-ins, Python ints).

Seeded random inputs; corner cases (prime powers, small and repeated factors, close
factors, many factors, primes and junk input) included. Run: make test-capstones
CAPSTONE=quadratic-sieve.
"""

import json
import math
import random
import subprocess
import sys

import pytest
from sage.all import GF, Integer, factor, is_prime, legendre_symbol, matrix, next_prime, prime_range

import qs_linalg
import qs_numtheory as nt
import qsieve
from conftest import REF


def rand_prime(rng, bits):
    return int(next_prime(Integer(rng.getrandbits(bits) | (1 << (bits - 1)))))


def semiprime(rng, bits):
    while True:
        p, q = rand_prime(rng, bits // 2), rand_prime(rng, bits - bits // 2)
        if p != q:
            return p * q


# --- number theory ---------------------------------------------------------------------

def test_primes_up_to():
    for b in (0, 1, 2, 3, 100, 7919, 10 ** 5):
        assert nt.primes_up_to(b) == [int(p) for p in prime_range(b + 1)]


def test_legendre_and_sqrt_mod_prime():
    rng = random.Random(1)
    # include primes p = 1 (mod 2^k) for large k: the long branch of Tonelli--Shanks
    primes = [3, 5, 7, 13, 17, 41, 97, 257, 65537, 7681, 12289, 40961, 786433]
    primes += [rand_prime(rng, b) for b in (20, 40, 64, 100) for _ in range(5)]
    for p in primes:
        for _ in range(30):
            a = rng.randrange(p)
            assert nt.legendre(a, p) == legendre_symbol(a, p)
            if legendre_symbol(a, p) == 1:
                r = nt.sqrt_mod_prime(a, p)
                assert 0 <= r < p and r * r % p == a
            elif a:
                with pytest.raises(ValueError):
                    nt.sqrt_mod_prime(a, p)
        assert nt.sqrt_mod_prime(0, p) == 0


def test_lift_root():
    rng = random.Random(2)
    for p in (3, 5, 11, 101, 1009):
        for _ in range(20):
            n = rng.randrange(1, 10 ** 12)
            if n % p == 0 or legendre_symbol(n, p) != 1:
                continue
            r = nt.sqrt_mod_prime(n, p)
            for k in range(1, 5):
                r2 = nt.lift_root(r, n, p, k)
                assert r2 % p ** k == r and (r2 * r2 - n) % p ** (k + 1) == 0
                r = r2


def test_is_probable_prime():
    rng = random.Random(3)
    carmichael = [561, 1105, 1729, 2465, 2821, 6601, 8911, 41041, 3215031751, 3825123056546413051]
    for n in list(range(-3, 2000)) + carmichael + [rng.getrandbits(b) for b in (30, 60, 90, 130)
                                                   for _ in range(50)]:
        assert nt.is_probable_prime(n) == (n > 1 and bool(is_prime(n))), n
    for b in (40, 80, 120):
        assert nt.is_probable_prime(rand_prime(rng, b))


def test_iroot_and_perfect_power():
    rng = random.Random(4)
    for _ in range(200):
        n, k = rng.getrandbits(rng.randrange(1, 200)), rng.randrange(1, 7)
        r = nt.iroot(n, k)
        assert r == int(Integer(n).nth_root(k, truncate_mode=True)[0])
    for m, k in [(2, 90), (3, 5), (1000000007, 2), (6, 4), (35, 3), (2 ** 31 - 1, 3)]:
        assert nt.perfect_power(m ** k) == (m, k)
    for n in (2, 3, 12, 1000000016000000063, 2 ** 89 - 1):
        assert nt.perfect_power(n) is None
    assert nt.perfect_power(2 ** 12) == (2, 12)       # the largest exponent, not (64, 2)


def test_dickman_rho():
    for u, want in [(0.5, 1.0), (1, 1.0), (2, 1 - math.log(2)), (3, 0.0486083882),
                    (4, 0.0049109256), (5, 0.0003547247), (10, 2.77017e-11)]:
        assert qsieve.dickman_rho(u) == pytest.approx(want, rel=1e-3)


# --- linear algebra mod 2 ----------------------------------------------------------------

@pytest.mark.parametrize("rows,cols,density", [(10, 8, 0.5), (60, 50, 0.1), (200, 180, 0.05),
                                               (30, 30, 0.0), (40, 25, 0.9)])
def test_dependencies_vs_sage_kernel(rows, cols, density):
    rng = random.Random(rows * cols)
    rs = [sum(1 << j for j in range(cols) if rng.random() < density) for _ in range(rows)]
    deps = qs_linalg.dependencies(rs)
    m = matrix(GF(2), rows, cols, [[(r >> j) & 1 for j in range(cols)] for r in rs])
    assert len(deps) == rows - m.rank() == m.left_kernel().dimension()
    for d in deps:                                     # each is a dependency ...
        acc = 0
        for i in range(rows):
            if d >> i & 1:
                acc ^= rs[i]
        assert d and acc == 0
    if deps:                                           # ... and they are independent
        dm = matrix(GF(2), len(deps), rows, [[(d >> i) & 1 for i in range(rows)] for d in deps])
        assert dm.rank() == len(deps)
    assert len(qs_linalg.dependencies_sage(rs, cols)) == len(deps)


# --- the sieve -----------------------------------------------------------------------

def test_params_and_factor_base():
    rng = random.Random(5)
    prev = 0
    for bits in (40, 60, 80, 100, 120):
        n = semiprime(rng, bits)
        par, fb = qsieve.choose_params(n)
        assert fb[0] == 2 and len(fb) == par.fb_size and fb[-1] <= par.B
        assert all(legendre_symbol(n, p) == 1 for p in fb[1:])
        assert set(fb[1:]) == {int(p) for p in prime_range(3, par.B + 1) if legendre_symbol(n, p) == 1}
        assert par.needed == par.fb_size + 1 + qsieve.EXTRA_REL
        assert par.B > prev and par.B_theory > par.B and par.length_theory > par.expected_length > 0
        prev = par.B


def test_relations_are_correct_and_smooth():
    rng = random.Random(6)
    n = semiprime(rng, 70)
    par, fb = qsieve.choose_params(n)
    rels, st = qsieve.sieve(n, fb, par.needed, 0.5 * math.log2(par.B) + 4, 10 ** 8)
    assert len(rels) == par.needed and st.candidates >= len(rels) and st.length % qsieve.BLOCK == 0
    assert len({r.t for r in rels}) == len(rels)
    for r in rels:
        v = r.t * r.t - n
        prod = (-1) ** r.exps.get(0, 0)
        for c, e in r.exps.items():
            if c:
                prod *= fb[c - 1] ** e
        assert prod == v
        assert r.mask == sum(1 << c for c, e in r.exps.items() if e % 2)
    # compare with brute force over the first block: the log threshold (fudge) trades
    # missed smooth values (mostly ones with many small factors, which are not sieved)
    # for fewer trial divisions; with the default fudge it keeps well over half
    s = nt.iroot(n, 2)
    found = {r.t - s for r in rels if 0 <= r.t - s < qsieve.BLOCK}

    def smooth(v):
        v = abs(v)
        for p in fb:
            while v % p == 0:
                v //= p
        return v == 1
    brute = {x for x in range(qsieve.BLOCK) if smooth((s + x) ** 2 - n)}
    assert found <= brute and len(found) >= 0.5 * len(brute)


@pytest.mark.parametrize("bits", [40, 50, 60, 70, 80, 90])
def test_qs_split_semiprimes(bits):
    rng = random.Random(bits)
    for _ in range(3):
        n = semiprime(rng, bits)
        r = qsieve.qs_split(n)
        assert r.method == "qs" and 1 < r.factor < n and n % r.factor == 0
        e = r.extra
        assert e["relations"] >= e["relations_needed"] and e["matrix"] == [e["relations"], e["fb_size"] + 1]
        assert (e["x"] ** 2 - e["y"] ** 2) % n == 0 and math.gcd(e["x"] - e["y"], n) == r.factor
        assert 1 <= e["dependencies_tried"] <= e["dependencies"]


def test_trace_and_sage_linalg():
    rng = random.Random(7)
    n = semiprime(rng, 60)
    r = qsieve.qs_split(n, trace=True, linalg="sage")
    assert n % r.factor == 0 and 1 < r.factor < n
    fb = r.extra["factor_base"]
    prod_t, total = 1, {}
    for i in r.extra["dependency"]:
        t, fac = r.extra["smooth"][i]
        prod_t = prod_t * t % n
        for p, e in fac.items():
            total[p] = total.get(p, 0) + e
    assert all(e % 2 == 0 for e in total.values()) and set(total) <= {"-1", *map(str, fb)}
    assert prod_t == r.extra["x"]


def test_split_corner_cases():
    rng = random.Random(8)
    p, q = rand_prime(rng, 40), rand_prime(rng, 40)
    assert qsieve.split(p * p).method == "perfect-power"
    assert qsieve.split(p ** 3).factor == p
    assert qsieve.split((p * q) ** 2).factor == p * q            # m^2 with m composite
    assert qsieve.split(2 * p).factor == 2
    assert qsieve.split(3 * 5 * p).method == "trial-division"
    m = p * p * rand_prime(rng, 30)                                # repeated factor, not a power
    r = qsieve.split(m)
    assert r.method == "qs" and 1 < r.factor < m and m % r.factor == 0
    pc = int(next_prime(Integer(p) + 10))                          # close factors
    assert qsieve.split(p * pc).factor in (p, pc)
    for bad in (-6, 0, 1, 2, 3, 97, p):
        with pytest.raises(ValueError):
            qsieve.split(bad)


def test_factorize_vs_sage():
    rng = random.Random(9)
    cases = [2 ** 10 * 3 ** 5, 30030, rand_prime(rng, 20) ** 2 * rand_prime(rng, 25) ** 3]
    for _ in range(6):
        n = 1
        for _ in range(rng.randrange(2, 5)):
            n *= rand_prime(rng, rng.randrange(15, 35))
        cases.append(n)
    for n in cases:
        fac, splits = qsieve.factorize(n)
        assert list(fac.items()) == [(int(p), int(e)) for p, e in factor(Integer(n))]
        assert splits[0][0] == n


# --- the CLI and the vector generator ------------------------------------------------------

def test_cli_contract():
    reqs = [{"id": "a", "input": {"n": 1000000016000000063}},
            {"id": "b", "input": {"n": 97}},
            {"id": "c", "input": {"n": "junk"}},
            {"id": "d", "input": {"n": 2 ** 10 * 1000003, "full": True}}]
    text = "".join(json.dumps(r) + "\n" for r in reqs) + "not json\n"
    out = subprocess.run([sys.executable, str(REF / "main.py")], input=text, capture_output=True,
                         text=True, check=True, timeout=120).stdout.splitlines()
    ans = [json.loads(x) for x in out]
    assert [a["id"] for a in ans] == ["a", "b", "c", "d", None]
    assert ans[0]["output"]["factor"] in (1000000007, 1000000009) and ans[0]["extra"]["method"] == "qs"
    assert "error" in ans[1] and "error" in ans[2] and "error" in ans[4]
    assert ans[3]["output"]["factorization"] == [[2, 10], [1000003, 1]]


def test_generator_and_verify():
    sys.path.insert(0, str(REF.parents[3]))
    from taskgen.capstone.gens import quadratic_sieve as g

    rng = random.Random(10)
    for shape in g.SHAPES:
        for bits in (40, 60):
            v = g.generate({"bits": bits, "shape": shape}, rng)
            n = v["input"]["n"]
            assert v["expected"]["factorization"] == [[int(p), int(e)] for p, e in factor(Integer(n))]
            assert abs(n.bit_length() - bits) <= 2
            vec = {"input": v["input"], "expected": v["expected"]}
            fac = v["expected"]["factorization"]
            d = fac[0][0]
            good = {"factor": d, "factorization": fac}
            assert g.verify(vec, good) is None
            if not v["input"].get("full"):
                assert g.verify(vec, {"factor": n // d}) is None       # any non-trivial divisor
            assert g.verify(vec, {"factor": 1}) and g.verify(vec, {"factor": n})
            assert g.verify(vec, {"factor": d, "factorization": [[n, 1]]})
            assert g.verify(vec, None) and g.verify(vec, {"factor": True})
            if v["input"].get("full"):
                assert g.verify(vec, {"factor": d})                   # factorization required
