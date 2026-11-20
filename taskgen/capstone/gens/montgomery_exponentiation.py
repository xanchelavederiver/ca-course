"""Modular exponentiation vectors with fresh and reused precomputation."""

VERSION = 1
METHODS = ("binary", "qary", "sliding", "montgomery")


def generate(params: dict, rng) -> dict:
    bits = int(params["bits"])
    method = rng.choice(params.get("methods") or METHODS)
    kind = rng.choice(("random", "random", "random", "cached", "zero-exp", "base-zero", "noncoprime", "mod-one"))
    n = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
    a = rng.getrandbits(bits + 16)
    e = rng.getrandbits(bits)
    reuse = False
    if kind == "cached":
        a = (1 << (bits // 2)) + 12345
        n = (1 << bits) - 1093
        reuse = True
    elif kind == "zero-exp":
        e = 0
    elif kind == "base-zero":
        a = 0
    elif kind == "noncoprime":
        a = n * rng.randrange(2, 8) + (n - 1)
    elif kind == "mod-one":
        n = 1
    parameter = None
    if method == "qary":
        parameter = rng.choice((2, 4, 8, 16))
    elif method == "sliding":
        parameter = rng.randrange(1, 7)
    return {
        "input": {"a": a, "e": e, "n": n, "method": method,
                  "parameter": parameter, "reuse": reuse},
        "expected": {"value": pow(a, e, n)},
        "tags": [method, kind, f"bits-{bits}"] + (["reuse"] if reuse else []),
    }


def verify(vector: dict, output: dict) -> str | None:
    value = (output or {}).get("value")
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            pass
    if not isinstance(value, int) or isinstance(value, bool):
        return f"value = {value!r} is not an integer"
    inp = vector["input"]
    if value != pow(inp["a"], inp["e"], inp["n"]):
        return "incorrect modular exponentiation result"
    return None
