# Primality testing reference

Implements Wilson, Fermat, Miller–Rabin, Solovay–Strassen (including Jacobi), Korselt and
squarefree liar counts, Mersenne reduction and Lucas–Lehmer. Sage primality, factorization and
Jacobi functions are independent test/vector oracles only. Factorizations needed by Korselt
are supplied in the request.

`input.op` is `wilson`, `fermat`, `miller_rabin`, `solovay_strassen`, `korselt`,
`lucas_lehmer` or `mersenne_reduce`. Probabilistic tests return `probable_prime` or `composite`
plus explicit witnesses; they never claim a probabilistic pass proves primality.

```sh
sage -python -m pytest -q reference/tests
```
