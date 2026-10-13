"""Scalar multiplication on elliptic curves over F_p (ported from main-2sem.py).

The "ternary expansion" is the signed binary expansion with digits -1, 0, 1
(NAF, as in Hoffstein–Pipher–Silverman §6.3.1); exponents whose expansion has
no -1 digit are rejected (legacy TODO: "trivial ternary exponents").
"""

from taskgen.core import steps
from taskgen.core.nt import first_primes, is_square_mod
from taskgen.core.task import SolutionDetail, Task


def _curve_tex(a: int, b: int) -> str:
    if a == 0:
        return f"x^3 + {b}"
    if b == 0:
        return f"x^3 + {a}x"
    return f"x^3 + {a}x + {b}"


def _random_point(rng, p: int, a: int, b: int):
    """Uniform-x random affine point with rng-chosen y sign (Sage's random_point is not seedable)."""
    from sage.all import GF

    F = GF(p)
    while True:
        x = rng.randrange(0, p)
        rhs = (x**3 + a * x + b) % p
        if is_square_mod(rhs, p):
            y = int(F(rhs).sqrt())
            if y and rng.random() < 0.5:
                y = p - y
            return x, y


def double_and_add(n: int, P: list[int], a: int, p: int, digits: list[int]) -> list[dict]:
    """Left-to-right over ``digits`` (most significant first, leading 1)."""
    R, k, rows = list(P), 1, []
    negP = [P[0], (-P[1]) % p]
    for d in digits[1:]:
        st = steps.ec_add_step(R, R, a, p)
        R, k = st["R"], 2 * k
        rows.append({"op": "2R", "k": k, "lam": st["lam"], "R": R})
        if d:
            st = steps.ec_add_step(R, P if d > 0 else negP, a, p)
            R, k = st["R"], k + d
            rows.append({"op": "R + P" if d > 0 else "R - P", "k": k, "lam": st["lam"], "R": R})
    assert k == n
    return rows


class _ScalarMult(Task):
    topics = ("ecc.scalar_mult",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"primes": list(first_primes(40)[10:25])}}
    expansion: str
    statement = (r"Вычислить степень $\VAR{n}P$ точки $P = (\VAR{x}, \VAR{y})$ эллиптической кривой "
                 r"\[y^2 \equiv \VAR{curve}\ (\textrm{mod}\ \VAR{p})\] "
                 r"с помощью \VAR{expansion} разложения показателя $\VAR{n}$.")
    solution = (r"\BLOCK{import 'macros.tex.j2' as tx}"
                r"\BLOCK{if signed}Тернарное разложение (цифры $-1, 0, 1$, без соседних ненулевых): "
                r"$\VAR{n} = \BLOCK{for d in digits}\BLOCK{if d < 0}\bar 1\BLOCK{else}\VAR{d}\BLOCK{endif}\BLOCK{endfor}$ "
                r"($\bar 1 = -1$), т.е. $\VAR{n} = \VAR{expansion_sum}$; для цифры $-1$ прибавляем "
                r"$-P = (\VAR{x}, \VAR{p - y})$."
                r"\BLOCK{else}$\VAR{n} = \VAR{n|bin}_2$.\BLOCK{endif} "
                r"Начиная с $R = P$, для каждой следующей цифры: $R \gets 2R$, затем при ненулевой цифре "
                r"$R \gets R \pm P$. Формулы: $\lambda = \frac{3x_1^2 + a}{2y_1}$ (удвоение), "
                r"$\lambda = \frac{y_2 - y_1}{x_2 - x_1}$ (сложение), $x_3 = \lambda^2 - x_1 - x_2$, "
                r"$y_3 = \lambda(x_1 - x_3) - y_1$; $a = \VAR{a}$, всё по модулю $\VAR{p}$."
                r"\[\begin{array}{l|r|r|c}"
                r"\text{операция} & kP & \lambda & R \\ \hline "
                r"\BLOCK{for r in rows}\VAR{r.op} & \VAR{r.k}P & \BLOCK{if r.lam is none}\text{---}\BLOCK{else}"
                r"\VAR{r.lam}\BLOCK{endif} & \VAR{tx.pt(r.R)} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"\[\VAR{n}P = (\VAR{answer[0]}, \VAR{answer[1]}).\]")

    def digits_for(self, n: int) -> list[int]:
        return [int(c) for c in format(n, "b")]

    def sample(self, rng):
        from sage.all import GF, EllipticCurve

        while True:
            p = rng.choice(self.cfg.primes)
            a, b = rng.randrange(0, p), rng.randrange(0, p)
            if (a == 0 and b == 0) or (4 * a**3 + 27 * b**2) % p == 0:
                continue
            E = EllipticCurve(GF(p), [a, b])
            x, y = _random_point(rng, p, a, b)
            P = E(x, y)
            po, co = int(P.order()), int(E.order())
            if po >= co // 8 and po > 15:
                n = rng.randrange(min(co // 8, 15), po)
                digits = self.digits_for(n)
                if digits is None:
                    continue
                R = n * P
                rows = double_and_add(n, [x, y], a, p, digits)
                L = len(digits)
                return {"expansion": self.expansion, "signed": self.signed, "p": p, "a": a, "b": b,
                        "curve": _curve_tex(a, b), "x": x, "y": y, "n": n, "digits": digits,
                        "expansion_sum": " ".join(
                            f"{'-' if d < 0 else '+'} 2^{{{L - 1 - i}}}" for i, d in enumerate(digits) if d
                        ).lstrip("+ "),
                        "rows": rows, "point_order": po, "curve_order": co,
                        "answer": [int(R[0]), int(R[1])]}

    def check(self, p):
        m, a, b = p["p"], p["a"], p["b"]
        assert (p["y"] ** 2 - p["x"] ** 3 - a * p["x"] - b) % m == 0, "P not on curve"
        assert 0 < p["n"] < p["point_order"]
        assert p["rows"][-1]["R"] == p["answer"]
        assert sum(d * 2**i for i, d in enumerate(p["digits"][::-1])) == p["n"]


class DoubleAndAddBinary(_ScalarMult):
    id = "ecc.double_and_add_binary"
    title_ru = "Возведение точки в степень: бинарное разложение"
    expansion = "бинарного"
    signed = False


class DoubleAndAddTernary(_ScalarMult):
    id = "ecc.double_and_add_ternary"
    title_ru = "Возведение точки в степень: тернарное разложение"
    expansion = "тернарного"
    signed = True

    def digits_for(self, n: int):
        d = steps.naf(n)
        return d if -1 in d else None
