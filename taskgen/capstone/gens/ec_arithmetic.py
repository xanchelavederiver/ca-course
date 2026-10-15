"""Capstone 06 — elliptic-curve arithmetic over F_p: test vectors and verifier.

Every vector has ``input = {"op": ..., "curve": {"p", "a", "b"}, ...}`` (the curve
y^2 = x^3 + a x + b over F_p, p > 3 prime). Points are ``[x, y]`` or ``null`` (O).
The operations, by spec item:

    add / sub     {P, Q}            -> {"point"}     item 1 (the group law)
    neg / double  {P}               -> {"point"}     item 1 (the inverse point; P + P)
    mul           {P, k, method}    -> {"point"}     item 2 (method "binary") and item 3
                                                     (method "ternary"); k may be < 0
    ternary       {n}  (no curve)   -> {"digits"}    remark 1: the signed-binary expansion,
                                                     least significant digit first
    point         {seed}            -> {"point"}     item 4 (any finite point on E)
    order         {method}          -> {"order"}     item 5 (method "shanks-mestre") and
                                                     remark 3 (method "schoof")

``repeat`` (optional) asks the solver to repeat the operation that many times, so that
fast operations can be timed per operation.

The instance family is chosen by ``params["kind"]``: ``add``, ``mul``, ``point``,
``order`` (with ``bits``) or ``misc`` (ternary expansions and tiny curves). Within a
family the case is drawn by ``rng``; corner cases are kept and tagged: O as an operand
or result, P + (-P), P + P through ``add``, doubling a point of order 2 (y = 0), the
scalars 0, +-1, the group order n, n - 1, n + 1, negative and oversized k, a = 0 and
b = 0 curves, a = -3 curves, supersingular curves (#E = p + 1), the standard curves
(P-192, P-256, secp256k1, P-384, P-521), p = 1 mod 2^s with a large s (the hard case of
Tonelli--Shanks), curves with full 2-torsion or prime order, and p <= 229 (below
Mestre's bound).

Expected answers come from Sage's EllipticCurve (group law, scalar multiplication,
``order()`` = PARI's SEA). ``verify`` uses the standard library only and accepts any
correct answer: any point on the curve for ``point``, any {-1, 0, 1} expansion for
``ternary``, and affine, projective or Jacobian coordinates for points.
"""

from __future__ import annotations

VERSION = 1

# Standard curves: (p, a, b, Gx, Gy, n); cofactor 1 for all of them.
STD = {
    "P-192": (2**192 - 2**64 - 1, -3,
              0x64210519E59C80E70FA7E9AB72243049FEB8DEECC146B9B1,
              0x188DA80EB03090F67CBF20EB43A18800F4FF0AFD82FF1012,
              0x07192B95FFC8DA78631011ED6B24CDD573F977A11E794811,
              0xFFFFFFFFFFFFFFFFFFFFFFFF99DEF836146BC9B1B4D22831),
    "P-256": (2**256 - 2**224 + 2**192 + 2**96 - 1, -3,
              0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B,
              0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
              0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5,
              0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551),
    "secp256k1": (2**256 - 2**32 - 977, 0, 7,
                  0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
                  0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
                  0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141),
    "P-384": (2**384 - 2**128 - 2**96 + 2**32 - 1, -3,
              0xB3312FA7E23EE7E4988E056BE3F82D19181D9C6EFE8141120314088F5013875AC656398D8A2ED19D2A85C8EDD3EC2AEF,
              0xAA87CA22BE8B05378EB1C71EF320AD746E1D3B628BA79B9859F741E082542A385502F25DBF55296C3A545E3872760AB7,
              0x3617DE4A96262C6F5D9E98BF9292DC29F8F41DBD289A147CE9DA3113B5F0B8C00A60B1CE1D7E819D7A431D7C90EA0E5F,
              0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC7634D81F4372DDF581A0DB248B0A77AECEC196ACCC52973),
    "P-521": (2**521 - 1, -3,
              0x0051953EB9618E1C9A1F929A21A0B68540EEA2DA725B99B315F3B8B489918EF109E156193951EC7E937B1652C0BD3BB1BF073573DF883D2C34F1EF451FD46B503F00,
              0x00C6858E06B70404E9CD9E3ECB662395B4429C648139053FB521F828AF606B4D3DBAA14B5E77EFE75928FE1DC127A2FFA8DE3348B3C1856A429BF97E7E31C2E5BD66,
              0x011839296A789A3BC0045C8A5FB42C7D1BD998F54449579B446817AFBD17273E662C97EE72995EF42640C550B9013FAD0761353C7086A272C24088BE94769FD16650,
              0x01FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFA51868783BF2F966B7FCC0148F709A5D03BB5C9B8899C47AEBB6FB71E91386409),
}

SEA_BITS = 256          # Sage's E.order() (SEA) is fast enough up to here for vectors


# --- generation (Sage) ----------------------------------------------------------------

def _sage():
    import sage.all as S  # noqa: F401  (heavy import, only when generating)
    return S


def _is_prime(n) -> bool:
    from sage.all import ZZ
    return ZZ(n).is_pseudoprime()


def _prime(rng, bits: int, shape: str = "any") -> int:
    """A (probable) prime of exactly ``bits`` bits; shape: any | 3mod4 | 1mod4 | 5mod8 |
    1mod8 | 2mod3 | 1mod3 | ts-hard (p = 1 + 2^s c with s = bits // 2)."""
    want = {"3mod4": (3, 4), "1mod4": (1, 4), "5mod8": (5, 8), "1mod8": (1, 8),
            "2mod3": (2, 3), "1mod3": (1, 3)}.get(shape)
    while True:
        if shape == "ts-hard":
            s = bits // 2
            c = rng.getrandbits(bits - s) | (1 << (bits - s - 1)) | 1
            n = c << s | 1
        else:
            n = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
            if want:
                r, m = want
                n += (r - n) % m
                if m == 3 and n % 2 == 0:      # keep it odd: step by 3 to the next odd one
                    n += 3
        if n.bit_length() == bits and n > 3 and _is_prime(n):
            return n


def _curve(rng, p: int, kind: str):
    """(a, b, tags) of a non-singular curve over F_p of the given kind."""
    from sage.all import GF
    while True:
        a, b, tags = rng.randrange(p), rng.randrange(p), []
        if kind == "a0":
            a, tags = 0, ["a=0"]
        elif kind == "b0":
            b, tags = 0, ["b=0"]
        elif kind == "a-3":
            a, tags = p - 3, ["a=-3"]
        elif kind == "2-torsion":
            x0 = rng.randrange(p)
            b, tags = (-x0 ** 3 - a * x0) % p, ["2-torsion"]
        elif kind == "full-2-torsion":
            r1, r2 = rng.randrange(p), rng.randrange(p)
            r3 = (-r1 - r2) % p
            # (x - r1)(x - r2)(x - r3) with r1 + r2 + r3 = 0
            a = (r1 * r2 + r1 * r3 + r2 * r3) % p
            b = (-r1 * r2 * r3) % p
            tags = ["full-2-torsion"]
        elif kind == "supersingular":
            # y^2 = x^3 + b, p = 2 mod 3, or y^2 = x^3 + a x, p = 3 mod 4: #E = p + 1
            if p % 3 == 2:
                a, tags = 0, ["a=0", "supersingular"]
            elif p % 4 == 3:
                b, tags = 0, ["b=0", "supersingular"]
            else:
                raise ValueError("supersingular needs p = 2 mod 3 or p = 3 mod 4")
        if (4 * a ** 3 + 27 * b ** 2) % p:
            F = GF(p, proof=False)
            if kind == "supersingular" and (F(a) == 0 and F(b) == 0):
                continue
            return a, b, tags


def _E(p, a, b):
    """Sage's E over GF(p). p is a BPSW probable prime; without ``proof`` off, the
    constructor proves p prime, which takes half a minute at 2048 bits."""
    from sage.all import GF, EllipticCurve, proof
    with proof.WithProof("arithmetic", False):
        return EllipticCurve(GF(p, proof=False), [a, b])


def _random_point(rng, E, p):
    """A random finite point of E, drawn with ``rng`` (not E.random_point())."""
    a, b = int(E.a4()), int(E.a6())
    F = E.base_field()
    while True:
        x = F(rng.randrange(p))
        r = x ** 3 + a * x + b
        if r.is_square():
            y = r.sqrt()
            if rng.getrandbits(1):
                y = -y
            return E(x, y)


def _pt(P):
    return None if P.is_zero() else [int(P[0]), int(P[1])]


def _cdict(p, a, b):
    return {"p": int(p), "a": int(a) % int(p), "b": int(b) % int(p)}


def _naf(n: int) -> list[int]:
    """The NAF by the textbook n mod 4 rule (independent of the reference's 3n trick)."""
    out = []
    while n:
        if n & 1:
            d = 2 - (n % 4)
            n -= d
        else:
            d = 0
        out.append(d)
        n >>= 1
    return out


def gen_add(params, rng):
    """Item 1: P + Q, P - Q, -P, 2P with the corner cases."""
    bits = int(params["bits"])
    case = rng.choices(["add", "add-same", "add-inverse", "add-infinity", "sub", "double",
                        "double-2-torsion", "neg", "neg-infinity"],
                       weights=[30, 8, 8, 8, 8, 18, 6, 8, 3])[0]
    kind = "2-torsion" if case == "double-2-torsion" else rng.choice(
        ["generic", "generic", "a0", "a-3"])
    p = _prime(rng, bits)
    a, b, tags = _curve(rng, p, kind)
    E = _E(p, a, b)
    P = _random_point(rng, E, p)
    tags = tags + [case, f"p{bits}"]
    inp = {"curve": _cdict(p, a, b)}
    if case in ("add", "sub"):
        Q = _random_point(rng, E, p)
        inp.update(op=case, P=_pt(P), Q=_pt(Q))
        R = P + Q if case == "add" else P - Q
    elif case == "add-same":
        inp.update(op="add", P=_pt(P), Q=_pt(P))
        R = P + P
    elif case == "add-inverse":
        inp.update(op="add", P=_pt(P), Q=_pt(-P))
        R = E(0)
        tags.append("result-infinity")
    elif case == "add-infinity":
        which = rng.choice(["O+P", "P+O", "O+O"])
        A, B = (E(0), P) if which == "O+P" else (P, E(0)) if which == "P+O" else (E(0), E(0))
        inp.update(op="add", P=_pt(A), Q=_pt(B))
        R = A + B
        tags.append("infinity")
    elif case == "double":
        inp.update(op="double", P=_pt(P))
        R = 2 * P
    elif case == "double-2-torsion":
        x0 = next(r for r in E.division_polynomial(2).roots(multiplicities=False))
        T = E(x0, 0)
        inp.update(op="double", P=_pt(T))
        R = 2 * T
        tags.append("result-infinity")
    elif case == "neg":
        inp.update(op="neg", P=_pt(P))
        R = -P
    else:
        inp.update(op="neg", P=None)
        R = E(0)
        tags.append("infinity")
    if params.get("repeat"):
        inp["repeat"] = int(params["repeat"])
    return {"input": inp, "expected": {"point": _pt(R)}, "tags": tags}


def gen_mul(params, rng):
    """Items 2-3: [k]P by the binary or the ternary method, with corner scalars."""
    bits = int(params["bits"])
    std = list(params.get("std") or [])
    method = rng.choice(["binary", "ternary"])
    case = rng.choices(["random", "std", "corner", "supersingular", "a0", "a-3",
                        "2-torsion", "infinity", "k-large", "k-negative"],
                       weights=[30, 20 if std else 0, 20, 6, 6, 6, 3, 3, 3, 3])[0]
    tags = [method, case]
    n = None
    if case == "std":
        name = rng.choice(std)
        p, a, b, gx, gy, n = STD[name]
        E = _E(p, a, b)
        G = E(gx, gy)
        P = G if rng.getrandbits(1) else rng.randrange(1, n) * G
        tags += [f"std-{name}"]
        k = rng.choice([rng.randrange(1, n), 0, 1, n - 1, n, -rng.randrange(1, n)])
    else:
        kind = {"supersingular": "supersingular", "a0": "a0", "a-3": "a-3",
                "2-torsion": "2-torsion"}.get(case, "generic")
        if kind == "supersingular":
            p = _prime(rng, bits, rng.choice(["2mod3", "3mod4"]))
        else:
            p = _prime(rng, bits)
        a, b, ctags = _curve(rng, p, kind)
        tags += ctags
        E = _E(p, a, b)
        P = _random_point(rng, E, p)
        if kind == "supersingular":
            n = p + 1                                  # #E = p + 1: [p + 1]P = O
        elif case == "corner" and bits <= SEA_BITS:
            n = int(E.order())
        if case == "2-torsion":
            x0 = E.division_polynomial(2).roots(multiplicities=False)[0]
            P = E(x0, 0)
        if case == "infinity":
            P = E(0)
        if case == "corner" and n is not None or case == "supersingular":
            k = rng.choice([0, 1, -1, 2, n, n - 1, n + 1, -(n - 1), 2 * n + 3])
            tags.append({0: "k=0", 1: "k=1", -1: "k=-1", 2: "k=2", n: "k=#E", n - 1: "k=#E-1",
                         n + 1: "k=#E+1", -(n - 1): "k=-(#E-1)"}.get(k, "k=2#E+3"))
        elif case == "corner":
            k = rng.choice([0, 1, -1, 2, 3])
            tags.append(f"k={k}")
        elif case == "k-large":
            k = rng.getrandbits(2 * bits)
        elif case == "k-negative":
            k = -rng.getrandbits(bits)
        else:
            k = rng.getrandbits(bits)
    if bits and f"p{bits}" not in tags:
        tags.append(f"p{bits}")
    R = k * P
    if R.is_zero():
        tags.append("result-infinity")
    inp = {"op": "mul", "curve": _cdict(E.base_field().order(), E.a4(), E.a6()),
           "P": _pt(P), "k": int(k), "method": method}
    if params.get("repeat"):
        inp["repeat"] = int(params["repeat"])
    return {"input": inp, "expected": {"point": _pt(R)}, "tags": tags}


def gen_point(params, rng):
    """Item 4: a point on a given curve; the shape of p decides the square-root case."""
    bits = int(params["bits"])
    shape = rng.choice(["3mod4", "5mod8", "1mod8", "ts-hard"])
    kind = rng.choice(["generic", "generic", "a0", "b0", "2-torsion"])
    p = _prime(rng, bits, shape)
    a, b, tags = _curve(rng, p, kind)
    E = _E(p, a, b)
    inp = {"op": "point", "curve": _cdict(p, a, b), "seed": rng.getrandbits(32)}
    if params.get("repeat"):
        inp["repeat"] = int(params["repeat"])
    return {"input": inp, "expected": {"example": _pt(_random_point(rng, E, p))},
            "tags": tags + [f"p={shape}", f"p{bits}"]}


def gen_order(params, rng):
    """Item 5 / remark 3: #E(F_p) by Shanks--Mestre or Schoof."""
    bits = int(params["bits"])
    method = params.get("method", "shanks-mestre")
    kind = rng.choices(["generic", "a0", "b0", "supersingular", "full-2-torsion", "prime-order"],
                       weights=[40, 12, 12, 12, 12, 12])[0]
    if kind == "supersingular":
        p = _prime(rng, bits, rng.choice(["2mod3", "3mod4"]))
    elif kind == "a0":
        p = _prime(rng, bits, "1mod3")       # ordinary j = 0 (six twists)
    elif kind == "b0":
        p = _prime(rng, bits, "1mod4")       # ordinary j = 1728 (four twists)
    else:
        p = _prime(rng, bits)
    while True:
        a, b, tags = _curve(rng, p, "generic" if kind == "prime-order" else kind)
        E = _E(p, a, b)
        n = int(E.order())
        if kind != "prime-order" or _is_prime(n):
            break
    t = p + 1 - n
    tags = tags + [{"a0": "j=0", "b0": "j=1728"}.get(kind, kind), f"p{bits}", method]
    if t == 0:
        tags.append("t=0")
    if p <= 229:
        tags.append("p<=229")
    inp = {"op": "order", "curve": _cdict(p, a, b), "method": method, "seed": rng.getrandbits(32)}
    return {"input": inp, "expected": {"order": n, "trace": t}, "tags": sorted(set(tags))}


def gen_misc(params, rng):
    """Ternary expansions (remark 1) and every operation on tiny curves (p < 256)."""
    case = rng.choice(["ternary", "ternary", "ternary", "tiny-add", "tiny-mul", "tiny-point",
                       "tiny-order"])
    if case == "ternary":
        sub = rng.choice(["zero", "one", "small", "ones", "power", "alternating", "random"])
        k = rng.randrange(2, 2049)
        n = {"zero": 0, "one": 1, "small": rng.randrange(2, 64), "ones": 2 ** k - 1,
             "power": 2 ** k, "alternating": (2 ** (2 * (k // 2)) - 1) // 3,
             "random": rng.getrandbits(k)}[sub]
        return {"input": {"op": "ternary", "n": n}, "expected": {"digits": _naf(n)},
                "tags": ["ternary", f"n-{sub}"]}
    from sage.all import prime_range
    p = rng.choice([q for q in prime_range(5, 256)])
    while True:
        a, b = rng.randrange(p), rng.randrange(p)
        if (4 * a ** 3 + 27 * b ** 2) % p:
            break
    E = _E(p, a, b)
    tags = [case, "tiny-p"]
    c = _cdict(p, a, b)
    if case == "tiny-add":
        pts = E.points()
        P, Q = rng.choice(pts), rng.choice(pts)
        return {"input": {"op": "add", "curve": c, "P": _pt(P), "Q": _pt(Q)},
                "expected": {"point": _pt(P + Q)}, "tags": tags}
    if case == "tiny-mul":
        P = rng.choice(E.points())
        k = rng.randrange(-3 * p, 3 * p)
        m = rng.choice(["binary", "ternary"])
        return {"input": {"op": "mul", "curve": c, "P": _pt(P), "k": k, "method": m},
                "expected": {"point": _pt(k * P)}, "tags": tags + [m]}
    if case == "tiny-point":
        n_fin = len(E.points()) - 1
        return {"input": {"op": "point", "curve": c, "seed": rng.getrandbits(32)},
                "expected": {"example": _pt(E.points()[1])},
                "tags": tags + (["few-points"] if n_fin <= 3 else [])}
    method = rng.choice(["shanks-mestre", "schoof"])
    return {"input": {"op": "order", "curve": c, "method": method, "seed": rng.getrandbits(32)},
            "expected": {"order": int(E.order())},
            "tags": tags + [method] + (["p<=229"] if p <= 229 else [])}


def generate(params: dict, rng) -> dict:
    kind = params["kind"]
    return {"add": gen_add, "mul": gen_mul, "point": gen_point, "order": gen_order,
            "misc": gen_misc}[kind](params, rng)


# --- verification (standard library) ---------------------------------------------------

def _int(v):
    if isinstance(v, bool):
        raise ValueError(f"not an integer: {v!r}")
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        return int(v, 0)
    raise ValueError(f"not an integer: {v!r}")


def _affine(out: dict, p: int) -> list:
    """The answer's point in affine coordinates: candidates (one per plausible reading).

    Accepted: null / "O" / "inf" (the point at infinity), [x, y], {"x": .., "y": ..},
    and [X, Y, Z] with ``"coords"`` = "projective" (x = X/Z, y = Y/Z) or "jacobian"
    (x = X/Z^2, y = Y/Z^3); without ``coords`` both readings are tried. Z = 0 is O.
    """
    P = out.get("point")
    if P is None or (isinstance(P, str) and P.lower() in ("o", "inf", "infinity")):
        return [None]
    if isinstance(P, dict):
        P = [P["x"], P["y"]] + ([P["z"]] if "z" in P else [])
    P = [_int(v) for v in P]
    if len(P) == 2:
        return [(P[0] % p, P[1] % p)]
    if len(P) != 3:
        raise ValueError(f"a point has 2 or 3 coordinates, got {len(P)}")
    X, Y, Z = (v % p for v in P)
    if Z == 0:
        return [None]
    zi = pow(Z, -1, p)
    coords = out.get("coords")
    cands = []
    if coords in (None, "projective"):
        cands.append((X * zi % p, Y * zi % p))
    if coords in (None, "jacobian"):
        cands.append((X * zi * zi % p, Y * zi ** 3 % p))
    if not cands:
        raise ValueError(f"unknown coords {coords!r}")
    return cands


def _fmt(P):
    return "O" if P is None else f"({P[0]}, {P[1]})"


def verify(vector: dict, output: dict) -> str | None:
    inp, exp = vector["input"], vector["expected"]
    if not isinstance(output, dict):
        return f"output {output!r} is not an object"
    op = inp["op"]
    try:
        if op == "ternary":
            d = output.get("digits")
            if not isinstance(d, list) or any(isinstance(x, bool) or x not in (-1, 0, 1) for x in d):
                return f"digits must be a list over {{-1, 0, 1}}, got {str(d)[:80]}"
            v = sum(x << i for i, x in enumerate(d))
            return None if v == inp["n"] else f"sum d_i 2^i = {v} != n = {inp['n']}"
        c = inp["curve"]
        p, a, b = c["p"], c["a"], c["b"]
        if op == "order":
            n = output.get("order")
            return None if n == exp["order"] else f"#E = {exp['order']}, got {n!r}"
        cands = _affine(output, p)
        if op == "point":
            for P in cands:
                if P is not None and (P[1] ** 2 - P[0] ** 3 - a * P[0] - b) % p == 0:
                    return None
            return f"{_fmt(cands[0])} is not a finite point of the curve"
        want = exp["point"]
        want = None if want is None else (want[0], want[1])
        if want in cands:
            return None
        return f"expected {_fmt(want)}, got {_fmt(cands[0])}"
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as e:
        return f"malformed output: {type(e).__name__}: {e}"
