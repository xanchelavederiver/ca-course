# Index calculus — calibration notes

## Original spec

«…тестовые примеры с числами размеров примерно **100-150 бит** должны выполняться за
приемлемое время – несколько десятков секунд.» Step 1 asks for B and the expected
number of trials from the L(p) estimate (HPS §3.7.1). Smoothness may be checked "directly,
by trial division over the factor base", and linear algebra packages are allowed.

## What the reference measures

`sage -python reference/main.py`: B = L(p)^(1/√2), about π(B)·1.05 relations from
`γ^k mod p`, linear algebra modulo every prime power of p − 1 (Sage: echelon forms mod ℓ
and one rational solve, then CRT), then the individual logarithm. The smoothness test is
`P^(2^s) mod r == 0` with gmpy2 (≈1 µs per candidate); smooth candidates are then factored
by trial division. The vectors (`taskgen/capstone/gens/index_calculus.py`) mix random,
safe, `2^k`/`3^k | p − 1` and smooth-order primes, primitive-root and non-generator bases
(subgroup, prime order, small order), and h = 1, g, g^-1 or random. Almost every h is
not B-smooth (tag `h-not-smooth`). Expected answers come from PARI's `znlog`, and `verify`
accepts any x with g^x ≡ h.

Measured on the AMD EPYC 7352 (`results.md`; other benchmarks ran at the same time, so the
timings are noisy):

| class | median, s | max, s | relations step / linalg (typical) |
|---|---|---|---|
| p40 | 0.07 | 0.09 | — |
| p50 | 0.43 | 0.67 | 0.15 / 0.3 |
| p60 | 3.4 | 4.6 | 1.2 / 2.9 |
| p64 | 6.6 | 7.8 | 2.2 / 5.4 |
| p70 | 26 | 28 | 12 / 13 |
| p80 | 182 | 198 | ≈ 50 % / 50 % |

The time grows like L(p)^√2 (×6–7 per 10 bits around 60 bits). At 80 bits the factor base
has ≈ 5000 primes, the dense core matrix is ≈ 4000 × 3500, and the peak RSS is 1.6 GB.
Extrapolated: 100 bits ≈ 2 h, 150 bits is far out of reach (L(2^150)^√2 ≈ 10^13 trials).

## Derived requirements (slack 10)

- `\ReqBitsMin`–`\ReqBitsMax` = **50–60 bits** (values).
- `\ReqSeconds` = 10 × max(p60), rounded up on the 1-2-5 scale: **50 s**. This matches the
  original wording "несколько десятков секунд".

## Confirmed or adjusted?

**Adjusted: 100–150 bits → 50–60 bits.** The method the spec describes (random `g^k`,
B = L(p)^(1/√2), trial-division smoothness) needs about L(p)^√2 trials: ≈ 10^6 at 60 bits,
≈ 10^9 at 100 bits and ≈ 10^13 at 150 bits. No implementation of *this* method gets to
100–150 bits in tens of seconds. That size needs the linear sieve or other sieve
variants, or at least the rational-reconstruction trick (test two numbers of size √p
instead of one of size p). The number in the original spec was probably copied from
another capstone (Pohlig–Hellman also says 50–100 bits).

**Plain trial division** (`"smooth": "trial"` in the input runs the same reference with
it): p50 takes 6–10 s and p60 takes 73–95 s, so it is 10–20× slower than the reference in
step 2. A student who follows the spec literally in pure Python therefore meets the
50 s limit at 50–56 bits, and at 60 bits only with a faster smoothness test (the product
trick above, gcd with the primorial, early abort) or a compiled language. No C helper was
needed for the reference.

## Open questions for the instructor

1. Accept 50–60 bits / 50 s? Or, to let the literal trial-division approach pass at 60
   bits, use `slack: 25` (or `ReqBitsMax: 56`)?
2. Should the spec mention a faster smoothness test (product of the factor base or
   rational reconstruction) as an optional item, given that it already allows "напрямую"?
3. The reference builds the system on a primitive root γ when g is not one (the factor-base
   primes need not lie in ⟨g⟩). The spec's step 3 says "по основанию g". Should the spec say
   that g is a primitive root, or keep non-generator bases as a "why?" moment?
4. With π(B) + 5 % relations, ≈ 10–15 % of the factor-base logarithms stay undetermined:
   primes that occur in no relation, or that the rank-deficient sparse core does not pin
   down. Step 4 just avoids them. Students who demand a full-rank system will collect noticeably
   more relations than the estimate. That could be a good footnote question.
