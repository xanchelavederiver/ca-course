"""Exact LLL lattice reduction: Gram--Schmidt data, size reduction, the Lovász
condition, the LLL loop, the LLL-reducedness check and dependent generators.

Arithmetic
----------
Everything is exact. The LLL loop is the *integral* LLL of H. Cohen, "A Course in
Computational Algebraic Number Theory", Algorithm 2.6.7 (de Weger's formulation): instead
of the rational Gram--Schmidt data

    B_i  = |b*_i|^2,        mu_ij = <b_i, b*_j> / B_j      (j < i),

it keeps the integers

    d_0 = 1,  d_i = B_1 B_2 ... B_i = det Gram(b_1, ..., b_i),     lambda_ij = d_j mu_ij,

which are integral for an integer basis (they are minors of the Gram matrix). All the
divisions in the updates are exact, so there are no fractions and no gcds: this is several
times faster in Python than `fractions.Fraction` and needs no floating point at all.
The rational values are recovered as mu_ij = lambda_ij / d_j and B_i = d_i / d_{i-1}
(see `GSO.mu`, `GSO.B`), which `check_reduced` reports.

With delta = p/q (1/4 < delta <= 1) the two LLL conditions read

    size condition    |mu_ij| <= 1/2              <=>  2 |lambda_ij| <= d_j,
    Lovász condition  B_k >= (delta - mu^2) B_{k-1}   (mu = mu_{k,k-1})
                      <=>  q (d_k d_{k-2} + lambda_{k,k-1}^2) >= p d_{k-1}^2.

Linearly dependent input
------------------------
The integral LLL needs independent vectors (d_k > 0). If the input generators are
dependent, `lll_generators` uses the classical embedding trick (Pohst; Havas--Majewski--
Matthews): reduce the *independent* rows of [N*B | I_n] for a large weight N. The
transformation is unimodular, so the first blocks of the output rows generate the same
lattice L(B); once N exceeds 2^((n-1)/2) times the length of a short kernel basis, the
first n - r output rows are kernel vectors (zero first block) and the other r first blocks
are a basis of L(B). The function checks this (the r nonzero blocks must be independent),
squares N if the check fails, and finally LLL-reduces the extracted basis. As a by-product
the identity block of the zero rows gives a basis of the integer relations between the
input vectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

try:   # GMP integers when available (the spec allows big-integer libraries): 3-4x faster
    from gmpy2 import mpz as Z
except ImportError:   # pragma: no cover - plain Python ints give identical results
    Z = int


class DependentVectors(ValueError):
    """The vectors are linearly dependent (some Gram determinant d_k is 0)."""

    def __init__(self, k: int):
        super().__init__(f"vectors are linearly dependent: b_{k + 1} lies in the span of "
                         f"b_1, ..., b_{k}")
        self.k = k


# --- small vector helpers ----------------------------------------------------------

def dot(u: list[int], v: list[int]) -> int:
    return sum(a * b for a, b in zip(u, v))


def round_div(a: int, b: int) -> int:
    """The nearest integer to a/b for b > 0 (ties go up): floor(a/b + 1/2)."""
    return (2 * a + b) // (2 * b)


def parse_delta(delta) -> Fraction:
    """delta as a Fraction: "3/4", "0.99", 0.75, [3, 4]; must satisfy 1/4 < delta <= 1."""
    if delta is None:
        d = Fraction(3, 4)
    elif isinstance(delta, (list, tuple)) and len(delta) == 2:
        d = Fraction(int(delta[0]), int(delta[1]))
    else:
        d = Fraction(str(delta))         # str() so that 0.99 means 99/100, not the binary float
    if not Fraction(1, 4) < d <= 1:
        raise ValueError(f"delta = {d} is outside (1/4, 1]")
    return d


def as_basis(rows) -> list[list[int]]:
    """Validate an integer matrix given as a list of rows of equal length."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("the basis must be a non-empty list of vectors")
    m = None
    out = []
    for r in rows:
        if not isinstance(r, list) or not r or not all(isinstance(x, int) and not isinstance(x, bool)
                                                       for x in r):
            raise ValueError("every vector must be a non-empty list of integers")
        if m is None:
            m = len(r)
        elif len(r) != m:
            raise ValueError("all vectors must have the same length")
        out.append(list(r))
    return out


# --- Gram--Schmidt data in integral form -----------------------------------------------

@dataclass
class GSO:
    """Integral Gram--Schmidt data of b_1..b_n (0-based here: d[0] = 1, d[i+1] for b_i).

    lam[i][j] = d_{j+1} mu_ij for j < i;  d[i+1] = B_1 ... B_{i+1}.
    """
    d: list[int]
    lam: list[list[int]]

    def B(self, i: int) -> Fraction:
        """|b*_i|^2 (0-based i)."""
        return Fraction(self.d[i + 1], self.d[i])

    def mu(self, i: int, j: int) -> Fraction:
        """mu_ij = <b_i, b*_j> / |b*_j|^2 for j < i (0-based)."""
        return Fraction(self.lam[i][j], self.d[j + 1])


def gso_row(b: list[list[int]], k: int, d: list[int], lam: list[list[int]]) -> None:
    """Compute lam[k][0..k-1] and d[k+1] from rows 0..k-1 (Cohen 2.6.7, step 2).

    u_j = d_j <b_k, b_j> - sum ... is built with exact divisions; raises
    DependentVectors if b_k lies in the span of b_0..b_{k-1} (then d_{k+1} = 0).
    """
    for j in range(k + 1):
        u = dot(b[k], b[j])
        for i in range(j):
            u = (d[i + 1] * u - lam[k][i] * lam[j][i]) // d[i]     # exact division
        if j < k:
            lam[k][j] = u
        else:
            if u == 0:
                raise DependentVectors(k)
            d[k + 1] = u


def gram_schmidt(b: list[list[int]]) -> GSO:
    """Integral Gram--Schmidt data of independent integer vectors (DependentVectors otherwise)."""
    n = len(b)
    d = [1] + [0] * n
    lam = [[0] * n for _ in range(n)]
    for k in range(n):
        gso_row(b, k, d, lam)
    return GSO(d, lam)


# --- the LLL-reducedness check ----------------------------------------------------------

def check_reduced(basis, delta="3/4", max_listed: int = 20) -> dict:
    """Check that a basis is delta-LLL-reduced: the size condition |mu_ij| <= 1/2 for all
    j < i and the Lovász condition B_k >= (delta - mu_{k,k-1}^2) B_{k-1} for all k.

    Returns the verdict and the artefacts of the check (mu, B_i, the violations).
    """
    b = as_basis(basis)
    dl = parse_delta(delta)
    p, q = dl.numerator, dl.denominator
    try:
        g = gram_schmidt(b)
    except DependentVectors as e:
        return {"independent": False, "size_reduced": False, "lovasz": False, "reduced": False,
                "reason": str(e), "dependent_at": e.k}
    n = len(b)
    size_bad = [[i, j] for i in range(n) for j in range(i) if 2 * abs(g.lam[i][j]) > g.d[j + 1]]
    # Lovász for k = 1..n-1 (0-based), in the integral form (see the module docstring).
    lov_bad = [k for k in range(1, n)
               if q * (g.d[k + 1] * g.d[k - 1] + g.lam[k][k - 1] ** 2) < p * g.d[k] ** 2]
    return {"independent": True, "size_reduced": not size_bad, "lovasz": not lov_bad,
            "reduced": not size_bad and not lov_bad,
            "size_violations": size_bad[:max_listed], "n_size_violations": len(size_bad),
            "lovasz_violations": lov_bad[:max_listed], "n_lovasz_violations": len(lov_bad),
            "B": [str(g.B(i)) for i in range(n)],
            "mu": [[str(g.mu(i, j)) for j in range(i)] for i in range(n)]}


# --- the LLL loop ---------------------------------------------------------------------

@dataclass
class Stats:
    """Counters of one LLL run (reported in "extra")."""
    iterations: int = 0          # passes of the main loop (one Lovász test each)
    swaps: int = 0
    size_reductions: int = 0     # nontrivial b_k <- b_k - q b_l steps
    trace: list | None = field(default=None, repr=False)

    def as_dict(self) -> dict:
        out = {"iterations": self.iterations, "swaps": self.swaps,
               "size_reductions": self.size_reductions}
        if self.trace is not None:
            out["trace"] = self.trace
        return out


def lll(basis, delta="3/4", trace: bool = False, max_trace: int = 2000) -> tuple[list[list[int]], Stats]:
    """delta-LLL-reduce linearly independent integer vectors (Cohen, Algorithm 2.6.7).

    Returns the reduced basis and the counters; with ``trace`` also the basis after every
    swap (up to ``max_trace`` snapshots): "the coordinates of the basis vectors on each
    iteration" asked for by the spec. Raises DependentVectors for dependent input.
    """
    b = [[Z(x) for x in r] for r in as_basis(basis)]
    dl = parse_delta(delta)
    p, q = dl.numerator, dl.denominator
    n = len(b)
    st = Stats(trace=[] if trace else None)
    d = [1] + [0] * n
    lam = [[0] * n for _ in range(n)]

    def red(k: int, l: int) -> None:
        """Size-reduce b_k against b_l: make |mu_kl| <= 1/2 (Cohen's RED(k, l))."""
        if 2 * abs(lam[k][l]) > d[l + 1]:
            r = round_div(lam[k][l], d[l + 1])
            bl, bk = b[l], b[k]
            b[k] = [x - r * y for x, y in zip(bk, bl)]
            lam[k][l] -= r * d[l + 1]
            lk, ll = lam[k], lam[l]
            for i in range(l):
                lk[i] -= r * ll[i]
            st.size_reductions += 1

    def swap(k: int) -> None:
        """Exchange b_k and b_{k-1} and update d, lambda (Cohen's SWAP(k))."""
        b[k], b[k - 1] = b[k - 1], b[k]
        for j in range(k - 1):
            lam[k][j], lam[k - 1][j] = lam[k - 1][j], lam[k][j]
        la = lam[k][k - 1]
        bb = (d[k - 1] * d[k + 1] + la * la) // d[k]          # new d_{k-1} (1-based)
        for i in range(k + 1, kmax + 1):
            t = lam[i][k]
            lam[i][k] = (d[k + 1] * lam[i][k - 1] - la * t) // d[k]
            lam[i][k - 1] = (bb * t + la * lam[i][k]) // d[k + 1]
        d[k] = bb
        st.swaps += 1
        if st.trace is not None and len(st.trace) < max_trace:
            st.trace.append({"iteration": st.iterations, "swap": [k - 1, k],
                             "basis": _ints(b)})

    gso_row(b, 0, d, lam)
    k, kmax = 1, 0
    while k < n:
        if k > kmax:                       # first visit: incremental Gram--Schmidt
            kmax = k
            gso_row(b, k, d, lam)
        st.iterations += 1
        red(k, k - 1)
        if q * (d[k + 1] * d[k - 1] + lam[k][k - 1] ** 2) < p * d[k] ** 2:   # Lovász fails
            swap(k)
            k = max(1, k - 1)
        else:
            for l in range(k - 2, -1, -1):
                red(k, l)
            k += 1
    if st.trace is not None:
        st.trace.append({"iteration": st.iterations, "final": True, "basis": _ints(b)})
    return _ints(b), st


def _ints(b) -> list[list[int]]:
    return [[int(x) for x in r] for r in b]


def lll_generators(gens, delta="3/4", trace: bool = False) -> tuple[list[list[int]], dict]:
    """A delta-LLL-reduced basis of the lattice generated by arbitrary integer vectors.

    Independent input goes straight to `lll`. Dependent input (including zero vectors)
    goes through the embedding [N*B | I] described in the module docstring. Returns the
    basis (r rows, r = rank) and the "extra" dict (counters, rank, relations).
    """
    b = as_basis(gens)
    try:
        red, st = lll(b, delta, trace)
        return red, {"rank": len(red), "dependent": False, **st.as_dict()}
    except DependentVectors as e:
        first = e.k
    n, m = len(b), len(b[0])
    nz = [r for r in b if any(r)]
    if not nz:
        return [], {"rank": 0, "dependent": True, "relations": [[int(i == j) for j in range(n)]
                                                                 for i in range(n)]}
    maxb = max(abs(x) for r in b for x in r)
    N = 1 << (n + maxb.bit_length())               # initial weight, squared on failure
    attempts, total = 0, Stats()
    while True:
        attempts += 1
        emb = [[N * x for x in r] + [int(i == j) for j in range(n)] for i, r in enumerate(b)]
        out, st = lll(emb, delta)                  # rows of emb are independent (the I block)
        for key in ("iterations", "swaps", "size_reductions"):
            setattr(total, key, getattr(total, key) + getattr(st, key))
        image = [[x // N for x in r[:m]] for r in out if any(r[:m])]
        relations = [r[m:] for r in out if not any(r[:m])]
        try:
            gram_schmidt(image)                    # the nonzero blocks must be independent
        except DependentVectors:
            N = N * N
            continue
        break
    red, st = lll(image, delta, trace)
    extra = {"rank": len(red), "dependent": True, "first_dependent_index": first,
             "embedding_weight_bits": N.bit_length() - 1, "embedding_attempts": attempts,
             "embedding": total.as_dict(), "relations": relations, **st.as_dict()}
    return red, extra
