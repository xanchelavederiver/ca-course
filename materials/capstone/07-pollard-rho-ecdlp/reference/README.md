# Capstone 07 — reference solver (Pollard's rho for the ECDLP)

Instructor-only. A pure-Python solver (Python ints only; it does not import Sage) for
the JSON-lines contract of `materials/capstone/README.md`. It runs as
`sage -python reference/main.py` in the `taskgen` image (`bench/config.yaml`), and
`python3 reference/main.py` also works.

## Usage

```sh
echo '{"id":1,"input":{"p":10007,"a":1,"b":6,"P":[...],"Q":[...],"n":...,"method":"floyd"}}' \
  | python3 reference/main.py
```

| `op` | input | output | `extra` |
|---|---|---|---|
| `dlog` (default) | `p, a, b, P, Q` (`null` = O), `n` = ord(P) (computed if absent), `method`: `floyd` \| `dp`; optional `start` = [α₀, β₀], `max_iter`, `max_attempts`, `seed`, and for `dp` `r`, `theta` | `{"x"}`, 0 ≤ x < n | `method`, `n`, `attempts`, `iterations`, `retries`, `verified`, `seed` |
| `order` | `p, a, b, P` | `{"n": ord(P)}` | BSGS data: Hasse interval, M, factorization of M |

The spec's items map as follows:

1. **Search parameters.** `start` fixes the start point X₀ = [α₀]P + [β₀]Q of the first
   attempt. `extra.attempts[0].start_point` gives its coordinates. A start point given
   as bare coordinates would be useless, since rho needs its representation in P and Q.
   `max_iter` caps the collision-search loop: per attempt for Floyd, and in total for
   distinguished points.
2. **ord(P).** `rho_ecdlp/order.py` implements Shanks–Mestre. A BSGS over the Hasse
   interval [p+1−2√p, p+1+2√p] finds M with [M]P = O in O(p^¼) operations. M is then
   factored by hand (trial division plus Pollard–Brent, `ntheory.py`), and prime
   factors are stripped while [M/q]P = O. This is the "весомый плюс" of the remark.
   When a `dlog` request has no `n`, the solver uses this order. When `n` is given, it
   checks [n]P = O.
3. **Solve and check.** Both variants are in `rho_ecdlp/rho.py`:
   - `floyd` is Pollard's three-class walk (x mod 3: +P, doubling, +Q) with Floyd's
     tortoise and hare. It records α_i, β_i (X_i) and γ_i, δ_i (Y_i = X_{2i}), the
     collision point, and the congruence (β−δ)x ≡ γ−α (mod n) with d = gcd(β−δ, n). It
     lists **all** d solutions (the first 64 are kept in `extra`), then checks them by
     [x]P = Q.
   - `dp` uses distinguished points (x ≡ 0 mod 2^θ, θ = ⌊k/2⌋ − 5 by default) with
     Teske's r-adding walk (r = 20). Trails from random [a]P + [b]Q are stored at their
     distinguished point, and a second visit with different (a, b) gives the congruence.
   - A degenerate collision is recorded and the search goes on: either d is too large to
     enumerate (> 2¹⁶, e.g. β ≡ δ mod n), or no candidate verifies. Floyd restarts from a
     new random start (`retries` = restarts). DP walks on (`retries` = degenerate
     collisions).
   - Finally `extra.verified` rechecks [x]P = Q.

Randomness comes only from `random.Random(seed)`. The seed is `input.seed`, or else a
SHA-256 of the canonical request, so every request gives the same answer and the same
`extra`. Bad input gives an `"error"` answer instead of a crash: p not prime, a
singular curve, a point off the curve, [n]P ≠ O, `max_iter` exhausted, or Q ∉ ⟨P⟩.

## Restrictions

The spec allows students to use a library for the points and for linear algebra. The
reference is stricter, so that its timings measure rho itself and stay comparable to
any language. Sage points are also about 4.6× slower per addition at 40 bits:

- The curve arithmetic is affine, by hand (`ec.py`).
- It does not use Sage at all: no `EllipticCurve`, `discrete_log`, `P.order()`,
  `E.order()` or `factor`.

Those functions are the oracle only, used by the vector generator
`taskgen/capstone/gens/pollard_rho_ecdlp.py` and the tests.

## Tests

`make test-capstones CAPSTONE=pollard-rho-ecdlp` runs `reference/tests/`, which compares
against Sage on seeded random inputs:

- the curve arithmetic, `is_prime`, `factor`, and the linear congruences (against brute
  force);
- ord(P) on random, j = 0 and j = 1728 curves;
- both rho variants against `discrete_log` on prime, cofactor, a = 0 and composite-n
  instances;
- Q = O, P, −P; tiny n (degenerate collisions); a given start; determinism;
  `max_iter` exhausted; Q ∉ ⟨P⟩; a wrong n;
- the CLI contract;
- the generator's vectors, with a check that `verify` rejects wrong answers.

## Use in the benchmark

`make bench CAPSTONE=pollard-rho-ecdlp` starts one solver process per size class of
`bench/config.yaml`. The runner times every request and checks the answer with the
generator's `verify`. See `bench/README.md` for the classes and the calibration.
