# Calibration notes: Lenstra's ECM (capstone 5)

## The original spec

> тестовые примеры с числами размеров примерно **50-100 бит** должны выполняться за
> приемлемое время – несколько десятков секунд.

There is one number pair: n of 50--100 bits, "tens of seconds". The hardest n of a given
size for ECM is a balanced semiprime, so the requirement is calibrated on n = p q with
p, q of n/2 bits; the worst case of the spec is n = 100 bits, p = 50 bits.

## What is measured

`config.yaml` runs `reference/main.py --family weierstrass`: Lenstra's random curves
`y^2 = x^3 + a x + b` in affine coordinates (items 1--3 of the spec, no special
parametrisation), stage 1 with prime powers <= B1, the standard stage 2 with B2 = 100 B1,
and B1 and the number of curves chosen per level from the expected factor size
(`reference/lenstra/params.py`). Random choices are seeded by n, so each vector takes the
same curves on every run.

Classes (x = bits of the smallest prime factor):

- `pX-n2X`, X = 10, 15, ..., 50: balanced semiprimes, `op: factor` (any proper factor
  is accepted). X = 25--50 is the spec's range of n = 50--100 bits.
- `p55-n110`, `p60-n120`, `p65-n130`: a step beyond (not committed, regenerated from the seed).
- `unbalanced-n100`, `square-n100` (p^2 q and p q^2), `power-n100` (p^k), `multi-n100`
  (3--5 primes), `prime-n100` (n prime: the expected answer is "n is prime"): full
  factorization, `op: factorize`, n up to 100 (128 for unbalanced and prime) bits.

## Results (2026-10-14, AMD EPYC 7352, loaded machine: load average ~7)

| class | median, s | max, s |
|---|---|---|
| p25-n50 | 0.0035 | 0.022 |
| p40-n80 | 0.19 | 0.40 |
| p50-n100 | 0.97 | 3.5 |
| p55-n110 | 4.7 | 13 |
| p60-n120 | 12 | 38 |
| p65-n130 | 25 | 124 |

The other shapes of n take < 0.6 s (the smallest factor is <= 40 bits). All 154 vectors
pass. The full bench takes about 8 minutes.

Other configurations of the same reference (`taskgen.capstone check`, 8 vectors per
class; the stage-1-only row from a separate run of 5 random semiprimes per size):

| configuration | p40-n80 max, s | p50-n100 max, s | p60-n120 max, s |
|---|---|---|---|
| Weierstrass, stage 1 only (the "basic" algorithm) | 5.3 | 31 | 231 |
| Weierstrass + stage 2 (**the bench**) | 0.40 | 3.5 | 38 |
| Suyama (12 \| #E) + stage 2, Montgomery x-only | 0.19 | 1.2 | 3.9 |
| Z/2 x Z/8 (16 \| #E) + stage 2, Montgomery x-only | 0.19 | 0.55 | 2.7 |

## Requirements

- `\ReqBitsMin = 50`, `\ReqBitsMax = 100` (the spec's numbers, as values).
- `\ReqSeconds = 50`: 10 x max(p50-n100) = 35 s, rounded up to the 1-2-5 series.

**The spec's number is confirmed**: "несколько десятков секунд" for a 100-bit n, now
"не более 50 с". The spec text keeps its wording and adds the measured limit in brackets.
The reference without stage 2 (the minimum the spec asks for) also fits in it (max 31 s);
a student solution 10x slower than that would need stage 2 or a special family to pass,
which the remarks of the spec encourage anyway.

## Open questions for the instructor

1. Calibrate on Weierstrass + stage 2 (as now) or on the stage-1-only basic algorithm?
   The latter gives 10 x 31 s, i.e. a 500 s limit, much looser than the spec's
   "tens of seconds".
2. Is the 100-bit balanced semiprime the intended worst case, or did "50-100 бит" refer to
   n with a smaller smallest factor? With the latter the limit would be far below a second.
3. The spec allows libraries for elliptic curves. Sage's `EllipticCurve(Zmod(n))` makes the
   failed inversion an exception that carries the factor; arithmetic through it is roughly
   an order of magnitude slower than plain integers. Should the requirement assume plain
   integer arithmetic (as the reference) or Sage's curve objects?
4. The 16 | #E family: the reference uses its own derivation (README of the reference).
   C&P's "16" refers to Montgomery's / Atkin--Morain's families; any Z/2 x Z/8 or
   Z/4 x Z/4 construction should count.
