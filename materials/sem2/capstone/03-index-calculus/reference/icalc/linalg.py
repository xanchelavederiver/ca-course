"""Step 3 of the spec: the logarithms of the factor base from the system of congruences

    sum_i e_ri * x_i = k_r   (mod N),   r = 1..m,   N = p - 1 (the order of the base gamma).

N is composite (at least even), so Z/N is not a field. We solve the system modulo every
prime power l^a || N and glue the answers by the CRT (nt.crt):

* Echelon form of the matrix modulo l: its pivot columns are independent mod l; the other
  (free) columns are set to 0. A pivot column is *determined* (its value is the same in
  every solution) iff its row of the reduced echelon form vanishes on the free columns.
  The logarithms of the undetermined primes stay unknown, and step 4 avoids them.
* A square subsystem S x = b on the pivot columns (pivot rows of those columns) has
  det S != 0 (mod l), so it has a unique solution modulo l^a, namely x = S^-1 b computed
  over Q (its denominators divide det S, coprime to l) reduced mod l^a. No Hensel lifting
  is needed, and one rational solve (Sage over ZZ/QQ: FLINT/IML p-adic lifting) serves
  every l for which S stays invertible.
* The structure (pivots, rows) is computed once modulo a fixed 23-bit prime (Sage's fast
  word-size GF(l) matrices); it serves every large l | N (det S = 0 mod l has probability
  ~1/l and shows as a denominator divisible by l), and every small l with the same pivot
  columns mod l and det S != 0 mod l. Otherwise the small l gets its own subsystem.

Before that, structured-Gaussian-elimination-style pruning: a prime that occurs in exactly
one relation (a singleton column) is determined by that relation once the others are
known, so the relation and the column are set aside and back-substituted at the end.
This shrinks the matrix. Primes that occur in no relation remain unknown.

The spec allows linear algebra packages: Sage's matrices are used for echelon forms,
ranks and rational solving only. The caller (solver.py) checks every logarithm:
gamma^x = q (mod p).
"""

from __future__ import annotations

import math

from icalc.nt import crt

WORD_PRIME = 8388593          # the largest prime < 2^23: Sage's fast GF(l) matrices
FAST_LIMIT = 1 << 23


def prune_singletons(rows: list[dict[int, int]]) -> tuple[list[int], list[tuple[int, int]]]:
    """Repeatedly set aside a relation containing a prime that occurs only there.

    Returns (indices of the core relations, [(relation, prime), ...] in removal order)."""
    where: dict[int, set[int]] = {}
    for r, row in enumerate(rows):
        for j in row:
            where.setdefault(j, set()).add(r)
    alive = set(range(len(rows)))
    removed: list[tuple[int, int]] = []
    queue = [j for j, rs in where.items() if len(rs) == 1]
    while queue:
        j = queue.pop()
        if len(where[j]) != 1:
            continue
        (r,) = where[j]
        removed.append((r, j))
        alive.discard(r)
        for i in rows[r]:
            where[i].discard(r)
            if len(where[i]) == 1:
                queue.append(i)
    return sorted(alive), removed


def solve(relations: list[tuple[int, dict[int, int]]], n: int, order: int,
          order_factors: dict[int, int]) -> tuple[list[int | None], dict]:
    """Logarithms (mod `order`) of the n factor-base primes; None where undetermined
    (a prime in no relation, or one the relations do not pin down modulo some l | order)."""
    from sage.all import GF, ZZ, matrix, vector

    rows = [f for _, f in relations]
    rhs = [k for k, _ in relations]
    core, removed = prune_singletons(rows)
    cols = sorted({j for r in core for j in rows[r]})       # ordered by the prime
    col_of = {j: c for c, j in enumerate(cols)}
    info = {"relations": len(relations), "core_rows": len(core), "core_cols": len(cols),
            "singletons": len(removed), "rational_solves": 0, "rank": None,
            "determined": {}}
    logs: list[int | None] = [None] * n

    if cols:
        entries = {(i, col_of[j]): e for i, r in enumerate(core) for j, e in rows[r].items()}
        shape = (len(core), len(cols))
        a = matrix(ZZ, *shape, entries, sparse=False)
        b = [rhs[r] for r in core]
        solutions: dict[tuple, tuple[list[int], int]] = {}   # (rows, cols) -> (numerators, den)

        def rational_solve(rs: tuple[int, ...], cs: tuple[int, ...]) -> tuple[list[int], int]:
            if (rs, cs) not in solutions:
                s = a.matrix_from_rows_and_columns(list(rs), list(cs))
                x = s.solve_right(vector(ZZ, [b[i] for i in rs]))      # over Q
                d = x.denominator()
                solutions[rs, cs] = ([int(t) for t in d * x], int(d))
                info["rational_solves"] += 1
            return solutions[rs, cs]

        def structure(ell: int):
            """(matrix mod ell, pivot columns, determined columns)."""
            m = matrix(GF(ell), *shape, entries, sparse=False)
            ech = m.echelon_form()
            piv = tuple(m.pivots())
            free = sorted(set(range(len(cols))) - set(piv))
            bad = {i for i, _ in ech.matrix_from_columns(free).nonzero_positions()} if free else set()
            return m, piv, {c for i, c in enumerate(piv) if i not in bad}

        def pivot_rows(m, piv) -> tuple[int, ...]:
            return tuple(m.matrix_from_columns(list(piv)).transpose().pivots())

        m_w, piv_w, det_w = structure(WORD_PRIME)
        rows_w = pivot_rows(m_w, piv_w)
        info["rank"] = len(piv_w)
        known = set(range(len(cols)))
        residues, moduli = [], []
        for ell, e in order_factors.items():
            mod = ell ** e
            if ell < FAST_LIMIT:
                m, piv, det = structure(ell)
                # Any square subsystem invertible mod ell on rank(mod ell) columns gives the
                # same values on the determined columns: reuse the word-prime one if it is
                # invertible mod ell (rank mod ell <= rank over Q = its size).
                if len(piv) == len(piv_w) and m.matrix_from_rows_and_columns(
                        list(rows_w), list(piv_w)).is_invertible():
                    piv, rs = piv_w, rows_w
                else:
                    rs = pivot_rows(m, piv)
            else:
                piv, det, rs = piv_w, det_w, rows_w
            nums, den = rational_solve(rs, piv) if piv else ([], 1)
            if den % ell == 0:                  # det S = 0 (mod ell): practically never
                det = set()
            dinv = pow(den, -1, mod) if det else 0
            sol = dict.fromkeys(range(len(cols)), 0)
            sol.update({c: t * dinv % mod for c, t in zip(piv, nums)})
            residues.append(sol)
            moduli.append(mod)
            known &= det
            info["determined"][str(mod)] = len(det)
        for c in known:
            logs[cols[c]] = crt([res[c] for res in residues], moduli)[0]

    # back-substitute the set-aside singleton relations, last removed first
    for r, j in reversed(removed):
        e = rows[r][j]
        rest = [(i, f) for i, f in rows[r].items() if i != j]
        if math.gcd(e, order) != 1 or any(logs[i] is None for i, _ in rest):
            continue
        logs[j] = (rhs[r] - sum(f * logs[i] for i, f in rest)) * pow(e, -1, order) % order
    return logs, info
