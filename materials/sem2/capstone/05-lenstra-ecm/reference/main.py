#!/usr/bin/env python3
"""Reference solver of the capstone "Алгоритм факторизации Ленстры" (JSON-lines contract).

Each stdin line ``{"id": ..., "input": {...}}`` gets one stdout line
``{"id": ..., "output": {...}, "extra": {...}}`` or ``{"id": ..., "error": "..."}``.

Input (``n`` may be an int or a decimal string; every other field is optional)::

    {"op": "factorize" | "factor" | "curve",  "n": 1234567,
     "family": "z2z8" | "suyama" | "weierstrass",   # curve family (default: --family)
     "stage1": "primepowers" | "factorial",          # weierstrass only: k = p^e or j!
     "stage2": true, "B1": 2000, "B2": 200000, "curves": 25,
     "factor_bits": 40,                              # expected factor size (1st level)
     "trial": 100, "max_curves": 200000, "trace": false, "seed": 0}

Output:
    factorize: {"prime": bool, "factorization": [[p, e], ...]}   (incomplete if ECM gave up)
    factor:    {"prime": bool, "factor": d | null}              (d a proper factor)
    curve:     {"curve": {...}, "point": {...}}   a random curve modulo n with a point on it
"extra" holds the intermediate data the spec asks to keep: the number of curves, the
levels (B1, B2, curves) and, for every factor found, the curve, the starting point, the
bounds, the stage and the stage-1 prime after which the gcd appeared (with ``trace``:
the intermediate points of that curve).

The random choices are seeded by ``n`` and ``seed``, so a request is reproducible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lenstra import curves as C                     # noqa: E402
from lenstra.ecm import Options, Stats, factorize    # noqa: E402

OPTION_FIELDS = ("family", "stage1", "stage2", "B1", "B2", "curves", "factor_bits", "trial",
                 "max_curves", "trace")


def rng_for(n: int, seed) -> random.Random:
    h = hashlib.sha256(f"lenstra:{n}:{seed}".encode()).digest()
    return random.Random(int.from_bytes(h[:16], "big"))


def _int(v, name: str) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, str)):
        raise ValueError(f"{name} must be an integer")
    return int(v)


def options(inp: dict, defaults: Options) -> Options:
    o = Options(**vars(defaults))
    for k in OPTION_FIELDS:
        if inp.get(k) is not None:
            setattr(o, k, inp[k])
    for k in ("B1", "B2", "curves", "factor_bits", "trial", "max_curves"):
        if getattr(o, k) is not None:
            setattr(o, k, _int(getattr(o, k), k))
    if o.family not in C.FAMILIES:
        raise ValueError(f"unknown family {o.family!r} (have {', '.join(C.FAMILIES)})")
    if o.stage1 not in ("primepowers", "factorial"):
        raise ValueError(f"unknown stage1 {o.stage1!r}")
    if o.B1 is not None and o.B1 < 2:
        raise ValueError("B1 must be >= 2")
    return o


def solve(inp: dict, defaults: Options) -> tuple[dict, dict]:
    if not isinstance(inp, dict) or "n" not in inp:
        raise ValueError("input must be an object with an integer 'n'")
    n = _int(inp["n"], "n")
    op = inp.get("op", "factorize")
    opts = options(inp, defaults)
    rng = rng_for(n, inp.get("seed", 0))
    if op == "curve":
        return curve(n, rng, opts.family), {}
    if op not in ("factor", "factorize"):
        raise ValueError(f"unknown op {op!r}")
    if n < 2:
        raise ValueError(f"n must be >= 2, got {n}")
    stats = Stats()
    res, found, complete = factorize(n, rng, opts, stats, one=(op == "factor"))
    prime = not res if op == "factor" else res == {n: 1}
    extra = {"family": opts.family, "stage2": opts.stage2, "curves": stats.curves,
             "levels": stats.levels, "found": found}
    if op == "factor":
        return {"prime": prime, "factor": next(iter(res), None) if complete else None}, extra
    extra["complete"] = complete
    return {"prime": prime, "factorization": [[p, e] for p, e in res.items()]}, extra


def curve(n: int, rng: random.Random, family: str) -> dict:
    """Item 1 of the spec: a random curve modulo n and a point on it (affine coordinates)."""
    if n < 5 or n % 2 == 0 or n % 3 == 0:
        raise ValueError("curve: n must be > 3 and coprime to 6")
    for _ in range(1000):
        try:
            c = C.FAMILIES[family](n, rng)
            desc = c.describe()
            point = desc.pop("point")
            return {"curve": desc, "point": point}
        except (C.CurveFound, ArithmeticError) as e:
            d = getattr(e, "d", None)
            if d and 1 < d < n:
                return {"curve": None, "point": None, "factor": d}
    raise ValueError("could not build a curve")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--family", default="z2z8", choices=sorted(C.FAMILIES))
    ap.add_argument("--stage1", default="primepowers", choices=["primepowers", "factorial"])
    ap.add_argument("--no-stage2", action="store_true")
    ap.add_argument("--trial", type=int, default=100)
    a = ap.parse_args(argv)
    defaults = Options(family=a.family, stage1=a.stage1, stage2=not a.no_stage2, trial=a.trial)
    for line in sys.stdin:
        if not line.strip():
            continue
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            out, extra = solve(req.get("input"), defaults)
            ans = {"id": rid, "output": out, "extra": extra}
        except Exception as e:  # noqa: BLE001 — answer with an error, never crash
            ans = {"id": rid, "error": f"{type(e).__name__}: {e}"}
        sys.stdout.write(json.dumps(ans, separators=(",", ":")) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
