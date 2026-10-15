"""Capstone 07 — Pollard's rho for the ECDLP: test vectors and verifier.

``op: dlog`` vectors: a curve E: y^2 = x^3 + a x + b over F_p, a point P whose order
n = ord(P) has exactly ``bits`` bits, and Q = [x]P. Input ``{p, a, b, P, Q, n, method}``
(plus ``start`` and ``max_iter`` for the ``given-start`` kind: item 1 of the spec);
expected ``{"x": x mod n}``.

``op: order`` vectors (item 2 of the spec): ``{op, p, a, b, P}`` with p of ``p_bits``
bits; expected ``{"n": ord(P)}``.

The instance kind is drawn (by ``rng``) from ``params["kinds"]``:

    prime       #E(F_p) = n is prime (cofactor 1), p of ``bits`` bits
    cofactor    #E = h n, h > 1, n prime; p of ``bits`` + ``h_bits`` bits
                (``p_bits`` set: p of ``p_bits`` bits and P in a ``bits``-bit subgroup)
    a0          a = 0 (j = 0), prime n, any cofactor
    b0          b = 0 (j = 1728), prime n, cofactor >= 2 (the point (0, 0) has order 2)
    composite   n = ord(P) composite (P of the full order of a random point)
    q-zero | q-p | q-minus-p     Q = O, Q = P, Q = -P (x = 0, 1, n - 1), prime n
    given-start the request fixes the start [alpha_0, beta_0] and max_iter

Expected answers come from Sage (EllipticCurve over GF(p): ``order()``, ``factor``,
scalar multiplication); ``verify`` recomputes [x]P with the standard library only.
"""

from __future__ import annotations

VERSION = 1

KINDS = ("prime", "cofactor", "a0", "b0", "composite", "q-zero", "q-p", "q-minus-p", "given-start")


# --- verification (standard library) ---------------------------------------------------

def _add(p, a, P, Q):
    if P is None:
        return Q
    if Q is None:
        return P
    (x1, y1), (x2, y2) = P, Q
    if x1 == x2 and (y1 + y2) % p == 0:
        return None
    if x1 == x2:
        lam = (3 * x1 * x1 + a) * pow(2 * y1, -1, p) % p
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (lam * lam - x1 - x2) % p
    return (x3, (lam * (x1 - x3) - y1) % p)


def _mul(p, a, k, P):
    R = None
    while k:
        if k & 1:
            R = _add(p, a, R, P)
        P = _add(p, a, P, P)
        k >>= 1
    return R


def _pt(xy):
    return None if xy is None else (xy[0], xy[1])


def verify(vector: dict, output: dict) -> str | None:
    inp, exp = vector["input"], vector["expected"]
    if not isinstance(output, dict):
        return f"output {output!r} is not an object"
    if inp.get("op") == "order":
        n = output.get("n")
        return None if n == exp["n"] else f"ord(P) = {exp['n']}, got {n!r}"
    x = output.get("x")
    if not isinstance(x, int) or isinstance(x, bool):
        return f"x must be an integer, got {x!r}"
    p, a = inp["p"], inp["a"]
    R = _mul(p, a, x % inp["n"], _pt(inp["P"]))
    if R != _pt(inp["Q"]):
        return f"[{x}]P = {list(R) if R else 'O'} != Q (expected x = {exp['x']} mod n)"
    return None


# --- generation (Sage) ------------------------------------------------------------------

def _prime(rng, bits):
    from sage.all import next_prime

    while True:
        p = int(next_prime(rng.getrandbits(bits - 1) | (1 << (bits - 1))))
        if p.bit_length() == bits:
            return p


def _point(E, rng):
    """A random affine point of E, from rng only."""
    from sage.all import GF

    F = E.base_field()
    p = int(F.order())
    a, b = (int(c) for c in E.a_invariants()[3:5])
    while True:
        x = rng.randrange(p)
        rhs = GF(p)(x ** 3 + a * x + b)
        if rhs.is_square():
            y = int(rhs.sqrt())
            if rng.getrandbits(1):
                y = -y % p
            return E(x, y)


def _curve(rng, p_bits, kind, accept):
    """(E, p, a, b, N) with N = #E(F_p) passing ``accept(N)`` -> n (or None to reject)."""
    from sage.all import GF, EllipticCurve

    while True:
        p = _prime(rng, p_bits)
        a = 0 if kind == "a0" else rng.randrange(p)
        b = 0 if kind == "b0" else rng.randrange(1, p)
        if (4 * a ** 3 + 27 * b * b) % p == 0:
            continue
        E = EllipticCurve(GF(p), [a, b])
        N = int(E.order())
        n = accept(N)
        if n:
            return E, p, a, b, N, n


def _subgroup_prime(bits, need_cofactor):
    """accept(): a prime q | N of exactly ``bits`` bits (the largest such)."""
    from sage.all import factor

    def accept(N):
        if not need_cofactor:
            from sage.all import is_prime
            return N if N.bit_length() == bits and is_prime(N) else None
        qs = [int(q) for q, _ in factor(N) if int(q).bit_length() == bits]
        if not qs or N == max(qs):
            return None
        return max(qs)
    return accept


def _tags(kind, a, b, N, n):
    tags = [kind]
    if a == 0:
        tags.append("a=0")
    if b == 0:
        tags.append("b=0")
    if N != n:
        tags.append("cofactor")
    return tags


def _gen_order(params, rng, kind):
    """ord(P) of a random point (or of a point of a prime-order subgroup)."""
    from sage.all import is_prime

    p_bits = int(params["p_bits"])
    E, p, a, b, N, _ = _curve(rng, p_bits, kind,
                              lambda N: N if kind != "prime" or is_prime(N) else None)
    while True:
        R = _point(E, rng)
        if kind == "cofactor":               # a point of order N / (small factor)
            from sage.all import factor
            q = int(max(factor(N))[0])
            R = (N // q) * R
        if not R.is_zero():
            break
    n = int(R.order())
    tags = _tags(kind, a, b, N, n) + ["order"]
    if n != N:
        tags.append("ord(P)<#E")
    return {"input": {"op": "order", "p": p, "a": a, "b": b, "P": [int(R[0]), int(R[1])]},
            "expected": {"n": n}, "tags": tags}


def generate(params: dict, rng) -> dict:
    kinds = list(params.get("kinds") or ["prime"])
    kind = kinds[rng.randrange(len(kinds))]
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    if params.get("op") == "order":
        return _gen_order(params, rng, kind)
    bits = int(params["bits"])
    method = params.get("method", "floyd")
    curve_kind = kind if kind in ("prime", "cofactor", "a0", "b0", "composite") else "prime"
    if params.get("p_bits"):                 # a large field, a small subgroup
        p_bits, curve_kind = int(params["p_bits"]), "cofactor" if curve_kind == "prime" else curve_kind
    elif curve_kind == "prime" or curve_kind == "composite":
        p_bits = bits
    else:                                    # cofactor h of 1..6 bits (a = 0: 0..4)
        p_bits = bits + rng.randrange(0 if curve_kind == "a0" else 1, 5 if curve_kind == "a0" else 7)

    if curve_kind == "composite":
        from sage.all import is_prime

        def accept(N):
            return N if N.bit_length() == bits and not is_prime(N) else None
        while True:
            E, p, a, b, N, _ = _curve(rng, p_bits, "composite", accept)
            R = _point(E, rng)
            n = int(R.order())
            if n.bit_length() == bits and not is_prime(n):
                P = R
                break
    else:
        E, p, a, b, N, n = _curve(rng, p_bits, curve_kind,
                                  _subgroup_prime(bits, curve_kind in ("cofactor", "b0")
                                                  or (curve_kind == "a0" and p_bits > bits)))
        while True:
            P = (N // n) * _point(E, rng)
            if not P.is_zero():
                break
    x = {"q-zero": 0, "q-p": 1, "q-minus-p": n - 1}.get(kind)
    if x is None:
        x = rng.randrange(n)
    Q = x * P
    inp = {"p": p, "a": a, "b": b, "P": [int(P[0]), int(P[1])],
           "Q": None if Q.is_zero() else [int(Q[0]), int(Q[1])], "n": n, "method": method}
    if kind == "given-start":
        inp["start"] = [rng.randrange(n), rng.randrange(n)]
        inp["max_iter"] = 40 * (1 << (bits // 2)) + 1000
    tags = _tags("subgroup" if params.get("p_bits") and kind == "prime" else kind, a, b, N, n)
    if kind == "composite":
        tags.append("composite-n")
    tags.append(method)
    if p_bits > bits:
        tags.append(f"p{p_bits}")
    return {"input": inp, "expected": {"x": x}, "tags": sorted(set(tags))}
