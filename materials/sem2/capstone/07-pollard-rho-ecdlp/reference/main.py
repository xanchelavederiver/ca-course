#!/usr/bin/env python3
"""Reference solver of capstone 07 (Pollard's rho for the ECDLP), JSON-lines CLI.

Reads ``{"id": ..., "input": {...}}`` lines on stdin and answers each with one line
``{"id": ..., "output": {...}, "extra": {...}}`` (or ``"error"``), flushing after
every line. See ``rho_ecdlp/solver.py`` for the operations and README.md for usage.
Pure Python (no Sage): ``python3 reference/main.py`` or ``sage -python reference/main.py``.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rho_ecdlp.solver import handle_safe  # noqa: E402


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            print(json.dumps({"id": None, "error": f"bad JSON: {e}"}), flush=True)
            continue
        rid = req.get("id") if isinstance(req, dict) else None
        ans = handle_safe(req.get("input") if isinstance(req, dict) else None)
        print(json.dumps({"id": rid, **ans}, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
