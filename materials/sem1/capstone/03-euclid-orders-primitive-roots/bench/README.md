# Euclid/orders/primitive-roots calibration

Each request exercises one required operation. Prime order/root inputs include the complete
factorization of p−1; it is generated independently with Sage and is not part of the timed
work. Batch vectors deliberately contain zero and non-unit entries. CRT/Garner vectors vary
the modulus order, and primitive-root verification accepts every valid root.

The required range extends to 64-bit inputs. `ReqSeconds` is derived from the slowest b64
request with default slack. Product-tree and sequential order vectors use the same prime
population and carry separate operation tags for comparison.
