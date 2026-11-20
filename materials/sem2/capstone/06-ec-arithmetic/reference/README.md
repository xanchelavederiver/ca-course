# Reference: elliptic-curve arithmetic over F_p (capstone 06)

Instructor-only. A from-scratch implementation of every item of the spec's
«Требуемый функционал», including the optional Schoof algorithm of remark 3, used to
calibrate the spec's performance requirements (`make bench CAPSTONE=ec-arithmetic`).

## Usage

```sh
sage -python reference/main.py            # JSON lines on stdin -> JSON lines on stdout
make test-capstones CAPSTONE=ec-arithmetic  # pytest against Sage's EllipticCurve
```

Only `gmpy2` is needed (it ships with Sage); Sage itself is not imported by the solver,
so the start-up is fast.

Each request is `{"id": ..., "input": {"op": ..., "curve": {"p", "a", "b"}, ...}}` for the
curve y² = x³ + ax + b over F_p (p > 3 prime). Points are `[x, y]` or `null` (the point
at infinity O). Integers are JSON numbers (strings like `"0x1f"` are accepted too).

| op | input | output | `extra` | spec |
|---|---|---|---|---|
| `add`, `sub` | `P`, `Q` | `point` | | item 1 |
| `neg`, `double` | `P` | `point` | | item 1 |
| `mul` | `P`, `k` (any sign), `method`: `binary` \| `ternary`, `coords`: `jacobian` (default) \| `affine` | `point` | for `ternary`: the expansion of \|k\| (`+0-…`, most significant first) and its weight | items 2, 3 |
| `ternary` | `n ≥ 0` (no curve) | `digits` ∈ {−1, 0, 1}, least significant first | | remark 1 |
| `point` | `seed` (optional) | `point` | | item 4, remark 2 |
| `order` | `method`: `shanks-mestre` (default) \| `schoof` \| `naive`, `seed` | `order` | trace, the point and curve (E or twist) that decided it / the residues t mod l | item 5, remark 3 |

`repeat: R` repeats the operation R times (the bench times fast operations per
operation). Bad input (p not prime, a singular curve, a point off the curve, an
unknown op) gives `{"id", "error"}`, never a crash.

## Design (`ecarith/`)

- `field.py` — F_p on gmpy2: inversion, powering and the primality test are the bigint
  library's; the Legendre symbol (Euler's criterion) and the square root
  (Tonelli–Shanks, with the p ≡ 3 (mod 4) shortcut) are written here.
- `curve.py` — the group law in affine coordinates with all special cases (O, P + (−P),
  P + P through `add`, 2P = O for y = 0); Jacobian doubling (special forms for a = 0
  and a = −3) and mixed Jacobian + affine addition; random point generation.
- `scalar.py` — `ternary_expansion` (a separate function, remark 1): the signed-binary
  expansion by the 3n trick of Crandall–Pomerance, Alg. 7.2.4 (it is the NAF);
  `mul_binary` (double-and-add) and `mul_ternary` (add–subtract ladder), each in
  affine or Jacobian coordinates; negative k multiplies −P.
- `order.py` — the naive count (p ≤ 229, below Mestre's bound) and Shanks–Mestre:
  BSGS over the Hasse interval with x-coordinate baby steps (each giant step covers
  2W + 1 values), random points on E or its quadratic twist until exactly one
  multiple of the point's order lies in the interval.
- `poly.py`, `schoof.py` — Schoof's algorithm: polynomials over F_p with Kronecker
  substitution (one GMP multiplication per polynomial product) and Newton-inverse
  reduction; division polynomials by the standard recurrences; t mod l from
  φ² − tφ + p = 0 on E[l], points of F_p[x, y]/(ψ_l, y² − f) kept as fractions (no
  inversions). The one non-uniform test (x(φ²P) = x([p mod l]P)) is decided by a gcd,
  and a proper factor of ψ_l replaces ψ_l. CRT until ∏ l > 4√p.

## What the restrictions forbid

The spec forbids "the corresponding functions of specialized libraries" and allows a
bigint library. So the solver never uses Sage's `EllipticCurve`, its points, `order()`,
`lift_x`, `division_polynomial`, Sage/PARI polynomial rings, `sqrt` mod p or
`kronecker`. It uses only gmpy2 integers (`invert`, `powmod`, `is_prime`, `isqrt`) and
Python. Sage's `EllipticCurve` is the oracle: it computes the expected answers in
`taskgen/capstone/gens/ec_arithmetic.py` and in `tests/`.

## How the bench uses it

`bench/config.yaml` runs `sage -python reference/main.py` once per size class over
`vectors/<class>.jsonl`. The runner times each request; `add-*` and small `mul-*` /
`point-*` classes use `repeat` so that the per-operation time (`max_op`) is measured.
`taskgen.capstone.gens.ec_arithmetic.verify` checks every answer (any point on the
curve for `point`, any {−1, 0, 1} expansion for `ternary`, affine, projective or
Jacobian coordinates for points).
