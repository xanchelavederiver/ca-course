# LLL capstone — reference implementation

Instructor-only reference for `spec.tex` (capstone 8). Pure Python with exact integer
arithmetic. It uses `gmpy2.mpz` integers when gmpy2 is installed (the spec allows
big-integer libraries; this makes it 3–4× faster on large lattices) and plain Python
ints otherwise, with identical results. It needs no Sage: the bench runs it with
`sage -python` only because the capstone's image is `taskgen`. Sage is the **oracle** of the tests and of the vector
generator `taskgen/capstone/gens/lll.py`. It is never used in the solver.

## Usage

```sh
echo '{"id":1,"input":{"op":"lll","basis":[[1,0,0,1345],[0,1,0,35],[0,0,1,154]],"delta":"3/4"}}' \
  | python3 reference/main.py
make bench CAPSTONE=lll           # all vectors, timings, requirements.tex
make test-capstones CAPSTONE=lll  # pytest vs Sage
```

JSON lines, one answer per request, flushed. Bad input gets an `"error"`, never a crash.

| `op` | input | output | `extra` (intermediate data the spec asks to keep) |
|---|---|---|---|
| `gauss` | `basis` (2 vectors in Z^m) | `basis` (Gauss-reduced; 1 vector if collinear) | `trace` (m, v1, v2 at every iteration), iterations, swaps, norms |
| `check` | `basis`, `delta` | `reduced`, `size_reduced`, `lovasz`, `independent` | all mu_ij and B_i = \|b*_i\|^2 (exact fractions), the violating (i, j) / k |
| `lll` | `basis` (any generators), `delta` (default 3/4), `trace` | `basis` (delta-LLL-reduced, rank many rows) | iterations, swaps, size reductions, `trace` (basis after every swap); for dependent input rank, relations, embedding data |
| `congruential` | `q`, `h`, `e` | `f`, `g`, `m` | the lattice [(1,h),(0,q)], its Gauss-reduced basis, the keys tried, r |
| `knapsack` | `M`, `S` | `x` | the lattice (HPS 7.2), the weight, the found vector, LLL counters per attempt |

`delta` is exact: `"3/4"`, `"0.99"` (= 99/100), `[3, 4]`. It must lie in (1/4, 1].

## Design

- `lattice.py` holds the core: the **integral LLL** of Cohen, *A Course in Computational
  Algebraic Number Theory*, Alg. 2.6.7. It keeps the Gram determinants
  `d_i = B_1⋯B_i` and `λ_ij = d_j μ_ij` as integers. All divisions are exact, so it needs
  no fractions, no gcds and no floating point. It is several times faster than
  `Fraction`-based HPS pseudocode, and the results are identical. The size condition
  becomes `2|λ_kj| ≤ d_j`, and the Lovász condition with δ = p/q becomes
  `q(d_k d_{k-2} + λ²) ≥ p d_{k-1}²`. `check_reduced` evaluates both conditions and
  reports μ and B as exact fractions.
- **Dependent generators** (MLLL): `lll_generators` reduces `[N·B | I]` for a growing
  weight N. The output rows with a zero first block are integer relations. The remaining
  first blocks form a basis of L(B), and the code checks that they are independent before
  it reduces them. (This is the embedding method of Pohst and Havas–Majewski–Matthews.)
- `gauss.py` implements HPS §7.13.1 in integers. Collinear input reduces to Euclid's
  algorithm and returns a single vector.
- `crypto.py` implements the HPS 7.1 congruential attack (Gauss on [(1,h),(0,q)]; it
  checks the candidate key with the small blinding value r) and the HPS 7.2 knapsack
  attack (LLL with δ = 0.99 on the lattice of (2e_i, M_i) and (1…1, S). It tries the weights
  w = 1, ⌈√n⌉, n on the last column, and it scans the rows and the sums and differences of
  pairs of rows).

## What the restrictions forbid

The spec allows big-integer and linear-algebra libraries. The reference does not use
Sage's `LLL()`, `BKZ()`, `is_LLL_reduced()`, `gram_schmidt()`, `hermite_form()` or fpLLL/NTL
in the solver. Those are the oracle. It also avoids floating-point Gram–Schmidt, because
the spec stresses correctness, and exactness is what makes the check meaningful.

## Tests

`tests/test_reference.py` compares the reference with Sage on seeded random inputs: the
GSO against `gram_schmidt` over QQ; reducedness by an exact Sage check; equality of the
lattices by `hermite_form`; the 2-dim minima from fpLLL plus enumeration. The tests cover
the corner cases: μ = ±1/2, Lovász with equality, δ = 1 and δ ≈ 1/4, dependent, zero and
repeated vectors, rank-deficient sets, an already reduced basis (it stays unchanged) and
the HPS Example 7.67. They also run the generator and the verifier on every op and check
the CLI.
