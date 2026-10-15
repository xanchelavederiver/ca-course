# Pohlig–Hellman — reference solver (instructor-only)

Solves g^x = h in (Z/pZ)^* by the Pohlig–Hellman reduction, implementing every item of
the spec's «Требуемый функционал» by hand.

## Usage

```sh
# JSON lines on stdin -> JSON lines on stdout (one answer per request, flushed)
echo '{"id": 1, "input": {"p": 1000003, "g": 2, "h": 12345, "factors": [[2,1],[3,1],[166667,1]]}}' \
  | docker compose run --rm -T --entrypoint sage taskgen -python materials/capstone/02-pohlig-hellman/reference/solver.py
make test-capstones CAPSTONE=pohlig-hellman      # pytest vs Sage oracles
make bench CAPSTONE=pohlig-hellman               # vectors + timing + requirements.tex
```

Input: `p`, `g`, `h` (ints or decimal strings), optional `factors` = factorization of
p − 1 as `[[q, e], ...]`, optional `prime_method` (`auto` | `brute` | `bsgs`) and
`prime_power_method` (`digits` | `direct`). Output: `{"x": x}` with x = log_g h in
[0, ord g). Malformed input, a composite p, wrong factors or h ∉ ⟨g⟩ give `{"error": ...}`.

`extra` keeps the intermediate data the spec asks to save («система сравнений …, решения
«маленьких» задач»):

| key | meaning |
|---|---|
| `order`, `order_factors` | n = ord(g) and its factorization |
| `factorization` | `input` (from `factors`) or `solver` (factored here) |
| `congruences` | the reduced system x ≡ x_i (mod q_i^e_i) as `[[x_i, q_i^e_i], ...]` |
| `subproblems` | per prime: q, e, g_i = g^(n/q^e), h_i, x_i, the base-q digits of x_i, method |

## Design (`dlp.py`)

1. **Prime order q** — `dlog_brute` (q ≤ `BRUTE_MAX` = 64 in `auto`) or Shanks'
   baby-step giant-step `BabySteps` (table of ⌈√q⌉ baby steps, then giant steps by g^(−m)).
2. **Prime power q^e** — `dlog_prime_power`: x = d_0 + d_1 q + … ; each digit is a DLP of
   order q with the *same* base γ = g^(q^(e−1)), so the baby-step table is built once per
   prime and reused for all e digits. `prime_power_method: direct` skips the reduction and
   runs BSGS on the whole group of order q^e (the fallback that remark 2 of the spec allows).
3. **Composite order** — `pohlig_hellman`: ord(g) from the factorization of p − 1
   (`element_order`), then one prime-power problem per q_i, glued by `crt` (Garner).
   The order of g need not be p − 1.

Cost: Σ e_i·√q_i group operations; the largest prime factor of ord(g) dominates. On the
reference machine a 40-bit prime factor takes ≈ 1 s and ≈ 170 MB (a 2^20-entry dict),
44 bits ≈ 4 s and ≈ 650 MB (see `../bench/README.md`).

## What the restrictions forbid, and the factorization choice

The spec allows big-integer libraries and linear algebra, nothing DLP-specific, so the
solver uses only Python ints (`pow` for powers and inverses). It never calls Sage's
`discrete_log`, `log`, `znlog`, `multiplicative_order`, `factor`, `crt`; those are used
only by the tests and the vector generator (`taskgen/capstone/gens/pohlig_hellman.py`) as
the oracle. The solver does not even import Sage.

**The factorization of p − 1 is part of the input.** The spec's goal is the DLP, and its
three items all speak of "the order of the base" as known structure; factoring is not
part of the required functionality (and is the subject of other capstones). So each vector
carries `factors` of p − 1 (what a task statement would give, computed by the generator
with Sage), and the solver derives ord(g) itself from it — the order of g is generally a
proper divisor of p − 1. As a fallback, if `factors` is absent the solver factors p − 1 by
hand (`factor`: trial division, Pollard–Brent ρ, Miller–Rabin); this path is tested but
not benchmarked, since its cost (≈ 2^(b/2) steps for a b-bit factor, like BSGS) would
otherwise blur what the calibration measures.

## How the bench uses it

`bench/config.yaml` runs `sage -python reference/solver.py` in the `taskgen` image, one
process per size class; `taskgen/capstone/gens/pohlig_hellman.py:verify` accepts any x
with g^x ≡ h (mod p). The `p100` class gives `\ReqSeconds`.
