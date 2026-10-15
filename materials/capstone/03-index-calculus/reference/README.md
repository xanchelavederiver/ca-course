# Index calculus — reference implementation (instructor-only)

The reference solver of capstone 3 (`spec.tex`): the index-calculus method for
`g^x ≡ h (mod p)` in GF(p)^*, written under the student's restrictions. It implements
every item of «Требуемый функционал»:

| spec item | module | what it does |
|---|---|---|
| 1. B, the number of B-smooth numbers, the expected number of trials | `icalc/params.py` | `B = L(p)^(1/√2)`, `L(x) = exp(√(ln x · ln ln x))`; relations needed `π(B) + max(10, 5 %)`; expected trials `needed / ρ(u)`, `u = ln p / ln B` (Dickman ρ, tabulated), plus the asymptotic `L(p)^√2` and the cruder `u^-u` of HPS §3.7.1 |
| 2. B-smooth numbers and the system of congruences | `icalc/relations.py` | residues `γ^k mod p`, `k = k0, k0+s, k0+2s, …`; smoothness test `P^(2^s) ≡ 0 (mod r)`, `P = ∏ q ≤ B` (one `gmpy2.powmod`); only smooth residues are factored by trial division over the factor base |
| 3. logs of the factor base | `icalc/linalg.py` | singleton pruning; the system modulo each prime power `ℓ^a ∥ p−1` via a square subsystem invertible mod ℓ solved over Q; CRT |
| 4. B-smooth `h·g^-k` and the answer | `icalc/relations.py`, `icalc/solver.py` | `h·γ^-k mod p` smooth over the primes of known log; `log h = k + Σ e_i log q_i` |
| (by hand) | `icalc/nt.py` | Eratosthenes, Miller–Rabin, Pollard–Brent ρ for `p − 1`, CRT, multiplicative order, primitive root |

## Usage

JSON lines on stdin/stdout (the capstone contract, `materials/capstone/README.md`):

```sh
echo '{"id": 1, "input": {"p": 1000000007, "g": 5, "h": 123456789}}' \
  | docker compose run --rm -T --entrypoint sage taskgen -python \
      materials/capstone/03-index-calculus/reference/main.py
```

Input: `p, g, h` (ints), optional `B` (explicit smoothness bound), `c` (`B = L(p)^c`),
`margin` (extra relations, default 0.05), `smooth` (`"powmod"`, the default, or `"trial"`: plain trial division of every candidate), `seed` (default: derived from `p, g, h`, so
runs are reproducible), `full` (keep every relation and logarithm in `extra`).
Output: `{"x": x}` with `0 ≤ x < ord g`, or `{"x": null}` if `h ∉ ⟨g⟩`; bad input
(composite `p`, `g ≡ 0`, missing fields, bad JSON) gives `"error"`, never a crash.

`extra` keeps the intermediate data the spec asks for: `params` (L, c, B, u, ρ(u),
relations needed, expected and asymptotic trials), `factor_base_size`, `order_factors`,
`gamma` (the base of the system), `relations_found`, `trials`, `linalg` (core size,
rank, singletons, rational solves, determined columns per prime power), `logs_known`,
`factor_base_logs` (all of them when the factor base has ≤ 200 primes or `full`, else the
first 20), `relations_sample` (the first 10 relations, or all with `full`),
`individual_h` / `individual_g` (the found `k`, the smooth residue and its factorization),
`log_gamma_h`, `log_gamma_g` and `seconds` per step.

## Design notes

- **Base of the system.** If `g` is a primitive root the relations are `g^k`, as in the
  spec. Otherwise the factor-base primes need not lie in `⟨g⟩`, so the system is built on
  a primitive root `γ` (found from the factorization of `p − 1`, which the CRT needs anyway),
  step 4 runs for `h` and for `g`, and `x · log_γ g ≡ log_γ h (mod p − 1)` gives `x`
  modulo `ord g` (no solution iff `h ∉ ⟨g⟩`).
- **Composite modulus `p − 1`.** For each `ℓ^a ∥ p − 1`: echelon form modulo ℓ; pivot
  columns are independent mod ℓ, free ones are set to 0; a column is *determined* iff its
  reduced-echelon row vanishes on the free columns. A square subsystem `S` on the pivot
  columns has `det S ≢ 0 (mod ℓ)`, so `S^-1 b` over Q (FLINT/IML, denominators coprime to ℓ)
  reduced mod `ℓ^a` is the unique solution — no Hensel lifting. One subsystem (chosen modulo
  a 23-bit prime) usually serves every ℓ; ℓ = 2 often needs its own (its determinant
  tends to be even). Every logarithm is finally checked (`γ^x ≡ q`).
- **Not every prime gets a log.** With ~π(B) relations many large factor-base primes
  occur in no relation or are not pinned down (the core is rank-deficient: about 85–90 %
  of the logs are known). Step 4 simply waits for a residue that factors over the known
  primes. If fewer than half the logs are known, 10 % more relations are collected.
- **Exponent progression, not `k+1`.** Consecutive exponents are a trap for a small `γ`
  (e.g. 2): `r` smooth ⇒ `2r` smooth, so the relations come in near-duplicate runs
  (we observed a rank of 155 out of 313 columns with 519 rows). A random step `s`
  coprime to `p − 1` fixes it at the same cost (one multiplication by `γ^s`).
- **Smoothness test.** `powmod(P, 2^s, r) == 0` replaces π(B) trial divisions for the
  non-smooth majority (~1 µs per candidate with gmpy2); the smooth ones are factored by
  trial division, as the spec suggests. Students doing plain trial division over the
  whole factor base will be slower by a factor of ~π(B)/10 in step 2; the slack covers
  part of that (see `bench/README.md`).
- **Tiny p.** If `p − 1 ≤ 4 ×` the relations needed, every exponent is tried once and
  the system is solved with what there is.

## What the restrictions forbid

Sage's `discrete_log`, `log`, `factor`, `primitive_root`, `multiplicative_order`,
`is_prime` are not used by the solver (only by the tests and the vector generator, as
the oracle). It uses Python ints, `gmpy2` (spec reference [2]) and Sage matrices for
linear algebra (echelon forms mod ℓ, ranks, rational solving), which the spec allows.

## Tests and the bench

`reference/tests/` (pytest, `make test-capstones CAPSTONE=index-calculus`): `nt` against
Sage's `prime_range`, `is_prime`, `factor`, `primitive_root`, `multiplicative_order`;
Dickman ρ against known values; the relations; every computed factor-base log against
PARI's `znlog`; the solver on random `p` of 12–52 bits with generators, subgroup bases,
safe primes, `2^24 | p − 1`, `3^15 | p − 1`, all `(g, h)` for `p ≤ 13`, `h = 1`, `h = g`,
`g = −1`, `h ∉ ⟨g⟩`, bad input and the CLI.

`make bench CAPSTONE=index-calculus` runs `sage -python reference/main.py` over the
vectors (`taskgen/capstone/gens/index_calculus.py`); `bench/README.md` has the
calibration notes.
