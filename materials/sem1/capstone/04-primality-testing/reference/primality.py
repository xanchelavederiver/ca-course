from __future__ import annotations

import math


def basic_verdict(n: int) -> str | None:
    if n < 2:
        return "composite"
    if n == 2:
        return "prime"
    if n % 2 == 0:
        return "composite"
    return None


def wilson(n: int) -> dict:
    early = basic_verdict(n)
    if early:
        return {"verdict": early}
    value = math.factorial(n - 1) % n
    return {"verdict": "prime" if value == n - 1 else "composite", "residue": value}


def fermat(n: int, bases: list[int]) -> dict:
    early = basic_verdict(n)
    if early:
        return {"verdict": "probable_prime" if early == "prime" else early, "witnesses": []}
    witnesses = []
    for base in bases:
        if base <= 1 or base >= n - 1:
            continue
        a = base % n
        if math.gcd(a, n) != 1:
            witnesses.append({"base": base, "kind": "gcd", "value": math.gcd(a, n)})
        elif pow(a, n - 1, n) != 1:
            witnesses.append({"base": base, "kind": "fermat", "value": pow(a, n - 1, n)})
    return {"verdict": "composite" if witnesses else "probable_prime", "witnesses": witnesses}


def miller_rabin(n: int, bases: list[int]) -> dict:
    early = basic_verdict(n)
    if early:
        return {"verdict": "probable_prime" if early == "prime" else early, "witnesses": []}
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    witnesses = []
    for base in bases:
        if base <= 1 or base >= n - 1:
            continue
        a = base % n
        if math.gcd(a, n) != 1:
            witnesses.append({"base": base, "kind": "gcd", "value": math.gcd(a, n)})
            continue
        sequence = [pow(a, d, n)]
        if sequence[0] in (1, n - 1):
            continue
        passed = sequence[0] == n - 1
        for _ in range(1, s):
            sequence.append(sequence[-1] * sequence[-1] % n)
            if sequence[-1] == n - 1:
                passed = True
                break
        if not passed:
            witnesses.append({"base": base, "kind": "miller-rabin", "sequence": sequence})
    return {"verdict": "composite" if witnesses else "probable_prime", "witnesses": witnesses,
            "d": d, "s": s}


def jacobi(a: int, n: int) -> int:
    if n <= 0 or n % 2 == 0:
        raise ValueError("Jacobi denominator must be positive and odd")
    a %= n
    result = 1
    while a:
        while a % 2 == 0:
            a //= 2
            if n % 8 in (3, 5):
                result = -result
        a, n = n, a
        if a % 4 == n % 4 == 3:
            result = -result
        a %= n
    return result if n == 1 else 0


def solovay_strassen(n: int, bases: list[int]) -> dict:
    early = basic_verdict(n)
    if early:
        return {"verdict": "probable_prime" if early == "prime" else early, "witnesses": []}
    witnesses = []
    for base in bases:
        if base <= 1 or base >= n - 1:
            continue
        a = base % n
        if math.gcd(a, n) != 1:
            witnesses.append({"base": base, "kind": "gcd", "value": math.gcd(a, n)})
            continue
        j = jacobi(a, n)
        value = pow(a, (n - 1) // 2, n)
        if j == 0 or value != j % n:
            witnesses.append({"base": base, "kind": "solovay-strassen",
                              "jacobi": j, "value": value})
    return {"verdict": "composite" if witnesses else "probable_prime", "witnesses": witnesses}


def validate_factorization(n: int, factors: list[list[int]]) -> list[tuple[int, int]]:
    normalized = [(int(p), int(e)) for p, e in factors]
    if n < 2 or not normalized or any(p <= 1 or e <= 0 for p, e in normalized):
        raise ValueError("invalid factorization")
    if math.prod(p ** e for p, e in normalized) != n:
        raise ValueError("factorization does not multiply to n")
    return normalized


def korselt(n: int, factors: list[list[int]]) -> dict:
    factors = validate_factorization(n, factors)
    squarefree = all(e == 1 for _, e in factors)
    bad = [p for p, _ in factors if (n - 1) % (p - 1) != 0]
    composite = not (len(factors) == 1 and factors[0] == (n, 1))
    carmichael = composite and squarefree and not bad and n > 2
    result = {"carmichael": carmichael, "squarefree": squarefree, "bad_divisors": bad}
    if squarefree:
        result["liars"] = math.prod(math.gcd(n - 1, p - 1) for p, _ in factors)
        result["phi"] = math.prod(p - 1 for p, _ in factors)
    else:
        result["liars"] = None
        result["phi"] = None
    return result


def mersenne_reduce(x: int, exponent: int) -> int:
    if exponent < 2:
        raise ValueError("Mersenne exponent must be at least 2")
    if x < 0:
        raise ValueError("reduction input must be nonnegative")
    m = (1 << exponent) - 1
    while x > m:
        x = (x & m) + (x >> exponent)
    return 0 if x == m else x


def lucas_lehmer(exponent: int) -> dict:
    if exponent == 2:
        return {"verdict": "prime", "residue": 0, "trace": [0]}
    if exponent < 3 or exponent % 2 == 0:
        raise ValueError("Lucas-Lehmer exponent must be 2 or an odd prime")
    m = (1 << exponent) - 1
    s = 4
    trace = []
    for _ in range(exponent - 2):
        s = mersenne_reduce(s * s - 2, exponent)
        trace.append(s)
    return {"verdict": "prime" if s == 0 else "composite", "residue": s, "trace": trace,
            "modulus": m}
