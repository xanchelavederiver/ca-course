# Fast multiplication reference

Python + Sage reference for all four required methods. Whole-input `*` is used only for
fixed-width digit products and independent tests/oracles, never as a multiplication method.
Sage primality testing is allowed during automatic finite-field prime selection; exact-order
root construction and the FFT are implemented here.

Run the solver from this capstone directory:

```sh
sage -python reference/main.py
```

Input: `{"id":"x","input":{"a":"123","b":"456","method":"karatsuba"}}`.
Methods are `schoolbook`, `karatsuba`, `toom3`, `fft`. Output contains `output.product`;
FFT requests also report `n`, `p`, `omega` and the coefficient bound in `extra.fft`.

Tests:

```sh
sage -python -m pytest -q reference/tests
```
