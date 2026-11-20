import json
import sys

from primality import (fermat, korselt, lucas_lehmer, mersenne_reduce, miller_rabin,
                       solovay_strassen, wilson)


def main():
    for line in sys.stdin:
        req = json.loads(line)
        try:
            inp = req["input"]
            op = inp["op"]
            if op == "wilson":
                output = wilson(int(inp["n"]))
            elif op in ("fermat", "miller_rabin", "solovay_strassen"):
                function = {"fermat": fermat, "miller_rabin": miller_rabin,
                            "solovay_strassen": solovay_strassen}[op]
                output = function(int(inp["n"]), [int(a) for a in inp["bases"]])
            elif op == "korselt":
                output = korselt(int(inp["n"]), inp["factors"])
            elif op == "lucas_lehmer":
                output = lucas_lehmer(int(inp["exponent"]))
            elif op == "mersenne_reduce":
                output = {"value": mersenne_reduce(int(inp["x"]), int(inp["exponent"]))}
            else:
                raise ValueError(f"unknown operation {op!r}")
            answer = {"id": req["id"], "output": output, "extra": {"op": op}}
        except Exception as exc:
            answer = {"id": req.get("id"), "error": str(exc)}
        print(json.dumps(answer), flush=True)


if __name__ == "__main__":
    main()
