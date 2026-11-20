"""Reference solver of the LLL capstone: a JSON-lines CLI (see README.md).

Each stdin line ``{"id": ..., "input": {"op": ..., ...}}`` gets one stdout line
``{"id": ..., "output": {...}, "extra": {...}}`` or ``{"id": ..., "error": "..."}``.

    op = gauss          {"basis": [v1, v2]}                  -> {"basis": [...]}
    op = check          {"basis": [...], "delta": "3/4"}     -> {"reduced", "size_reduced", "lovasz", "independent"}
    op = lll            {"basis": [...], "delta": "99/100", "trace": false} -> {"basis": [...]}
    op = congruential   {"q", "h", "e"}                      -> {"f", "g", "m"}
    op = knapsack       {"M": [...], "S"}                    -> {"x": [...]}

Pure Python: exact integer arithmetic only, no Sage needed (it runs under ``sage -python``
in the bench only because the taskgen image is the capstone's image).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.set_int_max_str_digits(0)      # big lattice entries are fine in JSON

from crypto import congruential_attack, knapsack_attack  # noqa: E402
from gauss import gauss_reduce  # noqa: E402
from lattice import check_reduced, lll_generators  # noqa: E402

CHECK_KEYS = ("reduced", "size_reduced", "lovasz", "independent")


def solve(inp: dict) -> tuple[dict, dict]:
    if not isinstance(inp, dict):
        raise ValueError("input must be an object")
    op = inp.get("op", "lll")
    if op == "gauss":
        red, extra = gauss_reduce(inp.get("basis"), trace=inp.get("trace", True))
        return {"basis": red}, extra
    if op == "check":
        res = check_reduced(inp.get("basis"), inp.get("delta", "3/4"))
        return {k: res.pop(k) for k in CHECK_KEYS}, res
    if op == "lll":
        red, extra = lll_generators(inp.get("basis"), inp.get("delta", "3/4"),
                                    trace=bool(inp.get("trace", False)))
        return {"basis": red}, extra
    if op == "congruential":
        return congruential_attack(inp)
    if op == "knapsack":
        return knapsack_attack(inp)
    raise ValueError(f"unknown op {op!r}")


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            out, extra = solve(req.get("input"))
            ans = {"id": rid, "output": out, "extra": extra}
        except Exception as e:  # noqa: BLE001 — answer with "error", never crash
            ans = {"id": rid, "error": f"{type(e).__name__}: {e}"}
        sys.stdout.write(json.dumps(ans, separators=(",", ":")) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
