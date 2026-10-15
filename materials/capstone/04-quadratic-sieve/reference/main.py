"""Quadratic sieve reference solver: a JSON-lines CLI (see reference/README.md).

    {"id": ..., "input": {"n": 1234567, "full": false, "trace": false}}
 -> {"id": ..., "output": {"factor": d, "cofactor": n // d}, "extra": {...}}
    with "full": true the output also has "factorization": [[p, e], ...].

Command-line options: --b-factor X (B = X * L(N)^(1/2)), --linalg gauss|sage
(Sage's GF(2) kernel instead of the hand-written elimination; for cross-checks).
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import qsieve


def solve(inp: dict, kw: dict) -> tuple[dict, dict]:
    n = inp.get("n")
    if isinstance(n, str) and n.lstrip("-").isdigit():
        n = int(n)
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError(f"n must be an integer, got {n!r}")
    t0 = time.perf_counter()
    kw = {**kw, "trace": bool(inp.get("trace"))}
    if inp.get("full"):
        fac, splits = qsieve.factorize(n, **kw)
        if not splits:
            raise ValueError(f"n = {n} is not composite")
        r = splits[0][1]
    else:
        r = qsieve.split(n, **kw)
    out = {"factor": r.factor, "cofactor": n // r.factor}
    extra = {"method": r.method, **r.extra}
    if inp.get("full"):
        out["factorization"] = [[p, e] for p, e in fac.items()]
        # the later splits (of the cofactors), in brief
        extra["splits"] = [{"n": m, "factor": s.factor, "method": s.method,
                            **{k: s.extra[k] for k in ("B", "fb_size", "relations") if k in s.extra}}
                           for m, s in splits[1:]]
    extra["wall_s"] = round(time.perf_counter() - t0, 4)
    return out, extra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--b-factor", type=float, default=qsieve.B_FACTOR)
    ap.add_argument("--linalg", choices=["gauss", "sage"], default="gauss")
    a = ap.parse_args(argv)
    kw = {"b_factor": a.b_factor, "linalg": a.linalg}
    for line in sys.stdin:
        if not line.strip():
            continue
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            out, extra = solve(req.get("input") or {}, kw)
            ans = {"id": rid, "output": out, "extra": extra}
        except Exception as e:  # noqa: BLE001 — answer with an error, never crash
            ans = {"id": rid, "error": f"{type(e).__name__}: {e}"}
        sys.stdout.write(json.dumps(ans) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
