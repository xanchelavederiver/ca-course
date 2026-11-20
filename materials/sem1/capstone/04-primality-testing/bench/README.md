# Primality-testing calibration

The mix covers all required operations, fixed pseudoprime families, supplied factorizations,
non-squarefree Korselt examples and Mersenne exponents through 31. Wilson is deliberately
restricted to n < 25 and is excluded from the meaningful performance comparison; its presence
in the b128 class does not imply factorial-time testing of 128-bit inputs.

`ReqSeconds` is a conservative maximum request limit over the mixed b128 class with default
slack. Probabilistic verdicts and every witness are independently verified. Lucas–Lehmer
vectors are tagged by prime/composite outcome, and Mersenne reduction has separate vectors.
