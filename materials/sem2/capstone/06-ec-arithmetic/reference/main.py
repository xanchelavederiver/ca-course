"""Reference solver of the EC-arithmetic capstone: a JSON-lines CLI.

Reads ``{"id": ..., "input": {...}}`` lines on stdin and answers each with
``{"id": ..., "output": {...}}`` (plus ``"extra"`` or ``"error"``), flushing every line.
See README.md for the operations. Run: ``sage -python reference/main.py``
(only gmpy2 is needed; Sage itself is not imported).
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ecarith import Curve, CurveError, order_naive, order_shanks_mestre, order_schoof  # noqa: E402
from ecarith.scalar import mul, ternary_expansion  # noqa: E402

_curves: dict[tuple, Curve] = {}


def as_int(v) -> int:
    """JSON ints, or strings in any base Python accepts ("123", "0x7b")."""
    if isinstance(v, bool):
        raise ValueError(f"not an integer: {v!r}")
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        return int(v, 0)
    raise ValueError(f"not an integer: {v!r}")


def curve_of(inp: dict) -> Curve:
    c = inp["curve"]
    key = (as_int(c["p"]), as_int(c["a"]), as_int(c["b"]))
    if key not in _curves:                    # validation (primality, discriminant) once
        _curves[key] = Curve(*key)
    return _curves[key]


def point_in(E: Curve, P):
    return E.point(None if P is None else [as_int(P[0]), as_int(P[1])])


def point_out(P):
    return None if P is None else [int(P[0]), int(P[1])]


def solve(inp: dict) -> tuple[dict, dict | None]:
    op = inp.get("op")
    reps = max(1, int(inp.get("repeat", 1)))
    if op == "ternary":
        n = as_int(inp["n"])
        for _ in range(reps):
            d = ternary_expansion(n)
        return {"digits": d}, None
    E = curve_of(inp)
    if op in ("add", "sub"):
        P, Q = point_in(E, inp["P"]), point_in(E, inp["Q"])
        f = E.add if op == "add" else E.sub
        for _ in range(reps):
            R = f(P, Q)
        return {"point": point_out(R)}, None
    if op in ("double", "neg"):
        P = point_in(E, inp["P"])
        f = E.double if op == "double" else E.neg
        for _ in range(reps):
            R = f(P)
        return {"point": point_out(R)}, None
    if op == "mul":
        P, k = point_in(E, inp["P"]), as_int(inp["k"])
        method, coords = inp.get("method", "ternary"), inp.get("coords", "jacobian")
        for _ in range(reps):
            R = mul(E, P, k, method, coords)
        extra = None
        if method == "ternary" and k:
            d = ternary_expansion(abs(k))
            extra = {"ternary": "".join("+0-"[1 - x] for x in reversed(d)),
                     "nonzero_digits": sum(x != 0 for x in d)}
        return {"point": point_out(R)}, extra
    if op == "point":
        rng = random.Random(inp.get("seed", 0))
        for _ in range(reps):
            R = E.random_point(rng)
        return {"point": point_out(R)}, None
    if op == "order":
        method = inp.get("method", "shanks-mestre")
        rng = random.Random(inp.get("seed", 0))
        if method == "shanks-mestre":
            n, extra = order_shanks_mestre(E, rng)
        elif method == "schoof":
            n, extra = order_schoof(E)
        elif method == "naive":
            if E.p > 10 ** 6:
                raise ValueError("naive counting is for p <= 10^6")
            n, extra = order_naive(E), {"method": "naive"}
        else:
            raise ValueError(f"unknown method {method!r} (shanks-mestre | schoof | naive)")
        return {"order": n}, extra
    raise ValueError(f"unknown op {op!r} (add, sub, neg, double, mul, ternary, point, order)")


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            out, extra = solve(req["input"])
            ans = {"id": rid, "output": out}
            if extra:
                ans["extra"] = extra
        except (CurveError, ValueError, KeyError, TypeError, IndexError, ZeroDivisionError,
                ArithmeticError) as e:
            ans = {"id": rid, "error": f"{type(e).__name__}: {e}"}
        sys.stdout.write(json.dumps(ans, separators=(",", ":")) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
