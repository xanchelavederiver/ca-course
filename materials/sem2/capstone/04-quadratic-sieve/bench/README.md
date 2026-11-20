# Quadratic sieve — calibration notes

## The original spec

«Мини-курсовая - метод Квадратичного решета»: "тестовые примеры с числами размеров примерно
**100 бит** должны выполняться за приемлемое время – несколько десятков секунд", with the
footnote that the cost depends strongly on the structure of N. There are no other numbers.

## What is measured

`sage -python reference/main.py` (pure Python, single polynomial t² − N, B = 4·L(N)^½,
log sieve in 2¹⁶ blocks, hand-written GF(2) elimination; see `reference/README.md`), one
process per class, warm-up excluded, timeout 120–400 s per vector. Classes
(`config.yaml`):

- `n40` … `n100` (10 each, committed) and `n110`, `n120`, `n140` (8/8/5, regenerated from
  the seed): balanced semiprimes n = pq with p, q of bits/2 bits — the plotted curve; it
  covers the spec's "about 100 bits" and goes beyond.
- corner classes (not plotted, committed): `corner60` (a mix of all corner shapes at 60
  bits), `pp100` (p², m² with m = pq, p³), `small100` (a factor of 2–12 bits, n may be
  even), `unbal100` (a 25-bit factor), `repeat100` (p²q), `close100` (|p − q| < 2¹²),
  `multi80`/`multi100` (3–4 primes, `full: true`: the full factorization is required).

A full `make bench` takes about 3.5 min (n140 is ~2.5 min of it).

## Results (reference machine: AMD EPYC 7352, other benchmarks running concurrently)

| class | median, s | max, s |
|---|---|---|
| n60 | 0.019 | 0.024 |
| n80 | 0.077 | 0.14 |
| n100 | 0.57 | 0.74 |
| n120 | 3.6 | 5.9 |
| n140 | 24 | 39 |

The time grows by about 2.5–3× per 10 bits, as L(N)^{const} predicts; the corner cases
are either instant (perfect powers and factors ≤ B are found before sieving) or cost the
same as a balanced n of the same size (QS does not care about the sizes of the factors).
All 135 vectors pass. Peak RSS ≤ 30 MB.

## Requirements

- `\ReqBits` = 100 (the spec's size, a literal).
- `\ReqSeconds` = 10 × max(n100), rounded up to 1-2-5: **10 s** (measured max 0.74 s).

**Adjusted, not confirmed:** the spec says "several tens of seconds" for 100 bits; the
measured reference with the default 10× slack gives 10 s. The spec text keeps "за
приемлемое время" and now reads "не более \ReqSeconds~с" (the phrase "несколько десятков
секунд" is dropped, since it would contradict 10 s). Reasons the reference is so fast in
pure Python: sieving by logarithms in a `bytearray` (≈ 1 Python operation per sieved
position after skipping primes < 30), a regex scan for candidates, trial division only by
the primes whose root matches, and bit-mask Gaussian elimination. A student who sieves by
division instead of logarithms, or trial-divides every value, is 1–2 orders of magnitude
slower and would miss 10 s; with logarithms (remark 4) 10 s is comfortable.

## Open questions for the instructor

1. Keep the calibrated 10 s for ~100 bits, or keep the original "несколько десятков секунд"?
   For the latter, set `slack: 50` in `config.yaml`, or `min: 30` on `ReqSeconds`.
2. Should the spec name a size the students cannot reach without MPQS (e.g. 120–140 bits,
   ~6–40 s for the reference) as an optional "bonus"? Remark 5 (other polynomials) hints at it.
3. The original's first reference is labelled "Discrete logarithm calculator" but links to
   alpertron's ECM.HTM; the port cites it as "Integer factorization calculator"
   (`alpertron-ecm`).
4. The original's goal says "методом Квадратичного числа"; the port says "решета".
5. Perfect powers and n with a factor ≤ B are in the vectors; the spec does not ask the
   students to handle them explicitly. Should the defence require it?
