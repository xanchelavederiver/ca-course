"""Signed integer multiplication vectors for all required methods."""

VERSION = 1
METHODS = ("schoolbook", "karatsuba", "toom3", "fft")


def generate(params: dict, rng) -> dict:
    bits = int(params["bits"])
    method = rng.choice(params.get("methods") or METHODS)
    kind = rng.choice(("random", "random", "random", "signed", "unbalanced", "carry", "zero"))
    if kind == "zero":
        a, b = 0, rng.getrandbits(bits)
    elif kind == "carry":
        a = (1 << bits) - 1
        b = (1 << max(8, bits - rng.randrange(0, 4))) - 1
    else:
        bbits = max(8, bits // rng.choice((2, 4, 8))) if kind == "unbalanced" else bits
        a = rng.getrandbits(bits) | (1 << (bits - 1))
        b = rng.getrandbits(bbits) | (1 << (bbits - 1))
        if kind == "signed":
            a = -a
    if rng.randrange(8) == 0:
        b = -b
    return {
        "input": {"a": a, "b": b, "method": method},
        "expected": {"product": a * b},
        "tags": [method, kind, f"bits-{bits}"],
    }


def verify(vector: dict, output: dict) -> str | None:
    product = (output or {}).get("product")
    if isinstance(product, str):
        try:
            product = int(product)
        except ValueError:
            pass
    if not isinstance(product, int) or isinstance(product, bool):
        return f"product = {product!r} is not an integer"
    inp = vector["input"]
    if product != inp["a"] * inp["b"]:
        return "incorrect product"
    return None
