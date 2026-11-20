# LLL capstone — calibration notes

## The original spec's numbers

The original («Мини-курсовая - LLL») gives **no sizes and no times**. It says only: «важна
не скорость, а корректность … Однако тестовые примеры должны выполняться за приемлемое
время» (footnote: «хотя бы до конца сдачи работы»). The port keeps this wording. It adds a
parenthetical guideline built from the `requirements.tex` macros: LLL in dimension up to
`\ReqDim` with entries up to `\ReqBits` bits in at most `\ReqSeconds` s, and the knapsack
attack with n = `\ReqKnapN` in at most `\ReqKnapSeconds` s. **Nothing is confirmed or
adjusted**, because there is nothing to confirm. The numbers are a proposal for the
instructor (see the open questions).

## What the reference measures per class

All classes ran 100 % correct. The reference uses exact integral LLL (Cohen 2.6.7) with
gmpy2 integers. Times are from `results.md` on the shared machine (load ≈ 6, so they are
noisy). The whole bench takes about 1.5 min.

| class | op / content | max, s |
|---|---|---|
| gauss (30) | Gauss reduction, 8–512-bit entries; scrambled, already reduced, equal norms, collinear (rank 1), zero vector, Z^3, the HPS example | 0.007 |
| check (30) | LLL-reducedness check, n = 1..10, δ ∈ {1/2, 3/4, 0.99, 1}; μ = ±1/2, Lovász with equality, swapped/size-violating, dependent | 0.002 |
| corner (36) | LLL on dependent generators (MLLL: n+1 of rank n, rank-deficient, zero, duplicate), nearly dependent, already reduced, orthogonal, dim 1, δ = 1, δ = 0.26 | 0.03 |
| cong (12) | HPS 7.1 congruential attack, q of 32–1024 bits | 0.005 |
| knap16/32/48/64 | HPS 7.2 Merkle–Hellman attack (the lattice dimension is n+1) | 0.012 / 0.08 / 0.35 / 0.74 |
| lll5 … lll50 | random bases of dimension n: uniform, rectangular, knapsack-type (e_i, a_i), q-ary Λ_q(A) with k = n/2, U·R scrambled; 16/64/128-bit entries; δ ∈ {3/4, 0.99} | see the plot |

The cost of LLL depends mostly on the *kind* of lattice, not only on n. The slowest
instances are q-ary lattices with a 128-bit q (half of the columns are large) and scrambled
U·R bases. Uniform and knapsack-type bases with one large column take 0.1 s even at n = 50.
That is why the median in the plot is flat and the maximum grows (lll30: 5.2 s, a q-ary
lattice with a 128-bit q).

A first calibration used entries up to 256 bits. A 30-dimensional q-ary lattice with a
256-bit q took 150 s with Python ints (an estimated 40–55 s with gmpy2). That is too slow for "≈ 15 min
for the whole bench" and for a student solution under 10× slack, so the entry sizes are
16/64/128 bits and `\ReqBits` = 128. With plain Python ints instead of gmpy2, the reference
is 3–4× slower (lll30-000 takes 23 s instead of 5.2 s, still under `\ReqSeconds`).

## Derived requirements (slack 10×)

| macro | value | source |
|---|---|---|
| `\ReqDim` | 30 | proposed (the plan's "dimension 5..30") |
| `\ReqBits` | 128 | proposed (see above) |
| `\ReqSeconds` | 100 | max of lll30 (5.2 s) × 10, rounded up to 1-2-5 |
| `\ReqKnapN` | 48 | proposed |
| `\ReqKnapSeconds` | 5 | max of knap48 (0.35 s) × 10, rounded up |

## Open questions for the instructor

1. The spec has no performance numbers. Should the parenthetical guideline stay, or should
   the spec keep only «приемлемое время»?
2. Is 100 s fair for students who use `Fraction` (HPS pseudocode with rationals)? Such code
   can be 10× or more slower than the integral version on q-ary lattices. A floating-point
   LLL would be much faster, but the spec stresses correctness. Should floating point be
   allowed?
3. Footnote 3 says «п.п. 6.1–6.2 в [2]» with [2] = HPS **2nd ed.** Those sections (the
   congruential and knapsack cryptosystems) are 6.1–6.2 in the 1st edition and 7.1–7.2 in
   the 2nd. The footnote is kept verbatim. Should it say 7.1–7.2?
4. Should dependent generating vectors (MLLL) be required, or is "базовая версия" only
   about bases? The reference supports them. Only the `corner` class contains them.
