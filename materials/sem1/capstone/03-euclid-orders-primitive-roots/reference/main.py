import json
import sys

from ntheory import (batch_inverse, binary_gcd, crt, garner, inverse, order_product_tree,
                     order_sequential, primitive_root, xgcd)


def solve(inp):
    op = inp["op"]
    if op == "binary_gcd":
        return {"g": binary_gcd(int(inp["a"]), int(inp["b"]))}, {}
    if op == "xgcd":
        g, x, y = xgcd(int(inp["a"]), int(inp["b"]))
        return {"g": g, "x": x, "y": y}, {}
    if op == "inverse":
        return {"inverse": inverse(int(inp["a"]), int(inp["n"]))}, {}
    if op == "batch_inverse":
        return batch_inverse([int(x) for x in inp["values"]], int(inp["n"])), {}
    if op in ("crt", "garner"):
        residues = [int(x) for x in inp["residues"]]
        moduli = [int(x) for x in inp["moduli"]]
        if op == "crt":
            x, modulus = crt(residues, moduli)
            return {"x": x, "modulus": modulus}, {}
        x, modulus, coefficients = garner(residues, moduli)
        return {"x": x, "modulus": modulus}, {"coefficients": coefficients}
    if op in ("order_sequential", "order_product_tree"):
        function = order_sequential if op == "order_sequential" else order_product_tree
        order, trace = function(int(inp["g"]), int(inp["p"]), inp["factors"])
        return {"order": order}, {"trace": trace}
    if op == "primitive_root":
        return {"root": primitive_root(int(inp["p"]), inp["factors"], int(inp.get("start", 2)))}, {}
    raise ValueError(f"unknown operation {op!r}")


def main():
    for line in sys.stdin:
        req = json.loads(line)
        try:
            output, extra = solve(req["input"])
            answer = {"id": req["id"], "output": output, "extra": {"op": req["input"]["op"], **extra}}
        except Exception as exc:
            answer = {"id": req.get("id"), "error": str(exc)}
        print(json.dumps(answer), flush=True)


if __name__ == "__main__":
    main()
