"""Breaking the two toy public-key cryptosystems of Hoffstein--Pipher--Silverman with
lattice reduction (2nd ed., Sections 7.1 and 7.2; Sections 6.1--6.2 of the 1st ed.).

Congruential cryptosystem (HPS 7.1)
    Private key: f, g with f < sqrt(q/2), sqrt(q/4) < g < sqrt(q/2), gcd(f, q g) = 1.
    Public key: (q, h), h = f^{-1} g mod q. Ciphertext: e = r h + m mod q with
    m < sqrt(q/4), r < sqrt(q/2). Since f h = g (mod q), the vector (f, g) lies in the
    two-dimensional lattice spanned by (1, h) and (0, q) and is very short there, so Gauss
    reduction finds it (or another key that decrypts equally well).
    Decryption: a = f e mod q (= r g + f m exactly), m = f^{-1} a mod g.

Knapsack (Merkle--Hellman) cryptosystem (HPS 7.2)
    Private: a superincreasing r_1..r_n, A, B with B > 2 r_n, gcd(A, B) = 1.
    Public: M_i = A r_i mod B. Ciphertext of x in {0,1}^n: S = sum x_i M_i.
    The lattice spanned by the rows of

        | 2  0 ... 0  w M_1 |
        | 0  2 ... 0  w M_2 |
        | ...               |
        | 0  0 ... 2  w M_n |
        | 1  1 ... 1  w S   |

    contains t = sum x_i row_i - row_{n+1} = (2 x_1 - 1, ..., 2 x_n - 1, 0), a vector of
    length sqrt(n), much shorter than the other lattice vectors when the density is low,
    so LLL tends to put +-t into the reduced basis. HPS use w = 1; a larger weight w
    (Coster et al.) makes the last coordinate of short vectors zero more often. We try
    w = 1 and then w = ceil(sqrt(n)) and w = n, and in each reduced basis the rows and the
    sums/differences of two rows.
"""

from __future__ import annotations

from math import isqrt

from gauss import gauss_reduce
from lattice import lll


def _ints(d: dict, *keys):
    out = []
    for k in keys:
        v = d.get(k)
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError(f"{k!r} must be an integer")
        out.append(v)
    return out


# --- congruential ---------------------------------------------------------------------

def congruential_decrypt(q: int, f: int, g: int, e: int) -> int:
    a = f * e % q
    return pow(f, -1, g) * a % g


def congruential_attack(inp: dict) -> tuple[dict, dict]:
    """Recover a private key (f, g) and the plaintext m from (q, h, e)."""
    q, h, e = _ints(inp, "q", "h", "e")
    if q < 2 or not 0 <= h < q or not 0 <= e < q:
        raise ValueError("need q >= 2 and 0 <= h, e < q")
    lattice = [[1, h], [0, q]]
    red, gx = gauss_reduce(lattice)
    if len(red) != 2:
        raise ValueError("degenerate public key")
    hinv = pow(h, -1, q) if _gcd(h, q) == 1 else None
    tried = []
    # The key is +-v1 for a typical key; +-v2 and +-(v1 +- v2) are cheap fall-backs.
    v1, v2 = red
    cands = [v1, v2, [v1[0] + v2[0], v1[1] + v2[1]], [v1[0] - v2[0], v1[1] - v2[1]]]
    for v in cands:
        for s in (1, -1):
            f, g = s * v[0], s * v[1]
            if f <= 0 or g <= 0 or _gcd(f, g) != 1 or (f * h - g) % q:
                continue
            m = congruential_decrypt(q, f, g, e)
            tried.append([f, g])
            # Certificate: the blinding value r = (e - m) h^{-1} mod q must be small
            # (r < sqrt(q/2)); then e = r h + m is a valid ciphertext of m.
            if hinv is not None:
                r = (e - m) * hinv % q
                if 2 * r * r >= q or 4 * m * m >= q:
                    continue
            out = {"f": f, "g": g, "m": m}
            return out, {"lattice": lattice, "reduced": red, "gauss": gx, "tried_keys": tried,
                         "r": r if hinv is not None else None}
    raise ValueError("the reduced basis yields no decrypting key")


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)


# --- knapsack -------------------------------------------------------------------------

def knapsack_lattice(M: list[int], S: int, w: int = 1) -> list[list[int]]:
    n = len(M)
    rows = [[2 * (i == j) for j in range(n)] + [w * M[i]] for i in range(n)]
    rows.append([1] * n + [w * S])
    return rows


def _as_solution(v: list[int], M: list[int], S: int) -> list[int] | None:
    """x from a candidate +-(2x - 1, 0) if it solves the knapsack."""
    n = len(M)
    if v[n] != 0 or any(abs(c) != 1 for c in v[:n]):
        return None
    for s in (1, -1):
        x = [(1 + s * c) // 2 for c in v[:n]]
        if sum(xi * mi for xi, mi in zip(x, M)) == S:
            return x
    return None


def knapsack_attack(inp: dict, delta="99/100") -> tuple[dict, dict]:
    """Recover x in {0,1}^n with sum x_i M_i = S from the public key M and S."""
    M = inp.get("M")
    if not isinstance(M, list) or not M or not all(isinstance(a, int) and a > 0 for a in M):
        raise ValueError("'M' must be a non-empty list of positive integers")
    (S,) = _ints(inp, "S")
    n = len(M)
    attempts = []
    for w in dict.fromkeys((1, isqrt(n - 1) + 1, n)):
        lat = knapsack_lattice(M, S, w)
        red, st = lll(lat, inp.get("delta", delta))
        attempts.append({"weight": w, **st.as_dict()})
        cands = list(red)
        cands += [[a + b for a, b in zip(u, v)] for i, u in enumerate(red) for v in red[i + 1:]]
        cands += [[a - b for a, b in zip(u, v)] for i, u in enumerate(red) for v in red[i + 1:]]
        for v in cands:
            x = _as_solution(v, M, S)
            if x is not None:
                return {"x": x}, {"lattice": knapsack_lattice(M, S, 1), "weight": w,
                                  "vector": v, "attempts": attempts,
                                  "reduced_first_rows": red[:3]}
    raise ValueError(f"LLL found no solution (tried weights {[a['weight'] for a in attempts]})")
