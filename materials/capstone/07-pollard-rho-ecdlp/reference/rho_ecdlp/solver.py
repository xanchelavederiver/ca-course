"""Request handling of the reference solver (the JSON-lines CLI is in ``main.py``).

Operations (``input["op"]``):

``dlog`` (default) — solve [x]P = Q on E: y^2 = x^3 + a x + b over F_p.
    in:  p, a, b, P = [x, y], Q = [x, y] | null (O), n = ord(P) (optional: computed
         by Shanks-Mestre if absent), method = "floyd" | "dp" (default "floyd"),
         and the search parameters of item 1 of the spec: start = [alpha_0, beta_0]
         (the start point is [alpha_0]P + [beta_0]Q), max_iter, max_attempts; for
         "dp" also r and theta; seed (default: derived from the request).
    out: {"x": x} with 0 <= x < n.
    extra: method, n, the attempts with alpha_i, beta_i, gamma_i, delta_i (floyd) or
         the colliding distinguished points (dp), the congruence, all its solutions,
         iterations, retries, and "verified" ([x]P = Q rechecked).

``order`` — ord(P) (item 2 of the spec).
    in:  p, a, b, P.   out: {"n": ord(P)}.   extra: the BSGS data.
"""

from __future__ import annotations

import hashlib
import json
import random

from .ec import Curve, CurveError, to_json
from .order import point_order
from .rho import Rho, RhoFailure


class RequestError(ValueError):
    pass


def _int(inp: dict, key: str, default=None, lo: int | None = None) -> int | None:
    v = inp.get(key, default)
    if v is None:
        return None
    if not isinstance(v, int) or isinstance(v, bool) or (lo is not None and v < lo):
        raise RequestError(f"{key} must be an integer{'' if lo is None else f' >= {lo}'}, got {v!r}")
    return v


def request_seed(inp: dict) -> int:
    """A per-request seed: the given one, else a hash of the canonical request."""
    if "seed" in inp:
        return _int(inp, "seed")
    text = json.dumps(inp, sort_keys=True, separators=(",", ":"))
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")


def handle(inp: dict) -> tuple[dict, dict]:
    """(output, extra) for one request; raises RequestError / CurveError / RhoFailure."""
    if not isinstance(inp, dict):
        raise RequestError("input must be an object")
    op = inp.get("op", "dlog")
    for k in ("p", "a", "b", "P"):
        if k not in inp:
            raise RequestError(f"missing {k!r}")
    E = Curve.checked(inp["p"], inp["a"], inp["b"])
    P = E.point(inp["P"])
    if op == "order":
        n, info = point_order(E, P)
        return {"n": n}, info
    if op != "dlog":
        raise RequestError(f"unknown op {op!r} (dlog | order)")
    if "Q" not in inp:
        raise RequestError("missing 'Q'")
    Q = E.point(inp["Q"])
    seed = request_seed(inp)
    extra: dict = {"seed": seed}
    n = _int(inp, "n", lo=1)
    if n is None:
        n, extra["order"] = point_order(E, P)
        extra["n_source"] = "computed"
    elif E.mul(n, P) is not None:
        raise RequestError(f"[n]P != O: n = {n} is not a multiple of ord(P)")
    extra["n"] = n
    method = inp.get("method", "floyd")
    if method not in ("floyd", "dp"):
        raise RequestError(f"unknown method {method!r} (floyd | dp)")
    start = inp.get("start")
    if start is not None and not (isinstance(start, list) and len(start) == 2
                                  and all(isinstance(t, int) for t in start)):
        raise RequestError("start must be [alpha_0, beta_0]")
    rho = Rho(E, P, Q, n, random.Random(seed), start=tuple(start) if start else None,
              max_iter=_int(inp, "max_iter", lo=1), max_attempts=_int(inp, "max_attempts", 10, lo=1))
    extra["method"] = method
    if P is None:                       # n = 1: only Q = O is solvable, by x = 0
        if Q is not None:
            raise RequestError("P = O but Q != O: no solution")
        x = 0
        extra["method"] = "trivial"
    elif method == "floyd":
        x = rho.floyd()
    else:
        x = rho.distinguished(r=_int(inp, "r", 20, lo=2), theta=_int(inp, "theta", lo=0))
    extra["attempts"] = rho.attempts
    extra["iterations"] = sum(a.get("iterations", 0) for a in rho.attempts)
    extra["retries"] = (max(0, len(rho.attempts) - 1) if method == "floyd"
                        else len(rho.attempts[0].get("degenerate", [])) if rho.attempts else 0)
    extra["verified"] = E.mul(x, P) == Q   # item 3: check the solution
    extra["Q"] = to_json(Q)
    return {"x": x}, extra


def handle_safe(inp) -> dict:
    """The answer object (without the id): output + extra, or error."""
    try:
        out, extra = handle(inp)
        return {"output": out, "extra": extra}
    except (RequestError, CurveError, RhoFailure, ArithmeticError) as e:
        return {"error": f"{type(e).__name__}: {e}"}


__all__ = ["handle", "handle_safe", "RhoFailure"]
