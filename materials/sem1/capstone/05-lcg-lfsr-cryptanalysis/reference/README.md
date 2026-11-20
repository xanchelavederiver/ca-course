# LCG/LFSR cryptanalysis reference

Implements LCG generation, period detection, Hull–Dobell checks, known-parameter next-state
recovery and unique full-output parameter recovery; LFSR simulation, polynomial conversion,
Berlekamp–Massey, prediction and XOR stream decryption. Sage Berlekamp–Massey and the separate
taskgen LFSR simulator are test oracles only.

LCG recovery accepts only uniquely determined inputs; it does not enumerate ambiguous moduli.
Berlekamp–Massey rejects sequences shorter than twice the recovered linear complexity.

`input.op`: `lcg_generate`, `lcg_period`, `lcg_full_period`, `lcg_next`, `lcg_recover`,
`lfsr_generate`, `berlekamp_massey`, `lfsr_recover`, `lfsr_polynomial`, `lfsr_decrypt`.

```sh
sage -python -m pytest -q reference/tests
```
