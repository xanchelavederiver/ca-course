"""Capstone 8 (LLL): lattice-reduction instances and their verifier.

Every vector has ``input.op`` (the operation of the reference CLI); ``params`` of a size
class (bench/config.yaml) choose the op and the kinds of instances::

    op: lll                 # gauss | check | lll | congruential | knapsack
    n: 20                   # lll: dimension (number of basis vectors); or dims: [lo, hi]
    bits: [16, 64, 256]     # entry sizes to draw from (gauss, check, lll; q for qary)
    kinds: [uniform, knapsack, qary, scrambled, rectangular]   # drawn uniformly (repeat = weight)
    deltas: ["99/100", "3/4"]                                  # the LLL parameter

Kinds per op (each becomes a tag; corner cases are kept, never filtered):

    gauss         random, scrambled, already_reduced, equal_norms, hps-example,
                  ambient3, collinear (rank 1), zero_vector
    check         reduced, random, size_violation, swapped, mu_half, lovasz_equality,
                  dependent
    lll           uniform, rectangular, knapsack (rows (e_i, a_i)), qary (Lambda_q(A)),
                  scrambled (U R with U unimodular), already_reduced, nearly_dependent,
                  orthogonal, dim1, dependent (n+1 generators of rank n), rank_deficient,
                  zero_vector, duplicate, delta1, delta_low
    congruential  bits: q of that many bits (HPS 7.1)
    knapsack      n: Merkle--Hellman of n items (HPS 7.2); kinds random, zeros, ones, single

Expected answers come from Sage, independently of the reference: ``M.LLL()`` (fpLLL) and
NTL's exact LLL, ``hermite_form`` and ``gram_schmidt`` over QQ; the planted keys and
plaintexts for the cryptosystems. ``verify`` accepts every correct answer:

    gauss         same lattice (Hermite normal forms), Gauss-reduced
                  (|v1| <= |v2|, 2|<v1,v2>| <= |v1|^2), |v1|^2, |v2|^2 = the minima
    check         the verdicts (reduced, independent; size_reduced and lovasz when the
                  vectors are independent) equal the exact ones
    lll           rank many vectors, delta-LLL-reduced (exact rational Gram--Schmidt with
                  eta = 1/2) and generating the same lattice (equal Hermite normal forms):
                  Sage's LLL output is only one of many valid answers
    congruential  (f, g) is a key (f h = g mod q, f, g > 0) and m is the plaintext
    knapsack      x in {0,1}^n and sum x_i M_i = S
"""

from __future__ import annotations

import math
from fractions import Fraction

VERSION = 1

GAUSS_KINDS = ("random", "random", "scrambled", "scrambled", "already_reduced", "equal_norms",
               "hps-example", "ambient3", "collinear", "zero_vector")
CHECK_KINDS = ("reduced", "reduced", "random", "size_violation", "swapped", "mu_half",
               "lovasz_equality", "dependent")
LLL_KINDS = ("uniform", "rectangular", "knapsack", "knapsack", "qary", "qary", "scrambled")
KNAP_KINDS = ("random", "random", "random", "zeros", "ones", "single")
HPS_GAUSS = [[66586820, 65354729], [6513996, 6393464]]     # HPS 2nd ed., Example 7.67


# --- random helpers (randomness only from rng) -------------------------------------------

def _int(rng, bits: int) -> int:
    """A random integer in (-2^bits, 2^bits)."""
    return rng.randrange(-(1 << bits) + 1, 1 << bits)


def _rand_prime(bits: int, rng) -> int:
    from sage.all import is_prime

    while True:
        p = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
        if is_prime(p):
            return p


def _rows(M) -> list[list[int]]:
    return [[int(x) for x in r] for r in M.rows()]


def _unimodular(n: int, rng, steps: int, qmax: int = 3) -> list[list[int]]:
    """A random unimodular n x n matrix: a product of elementary row operations."""
    U = [[int(i == j) for j in range(n)] for i in range(n)]
    for _ in range(steps):
        i, j = rng.sample(range(n), 2) if n > 1 else (0, 0)
        if n == 1:
            U[0] = [-x for x in U[0]]
            continue
        c = rng.choice([1, -1]) * rng.randrange(1, qmax + 1)
        U[i] = [a + c * b for a, b in zip(U[i], U[j])]
        if rng.random() < 0.3:
            U[i], U[j] = U[j], U[i]
    return U


def _mul(A: list[list[int]], B: list[list[int]]) -> list[list[int]]:
    cols = list(zip(*B))
    return [[sum(a * b for a, b in zip(r, c)) for c in cols] for r in A]


def _scramble(R: list[list[int]], rng, bits: int) -> list[list[int]]:
    """U R with a random unimodular U whose product reaches about ``bits``-bit entries."""
    n = len(R)
    B = R
    for _ in range(10_000):
        B = _mul(_unimodular(n, rng, max(1, n)), B)
        if max(abs(x) for r in B for x in r).bit_length() >= bits:
            break
    return B


def _sage_lll(rows, delta: Fraction, exact: bool = False):
    from sage.all import ZZ, matrix

    M = matrix(ZZ, rows)
    if exact:      # NTL's LLL in exact integer arithmetic, delta = a/b
        return M.LLL(algorithm="NTL:LLL", fp=None, delta=float(delta))
    return M.LLL(delta=min(float(delta), 0.999))


def _hnf(rows):
    from sage.all import ZZ, matrix

    return matrix(ZZ, rows).hermite_form(include_zero_rows=False)


# --- exact Gram--Schmidt (independent of the reference's integral version) -------------------

def gso(rows: list[list[int]]) -> tuple[list[Fraction], list[list[Fraction]]] | None:
    """B_i = |b*_i|^2 and mu_ij from the Gram matrix by the rational Cholesky recurrence
    r_ij = G_ij - sum_{k<j} mu_jk r_ik, mu_ij = r_ij / r_jj; None if dependent."""
    n = len(rows)
    G = [[sum(a * b for a, b in zip(rows[i], rows[j])) for j in range(i + 1)] for i in range(n)]
    mu = [[Fraction(0)] * n for _ in range(n)]
    B: list[Fraction] = []
    for i in range(n):
        r = [Fraction(0)] * (i + 1)
        for j in range(i + 1):
            r[j] = Fraction(G[i][j]) - sum((mu[j][k] * r[k] for k in range(j)), Fraction(0))
            if j < i:
                mu[i][j] = r[j] / B[j]
        if r[i] == 0:
            return None
        B.append(r[i])
    return B, mu


def lll_verdict(rows: list[list[int]], delta: Fraction) -> dict:
    """Exact verdict on delta-LLL-reducedness (eta = 1/2)."""
    g = gso(rows)
    if g is None:
        return {"independent": False, "reduced": False}
    B, mu = g
    n = len(rows)
    size = all(abs(mu[i][j]) <= Fraction(1, 2) for i in range(n) for j in range(i))
    lov = all(B[k] >= (delta - mu[k][k - 1] ** 2) * B[k - 1] for k in range(1, n))
    return {"independent": True, "size_reduced": size, "lovasz": lov, "reduced": size and lov}


def _sage_verdict(rows, delta: Fraction) -> dict:
    """The same verdict from Sage's exact gram_schmidt over QQ (the generator's oracle)."""
    from sage.all import QQ, matrix

    M = matrix(QQ, rows)
    if M.rank() < M.nrows():
        return {"independent": False, "reduced": False}
    Gs, mu = M.gram_schmidt()
    n = M.nrows()
    Bs = [Gs.row(i) * Gs.row(i) for i in range(n)]
    d = QQ(delta.numerator) / delta.denominator
    size = all(abs(mu[i, j]) <= QQ(1) / 2 for i in range(n) for j in range(i))
    lov = all(Bs[k] >= (d - mu[k, k - 1] ** 2) * Bs[k - 1] for k in range(1, n))
    return {"independent": True, "size_reduced": bool(size), "lovasz": bool(lov),
            "reduced": bool(size and lov)}


def _delta_str(d: Fraction) -> str:
    return f"{d.numerator}/{d.denominator}" if d.denominator != 1 else str(d.numerator)


# --- generators per op -----------------------------------------------------------------

def _gauss(params, rng) -> dict:
    from sage.all import ZZ, matrix

    kind = rng.choice(params.get("kinds") or GAUSS_KINDS)
    b = rng.choice(params.get("bits") or [8, 32, 128])
    tags = [kind]
    if kind == "hps-example":
        B = HPS_GAUSS
    elif kind == "random":
        B = [[_int(rng, b), _int(rng, b)] for _ in range(2)]
    elif kind == "ambient3":
        B = [[_int(rng, b) for _ in range(3)] for _ in range(2)]
    elif kind in ("scrambled", "equal_norms", "already_reduced"):
        s = max(2, b // 4)
        while True:
            x, y = _int(rng, s), _int(rng, s)
            R = [[x, y], [-y, x]] if kind == "equal_norms" else [[x, y], [_int(rng, s), _int(rng, s)]]
            if matrix(ZZ, R).det() != 0:
                break
        if kind == "already_reduced":
            R = _rows(matrix(ZZ, R).LLL(delta=0.99))
            if 2 * abs(sum(p * q for p, q in zip(*R))) > sum(p * p for p in R[0]):
                tags = ["nearly_reduced"]      # LLL(0.99) with eta = 0.51 is not always Gauss-reduced
            B = R
        else:
            B = _scramble(R, rng, b)
            if kind == "equal_norms":
                tags.append("scrambled")
    elif kind == "collinear":
        w = [_int(rng, max(2, b // 2)), _int(rng, max(2, b // 2))]
        g = math.gcd(*w) or 1
        w = [w[0] // g or 1, w[1] // g]
        B = [[c * x for x in w] for c in (_int(rng, b // 2 + 1), _int(rng, b // 2 + 1))]
        tags.append("dependent")
    else:  # zero_vector
        B = [[_int(rng, b), _int(rng, b)], [0, 0]]
        if rng.random() < 0.5:
            B.reverse()
        tags.append("dependent")
    tags.append(f"bits:{b}")
    H = _hnf(B)
    rank = H.nrows()
    if rank == 2:
        L = _rows(matrix(ZZ, B).LLL(delta=0.99))
        vs = sorted({sum(x * x for x in (a * L[0][t] + c * L[1][t] for t in range(len(L[0]))))
                     for a in range(-3, 4) for c in range(-3, 4) if (a, c) != (0, 0)})
        # successive minima: |v1|^2 is the least norm; |v2|^2 the least norm of a vector
        # independent of a shortest one (search the small combinations of the LLL basis)
        n1 = vs[0]
        shortest = [(a, c) for a in range(-3, 4) for c in range(-3, 4) if (a, c) != (0, 0)
                    and _norm2(_comb(L, a, c)) == n1]
        n2 = min(_norm2(_comb(L, a, c)) for a in range(-3, 4) for c in range(-3, 4)
                 if any(a * c2 - c * a2 != 0 for a2, c2 in shortest))
        exp = {"rank": 2, "norms2": [n1, n2], "basis": L}
    else:
        exp = {"rank": rank, "norms2": [_norm2(r) for r in _rows(H)], "basis": _rows(H)}
    return {"input": {"op": "gauss", "basis": B}, "expected": exp, "tags": tags}


def _norm2(v) -> int:
    return sum(x * x for x in v)


def _comb(L, a, c):
    return [a * x + c * y for x, y in zip(L[0], L[1])]


def _check(params, rng) -> dict:
    lo, hi = params.get("dims") or [2, 8]
    n = rng.randrange(lo, hi + 1)
    b = rng.choice(params.get("bits") or [8, 32])
    delta = Fraction(rng.choice(params.get("deltas") or ["3/4", "99/100"]))
    kind = rng.choice(params.get("kinds") or CHECK_KINDS)
    rand = [[_int(rng, b) for _ in range(n)] for _ in range(n)]
    tags = [kind]
    if kind == "random":
        B = rand
    elif kind == "dependent":
        B = rand[:-1] + [[x + y for x, y in zip(rand[0], rand[1 % n])] if n > 1 else [0]]
        if n == 1:
            B = [[0]]
    elif kind == "mu_half":
        # b_1 = (2a, 0, ...), b_2 = (+-a, c, 0, ...): mu_21 = +-1/2 exactly (|mu| <= 1/2 holds)
        n = max(n, 2)
        a = abs(_int(rng, b)) or 1
        B = [[2 * a] + [0] * (n - 1), [rng.choice([a, -a]), abs(_int(rng, b)) + 2 * a] + [0] * (n - 2)]
        B += [[_int(rng, b) for _ in range(n)] for _ in range(n - 2)]
    else:
        R = _rows(_sage_lll(rand, delta, exact=True))
        if kind == "reduced" or n == 1:
            B = R
        elif kind == "size_violation":
            k = rng.randrange(1, n)
            B = [r[:] for r in R]
            B[k] = [x + rng.choice([2, -2, 3]) * y for x, y in zip(R[k], R[k - 1])]
        elif kind == "swapped":
            k = rng.randrange(1, n)
            B = [r[:] for r in R]
            B[k], B[k - 1] = B[k - 1], B[k]
        else:  # lovasz_equality: delta = B_k / B_{k-1} + mu^2 for some k, if in (1/4, 1]
            B = R
            g = gso(R)
            ks = list(range(1, n)) if g else []
            rng.shuffle(ks)
            for k in ks:
                Bv, mu = g
                d = Bv[k] / Bv[k - 1] + mu[k][k - 1] ** 2
                if Fraction(1, 4) < d <= 1:
                    delta = d
                    break
            else:
                tags = ["reduced"]
    if n == 1:
        tags.append("dim1")
    tags += [f"n:{len(B)}", f"bits:{b}"]
    exp = _sage_verdict(B, delta)
    return {"input": {"op": "check", "basis": B, "delta": _delta_str(delta)},
            "expected": exp, "tags": tags}


def _lll_basis(kind: str, n: int, b: int, rng) -> tuple[list[list[int]], list[str]]:
    from sage.all import ZZ, matrix

    tags = [kind]
    if kind == "uniform":
        B = [[_int(rng, b) for _ in range(n)] for _ in range(n)]
    elif kind == "rectangular":
        m = n + rng.randrange(1, max(2, n // 2) + 1)
        B = [[_int(rng, b) for _ in range(m)] for _ in range(n)]
    elif kind == "knapsack":
        B = [[int(i == j) for j in range(n)] + [rng.getrandbits(b) | 1] for i in range(n)]
    elif kind == "qary":
        q = _rand_prime(max(b, 3), rng)
        k = max(1, n // 2)
        B = [[int(i == j) for j in range(k)] + [rng.randrange(q) for _ in range(n - k)]
             for i in range(k)]
        B += [[0] * k + [q * (i == j) for j in range(n - k)] for i in range(n - k)]
    elif kind == "scrambled":
        R = [[_int(rng, 4) for _ in range(n)] for _ in range(n)]
        while matrix(ZZ, R).det() == 0:
            R = [[_int(rng, 4) for _ in range(n)] for _ in range(n)]
        B = _scramble(R, rng, b)
    elif kind == "already_reduced":
        B = _rows(_sage_lll([[_int(rng, b) for _ in range(n)] for _ in range(n)], Fraction(99, 100),
                            exact=True))
    elif kind == "orthogonal":
        B = [[(_int(rng, max(2, b // 4)) or 1) * (i == j) for j in range(n)] for i in range(n)]
        rng.shuffle(B)
    elif kind == "nearly_dependent":
        # b_i = c_i v + e_i: a long common direction v, tiny independent perturbations e_i
        v = [_int(rng, b) for _ in range(n)]
        B = [[c * x + _int(rng, 2) for x in v] for c in (_int(rng, 8) or 1 for _ in range(n))]
        while matrix(ZZ, B).rank() < n:
            B[0] = [x + 1 for x in B[0]]
    elif kind == "dim1":
        B = [[_int(rng, b) or 1 for _ in range(rng.randrange(1, 4))]]
    elif kind in ("dependent", "rank_deficient", "zero_vector", "duplicate"):
        tags.append("dependent")
        if kind == "dependent":      # n+1 generators of a rank-n lattice
            B = [[_int(rng, b) for _ in range(n)] for _ in range(n)]
            c = [_int(rng, 3) for _ in range(n)]
            B.append([sum(ci * r[j] for ci, r in zip(c, B)) for j in range(n)])
            rng.shuffle(B)
        elif kind == "rank_deficient":
            r = max(1, n // 2)
            base = [[_int(rng, max(2, b // 2)) for _ in range(n + 1)] for _ in range(r)]
            B = _mul([[_int(rng, 4) for _ in range(r)] for _ in range(n)], base)
        elif kind == "zero_vector":
            B = [[_int(rng, b) for _ in range(n)] for _ in range(n - 1)] + [[0] * n]
            rng.shuffle(B)
        else:
            B = [[_int(rng, b) for _ in range(n)] for _ in range(n - 1)]
            B.insert(rng.randrange(n), list(B[rng.randrange(n - 1)]))
    else:
        raise ValueError(f"unknown lll kind {kind!r}")
    return B, tags


def _lll(params, rng) -> dict:
    if "dims" in params:
        lo, hi = params["dims"]
        n = rng.randrange(lo, hi + 1)
    else:
        n = int(params["n"])
    b = rng.choice(params.get("bits") or [16])
    kind = rng.choice(params.get("kinds") or LLL_KINDS)
    delta = Fraction(rng.choice(params.get("deltas") or ["99/100"]))
    tags = []
    if kind == "delta1":
        delta, kind = Fraction(1), rng.choice(["uniform", "knapsack"])
        tags.append("delta1")
    elif kind == "delta_low":
        delta, kind = Fraction(26, 100), rng.choice(["uniform", "knapsack", "scrambled"])
        tags.append("delta_low")
    B, t = _lll_basis(kind, n, b, rng)
    tags += t + [f"n:{len(B)}", f"bits:{b}", f"delta:{_delta_str(delta)}"]
    L = _sage_lll(B, delta)
    red = [r for r in _rows(L) if any(r)]
    from sage.all import ZZ, matrix

    exp = {"rank": int(matrix(ZZ, B).rank()), "basis": red}
    return {"input": {"op": "lll", "basis": B, "delta": _delta_str(delta)}, "expected": exp,
            "tags": tags}


def _congruential(params, rng) -> dict:
    """HPS 7.1: a key, a message and its ciphertext; regenerated if (unusually) the
    shortest vectors of the lattice do not decrypt (an unsolvable instance)."""
    from sage.all import ZZ, matrix

    bits = int(rng.choice(params.get("bits") or [128]))
    for _ in range(1000):
        q = _rand_prime(bits, rng)
        lo_g, hi = math.isqrt(q // 4) + 1, math.isqrt(q // 2)   # sqrt(q/4) < g < sqrt(q/2)
        f = rng.randrange(1, hi)
        g = rng.randrange(lo_g, hi)
        if math.gcd(f, q * g) != 1:
            continue
        h = pow(f, -1, q) * g % q
        m = rng.randrange(0, math.isqrt((q - 1) // 4))         # m < sqrt(q/4)
        r = rng.randrange(0, hi)                               # r < sqrt(q/2)
        e = (r * h + m) % q
        v = _rows(matrix(ZZ, [[1, h], [0, q]]).LLL(delta=0.99))[0]
        F, G = (v if v[0] > 0 else [-v[0], -v[1]])
        if F > 0 and G > 0 and math.gcd(F, G) == 1 and pow(F, -1, G) * (F * e % q) % G == m:
            tags = ["hps-7.1", f"bits:{bits}"] + (["key=shortest"] if [F, G] == [f, g] else
                                                 ["other-short-key"])
            return {"input": {"op": "congruential", "q": q, "h": h, "e": e},
                    "expected": {"m": m, "f": f, "g": g}, "tags": tags}
    raise RuntimeError("no solvable congruential instance")


def _knapsack(params, rng) -> dict:
    """HPS 7.2: Merkle--Hellman with a superincreasing r_i = sum_{j<i} r_j + rand(1..2^n)."""
    from sage.all import ZZ, matrix

    n = int(params["n"])
    kind = rng.choice(params.get("kinds") or KNAP_KINDS)
    r, s = [], 0
    for _ in range(n):
        x = s + rng.randrange(1, 1 << n)
        r.append(x)
        s += x
    B = rng.randrange(2 * r[-1] + 1, 4 * r[-1])
    A = rng.randrange(2, B)
    while math.gcd(A, B) != 1:
        A = rng.randrange(2, B)
    M = [A * ri % B for ri in r]
    if kind == "zeros":
        x = [0] * n
    elif kind == "ones":
        x = [1] * n
    elif kind == "single":
        j = rng.randrange(n)
        x = [int(i == j) for i in range(n)]
    else:
        x = [rng.randrange(2) for _ in range(n)]
    S = sum(a * b for a, b in zip(x, M))
    # Oracle: does Sage's LLL of the HPS lattice expose +-(2x - 1, 0)? (Recorded as a tag;
    # the instance is kept either way, the planted x is a valid answer.)
    lat = [[2 * (i == j) for j in range(n)] + [M[i]] for i in range(n)] + [[1] * n + [S]]
    t = [2 * xi - 1 for xi in x] + [0]
    rows = _rows(matrix(ZZ, lat).LLL(delta=0.99))
    found = t in rows or [-c for c in t] in rows
    density = n / math.log2(max(M))
    return {"input": {"op": "knapsack", "M": M, "S": S},
            "expected": {"x": x, "private": {"r": r, "A": A, "B": B}},
            "tags": [kind, "hps-7.2", f"n:{n}", "sage-lll-finds" if found else "sage-lll-misses",
                     f"density:{density:.2f}"]}


GENERATORS = {"gauss": _gauss, "check": _check, "lll": _lll, "congruential": _congruential,
              "knapsack": _knapsack}


def generate(params: dict, rng) -> dict:
    return GENERATORS[params.get("op", "lll")](params, rng)


# --- verification ---------------------------------------------------------------------

def _int_matrix(x, name="basis") -> list[list[int]] | str:
    if not isinstance(x, list) or not all(isinstance(r, list) and all(
            isinstance(v, int) and not isinstance(v, bool) for v in r) for r in x):
        return f"{name} is not a list of integer vectors"
    return x


def _same_lattice(a: list[list[int]], b: list[list[int]]) -> bool:
    if not a or not b:
        return not any(any(r) for r in a) and not any(any(r) for r in b)
    if len({len(r) for r in a + b}) != 1:
        return False
    return _hnf(a) == _hnf(b)


def verify(vector: dict, output: dict) -> str | None:
    inp, exp = vector["input"], vector.get("expected") or {}
    op = inp.get("op", "lll")
    if not isinstance(output, dict):
        return "output is not an object"
    if op in ("gauss", "lll"):
        B = _int_matrix(output.get("basis"))
        if isinstance(B, str):
            return B
        if len(B) != exp["rank"]:
            return f"{len(B)} vectors, but the lattice has rank {exp['rank']}"
        if B and len(B[0]) != len(inp["basis"][0]):
            return "the vectors have the wrong length"
        if not _same_lattice(B, inp["basis"]):
            return "the output does not generate the same lattice (Hermite normal forms differ)"
        if op == "lll":
            delta = Fraction(inp.get("delta", "3/4"))
            v = lll_verdict(B, delta)
            if not v["independent"]:
                return "the output vectors are linearly dependent"
            if not v["reduced"]:
                return (f"not {_delta_str(delta)}-LLL-reduced (size condition: {v['size_reduced']}, "
                        f"Lovász condition: {v['lovasz']})")
            return None
        norms = [_norm2(r) for r in B]
        if len(B) == 2:
            if norms[0] > norms[1] or 2 * abs(sum(x * y for x, y in zip(*B))) > norms[0]:
                return "not Gauss-reduced (need |v1| <= |v2| and 2|<v1, v2>| <= |v1|^2)"
        if norms != exp["norms2"]:
            return f"squared norms {norms} != the successive minima {exp['norms2']}"
        return None
    if op == "check":
        keys = ["independent", "reduced"] + (["size_reduced", "lovasz"] if exp["independent"] else [])
        bad = [k for k in keys if output.get(k) is not exp[k]]
        return None if not bad else "wrong verdict: " + ", ".join(
            f"{k}={output.get(k)!r} (expected {exp[k]})" for k in bad)
    if op == "congruential":
        q, h = inp["q"], inp["h"]
        f, g, m = (output.get(k) for k in ("f", "g", "m"))
        if not all(isinstance(v, int) for v in (f, g, m)):
            return "f, g, m must be integers"
        if f <= 0 or g <= 0 or (f * h - g) % q:
            return f"(f, g) = ({f}, {g}) is not a key: f h != g (mod q)"
        return None if m == exp["m"] else f"m = {m} is not the plaintext"
    if op == "knapsack":
        x = output.get("x")
        M = inp["M"]
        if not isinstance(x, list) or len(x) != len(M) or any(v not in (0, 1) or isinstance(v, bool)
                                                              for v in x):
            return "x must be a list of len(M) bits"
        s = sum(a * b for a, b in zip(x, M))
        return None if s == inp["S"] else f"sum x_i M_i = {s} != S"
    return f"unknown op {op!r}"
