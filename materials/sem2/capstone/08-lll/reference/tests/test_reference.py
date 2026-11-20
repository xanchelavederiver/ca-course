"""The LLL reference against Sage (the oracle) on seeded random inputs and corner cases.

Oracles: Sage's exact ``gram_schmidt`` over QQ (mu, |b*_i|^2), ``hermite_form`` (same
lattice), ``rank``, fpLLL's ``LLL`` (only to compute the true minima of 2-dim lattices),
and the planted keys / plaintexts of the toy cryptosystems.
"""

import json
import random
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest
from sage.all import QQ, ZZ, matrix

from crypto import congruential_attack, knapsack_attack
from gauss import gauss_reduce
from lattice import DependentVectors, check_reduced, gram_schmidt, lll, lll_generators, parse_delta
from taskgen.capstone.gens import lll as gen

MAIN = Path(__file__).resolve().parents[1] / "main.py"
DELTAS = ["3/4", "99/100", "1", "26/100"]


def rand_basis(rng, n, m, bits):
    while True:
        B = [[rng.randrange(-(1 << bits), 1 << bits) for _ in range(m)] for _ in range(n)]
        if matrix(ZZ, B).rank() == n:
            return B


def knap_basis(rng, n, bits):
    return [[int(i == j) for j in range(n)] + [rng.getrandbits(bits)] for i in range(n)]


def sage_reduced(rows, delta) -> bool:
    """Exact delta-LLL-reducedness (eta = 1/2) from Sage's rational Gram--Schmidt."""
    M = matrix(QQ, rows)
    G, mu = M.gram_schmidt()
    d = QQ(Fraction(delta).numerator) / Fraction(delta).denominator
    n = M.nrows()
    Bs = [G.row(i) * G.row(i) for i in range(n)]
    return (all(abs(mu[i, j]) <= QQ(1) / 2 for i in range(n) for j in range(i))
            and all(Bs[k] >= (d - mu[k, k - 1] ** 2) * Bs[k - 1] for k in range(1, n)))


def same_lattice(a, b) -> bool:
    return (matrix(ZZ, a).hermite_form(include_zero_rows=False)
            == matrix(ZZ, b).hermite_form(include_zero_rows=False))


# --- Gram--Schmidt and the check ------------------------------------------------------------

@pytest.mark.parametrize("seed", range(10))
def test_integral_gso_matches_sage(seed):
    rng = random.Random(seed)
    n = rng.randrange(1, 9)
    B = rand_basis(rng, n, n + rng.randrange(3), rng.choice([4, 20, 60]))
    g = gram_schmidt(B)
    G, mu = matrix(QQ, B).gram_schmidt()
    for i in range(n):
        assert g.B(i) == Fraction(str(G.row(i) * G.row(i)))
        for j in range(i):
            assert g.mu(i, j) == Fraction(str(mu[i, j]))


@pytest.mark.parametrize("seed", range(20))
def test_check_matches_sage(seed):
    rng = random.Random(100 + seed)
    n = rng.randrange(2, 8)
    delta = rng.choice(DELTAS)
    B = rand_basis(rng, n, n, 12)
    if seed % 2:                      # half of them reduced by Sage/NTL (exact)
        B = [list(map(int, r)) for r in matrix(ZZ, B).LLL(algorithm="NTL:LLL", fp=None, delta=0.99)]
    res = check_reduced(B, delta)
    assert res["reduced"] == sage_reduced(B, delta)
    assert res["independent"]


def test_check_corner_cases():
    # mu_21 = 1/2 exactly satisfies the size condition; -1/2 too
    assert check_reduced([[2, 0], [1, 5]])["size_reduced"]
    assert check_reduced([[2, 0], [-1, 5]])["size_reduced"]
    assert not check_reduced([[2, 0], [2, 5]])["size_reduced"]
    # Lovász with equality holds (>=): b1 = (2, 0), b2 = (1, 1) has mu = 1/2, B_1 = 4,
    # B_2 = 1, and 1 >= (delta - 1/4) 4 iff delta <= 1/2
    assert check_reduced([[2, 0], [1, 1]], "1/2")["lovasz"]
    assert not check_reduced([[2, 0], [1, 1]], "51/100")["lovasz"]
    dep = check_reduced([[1, 2], [2, 4]])
    assert not dep["independent"] and not dep["reduced"]
    assert check_reduced([[5, 7, 1]])["reduced"]          # one vector is always reduced
    with pytest.raises(ValueError):
        parse_delta("1/4")
    with pytest.raises(ValueError):
        parse_delta("1.01")
    assert parse_delta(0.99) == Fraction(99, 100)


# --- LLL ------------------------------------------------------------------------------

@pytest.mark.parametrize("seed", range(24))
def test_lll_random(seed):
    rng = random.Random(1000 + seed)
    n = rng.choice([2, 3, 5, 8, 12, 16])
    delta = rng.choice(DELTAS[:3])
    kind = seed % 3
    if kind == 0:
        B = rand_basis(rng, n, n + rng.randrange(3), rng.choice([8, 40, 120]))
    elif kind == 1:
        B = knap_basis(rng, n, rng.choice([20, 80, 200]))
    else:   # a reduced basis hidden by a unimodular transformation
        R = rand_basis(rng, n, n, 3)
        B = gen._scramble(R, rng, 60)
    red, st = lll(B, delta)
    assert sage_reduced(red, delta)
    assert same_lattice(red, B)
    assert st.iterations >= st.swaps
    # the first vector obeys the LLL bound |b_1|^2 <= (1/(delta - 1/4))^(n-1) lambda_1^2;
    # with Sage's LLL as a proxy for lambda_1 (a valid upper bound for the check)
    s = matrix(ZZ, B).LLL(delta=0.99).row(0)
    alpha = 1 / (Fraction(delta) - Fraction(1, 4))
    assert sum(x * x for x in red[0]) <= alpha ** (n - 1) * int(s * s)


def test_lll_already_reduced_is_unchanged():
    rng = random.Random(7)
    B = [list(map(int, r)) for r in
         matrix(ZZ, rand_basis(rng, 10, 10, 30)).LLL(algorithm="NTL:LLL", fp=None, delta=0.99)]
    assert check_reduced(B, "99/100")["reduced"]
    red, st = lll(B, "99/100")
    assert red == B and st.swaps == 0 and st.size_reductions == 0


def test_lll_trace_and_dependent_error():
    red, st = lll([[1, 0, 0, 1345], [0, 1, 0, 35], [0, 0, 1, 154]], "3/4", trace=True)
    assert st.trace[-1]["final"] and st.trace[-1]["basis"] == red
    assert len(st.trace) == st.swaps + 1
    with pytest.raises(DependentVectors):
        lll([[1, 2, 3], [2, 4, 6]])


@pytest.mark.parametrize("seed", range(16))
def test_lll_generators_dependent(seed):
    """MLLL by the embedding: dependent, rank-deficient, zero and repeated vectors."""
    rng = random.Random(2000 + seed)
    n = rng.randrange(2, 9)
    kind = seed % 4
    B = rand_basis(rng, n, n, rng.choice([4, 20, 50]))
    if kind == 0:
        c = [rng.randrange(-5, 6) for _ in range(n)]
        B.append([sum(ci * r[j] for ci, r in zip(c, B)) for j in range(n)])
    elif kind == 1:
        B = [list(map(int, r)) for r in matrix(ZZ, [[rng.randrange(-9, 10) for _ in range(2)]
                                                    for _ in range(n)]) * matrix(ZZ, B[:2])]
    elif kind == 2:
        B.insert(rng.randrange(n + 1), [0] * n)
    else:
        B.append(list(B[rng.randrange(n)]))
    rng.shuffle(B)
    red, extra = lll_generators(B, "99/100")
    assert len(red) == matrix(ZZ, B).rank() == extra["rank"]
    assert same_lattice(red, B)
    assert sage_reduced(red, "99/100")
    # the relations returned are integer relations of the generators
    for rel in extra.get("relations", []):
        assert all(sum(c * r[j] for c, r in zip(rel, B)) == 0 for j in range(len(B[0])))


def test_lll_generators_trivial():
    assert lll_generators([[0, 0], [0, 0]])[0] == []
    assert lll_generators([[6, 4], [9, 6]])[0] in ([[3, 2]], [[-3, -2]])
    assert lll_generators([[-7]])[0] == [[-7]]


# --- Gauss ----------------------------------------------------------------------------

def minima(B):
    L = [list(map(int, r)) for r in matrix(ZZ, B).LLL(delta=0.99)]
    vs = [[a * x + c * y for x, y in zip(*L)] for a in range(-3, 4) for c in range(-3, 4)
          if (a, c) != (0, 0)]
    return min(sum(x * x for x in v) for v in vs)


@pytest.mark.parametrize("seed", range(20))
def test_gauss_random(seed):
    rng = random.Random(3000 + seed)
    m = 2 if seed % 4 else 3
    B = rand_basis(rng, 2, m, rng.choice([4, 30, 100, 300]))
    if seed % 2:
        B = gen._scramble(rand_basis(rng, 2, m, 6), rng, 200)
    red, extra = gauss_reduce(B)
    v1, v2 = red
    n1, n2 = sum(x * x for x in v1), sum(x * x for x in v2)
    assert n1 <= n2 and 2 * abs(sum(x * y for x, y in zip(v1, v2))) <= n1
    assert n1 == minima(B)
    assert same_lattice(red, B)
    assert extra["iterations"] == len(extra["trace"])


def test_gauss_hps_example_and_degenerate():
    red, _ = gauss_reduce(gen.HPS_GAUSS)
    assert red == [[2280, -1001], [-1324, -2376]]       # HPS 2nd ed., Example 7.67
    assert gauss_reduce([[6, 4], [9, 6]])[0] in ([[3, 2]], [[-3, -2]])   # collinear: Euclid
    assert gauss_reduce([[0, 0], [5, 1]])[0] == [[5, 1]]
    assert gauss_reduce([[0, 0], [0, 0]])[0] == []
    with pytest.raises(ValueError):
        gauss_reduce([[1, 2], [3, 4], [5, 6]])


# --- the cryptosystems and the generator/verifier ---------------------------------------------

@pytest.mark.parametrize("op,params", [
    ("congruential", {"op": "congruential", "bits": [40, 160, 600]}),
    ("knapsack", {"op": "knapsack", "n": 12}),
    ("knapsack", {"op": "knapsack", "n": 28}),
    ("gauss", {"op": "gauss"}),
    ("check", {"op": "check", "dims": [1, 6], "deltas": DELTAS}),
    ("lll", {"op": "lll", "dims": [2, 8], "kinds": ["dependent", "rank_deficient", "zero_vector",
                                                   "duplicate", "nearly_dependent", "dim1",
                                                   "delta1", "delta_low", "qary"]}),
])
def test_generated_vectors_are_solved(op, params):
    from main import solve

    for i in range(8):
        v = gen.generate(params, random.Random(f"{op}{i}"))
        out, extra = solve(v["input"])
        assert gen.verify(v, out) is None, (v["tags"], out)


def test_verify_rejects_wrong_answers():
    v = gen.generate({"op": "lll", "n": 6, "bits": [20]}, random.Random(1))
    good = lll(v["input"]["basis"], v["input"]["delta"])[0]
    assert gen.verify(v, {"basis": good}) is None
    assert "same lattice" in gen.verify(v, {"basis": [[2 * x for x in good[0]]] + good[1:]})
    assert "reduced" in gen.verify(v, {"basis": v["input"]["basis"]}) or \
        check_reduced(v["input"]["basis"], v["input"]["delta"])["reduced"]
    w = gen.generate({"op": "knapsack", "n": 10}, random.Random(2))
    assert gen.verify(w, {"x": [1 - b for b in w["expected"]["x"]]}) is not None
    c = gen.generate({"op": "congruential", "bits": [64]}, random.Random(3))
    out, _ = congruential_attack(c["input"])
    assert gen.verify(c, {**out, "m": out["m"] + 1}) is not None


def test_attacks_bad_input():
    with pytest.raises(ValueError):
        knapsack_attack({"M": [], "S": 1})
    with pytest.raises(ValueError):
        congruential_attack({"q": 10, "h": 20, "e": 1})


def test_cli_json_lines():
    reqs = [{"id": "a", "input": {"op": "gauss", "basis": gen.HPS_GAUSS}},
            {"id": "b", "input": {"op": "lll", "basis": [[1, 2], [3, 4]], "delta": "1/5"}},
            {"id": "c", "input": {"op": "check", "basis": [[1, 0], [0, 1]]}},
            {"id": "d", "input": "garbage"}]
    p = subprocess.run([sys.executable, str(MAIN)], input="".join(json.dumps(r) + "\n" for r in reqs),
                       capture_output=True, text=True, timeout=60, check=True)
    ans = [json.loads(line) for line in p.stdout.splitlines()]
    assert [a["id"] for a in ans] == ["a", "b", "c", "d"]
    assert ans[0]["output"]["basis"] == [[2280, -1001], [-1324, -2376]]
    assert "delta" in ans[1]["error"]
    assert ans[2]["output"]["reduced"] is True and "mu" in ans[2]["extra"]
    assert "error" in ans[3]
