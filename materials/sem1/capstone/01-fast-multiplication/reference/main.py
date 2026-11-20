import json
import sys

from fastmul import multiply


def main():
    for line in sys.stdin:
        req = json.loads(line)
        try:
            inp = req["input"]
            product, extra = multiply(int(inp["a"]), int(inp["b"]), inp["method"])
            answer = {"id": req["id"], "output": {"product": product},
                      "extra": {"method": inp["method"], **extra}}
        except Exception as exc:
            answer = {"id": req.get("id"), "error": str(exc)}
        print(json.dumps(answer), flush=True)


if __name__ == "__main__":
    main()
