# Quadratic sieve — reference implementation

Instructor-only. A single-polynomial quadratic sieve, f(t) = t² − N, in plain Python
(Python ints only), run with Sage's Python (`sage -python`, image `taskgen`) only so
that the tests can use Sage as the oracle. It does not import Sage at all, unless you
ask for `--linalg sage`.

## Usage

```sh
# JSON lines on stdin -> JSON lines on stdout (one answer per request, flushed)
echo '{"id": 1, "input": {"n": 1000000016000000063}}' | sage -python reference/main.py
echo '{"id": 2, "input": {"n": 30030, "full": true}}'  | sage -python reference/main.py
```

- input: `n` (an int, or a decimal string); `full: true` also asks for the complete
  factorization; `trace: true` adds the factor base, every B-smooth relation and the
  dependency used to `extra` (large: thousands of entries at 100 bits).
- output: `{"factor": d, "cofactor": n // d}` with 1 < d < n, plus
  `"factorization": [[p, e], ...]` when `full`.
- `extra` (the intermediate data the spec asks to keep): `method` (`qs`,
  `trial-division`, `perfect-power`); `L_N`, `B_theory` = L^(1/√2) and `length_theory` = L^√2
  (HPS 3.7.1); the `B` used, `fb_size`, `relations_needed`, `expected_length` (Dickman ρ
  estimate); `sieve_length` actually sieved, `blocks`, `candidates` (passed the log
  threshold), `relations`, `prime_powers_sieved`, `matrix` (rows × columns), `dependencies`
  (left-kernel dimension), `dependencies_tried`, `gcds` (gcd(x − y, N) of the dependencies
  tried), `dependency_size`, `x`, `y`; `times_s` per stage; with `full`, `splits` (the
  later splits of the cofactors).
- bad input or a prime n: `{"id": ..., "error": "ValueError: ..."}`; the solver never crashes.
- options: `--b-factor X` (B = X · L(N)^½, default 4), `--linalg gauss|sage`.

## Design (files)

| file | spec item | contents |
|---|---|---|
| `qs_numtheory.py` | — | Eratosthenes, Legendre symbol (Euler's criterion), Tonelli–Shanks, Hensel lifting of roots to p^k, Miller–Rabin, integer k-th roots, perfect-power detection |
| `qsieve.py` `choose_params` | 1 | B = 4·L(N)^½ (≥ 50); factor base {2} ∪ {odd p ≤ B : (N/p) = 1}; needed = \|FB\| + 1 (sign) + 16; expected length l solving l·ρ(u) = needed, u = (ln(√N·l/2) − KS bonus)/ln B, where the Knuth–Schroeppel bonus is the excess of small factor-base primes over a random number |
| `qsieve.py` `sieve` | 2 | blocks of 2¹⁶ values of x (t = ⌊√N⌋ + x), alternately right and left of √N (so the sign −1 is a factor-base column); a `bytearray` accumulates round(log₂ p) for every q = p^k ≤ B dividing f (roots by Tonelli–Shanks + Hensel); primes < 30 are not sieved (remark 3); a regex finds the bytes ≥ log₂\|f\| − fudge (fudge = ½·log₂ B + 4 bits) per chunk of 2¹¹; candidates are trial-divided by the primes whose root matches x mod p |
| `qs_linalg.py` | 3 | incremental Gaussian elimination over GF(2) on bit-mask rows with a history mask per row: every row that reduces to 0 gives one dependency (a basis of the left kernel); `dependencies_sage` is the same via Sage's `GF(2)` matrices (allowed by the spec; used as a cross-check) |
| `qsieve.py` `square_root_step`, `qs_split` | 4 | x = ∏t, y = ∏p^(e/2) (mod N), check x² ≡ y², d = gcd(x − y, N); dependencies are tried in turn; if all are trivial (never seen), more relations are collected and the matrix is redone |
| `qsieve.py` `split`, `factorize` | — | primality (Miller–Rabin), perfect powers, trial division up to B, then QS; `factorize` splits recursively |
| `main.py` | — | the JSON-lines CLI |

Corner cases: the sieve cannot split prime powers (the unit group mod p^k is cyclic, so
x² ≡ y² forces x ≡ ±y), so n = p², p³, m² are detected as perfect powers first; a prime
factor ≤ B is found by trial division (QS needs gcd(N, p) = 1 over the factor base);
even n is just such a case. Repeated factors (p²q), close factors and 3–4 prime factors
go through QS normally.

Not implemented (optional in the spec's remarks, or not mentioned): multiple polynomials
(MPQS/SIQS, remark 5), the large-prime variation, a Knuth–Schroeppel multiplier. A C sieve
helper was tried and dropped: plain Python already does 100 bits in under a second.

## What the restrictions forbid

The spec allows bigint libraries, linear algebra packages and library square roots mod p.
The reference uses only Python ints (`pow`, `math.isqrt`, `math.gcd`) and hand-written
Tonelli–Shanks and Gaussian elimination (the Sage `GF(2)` kernel is an option). It never
calls Sage's `factor`, `qsieve`, `ecm`, `is_prime`, `sqrt` mod p or `discrete_log`: those
are the oracle of the vectors (`taskgen/capstone/gens/quadratic_sieve.py`) and of the tests.

## Tests and the bench

```sh
make test-capstones CAPSTONE=quadratic-sieve   # reference/tests vs Sage (pytest, ~20 s)
make bench CAPSTONE=quadratic-sieve            # vectors + timings -> bench/, requirements.tex
docker compose run --rm --entrypoint sage taskgen -python -m taskgen.capstone verify-reference quadratic-sieve
```

The tests compare each helper with Sage (`prime_range`, `legendre_symbol`, `is_prime`
incl. Carmichael numbers, `nth_root`, `GF(2)` kernels), check every relation and the
congruence of squares, the sieve yield against brute force, `factorize` against
`factor`, the CLI contract (errors included) and the generator/verifier. The bench runs
`sage -python reference/main.py` over `vectors/` (see `bench/config.yaml`); `verify`
accepts any non-trivial divisor, and the full factorization where it is asked for.
