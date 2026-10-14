"""Representation of big integers and complexity of divide-and-conquer multiplication
(lecture sem1/02): balanced representation, the master theorem.
"""

import math
from fractions import Fraction

from taskgen.core.task import SolutionDetail, Task


def balanced_digits(x: int, B: int) -> list[dict]:
    """Balanced base-B digits of x (B even >= 4), least significant first, with the trace
    x_i -> digit d = ((x + B/2) mod B) - B/2, x_{i+1} = (x - d) / B."""
    rows = []
    while x != 0:
        d = (x + B // 2) % B - B // 2
        rows.append({"x": x, "d": d, "next": (x - d) // B})
        x = (x - d) // B
    return rows


def standard_digits(x: int, B: int) -> list[int]:
    out = []
    while True:
        x, r = divmod(x, B)
        out.append(r)
        if x == 0:
            return out


class BalancedRepresentation(Task):
    id = "arithmetic.balanced_repr"
    title_ru = "Сбалансированное представление числа"
    topics = ("arithmetic.representation",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = "Negative numbers (corner case: the sign lives in the digits) with probability 1/3."
    presets = {"default": {"bases": [8, 10, 12, 16], "lo": 200, "hi": 60000, "negative_ratio": 1 / 3}}
    statement = (r"Найти обычное (для $x \ge 0$) и сбалансированное представления числа $x = \VAR{x}$ "
                 r"по основанию $B = \VAR{B}$ (цифры сбалансированного представления: "
                 r"$-\VAR{B // 2} \le \hat x_i < \VAR{B // 2}$). Проверить ответ.")
    solution = (r"\BLOCK{if x >= 0}Обычное представление (остатки от деления на $\VAR{B}$, начиная с младшего "
                r"разряда): $x = (\VAR{std|reverse|join(',\\,')})_{\VAR{B}}$.\par \BLOCK{else}"
                r"Число отрицательно: обычного представления нет, знак будет записан в цифрах.\par \BLOCK{endif}"
                r"Сбалансированные цифры: $\hat x_i \equiv x_i \pmod{\VAR{B}}$, "
                r"$\hat x_i = ((x_i + \VAR{B // 2}) \bmod \VAR{B}) - \VAR{B // 2}$, "
                r"$x_{i+1} = (x_i - \hat x_i)/\VAR{B}$:"
                r"\[\begin{array}{c|r|r|r}"
                r"i & x_i & \hat x_i & x_{i+1} \\ \hline "
                r"\BLOCK{for r in rows}\VAR{loop.index0} & \VAR{r.x} & \VAR{r.d} & \VAR{r.next} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"Проверка: $\BLOCK{for r in rows|reverse}\BLOCK{if not loop.first}\BLOCK{if r.d >= 0} + "
                r"\BLOCK{else} - \BLOCK{endif}\BLOCK{else}\BLOCK{if r.d < 0}-\BLOCK{endif}\BLOCK{endif}"
                r"\VAR{r.d|abs} \cdot \VAR{B}^{\VAR{rows|length - loop.index}}\BLOCK{endfor} = \VAR{x}$."
                r"\[x = (\VAR{answer|join(',\\,')})_{\VAR{B}}^{\mathrm{bal}}\ "
                r"\text{(старшие разряды слева)}.\]")

    def sample(self, rng):
        B = rng.choice(self.cfg.bases)
        x = rng.randrange(self.cfg.lo, self.cfg.hi)
        if rng.random() < self.cfg.negative_ratio:
            x = -x
        rows = balanced_digits(x, B)
        return {"x": x, "B": B, "std": standard_digits(x, B) if x >= 0 else [],
                "rows": rows, "answer": [r["d"] for r in reversed(rows)]}

    def check(self, p):
        B, digits = p["B"], p["answer"]
        assert sum(d * B**i for i, d in enumerate(reversed(digits))) == p["x"]
        assert all(-B // 2 <= d < B // 2 for d in digits) and digits[0] != 0
        if p["x"] >= 0:
            assert sum(d * B**i for i, d in enumerate(p["std"])) == p["x"]


# --- master theorem -------------------------------------------------------------------


def _pow_tex(c: Fraction) -> str:
    """n^c for c in {0, 1/2, 1, 3/2, ...}."""
    if c == 0:
        return "1"
    if c == Fraction(1, 2):
        return r"\sqrt{n}"
    if c == 1:
        return "n"
    if c.denominator == 1:
        return f"n^{{{c.numerator}}}"
    if c.denominator == 2 and c > 1:
        return (f"n^{{{c.numerator // 2}}}" if c.numerator // 2 > 1 else "n") + r"\sqrt{n}"
    return f"n^{{{c.numerator}/{c.denominator}}}"


def _log_tex(k: int) -> str:
    return "" if k == 0 else (r"\log n" if k == 1 else rf"\log^{{{k}}} n")


def _f_tex(coef: int, c: Fraction, k: int, inv_log: bool = False) -> str:
    body = _pow_tex(c)
    if inv_log:
        return rf"\frac{{{'' if coef == 1 else coef}{body}}}{{\log n}}"
    parts = ([] if coef == 1 else [str(coef)]) + ([] if body == "1" else [body]) + \
        ([_log_tex(k)] if k else [])
    return " ".join(parts) or "1"


def _crit(a: int, b: int) -> Fraction | None:
    """log_b a if it is in (1/2) Z (exactly), else None."""
    for num in range(0, 4 * 8):
        c = Fraction(num, 2)
        if abs(b ** float(c) - a) < 1e-9:
            return c
    return None


class MasterTheorem(Task):
    id = "arithmetic.master_theorem"
    title_ru = "Основная теорема о рекуррентных соотношениях"
    topics = ("arithmetic.complexity",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("All three cases, log factors in case 2, and (corner case, ~1/8) f = n^crit / log n, "
             "where the theorem does not apply.")
    presets = {"default": {"inapplicable_ratio": 0.125}}
    statement = (r"С помощью основной теоремы о рекуррентных соотношениях найти асимптотику решения "
                 r"\[T(n) = \VAR{a_tex}T\!\left(\frac{n}{\VAR{b}}\right) + \VAR{f}\] "
                 r"или показать, что теорема неприменима.")
    solution = (r"$a = \VAR{a}$, $b = \VAR{b}$, критическая экспонента "
                r"$c_{\mathrm{crit}} = \log_{\VAR{b}} \VAR{a}\BLOCK{if crit_exact is not none} = \VAR{crit_exact}"
                r"\BLOCK{else} \approx \VAR{crit_num}\BLOCK{endif}$; $f(n) = \VAR{f}"
                r"\BLOCK{if case == 1} = \bigO(n^{c})$ при $c = \VAR{c_tex} < c_{\mathrm{crit}}$ "
                r"($\VAR{b}^{\VAR{c_tex}} = \VAR{bc} < \VAR{a}$). Случай~1 (доминируют подзадачи):"
                r"\BLOCK{elif case == 2} = \Theta(n^{c_{\mathrm{crit}}} \log^{k} n)$ с $k = \VAR{k}$. "
                r"Случай~2 (вклад всех уровней рекурсии одинаков), $T(n) = \Theta(n^{c_{\mathrm{crit}}} "
                r"\log^{k+1} n)$:"
                r"\BLOCK{elif case == 3} = \Omega(n^{c})$ при $c = \VAR{c_tex} > c_{\mathrm{crit}}$ "
                r"($\VAR{b}^{\VAR{c_tex}} = \VAR{bc} > \VAR{a}$). Условие регулярности: "
                r"$a f(n/b) = \VAR{a} \cdot \VAR{f_nb}\BLOCK{if k} \le\BLOCK{else} =\BLOCK{endif} \VAR{ratio} \cdot f(n)$, "
                r"$\VAR{ratio} < 1$. Случай~3 (доминирует разбиение):"
                r"\BLOCK{else}$. Здесь $f(n) / n^{c_{\mathrm{crit}}} = 1/\log n$: $f$ растёт медленнее "
                r"$n^{c_{\mathrm{crit}}}$, но не полиномиально медленнее ($f \ne \bigO(n^{c_{\mathrm{crit}} - "
                r"\varepsilon})$ ни при каком $\varepsilon > 0$), поэтому случай~1 не подходит; "
                r"$f \ne \Theta(n^{c_{\mathrm{crit}}} \log^k n)$ с $k \ge 0$ (случай~2), "
                r"$f \ne \Omega(n^{c})$ с $c > c_{\mathrm{crit}}$ (случай~3). Теорема неприменима "
                r"(прямой подсчёт по уровням рекурсии даёт $\Theta(n^{c_{\mathrm{crit}}} \log\log n)$)."
                r"\BLOCK{endif}"
                r"\BLOCK{if case}\[T(n) = \Theta\!\left(\VAR{theta}\right).\]\BLOCK{endif}")

    def sample(self, rng):
        case = 0 if rng.random() < self.cfg.inapplicable_ratio else rng.choice([1, 2, 3])
        coef = rng.choice([1, 1, 2, 3, 5, 7, 10, 23, 42])
        k, ctx = 0, {}
        if case in (0, 2):
            a, b = rng.choice([(2, 4), (3, 9), (4, 16), (2, 2), (3, 3), (4, 4), (4, 2), (9, 3), (8, 2),
                               (16, 4)])
            c = _crit(a, b)
            if case == 2:
                k = rng.choice([0, 0, 1, 2])
            f = _f_tex(coef, c, k, inv_log=(case == 0))
            theta = (_pow_tex(c) + " " + _log_tex(k + 1)).strip()
        else:
            while True:
                b = rng.choice([2, 3, 4])
                a = rng.randrange(1, 17)
                c = rng.choice([Fraction(0), Fraction(1, 2), Fraction(1), Fraction(3, 2), Fraction(2),
                                Fraction(3)] if case == 1 else [Fraction(1), Fraction(2), Fraction(3)])
                bc = b ** float(c)
                if case == 1 and a > 1 and bc < a - 1e-9:
                    break
                if case == 3 and bc > a + 1e-9:
                    break
            if case == 3:
                k = rng.choice([0, 0, 1])
            f = _f_tex(coef, c, k)
            crit = _crit(a, b)
            if case == 1:
                theta = _pow_tex(crit) if crit is not None else rf"n^{{\log_{{{b}}} {a}}}"
            else:
                theta = f"{_pow_tex(c)} {_log_tex(k)}".strip()
                ratio = Fraction(a, b ** int(c))
                ctx = {"ratio": rf"\tfrac{{{ratio.numerator}}}{{{ratio.denominator}}}"
                                if ratio.denominator != 1 else str(ratio),
                       "f_nb": _f_tex(coef, c, k).replace("n", r"(n/" + str(b) + ")")}
            ctx["bc"] = (str(int(round(b ** float(c)))) if (b ** float(c)).is_integer()
                         else f"{b ** float(c):.3f}")
        crit = _crit(a, b)
        c_tex = (str(c) if c.denominator == 1 else rf"\tfrac{{{c.numerator}}}{{{c.denominator}}}")
        return {"case": case, "a": a, "b": b, "k": k, "f": f, "theta": theta,
                "a_tex": "" if a == 1 else str(a),
                "crit_exact": (None if crit is None else
                               (str(crit) if crit.denominator == 1 else
                                rf"\tfrac{{{crit.numerator}}}{{{crit.denominator}}}")),
                "crit_num": f"{math.log(a, b):.3f}", "c_tex": c_tex,
                "ratio": "", "f_nb": "", "bc": "", **ctx,
                "answer": {"case": case, "theta": theta if case else None}}

    def check(self, p):
        a, b, case = p["a"], p["b"], p["case"]
        crit = math.log(a, b)
        assert case in (0, 1, 2, 3) and p["answer"]["case"] == case
        assert (p["answer"]["theta"] is None) == (case == 0)
        if case in (0, 2):
            assert p["crit_exact"] is not None
        if case == 1:
            assert float(p["bc"]) < a
        if case == 3:
            assert float(p["bc"]) > a
        assert crit >= 0
