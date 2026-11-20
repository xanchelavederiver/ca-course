# Reference: Lenstra's elliptic curve factorization (capstone 5)

Instructor-only. It implements every item of «Требуемый функционал» and the optional
remarks of the spec:

| spec item | where |
|---|---|
| 1. a curve mod N and a point on it (footnote "как это сделать?") | `lenstra/curves.py`: `random_weierstrass` picks `a, x0, y0` at random and sets `b = y0^2 - x0^3 - a x0`, so no square root mod N is needed; `op: "curve"` |
| 2. a non-trivial factor of N | `lenstra/ecm.py`: `find_factor`, `op: "factor"` |
| 3. the prime factorization of N | `lenstra/ecm.py`: `factorize` (trial division by 2, 3, ..., a primality test, perfect powers, recursion on the cofactors), `op: "factorize"` |
| intermediate data ("уравнение кривой, координаты точки P, n! P и проч.") | `"extra"`: the levels (B1, B2, number of curves), and for every factor the curve, the starting point, the bounds, the stage, the stage-1 prime after which the gcd became non-trivial; with `"trace": true` also the points after each prime (or after each `j` for `j! P`) |
| remark: special parametrisation, order divisible by 12 or 16 (C&P sec. 7.4.2, thm. 7.4.3, alg. 7.4.4) | `curves.suyama` (12), `curves.z2z8` (16), Montgomery x-only arithmetic, stage 2 |
| choice of B1, B2 and the number of curves from the expected factor size | `lenstra/params.py` |

## Usage

```sh
# JSON lines on stdin (see the docstring of main.py for every field)
echo '{"id": 1, "input": {"op": "factorize", "n": 1000000016000000063}}' |
  docker compose run --rm -T --entrypoint sage taskgen -python \
  materials/sem2/capstone/05-lenstra-ecm/reference/main.py [--family z2z8|suyama|weierstrass] [--no-stage2]
make test-capstones CAPSTONE=lenstra-ecm      # pytest vs Sage
make bench CAPSTONE=lenstra-ecm               # bench/config.yaml: --family weierstrass
```

Input: `{"op": "factorize"|"factor"|"curve", "n": ...}` plus optional `family`,
`stage1` (`primepowers` or the textbook `factorial`, i.e. `j! P`), `stage2`, `B1`, `B2`,
`curves`, `factor_bits` (expected factor size: first level of the schedule), `trial`,
`max_curves`, `trace`, `seed`. Output: `{"prime", "factorization": [[p, e], ...]}`,
`{"prime", "factor"}` or `{"curve", "point"}`. Bad input gives `{"error": ...}`.

**Determinism.** The random curves are drawn from `random.Random` seeded by
`sha256(n, seed)`, so the same request always takes the same curves and the same time.

## Design

- **Curves** (`curves.py`). Lenstra's original: `y^2 = x^3 + a x + b`, affine coordinates;
  every chord/tangent step inverts an element of Z/nZ, and the failed inversion
  (`arith.NotInvertible`, carrying `gcd(., n)`) *is* the factor. Montgomery curves
  `B y^2 = x^3 + A x^2 + x` in projective x-only form (the ladder, no inversions; the factor
  is `gcd(Z, n)`, checked after every prime of stage 1).
- **Suyama** (C&P thm. 7.4.3): `sigma`, `u = sigma^2 - 5`, `v = 4 sigma`,
  `A = (v-u)^3 (3u+v) / (4 u^3 v) - 2`, `x0 = u^3/v^3`; `12 | #E(F_p)`. The affine point is
  `B = (sigma^2-5)/sigma^3`, `y0 = (sigma^2-1)(sigma^2-25)(sigma^4-25)/(512 sigma^3)`.
- **Z/2 x Z/8** (`16 | #E(F_p)`). Derived for this reference (and checked by the tests over
  Q and over many F_p). The Edwards family of Bernstein--Birkner--Lange--Peters,
  `x8 = (u^2+2u+2)/(u^2-2)`, `d = (2 x8^2 - 1)/x8^4`, has torsion Z/2 x Z/8; its Montgomery
  form has `B = 4/(1-d)` a square, so it is `y^2 = x^3 + A x^2 + x` with `A + 2 = Q^2`,
  `Q = (u^2+2u+2)^2 / (2u(u+1)(u+2))`. A point of infinite order needs a curve on the
  surface: with `x0 = -2(u+1)^2/u^2`, `x0^3 + A x0^2 + x0` is a square times
  `q(u) = u^4 - 6u^2 - 8u - 4`, and `w^2 = q(u)` is birational (via `w = u^2 + T`) to
  `T: Y^2 = Z^3 + 4Z - 16`, of rank 1 with generator `G = (4, 8)`. So every `k >= 2` gives
  `(Z, Y) = k G`, `u = (8 + Y)/(2(Z - 4))`, the curve `A = Q^2 - 2` and the point
  `x0`, `y0 = (u+1)(u^2+4u+2)(u^2 - (Z+2)/2) / ((u+2) u^3)`. The reference computes `k G`
  modulo n (a failed inversion there is a factor too), with a random 32-bit `k`.
- **Stage 1**: multiply by `p^e <= B1` for every prime `p <= B1`; the textbook variant
  (HPS 6.6) multiplies by `2, 3, ..., B1` and records `j! P`.
- **Stage 2** (C&P alg. 7.4.4, the standard continuation): primes `q in (B1, B2]` are
  written `q = mD +- j`, `gcd(j, D) = 1`, `j < D/2`, `D` a primorial; the baby steps
  `x(jQ)` (one batched inversion), the giant steps `x(mDQ)` (differential additions, or
  affine additions on Weierstrass curves), one gcd of `prod (x(mDQ) - x(jQ))`.
- **Parameters** (`params.py`): levels of 12, 16, 20, ... bits up to half of `log2 n`.
  For each level the B1 of least expected work `curve_cost(B1, B2) / G(alpha, beta)` is
  taken from a 1-1.5-2-3-5-7 grid (B2 = 100 B1), where `G` is the semismooth probability
  computed from Dickman's rho and `alpha = ln(p/t)/ln B1` takes the known torsion `t` into
  account; the expected number of curves is `1/G`. The asymptotic optimum
  `L_p[1/2, 1/sqrt 2]` is given for comparison (`b1_asymptotic`). E.g. for a 50-bit factor:
  Weierstrass B1 = 3000, 45 curves; Z/2 x Z/8 B1 = 1500, 42 curves.
- **Factorization**: trial division by primes < 100 (always 2 and 3: the curve formulas
  divide by 2 and 3), then a stack of cofactors: Miller--Rabin (13 fixed bases,
  deterministic below 3.3e24; 24 more random bases above), perfect powers by integer
  Newton roots, otherwise ECM; the schedule resumes at the level that found the last
  factor.

## What the restrictions forbid

The spec lets students use libraries "для работы с эллиптическими кривыми". The
reference still does the curve arithmetic by hand, as a student would have to in order to
catch the failed inversion: no `EllipticCurve(Zmod(n))`, no Sage `factor`, `ecm`,
`is_prime` or `next_prime`. It uses Python integers only, with `pow(x, -1, n)` for the
inverse and `math.gcd`. Sage is the oracle in `tests/` and in the vector generator.

## Bench

`bench/config.yaml` runs `main.py --family weierstrass` (Lenstra's random curves, stage 1
and stage 2): this is the basic algorithm of the spec, and the special families are
measured separately for comparison (`bench/README.md`). The other configurations run
with `python -m taskgen.capstone check lenstra-ecm --cmd 'sage -python
reference/main.py --family z2z8'` and so on.
