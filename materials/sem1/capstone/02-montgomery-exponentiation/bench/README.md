# Montgomery/exponentiation calibration

Vectors cover all four required methods, window/q parameters, zero exponents and bases,
non-coprime inputs and modulus 1. `cached` vectors reuse one base and modulus so the persistent
solver can exercise precomputation hits; the remaining vectors measure fresh work.

The required maximum is 1024 bits. `ReqSeconds` uses the slowest b1024 request and default
10× slack. Operation counts and cache status are returned as extra data for instructor review;
the correctness verifier checks the modular power independently with Python's oracle.
