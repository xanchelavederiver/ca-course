# Calibration notes — capstone 01, «Арифметика больших чисел»

## The original spec's numbers

The original names a size but no time: «приемлемой будет считаться скорость работы,
позволяющая выполнять базовые арифметические операции с числами длиной примерно
**2048 бит**» (footnote: the current RSA length). Footnote 1 bounds the length at
512·4·8 = **16384 bits**. The port keeps both. It adds concrete per-operation thresholds
for 2048-bit numbers, derived below, so that «приемлемая скорость» can be checked at the
defence.

## What is measured

The reference is `reference/build/bigint-solver` (C, `-O2 -march=x86-64 -mno-avx`, no
GMP). One vector is one operation. The vector's `repeat` makes the solver repeat it R
times, R chosen by the generator's cost model so that a request takes ~30 ms. The
requirement macros use the **per-operation** time wall / R (`stat: max_op`). Request
overhead (JSON, hex conversion, pipe) is then below 1% even for an addition.

| class | contents | used for |
|---|---|---|
| `b256` … `b4096` | 72 vectors each, all 18 operations, random signs, ~30% corner cases | correctness, scaling |
| `b16384` | 30 vectors, R ≈ 1, multiplication/division/xgcd/Montgomery/powmod at 16384 bits | footnote 1 (correctness) |
| `corner128`, `corner1024` | 80 corner cases each (see below) | correctness |
| `mul2048` | `mul_school`, `mul_karatsuba`, `sqr`, 2048 × 2048 bits | `\ReqMulUs` |
| `div2048` | `divmod`, `mod`, 4096-bit dividend / 2048-bit divisor | `\ReqDivUs` |
| `gcd2048` | `gcd`, `xgcd`, `inv`, 2048 bits | `\ReqGcdMs` |
| `powmod2048` | `powmod_binary`, `powmod_qary` (q ∈ {2, 4, 8, 16}), 2048-bit odd modulus and exponent | `\ReqPowmodMs` |

The corner cases are zero, ±1, a = ±b, different lengths, carry/borrow through all limbs,
the Karatsuba thresholds (T ± 1, 2T ± 1 limbs, unbalanced) and thresholds forced down to
2–5 limbs, Algorithm D's step D6 (constructed, see `addback_pair`; the solver's
`extra.addbacks` confirms it) and q̂ = B − 1, exact division, a single-limb divisor,
consecutive Fibonacci numbers (Euclid's worst case), gcd(0, 0), non-invertible elements,
shifts by 0/63/64/65 and beyond the length, negative operands of `shr`, a ≡ 0 (mod m),
unreduced and negative bases, e = 0/1/2, 0⁰, even moduli, m = 2ᵏ, m = 1.

A full `make bench` takes ~30 s, most of it in the full-size 16384-bit powmods. Every
vector passes (100%).

## Reference times (median per operation, µs; reference machine, AMD EPYC 7352)

Measured while other benchmarks ran concurrently (load ≈ 8), so the maxima are noisy.
The lead's serial re-run replaces them.

| op | 256 | 512 | 1024 | 2048 | 4096 | 16384 |
|---|---|---|---|---|---|---|
| add / sub | 0.014 | 0.015 | 0.021 | 0.036 | 0.070 | — |
| mul_school | 0.053 | 0.11 | 0.35 | 1.2 | 4.8 | 99 |
| mul_karatsuba | 0.055 | 0.11 | 0.34 | 1.15 | 3.6 | 47 |
| sqr | 0.055 | 0.10 | 0.24 | 0.76 | 2.5 | 33 |
| divmod (2n / n) | 0.16 | 0.31 | 0.72 | 2.2 | 6.9 | 137 |
| mont_mul | 0.083 | 0.21 | 1.3 | 2.6 | 8.8 | 219 |
| gcd | 11 | — | 62 | 157 | 463 | — |
| xgcd / inv | — | 61 | 157 | 370 | 1050 | 12300 |
| powmod (q = 16, full exponent) | 39 | — | 907 | 7100 | 44800 | 2.3·10⁶ |

At 2048 bits Karatsuba is only ~5% faster than schoolbook (the threshold is 24 limbs and
2048 bits are 32), and it wins clearly from 4096 bits. Squaring is ~1.5× faster than a
product (remark 1). Montgomery multiplication costs about one product plus one REDC
(~n² limb products). Euclid makes ~0.6·bits division steps, which is why gcd costs
~100 products.

## Requirements (slack 10×, rounded up to 1-2-5)

| macro | class, stat | reference | requirement |
|---|---|---|---|
| `\ReqBits` | value | — | 2048 |
| `\ReqMulUs` | `mul2048`, max_op | 1.2 µs (median 1.15) | **20 µs** |
| `\ReqDivUs` | `div2048`, max_op | 4.3 µs (median 2.1) | **50 µs** |
| `\ReqGcdMs` | `gcd2048`, max_op | 0.78 ms (median 0.23; xgcd/inv ≈ 0.38) | **10 ms** |
| `\ReqPowmodMs` | `powmod2048`, max_op | 13.5 ms (median 6.9) | **200 ms** |

The spec's size (2048 bits) is **confirmed**: everything is fast there, even with the
plain schoolbook method. The time thresholds are **new**. They follow the plan's rule,
reference × slack, which gives a student 10× the reference time. On a quiet machine the
maxima approach the medians, and the serial re-run should give ≈ 20 µs / 50 µs / 5–10 ms
/ 100 ms. Python's built-in `int` meets all four; a pure-Python limb-array class does not
(it is ~100× slower). This matches the spec's tone about php/JS: a slow language must
prove itself.

## Open questions for the instructor

1. **Should the thresholds be part of the spec at all?** The original gives none. The
   port states them as «ориентиры» for one core of a modern x86-64. They are easy to
   relax (`slack:` in `config.yaml`) or to remove from `spec.tex`.
2. **Which operations count as «базовые»?** The port requires multiplication, division,
   gcd/inverse and modular exponentiation. Addition and shifts are too fast to matter
   (~0.04 µs).
3. **Euclid vs. Lehmer/binary gcd.** The reference does what the spec says (Euclid with a
   full division per step). A student with Lehmer's algorithm would be ~5× faster, which
   is fine.
4. **Even moduli in modular exponentiation.** The reference falls back to reduction by
   division and reports `"method": "division"`; Montgomery operations with an even
   modulus are errors. Should students be required to handle even m (the vectors include
   it)?
5. **The plot.** `plot.png` shows the wall time per request, which is ~30 ms by
   construction (repeat). The per-operation curve is in the table above. A framework
   option to plot `median_op` would show it (see the final report).
