"""Toy capstone generator for test_capstone.py: factor n = p*q (small primes)."""

VERSION = 1

PRIMES = [p for p in range(3, 400) if all(p % d for d in range(2, int(p ** 0.5) + 1))]


def generate(params, rng):
    p, q = rng.sample(PRIMES[: params["k"]], 2)
    return {"input": {"n": p * q}, "expected": {"p": min(p, q)}, "tags": ["balanced"]}


def verify(vector, output):
    n = vector["input"]["n"]
    p = (output or {}).get("p")
    if not isinstance(p, int) or not 1 < p < n or n % p:
        return f"{p!r} is not a proper factor of {n}"
    return None
