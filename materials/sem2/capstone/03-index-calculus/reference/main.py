"""JSON-lines CLI of the index-calculus reference (see README.md).

stdin:  {"id": ..., "input": {"p": int, "g": int, "h": int, ["B": int], ["c": float],
                              ["margin": float], ["seed": int], ["full": bool],
                              ["smooth": "powmod" | "trial"]}}
stdout: {"id": ..., "output": {"x": int | null}, "extra": {...}}   or   {"id": ..., "error": "..."}
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from icalc.solver import solve  # noqa: E402

OPTIONS = {"B": "b", "c": "c", "margin": "margin", "seed": "seed", "full": "full",
           "smooth": "smooth"}


def answer(req: dict) -> dict:
    out = {"id": req.get("id")}
    try:
        inp = req["input"]
        p, g, h = (int(inp[k]) for k in ("p", "g", "h"))
        kw = {v: inp[k] for k, v in OPTIONS.items() if inp.get(k) is not None}
        out["output"], out["extra"] = solve(p, g, h, **kw)
    except Exception as e:                       # a bad request must not kill the solver
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            req, bad = {}, f"bad JSON: {e}"
        else:
            bad = None
        res = {"id": req.get("id"), "error": bad} if bad else answer(req)
        sys.stdout.write(json.dumps(res, separators=(",", ":")) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
