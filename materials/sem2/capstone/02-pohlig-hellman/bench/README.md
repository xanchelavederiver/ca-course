# Pohlig–Hellman — calibration notes

Measured table: `results.md` (generated). Vectors: `taskgen/capstone/gens/pohlig_hellman.py`,
seed 20261014. Reference: `../reference/` (pure Python ints, BSGS + digit reduction + CRT).

## The original spec's numbers

«тестовые примеры с числами размеров примерно **50–100 бит** должны выполняться за
приемлемое время – несколько десятков секунд». No other number; nothing about the
structure of p − 1.

## What drives the cost

Not the size of p. Pohlig–Hellman costs Σ e_i·√q_i over the prime factors q_i^e_i of
ord(g), so a 100-bit p with smooth p − 1 is instant, while a safe 100-bit prime
(p − 1 = 2q) needs 2^50 BSGS steps and is out of reach for anyone. "50–100 bits in tens
of seconds" is only meaningful with a bound on the largest prime factor of ord(g). The
generator therefore takes `qmax_bits` per size class (every prime factor of p − 1 has at
most that many bits; tag `qmax-B`, plus `lpf-b` = actual bits of the largest prime factor
of ord g).

BSGS alone, one prime-order subgroup, h = g^(q−1) (worst case), reference machine,
measured while other benchmarks ran:

| q, bits | time, s | peak RSS, MB |
|---|---|---|
| 32 | 0.05 | 220 (incl. Sage start-up) |
| 36 | 0.16 | 240 |
| 40 | 0.9 | 335 |
| 44 | 3.7 | 660 |
| 48 | not finished (≈ 15 s and ≈ 2–3 GB extrapolated; killed) |

Time grows 4× per 4 bits, memory as 2^(B/2) dict entries. B = 40 is where a Python
BSGS still takes ~1 s and ~170 MB, so a 10× slower student solution meets "tens of
seconds". B = 44 already needs ~0.7 GB in the reference and several GB in a naive one.

## Size classes

| class | p, bits | qmax, bits | n | purpose |
|---|---|---|---|---|
| p20 | 20 | 18 | 10 | small p (`small-p`): brute force territory |
| p30 | 30 | 28 | 12 | small |
| p50, p70, p90, p100 | 50–100 | 40 | 12–20 | the spec's range |
| p120 | 120 | 44 | 8 | a step beyond, in both p and the factor bound |

Each vector draws a shape of p − 1 (`smooth`, `prime-power` = one q^e of 30–60 % of the
bits, `max-prime` = one factor of exactly qmax bits [double weight], `random`), a kind of
base (`generator`, `subgroup` = order a proper divisor of p − 1, `prime-order`,
`prime-power-order`) and an exponent (random, `x-zero`/`h-one`, `x-max` = n − 1).
p20–p70 are committed (16 KB); p90–p120 are regenerated from the seed.

## Measurements (first run, 2026-10-14, AMD EPYC 7352, load ≈ 4 from other agents)

| class | median, s | max, s | max × 10, s |
|---|---|---|---|
| p50 | 0.23 | 0.68 | 6.8 |
| p70 | 0.46 | 1.05 | 10.5 |
| p90 | 0.03 | 0.89 | 8.9 |
| p100 | 0.32 | 1.23 | 12.3 |
| p120 (q ≤ 44 bits) | 0.09 | 3.2 | 32 |

The curve is flat over 50–100 bits (the bound B = 40 is the same), as the cost model says;
the median depends on how often a 40-bit factor lands in ord(g). The reference passes
100 % of the vectors.

## Derived requirements (slack 10×)

- `\ReqBitsMin` = 50, `\ReqBitsMax` = 100 — the spec's range (values).
- `\ReqQBitsMax` = 40 — the prime-factor bound of ord(g) used for the range (value).
- `\ReqSeconds` = slack × max(p100), rounded up on the 1-2-5 series: **20 s**.

**Verdict: confirmed.** 20 s is "несколько десятков секунд" (the lower end) for
50–100-bit p, provided the prime factors of ord(g) stay within 40 bits. The spec text now
states that bound in a parenthesis (the only addition to the original wording besides
the macros), since without it the requirement is not satisfiable for arbitrary p.

## Open questions for the instructor

1. Is the bound "prime factors of ord(g) ≤ 40 bits" acceptable in the spec, and was this
   roughly the shape of the examples used at past defences? A bound of 44 bits gives
   ~4 s / 0.7 GB in the reference (×10 = 50 s) — also "tens of seconds", but memory-heavy.
2. The vectors give the factorization of p − 1 in the input; the solver computes ord(g)
   itself. Should students be expected to factor p − 1 themselves (the spec allows big-int
   libraries, i.e. Sage's `factor` is arguably fine)? The reference has a hand-written
   fallback factorizer either way.
3. Slack 10× against a ~1 s reference: a student BSGS in pure Python with a list instead of
   a dict would fail; is that the intended strictness?
