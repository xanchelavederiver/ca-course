# Calibration notes: elliptic-curve arithmetic (capstone 06)

Measured numbers: `results.md` / `results.json` (generated). Reference:
`reference/` (Python + gmpy2, all the curve arithmetic by hand, see its README).
Machine of the first calibration: AMD EPYC 7352, run while other capstone benchmarks were running at
the same time (load average ≈ 6), so the times are noisy. The lead's serial re-run is the one that counts.

## The original spec's numbers

The original states only sizes. Acceptable speed means doing "the basic arithmetic
operations with elliptic curves over residues modulo N of **512–1024 bits**". It gives no
times and no size for point counting.

## What each class measures

| classes | operation (spec item) | per-request work |
|---|---|---|
| `misc` | ternary expansions (remark 1) up to 2048 bits; add / mul / point / order on tiny curves (p < 256, incl. p ≤ 229, below Mestre's bound) | one op |
| `add-p64 … add-p2048` | item 1: `add` (generic, P + P, P + (−P), with O), `sub`, `double` (incl. y = 0), `neg` | the op ×1000 (`repeat`), per-op stats |
| `mul-p64 … mul-p2048` (the plot) | items 2–3: [k]P, binary or ternary method, k of p's size; corners k = 0, ±1, 2, #E, #E ± 1, −(#E − 1), 2#E + 3, k ≈ p², k < 0, P = O, P of order 2; a = 0, a = −3, supersingular curves; P-192, P-256, secp256k1, P-384, P-521 | one multiplication |
| `point-p64 … point-p2048` | item 4: a point on E (Tonelli–Shanks); p ≡ 3 (mod 4), 5 (mod 8), 1 (mod 8), and p = 1 + 2^(bits/2)·c (the long Tonelli–Shanks loop) | one point (×10 at 64 bits) |
| `sm-p32 … sm-p80` | item 5: #E by Shanks–Mestre; generic, j = 0, j = 1728, supersingular (t = 0), full 2-torsion, prime order | one count |
| `schoof-p32 … schoof-p128` | remark 3 (optional plus): #E by Schoof, the same curve kinds | one count |

The 1536/2048-bit, `sm-p80` and `schoof-p128` classes are the step beyond the spec (not
committed, regenerated from the seed). A full `make bench` takes about 5 minutes.

## Measurements (first run) and derived requirements (slack ×10, 1-2-5 rounding up)

| quantity | reference (max) | requirement |
|---|---|---|
| one addition / doubling, p of 1024 bits (`add-p1024`, per op) | ≈ 13 µs | `\ReqAddUs` = 200 µs |
| [k]P with a 1024-bit k, p of 1024 bits (`mul-p1024`) | ≈ 16 ms (512 bits: ≈ 8 ms) | `\ReqMulMs` = 200 ms |
| a point on E, p of 1024 bits (`point-p1024`) | ≈ 51 ms (worst: p = 1 + 2^512 c) | `\ReqPointMs` = 1000 ms |
| #E by Shanks–Mestre, p of 64 bits (`sm-p64`) | ≈ 0.38 s | `\ReqOrderSeconds` = 5 s at `\ReqOrderBits` = 64 |
| sizes | — | `\ReqBitsMin`–`\ReqBitsMax` = 512–1024 (the original's values) |

Other numbers, for reference: Shanks–Mestre grows like p^(1/4) (×4.5–5 per 8 bits: 1.8 s at
72 bits, 8 s and 0.5 GB RSS at 80 bits, the memory of the baby-step table). Schoof takes
0.3 s / 3.9 s / 15 s / 54 s at 32 / 64 / 96 / 128 bits. Scalar multiplication at 2048 bits takes
≈ 0.08 s (median).

## Decision

- **Confirmed**: 512–1024 bits for the basic operations. Even in Python, a 1024-bit
  scalar multiplication takes ~16 ms, so the range is comfortable for any language with a
  bigint library. A compiled student implementation will be well under the limits.
- **Added** (the original had no times): the per-operation limits above, in one new
  sentence after the original one. Point counting gets a size (64 bits) because the
  Shanks–Mestre method is O(p^(1/4)): it cannot reach 512 bits, so "basic operations"
  can only mean the group law, the scalar multiplication and point generation. 64 bits
  is where Shanks–Mestre takes under a second in Python. 80 bits still works (seconds),
  but the memory grows fast.
- Schoof gets no requirement: it is the optional "существенный плюс".

## Open questions for the instructor

1. «Тернарное разложение»: the reference reads it as the signed-binary (NAF) expansion
   with digits {−1, 0, 1}, as in Crandall–Pomerance, Alg. 7.2.4 (the m = 3n trick).
   If base-3 expansion with point tripling was meant, the spec could say so.
2. Should the time limits stay as orientation values ("ориентиры"), or become hard pass/fail
   limits at the defence?
3. Is a point-counting size of 64 bits right, or should it be larger (80 bits ≈ 10 s in
   Python and 0.5 GB)? Should Schoof get a target size (e.g. 64 bits in under 1 min)?
4. The original's typo «на php ил JS» is fixed to «или».
