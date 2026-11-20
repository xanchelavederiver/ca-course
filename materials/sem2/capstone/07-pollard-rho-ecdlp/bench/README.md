# Capstone 07 — calibration notes (Pollard's rho for the ECDLP)

## What the original spec says

> тестовые примеры с числами размеров примерно **50-100 бит** должны выполняться за
> приемлемое время – несколько десятков секунд.

The spec does not say which "numbers" are meant. The rho algorithm takes about
√(πn/2) steps, where n = ord(P), and the size of p barely matters. So a 100-bit n is out
of reach for anyone (about 2⁵⁰ steps). Even a 50-bit n takes the reference Floyd
variant about 10 minutes (extrapolated: ×4–5 per 4 bits, see below). The only reading
that fits "50–100 bits in tens of seconds" is p of 50–100 bits with ord(P) much smaller.

## Size classes (`config.yaml`)

| classes | what is measured |
|---|---|
| `n20` … `n44` (plotted, x = k) | `dlog` with Pollard's 3-class walk + Floyd (the spec's method, coefficients α, β, γ, δ), n = ord(P) of exactly k bits, p ≈ k…k+6 bits. The small classes contain all corner cases: prime-order curves, cofactor > 1, a = 0, b = 0, composite n, Q = O / P / −P, a given start and max_iter |
| `dp20` … `dp44` | the same with distinguished points + the r-adding walk (r = 20) |
| `p64-n32`, `p100-n32` | p of 64 / 100 bits, P in a 32-bit prime subgroup (Floyd): the spec's "50–100 bits" read as the size of p |
| `ord32`, `ord48`, `ord64` | `order`: ord(P) by Shanks–Mestre (item 2 and the remark), p of 32/48/64 bits |

The classes `n36`+ and `dp36`+ are not committed (they are regenerated from the seed).
A full `make bench` takes about 7.5 minutes.

## Measurements (reference machine, 2026-10-14, 16-core EPYC 7352, under load from parallel benchmarks)

| class | median, s | max, s |
|---|---|---|
| n32 / dp36 | 0.35 / 1.3 | 1.1 / 1.8 |
| n36 | 1.8 | 4.9 |
| **n40** | **12** | 18 |
| n44 | 59 | 131 |
| dp40 / dp44 | 4.4 / 6.5 | 7.2 / 32 |
| p64-n32 / p100-n32 | 1.3 / 2.4 | 2.9 / 5.4 |
| ord64 | 0.8 | 1.4 |

Floyd costs about 9 µs per iteration (3 group operations) in pure Python. The time
grows about ×4 per 4 bits of n, as √n predicts, and the spread is large because the
collision time of rho is random (max/median ≈ 2). The distinguished-point variant is
2–3× faster: 1 operation per step and a more random walk. A 100-bit p makes the same
32-bit subgroup about 2–4× slower than a 32-bit p, because the inversions and products
are on larger integers.

## Requirements (`requirements.tex`)

- `\ReqPBitsLo`–`\ReqPBitsHi` = 50–100 (value). The original numbers are kept as the
  size of p.
- `\ReqOrderBits` = 40 (value). This is new: the spec has to say how large ord(P) is.
  At k = 40, the reference Floyd takes 8–18 s, i.e. "несколько десятков секунд", so
  this is the n for which the original sentence holds for a careful implementation
  (×4 per 4 bits beyond it).
- `\ReqSeconds` = slack (10) × the median of `n40`, rounded up on the 1-2-5 scale:
  10 × 12 s = 120 → **200 s**. The median is used rather than the max because the
  running time of rho is random. A student's single unlucky run should be judged
  against a typical time, and the 10× slack already covers the spread (max/median ≈ 2).

**Verdict.** The time ("tens of seconds") is confirmed for ord(P) ≤ 40 bits, measured
on the reference itself. The required limit is 200 s, which includes the 10× slack.
The sizes are adjusted: "50–100 bits" can only be the size of p, so the spec now states
the size of ord(P) as well. The spec sentence reads: «…с числами размеров примерно
50–100 бит (при порядке основания ord(P) до 40 бит) должны выполняться за приемлемое
время — не более 200 секунд».

## Open questions for the instructor

1. Is the reading "p of 50–100 bits, ord(P) ≤ 40 bits" what you meant? The
   alternative is to drop the 50–100 and state only ord(P) ≤ 40 bits.
2. The spec allows students to use library point arithmetic (Sage's `EllipticCurve`).
   Measured at p ≈ 2⁴⁰, one Sage point addition takes 15 µs against 3.3 µs for the
   reference's plain-int formulas, i.e. 4.6× slower. A student with Sage points plus
   Floyd at 40 bits therefore expects about 1 min (median), up to about 1.5–2 min on
   an unlucky run. That is within the 200 s limit, but with less margin than the
   nominal 10×. Is that acceptable? Or should the limit use the max instead of the
   median (10 × 18 s → 200 s, the same value today)? Should 44 bits be a "+" level
   (reference: about 1 min median)?
3. The spec does not ask for distinguished points, Brent or the negation map. The
   reference implements distinguished points as a benchmark comparison (they are 2–3×
   faster). Should they be mentioned as an optional extra?
4. Item 1 ("координаты стартовой точки"): rho needs the start point as [α₀]P + [β₀]Q.
   Bare coordinates are useless unless they come with that representation. The
   reference takes α₀, β₀ and reports the coordinates. Should the wording say so?
