# LCG/LFSR cryptanalysis reference

Implements LCG generation, period detection, Hull–Dobell checks, known-parameter next-state
recovery and unique full-output parameter recovery; LFSR simulation, period and preperiod
detection, polynomial conversion and Berlekamp–Massey. Both known-plaintext attacks recover the
generator from a plaintext prefix before decrypting the remaining XOR-encrypted message. Sage
Berlekamp–Massey and the separate taskgen LFSR simulator are test oracles only.

LCG recovery accepts only uniquely determined inputs; it does not enumerate ambiguous moduli.
Berlekamp–Massey rejects sequences shorter than twice the recovered linear complexity.

`input.op`: `lcg_generate`, `lcg_period`, `lcg_full_period`, `lcg_next`, `lcg_recover`,
`lcg_decrypt`, `lfsr_generate`, `lfsr_period`, `berlekamp_massey`, `lfsr_recover`,
`lfsr_polynomial`, `lfsr_decrypt`.

```sh
sage -python -m pytest -q reference/tests
```
