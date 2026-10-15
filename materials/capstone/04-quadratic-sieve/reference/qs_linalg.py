"""Linear algebra over GF(2) for the quadratic sieve: dependencies among exponent vectors.

A relation t^2 = f(t) = (-1)^e0 * p1^e1 * ... * pk^ek is encoded by the parity of its
exponents, a vector in GF(2)^(k+1) stored as a Python int (bit j = e_j mod 2). A set S
of relations with sum_{i in S} v_i = 0 is a *dependency*: the product of their f(t) is
a perfect square. We look for many such S (the left kernel of the relation matrix).

``dependencies`` is Gaussian elimination by hand (rows as bit masks, XOR as row
addition); ``dependencies_sage`` does the same with Sage's GF(2) matrices (the spec
allows linear algebra packages) and serves as a cross-check in the tests.
"""

from __future__ import annotations


def dependencies(rows: list[int]) -> list[int]:
    """All dependencies found by eliminating ``rows`` in order.

    Returns bit masks over the row indices: mask m means sum_{i: bit i of m} rows[i] = 0.
    The masks form a basis of the left kernel (len(rows) - rank of them).

    Incremental elimination: each pivot row is reduced to have a distinct leading bit
    (its highest set bit). A new row is reduced by the pivots in turn; if it becomes 0,
    the record of which original rows were XORed into it ("history") is a dependency,
    otherwise it becomes a new pivot.
    """
    pivots: dict[int, tuple[int, int]] = {}     # leading bit -> (row, history)
    deps = []
    for i, row in enumerate(rows):
        hist = 1 << i
        while row:
            lead = row.bit_length() - 1
            piv = pivots.get(lead)
            if piv is None:
                pivots[lead] = (row, hist)
                break
            row ^= piv[0]
            hist ^= piv[1]
        else:
            deps.append(hist)
    return deps


def dependencies_sage(rows: list[int], ncols: int) -> list[int]:
    """The same with Sage: a basis of the left kernel of the 0/1 matrix over GF(2)."""
    from sage.all import GF, matrix

    m = matrix(GF(2), len(rows), ncols, [[(r >> j) & 1 for j in range(ncols)] for r in rows])
    return [sum(1 << i for i, c in enumerate(v) if c) for v in m.left_kernel().basis()]
