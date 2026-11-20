# Euclid, orders and primitive roots reference

All required algorithms are implemented in `ntheory.py`: binary GCD, xgcd/inversion,
batch inversion with explicit non-unit entries, coprime CRT, Garner, sequential and
product-tree order computation, and primitive-root search modulo a prime. Sage functions
are used only as test/vector oracles; factorizations of p−1 are inputs.

The JSON solver dispatches on `input.op`: `binary_gcd`, `xgcd`, `inverse`, `batch_inverse`,
`crt`, `garner`, `order_sequential`, `order_product_tree`, `primitive_root`. Order traces and
Garner coefficients are returned in `extra`.

```sh
sage -python -m pytest -q reference/tests
```
