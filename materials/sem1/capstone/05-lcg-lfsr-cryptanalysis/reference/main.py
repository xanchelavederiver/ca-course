import json
import sys

from prng import (berlekamp_massey, full_period_conditions, lcg_decrypt, lcg_generate, lcg_next,
                  lcg_period, lcg_recover, lfsr_decrypt, lfsr_generate, lfsr_period, lfsr_recover,
                  polynomial_forms)


def solve(inp):
    op = inp["op"]
    if op == "lcg_generate":
        return {"outputs": lcg_generate(inp["a"], inp["c"], inp["m"], inp["state"], inp["count"])}
    if op == "lcg_period":
        return lcg_period(inp["a"], inp["c"], inp["m"], inp["state"], inp.get("limit", 1_000_000))
    if op == "lcg_full_period":
        return full_period_conditions(inp["a"], inp["c"], inp["m"], inp["factors"])
    if op == "lcg_next":
        return {"next": lcg_next(inp["a"], inp["c"], inp["m"], inp["state"])}
    if op == "lcg_recover":
        return lcg_recover(inp["outputs"])
    if op == "lcg_decrypt":
        return lcg_decrypt(inp["ciphertext"], inp["known_plaintext"])
    if op == "lfsr_generate":
        return {"bits": lfsr_generate(inp["coefficients"], inp["state"], inp["count"])}
    if op == "lfsr_period":
        return lfsr_period(inp["coefficients"], inp["state"], inp.get("limit", 1_000_000))
    if op == "berlekamp_massey":
        return berlekamp_massey(inp["sequence"])
    if op == "lfsr_recover":
        return lfsr_recover(inp["sequence"])
    if op == "lfsr_polynomial":
        return polynomial_forms(inp["connection_mask"], inp["linear_complexity"])
    if op == "lfsr_decrypt":
        return lfsr_decrypt(inp["ciphertext"], inp["known_plaintext"])
    raise ValueError(f"unknown operation {op!r}")


def main():
    for line in sys.stdin:
        req = json.loads(line)
        try:
            output = solve(req["input"])
            if "trace" in output:
                extra = {"trace": output.pop("trace")}
            else:
                extra = {}
            answer = {"id": req["id"], "output": output, "extra": {"op": req["input"]["op"], **extra}}
        except Exception as exc:
            answer = {"id": req.get("id"), "error": str(exc)}
        print(json.dumps(answer), flush=True)


if __name__ == "__main__":
    main()
