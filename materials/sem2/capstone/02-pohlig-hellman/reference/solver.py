"""Reference solver of the Pohlig--Hellman capstone: a JSON-lines CLI.

Each stdin line ``{"id": ..., "input": {...}}`` gets one stdout line
``{"id": ..., "output": {"x": ...}, "extra": {...}}`` (or ``{"id": ..., "error": "..."}``).

Input fields (integers may also be given as decimal strings):

    p        prime modulus
    g, h     base and target in (Z/pZ)^*
    factors  optional: factorization of p - 1 as [[q, e], ...]; factored here if absent
    prime_method        optional: auto (default) | brute | bsgs   -- prime-order subproblems
    prime_power_method  optional: digits (default) | direct       -- prime-power subproblems

``output.x`` is the smallest x >= 0 with g^x = h (mod p), i.e. x mod ord(g).
``extra`` keeps the intermediate data the spec asks for: ord(g) and its factorization,
the congruence system x = x_i (mod q_i^e_i), and every subproblem with its digits.

Run: ``sage -python reference/solver.py`` (or any Python >= 3.10; no Sage is needed).
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dlp import DlogError, is_probable_prime, pohlig_hellman  # noqa: E402


def _int(v, name: str) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, str)):
        raise DlogError(f"{name} must be an integer")
    try:
        return int(v)
    except ValueError as e:
        raise DlogError(f"{name} must be an integer") from e


def parse(inp: dict) -> dict:
    """Validate a request input; returns keyword arguments of :func:`pohlig_hellman`."""
    if not isinstance(inp, dict):
        raise DlogError("input must be an object")
    for k in ("p", "g", "h"):
        if k not in inp:
            raise DlogError(f"missing field {k!r}")
    p = _int(inp["p"], "p")
    if p < 2 or not is_probable_prime(p):
        raise DlogError(f"p = {p} is not prime")
    args = {"p": p, "g": _int(inp["g"], "g"), "h": _int(inp["h"], "h")}
    fs = inp.get("factors")
    if fs is not None:
        try:
            fs = [(_int(q, "factor"), _int(e, "exponent")) for q, e in fs]
        except (TypeError, ValueError) as e:
            raise DlogError("factors must be a list of [q, e] pairs") from e
        prod = 1
        for q, e in fs:
            if e < 1 or not is_probable_prime(q):
                raise DlogError(f"bad factor {q}^{e} of p - 1")
            prod *= q ** e
        if prod != p - 1 or len({q for q, _ in fs}) != len(fs):
            raise DlogError("factors do not multiply to p - 1")
        args["group_factors"] = sorted(fs)
    pm = inp.get("prime_method", "auto")
    if pm not in ("auto", "brute", "bsgs"):
        raise DlogError(f"prime_method must be auto, brute or bsgs, not {pm!r}")
    ppm = inp.get("prime_power_method", "digits")
    if ppm not in ("digits", "direct"):
        raise DlogError(f"prime_power_method must be digits or direct, not {ppm!r}")
    args.update(prime_method=pm, reduce=ppm == "digits")
    return args


def answer(req: dict) -> dict:
    rid = req.get("id") if isinstance(req, dict) else None
    try:
        sol = pohlig_hellman(**parse(req.get("input") if isinstance(req, dict) else None))
    except DlogError as e:
        return {"id": rid, "error": str(e)}
    return {"id": rid, "output": {"x": sol.x}, "extra": sol.extra()}


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            out = {"id": None, "error": f"not a JSON line: {e}"}
        else:
            try:
                out = answer(req)
            except Exception as e:  # noqa: BLE001 -- one bad request must not kill the server
                out = {"id": req.get("id") if isinstance(req, dict) else None,
                       "error": f"{type(e).__name__}: {e}"}
        sys.stdout.write(json.dumps(out, separators=(",", ":")) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
