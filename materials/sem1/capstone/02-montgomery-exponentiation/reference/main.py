import json
import sys

from montgomery import evaluate, prepare

CACHE = {}


def main():
    for line in sys.stdin:
        req = json.loads(line)
        try:
            inp = req["input"]
            a, e, n = int(inp["a"]), int(inp["e"]), int(inp["n"])
            method, parameter = inp["method"], inp.get("parameter")
            key = (a, n, method, parameter)
            reuse = bool(inp.get("reuse"))
            if reuse and key in CACHE:
                prepared, cache_status = CACHE[key], "hit"
            else:
                prepared, cache_status = prepare(a, n, method, parameter), "miss" if reuse else "fresh"
                if reuse:
                    if len(CACHE) >= 32:
                        CACHE.pop(next(iter(CACHE)))
                    CACHE[key] = prepared
            value, stats = evaluate(prepared, a, e, n, method)
            answer = {"id": req["id"], "output": {"value": value, "operations": stats},
                      "extra": {"method": method, "cache": cache_status}}
        except Exception as exc:
            answer = {"id": req.get("id"), "error": str(exc)}
        print(json.dumps(answer), flush=True)


if __name__ == "__main__":
    main()
