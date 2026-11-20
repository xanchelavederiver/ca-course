# Montgomery arithmetic and exponentiation reference

Implements xgcd, REDC, Montgomery multiplication/exponentiation, binary left-to-right,
q-ary and sliding-window methods. Python's three-argument `pow` appears only in tests and
vector oracles. Precomputation is explicit and the JSON solver caches at most 32 full
(base, modulus, method, parameter) keys when `reuse` is true.

Run from the capstone directory with `sage -python reference/main.py`. Input fields:
`a`, `e`, `n`, `method` (`binary`, `qary`, `sliding`, `montgomery`), optional `parameter`
(q or window width) and `reuse`. Output contains `value` and operation counts; `extra.cache`
is `fresh`, `miss` or `hit`.

```sh
sage -python -m pytest -q reference/tests
```
