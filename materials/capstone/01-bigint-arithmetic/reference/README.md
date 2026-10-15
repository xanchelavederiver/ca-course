# Reference: big-integer arithmetic in C (capstone 01)

Instructor-only. A from-scratch library of signed big integers on 64-bit limbs that
implements every item of the spec's «Требуемый функционал», plus the JSON-lines solver
the bench runs. GMP is the **oracle** of the tests only: the solver never links it
(`test_solver_does_not_link_gmp` checks this).

## Build and run

```sh
make -C reference                         # in the capstone-c image (the bench does this)
reference/build/bigint-solver             # JSON lines on stdin -> stdout
reference/build/bigint-tune               # Karatsuba thresholds + per-operation times
reference/build/bigint-oracle SEED ROUNDS # random differential test against GMP
make test-capstones CAPSTONE=bigint-arithmetic
```

```sh
$ echo '{"id":1,"input":{"op":"divmod","a":"-0x64","b":"0x7"}}' | reference/build/bigint-solver
{"id":1,"output":{"q":"-0xe","r":"-0x2"},"extra":{"addbacks":0,"qhat_max":0}}
```

Compiler flags: `-O2 -march=x86-64 -mno-avx`. `-march=x86-64` is the baseline ISA
(SSE2; no AVX, BMI2 or ADX), which is what the spec asks for («x86-64 без расширения
AVX»). The binary runs on any 64-bit x86 machine at the defence, and the timings do not
depend on the build host's newer extensions. `make ARCH=` builds for other hosts.

## Protocol

A request is `{"id": ..., "input": {"op": ..., ...}}`. Bigints are hex strings with an
optional sign (`"-0x1f"`, `"0x0"`; a JSON integer is also accepted). `k`, `q`, `repeat`
and `threshold` are JSON numbers. The answer is `{"id", "output"[, "extra"]}` or
`{"id", "error"}`. The id is echoed verbatim. Bad JSON, missing fields, division by zero
and an even Montgomery modulus all give `"error"`, and the process keeps running.

| op | input | output | notes |
|---|---|---|---|
| `add`, `sub` | a, b | c | |
| `mul_school` | a, b | c | schoolbook |
| `mul_karatsuba` | a, b [, threshold] | c | Karatsuba, schoolbook below `threshold` limbs (default 24) |
| `mul` | a, b | c | = `mul_karatsuba` with the tuned threshold |
| `sqr`, `sqr_school` | a [, threshold] | c | squaring (remark 1), Karatsuba above 48 limbs |
| `divmod` | a, b | q, r | **truncated**: q = trunc(a/b), r has the sign of a (as C `/ %`) |
| `mod` | a, b | r | residue 0 ≤ r < \|b\| |
| `gcd` | a, b | g | g ≥ 0 |
| `xgcd` | a, b | g, x, y | a x + b y = g |
| `inv` | a, m | inv \| null | a⁻¹ mod m in [0, m), null if gcd(a, m) ≠ 1 |
| `shl`, `shr` | a, k | c | a·2ᵏ; `shr` is **floor** (arithmetic shift: −5 >> 1 = −3) |
| `mont_redc` | t, m | c, r_bits | c = t·R⁻¹ mod m, R = 2^r_bits = B^n (n limbs of m); m odd |
| `mont_mul` | a, b, m | c | a·b mod m through Montgomery form; extra `mont` = REDC(a·b), `r_bits` |
| `pow_binary` | a, e | c | aᵉ, left-to-right binary; refuses results over 2²⁴ bits |
| `pow_qary` | a, e, q | c | q-ary, q ∈ {2, 4, …, 256} |
| `powmod_binary` | a, e, m | c | aᵉ mod m ∈ [0, m); extra `method` |
| `powmod_qary` | a, e, m, q | c | same, q-ary |

`"repeat": R` repeats the operation R times on the same operands and answers the last
result, so the per-operation time is wall / R. One-time work stays outside the loop:
parsing, the Montgomery context and, for `mont_mul`, the conversion into Montgomery form.
`powmod_*` builds its context inside the call, as a library `powmod(a, e, m)` would.
`divmod`/`mod` report in `extra` how often Algorithm D ran its rare correction steps in
the last repetition (`addbacks` = step D6, `qhat_max` = the estimate started at B − 1).

**Even moduli.** Montgomery needs gcd(m, R) = 1. `mont_redc`/`mont_mul` with an even m
are errors. `powmod_*` with an even m (or a power of two) fall back to the same
binary/q-ary loops with reduction by division (`"method": "division"`). m = 1 gives 0.
e < 0 and m ≤ 0 are errors.

## Design

```
src/limbs.h, limbs.c   natural numbers as limb arrays: add/sub with carry (ADC/SBB via
                       _addcarry_u64), mul_1/addmul_1/submul_1 (128-bit products), shifts
src/mul.c              schoolbook, schoolbook squaring, Karatsuba (subtractive variant),
                       Karatsuba squaring, unbalanced Karatsuba (cut the longer operand)
src/div.c              Knuth's Algorithm D (D1 normalization ... D8), 128/64 DIV in inline asm
src/bigint.h, .c       the signed type (sign + magnitude, normalized), hex I/O, the signed
                       wrappers, division conventions, shifts
src/gcd.c              Euclid, extended Euclid (both cofactors), modular inverse
src/mont.c             Montgomery context (-m⁻¹ mod B by Newton, R mod m, R² mod m), REDC,
                       Montgomery multiplication/squaring, conversions
src/pow.c              binary left-to-right and q-ary exponentiation, generic over three
                       "domains": integers, Montgomery residues, residues by division
src/json.c, solver.c   strict JSON parser (RFC 8259, depth-limited) and the solver
src/tune.c             threshold measurement
tests/oracle.c         GMP differential test; tests/test_reference.py the pytest suite
```

Numbers are sign and magnitude. The magnitude has `n` significant limbs, and zero has
n = 0 and no sign. Every result goes into a caller-owned destination that may alias an
operand. Products and quotients are built in fresh arrays and then adopted. The length is
limited only by memory. The spec asks for 16384 bits (footnote 1: 512 bytes·4·8 bits);
the tests and the `b16384` vectors check that size.

**Thresholds.** `bigint-tune` compares the schoolbook product with one level of
Karatsuba at each length. On the reference machine (AMD EPYC 7352, gcc 12, `-O2
-march=x86-64`), Karatsuba wins from 24 limbs (1536 bits) for products and from 48 limbs
for squarings, where it competes with the schoolbook squaring, which is ~1.6× faster than a product. A 2048-bit
(32-limb) product therefore does one Karatsuba level. Both are `#define`s in `limbs.h`
(override with `-DKARATSUBA_THRESHOLD=...`). The vector generator mirrors them for its
threshold corner cases (T ± 1, 2T ± 1 limbs).

**Algorithm D.** After D1 the divisor's top bit is set. D3 estimates q̂ from two limbs of
the window, caps it at B − 1 and corrects it with the next limb (at most twice). If the
D4 subtraction still goes negative, D6 adds v back. This happens with probability ~2/B,
so random tests almost never reach it. The generator builds operands that force it, and
the tests check `extra.addbacks ≥ 1` on them.

**Exponentiation.** The q-ary method uses a table a¹ … a^(q−1) (q − 2 products), then
k = log₂ q squarings and at most one product per digit. For a 2048-bit exponent, q = 16
needs ~526 products instead of the ~1024 of the binary method (the 2047 squarings stay). In Montgomery form the whole chain needs
one conversion at each end.

## What the student restrictions forbid (and the reference avoids)

- No bignum library in the operations: no GMP, OpenSSL BN, Boost.Multiprecision or
  `__builtin` bignum helpers. Only machine words, `unsigned __int128` for the 64×64→128
  product, and the ADC/SBB/DIV instructions (remark 2, footnote 7).
- No AVX (spec): the baseline `-march=x86-64` guarantees it.
- GMP appears only in `tests/oracle.c`, linked into `bigint-oracle`.

## How the bench uses it

`bench/config.yaml`: `build: make -C reference`, `command: reference/build/bigint-solver`,
image `capstone-c`. One solver process serves each size class. Every vector carries
`repeat` (chosen by the generator's cost model, ~30 ms per request), and the requirement
macros use the per-operation statistics (`max_op`). See `../bench/README.md`.
