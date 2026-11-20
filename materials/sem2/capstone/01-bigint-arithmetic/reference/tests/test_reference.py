"""Tests of the bigint reference (capstone 01) against independent oracles.

* ``bigint-oracle`` (tests/oracle.c) compares the C library with GNU GMP on thousands
  of random operands per seed;
* the solver is driven through its JSON-lines protocol and compared with Python ints;
* the vector generator's instances (corner cases included) pass ``verify``, and
  ``verify`` rejects wrong answers;
* the solver binary does not link GMP.

Run: ``make test-capstones CAPSTONE=bigint-arithmetic`` (builds first), or pytest in the
capstone-c image.
"""

from __future__ import annotations

import json
import math
import random
import subprocess
from pathlib import Path

import pytest

from taskgen.capstone.gens import bigint_arithmetic as gen

REF = Path(__file__).resolve().parents[1]
BUILD = REF / "build"


@pytest.fixture(scope="session", autouse=True)
def built():
    subprocess.run(["make", "-s", "-C", str(REF)], check=True)


class Solver:
    def __init__(self):
        self.p = subprocess.Popen([str(BUILD / "bigint-solver")], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, bufsize=1)
        self.n = 0

    def raw(self, line: str) -> dict:
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())

    def ask(self, **inp) -> dict:
        self.n += 1
        enc = {k: hex(v) if isinstance(v, int) and k not in ("k", "q", "repeat", "threshold") else v
               for k, v in inp.items()}
        ans = self.raw(json.dumps({"id": self.n, "input": enc}))
        assert ans["id"] == self.n
        return ans

    def out(self, **inp) -> dict:
        ans = self.ask(**inp)
        assert "error" not in ans, ans
        return {k: int(v, 16) if isinstance(v, str) else v for k, v in ans["output"].items()}

    def close(self):
        self.p.stdin.close()
        assert self.p.wait(timeout=10) == 0


@pytest.fixture
def solver():
    s = Solver()
    yield s
    s.close()


# ------------------------------------------------------------------ the GMP oracle --

@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_library_against_gmp(seed):
    res = subprocess.run([str(BUILD / "bigint-oracle"), str(seed), "400"], capture_output=True,
                         text=True, timeout=300)
    assert res.returncode == 0, res.stdout + res.stderr
    stats = dict(kv.split("=") for kv in res.stdout.split())
    assert int(stats["failures"]) == 0 and int(stats["checks"]) > 10000
    # the rare branches of Algorithm D were exercised
    assert int(stats["addbacks"]) > 0 and int(stats["qhat_max"]) > 0


def test_solver_does_not_link_gmp():
    ldd = subprocess.run(["ldd", str(BUILD / "bigint-solver")], capture_output=True, text=True)
    assert "gmp" not in ldd.stdout
    nm = subprocess.run(["nm", str(BUILD / "bigint-solver")], capture_output=True, text=True)
    assert "__gmp" not in nm.stdout


# ------------------------------------------------------------------ the solver ------

def rnd(rng, bits):
    x = rng.getrandbits(bits) if bits else 0
    return -x if rng.random() < 0.5 else x


def test_solver_random_against_python(solver):
    rng = random.Random(2026)
    for _ in range(300):
        bits = rng.choice([0, 1, 63, 64, 65, 200, 1000, 1535, 1536, 1537, 2048, 3100, 4096])
        a, b = rnd(rng, bits), rnd(rng, rng.choice([0, 1, 64, 65, bits, 2 * bits + 1]))
        assert solver.out(op="add", a=a, b=b)["c"] == a + b
        assert solver.out(op="sub", a=a, b=b)["c"] == a - b
        assert solver.out(op="mul_school", a=a, b=b)["c"] == a * b
        assert solver.out(op="mul_karatsuba", a=a, b=b)["c"] == a * b
        assert solver.out(op="mul_karatsuba", a=a, b=b, threshold=rng.choice([2, 3, 7]))["c"] == a * b
        assert solver.out(op="sqr", a=a)["c"] == a * a
        assert solver.out(op="sqr", a=a, threshold=2)["c"] == a * a
        if b:
            o = solver.out(op="divmod", a=a, b=b)
            assert o["q"] * b + o["r"] == a and abs(o["r"]) < abs(b)
            assert o["q"] == int(abs(a) // abs(b)) * (1 if (a < 0) == (b < 0) else -1)  # truncated
            assert solver.out(op="mod", a=a, b=b)["r"] == a % abs(b)
        assert solver.out(op="gcd", a=a, b=b)["g"] == math.gcd(a, b)
        o = solver.out(op="xgcd", a=a, b=b)
        assert o["g"] == math.gcd(a, b) and a * o["x"] + b * o["y"] == o["g"]
        k = rng.choice([0, 1, 63, 64, 65, rng.randrange(0, 5000)])
        assert solver.out(op="shl", a=a, k=k)["c"] == a << k
        assert solver.out(op="shr", a=a, k=k)["c"] == a >> k            # floor, like Python


def test_solver_modular_against_python(solver):
    rng = random.Random(7)
    for _ in range(120):
        bits = rng.choice([2, 64, 65, 128, 512, 1000, 2048])
        m = rng.getrandbits(bits) | 1 | (1 << (bits - 1))
        a, b = rnd(rng, 2 * bits), rnd(rng, bits)
        assert solver.out(op="mont_mul", a=a, b=b, m=m)["c"] == a * b % m
        t = rng.randrange(0, m * m)
        o = solver.out(op="mont_redc", t=t, m=m)
        assert o["c"] == t * pow(2, -o["r_bits"], m) % m
        e = rng.getrandbits(rng.choice([0, 1, 2, 64, bits]))
        for mm in (m, m + 1, 1, 2, 1 << bits):          # odd, even (division fallback), 1, 2^k
            want = pow(a, e, mm)
            assert solver.out(op="powmod_binary", a=a, e=e, m=mm)["c"] == want
            for q in (2, 4, 8, 16, 32):
                assert solver.out(op="powmod_qary", a=a, e=e, m=mm, q=q)["c"] == want
        inv = solver.out(op="inv", a=a, m=m)["inv"]
        if math.gcd(a, m) == 1:
            assert inv == pow(a, -1, m)
        else:
            assert inv is None
    for a, e in [(0, 0), (0, 5), (1, 1000), (-1, 12345), (-3, 7), (2, 1000), (rnd(rng, 2048), 9)]:
        assert solver.out(op="pow_binary", a=a, e=e)["c"] == a ** e
        assert solver.out(op="pow_qary", a=a, e=e, q=16)["c"] == a ** e


def test_extra_and_methods(solver):
    ans = solver.ask(op="powmod_binary", a=3, e=10, m=1000)
    assert ans["extra"]["method"] == "division" and int(ans["output"]["c"], 16) == 3 ** 10 % 1000
    ans = solver.ask(op="powmod_qary", a=3, e=10, m=1001, q=4)
    assert ans["extra"]["method"] == "montgomery"
    m = (1 << 255) + 95
    ans = solver.ask(op="mont_mul", a=5, b=7, m=m)
    r = ans["extra"]["r_bits"]
    assert int(ans["extra"]["mont"], 16) == 35 * pow(2, -r, m) % m


def test_repeat_gives_the_same_answer(solver):
    a, b = (1 << 2047) + 12345, (1 << 1023) + 99
    for op in ("divmod", "mod", "mul_school", "gcd", "xgcd", "shr"):
        extra = {"k": 77} if op == "shr" else {"b": b}
        assert solver.out(op=op, a=a, repeat=1, **extra) == solver.out(op=op, a=a, repeat=50, **extra)
    m = (1 << 2047) | 1
    assert solver.out(op="mont_mul", a=a, b=b, m=m, repeat=7)["c"] == a * b % m


def test_16384_bits(solver):
    rng = random.Random(16384)
    a, b = rnd(rng, 16384), rnd(rng, 16384)
    m = rng.getrandbits(16384) | 1 | (1 << 16383)
    assert solver.out(op="mul_school", a=a, b=b)["c"] == a * b
    assert solver.out(op="mul_karatsuba", a=a, b=b)["c"] == a * b
    o = solver.out(op="divmod", a=a * b + 5, b=b)
    assert o["q"] * b + o["r"] == a * b + 5
    assert solver.out(op="gcd", a=a, b=b)["g"] == math.gcd(a, b)
    e = rng.getrandbits(256)
    assert solver.out(op="powmod_qary", a=a, e=e, m=m, q=16)["c"] == pow(a, e, m)


# ------------------------------------------------------------------ errors ----------

@pytest.mark.parametrize("line, needle", [
    ("not json", "bad JSON"),
    ('{"id": 1, "input": {"op": "add", "a": "0x1"', "bad JSON"),
    ('{"id": 1}', "expected"),
    ('[1, 2]', "expected"),
    ('{"id": 1, "input": {}}', "op"),
    ('{"id": 1, "input": {"op": "frobnicate"}}', "unknown op"),
    ('{"id": 1, "input": {"op": "add", "a": "0x1"}}', "missing field 'b'"),
    ('{"id": 1, "input": {"op": "add", "a": "0xZZ", "b": "0x1"}}', "not a hex"),
    ('{"id": 1, "input": {"op": "add", "a": "0x", "b": "0x1"}}', "not a hex"),
    ('{"id": 1, "input": {"op": "add", "a": [1], "b": "0x1"}}', "expected a hex"),
    ('{"id": 1, "input": {"op": "divmod", "a": "0x5", "b": "0x0"}}', "division by zero"),
    ('{"id": 1, "input": {"op": "mod", "a": "0x5", "b": "-0x0"}}', "division by zero"),
    ('{"id": 1, "input": {"op": "mont_mul", "a": "0x5", "b": "0x3", "m": "0x10"}}', "odd modulus"),
    ('{"id": 1, "input": {"op": "powmod_binary", "a": "0x5", "e": "-0x3", "m": "0x7"}}', "negative"),
    ('{"id": 1, "input": {"op": "powmod_binary", "a": "0x5", "e": "0x3", "m": "0x0"}}', "positive"),
    ('{"id": 1, "input": {"op": "powmod_qary", "a": "0x5", "e": "0x3", "m": "0x7", "q": 3}}', "power of two"),
    ('{"id": 1, "input": {"op": "pow_binary", "a": "0x5", "e": "0xffffffffffff"}}', "too large"),
    ('{"id": 1, "input": {"op": "shl", "a": "0x5", "k": -1}}', "'k'"),
    ('{"id": 1, "input": {"op": "shl", "a": "0x5", "k": 1.5}}', "'k'"),
    ('{"id": 1, "input": {"op": "add", "a": "0x1", "b": "0x1", "repeat": 0}}', "repeat"),
    ('{"id": 1, "input": {"op": "inv", "a": "0x1", "m": "-0x5"}}', "positive"),
    ('{"id": "x\\u00e9", "input": {"op": "add", "a": "0x1", "b": "0x1"}} trailing', "bad JSON"),
    ('[' * 100 + ']' * 100, "deep"),
])
def test_errors_do_not_crash(solver, line, needle):
    ans = solver.raw(line)
    assert needle in ans.get("error", ""), ans
    assert solver.out(op="add", a=1, b=2)["c"] == 3          # still alive


def test_ids_and_json_forms(solver):
    ans = solver.raw('{"input": {"op": "add", "a": 5, "b": "-0X1F"}, "id": {"k": [1, "\\u00e9"]}}')
    assert ans["id"] == {"k": [1, "é"]} and ans["output"]["c"] == "-0x1a"
    ans = solver.raw('  {"id": "s-001", "input": {"b": "ff", "op": "sub", "a": "+0x100"}}  ')
    assert ans["id"] == "s-001" and ans["output"]["c"] == "0x1"
    assert solver.raw('{"id": 3, "input": {"op": "add", "a": "-0x0", "b": "0x0"}}')["output"]["c"] == "0x0"


# ------------------------------------------------------------------ the generator ----

SIZES = [(256, 0.5), (1024, 0.5), (2048, 1.0), (4096, 0.5)]


def test_generated_vectors_pass(solver):
    tags = set()
    for bits, corner in SIZES:
        rng = random.Random(bits)
        for _ in range(150):
            v = gen.generate({"bits": bits, "corner": corner, "target_ms": 0.01}, rng)
            ans = solver.raw(json.dumps({"id": 0, "input": v["input"]}))
            assert "error" not in ans, (v["tags"], ans)
            assert gen.verify(v, ans["output"]) is None, (v["tags"], v["input"])
            tags.update(v["tags"])
            # the D6 corner vectors really exercise "add back" in the reference
            if "knuth-d-addback" in v["tags"]:
                assert ans["extra"]["addbacks"] >= 1
            # the expected answer itself passes verify
            assert gen.verify(v, v["expected"]) is None
    assert set(gen.OPS) <= tags
    assert {"knuth-d-addback", "knuth-d-qhat-max", "even-m", "threshold", "fib"} <= tags


def test_addback_construction():
    rng = random.Random(5)
    for nl in (3, 4, 32, 256):
        a, b = gen.addback_pair(rng, nl, 2)
        assert gen.knuth_d_stats(a, b)[0] >= 1
        a, b = gen.qhat_max_pair(rng, nl, 1)
        assert gen.knuth_d_stats(a, b)[1] >= 1


def test_verify_rejects_wrong_answers():
    v = {"input": {"op": "divmod", "a": "0x64", "b": "-0x7"}, "expected": {}}
    assert gen.verify(v, {"q": "-0xe", "r": "0x2"}) is None        # truncated
    assert gen.verify(v, {"q": "-0xf", "r": "-0x5"}) is None       # floored
    assert gen.verify(v, {"q": "-0xd", "r": "0x9"})                # |r| >= |b|
    assert gen.verify(v, {"q": "0xe", "r": "0x2"})
    assert gen.verify(v, {"q": "-0xe"})                            # missing r
    v = {"input": {"op": "xgcd", "a": "0xf", "b": "0x6"}, "expected": {}}
    assert gen.verify(v, {"g": "0x3", "x": "0x1", "y": "-0x2"}) is None
    assert gen.verify(v, {"g": "0x3", "x": "-0x1", "y": "0x3"}) is None   # other Bezout pair
    assert gen.verify(v, {"g": "0x3", "x": "0x1", "y": "0x2"})
    v = {"input": {"op": "inv", "a": "0x6", "m": "0x9"}, "expected": {}}
    assert gen.verify(v, {"inv": None}) is None
    assert gen.verify(v, {"inv": "0x3"})
    v = {"input": {"op": "shr", "a": "-0x5", "k": 1}, "expected": {}}
    assert gen.verify(v, {"c": "-0x3"}) is None and gen.verify(v, {"c": "-0x2"}) is None
    assert gen.verify(v, {"c": "-0x1"})
    v = {"input": {"op": "mont_redc", "t": "0x5", "m": "0x7"}, "expected": {}}
    assert gen.verify(v, {"c": hex(5 * pow(2, -3, 7) % 7), "r_bits": 3}) is None   # any R = 2^k > m
    assert gen.verify(v, {"c": hex(5 * pow(2, -64, 7) % 7), "r_bits": 3})
    assert gen.verify(v, {"c": "0x1", "r_bits": 2})                 # 2^2 < m
    v = {"input": {"op": "add", "a": "0x1", "b": "0x1"}, "expected": {}}
    assert gen.verify(v, {"c": "0x2"}) is None and gen.verify(v, {"c": 2}) is None
    assert gen.verify(v, {"c": "0x3"}) and gen.verify(v, {"c": "two"}) and gen.verify(v, None)
