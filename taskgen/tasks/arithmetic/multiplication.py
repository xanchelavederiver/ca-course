"""Fast multiplication of big integers (ported from main-{1,2}sem.py), plus variants:
subtractive/squaring/polynomial Karatsuba, alternative-points and unbalanced Toom-Cook.
"""

from taskgen.core import steps
from taskgen.core.nt import inverse, is_prime
from taskgen.core.task import SolutionDetail, Task

M = r"\BLOCK{import 'macros.tex.j2' as tx}"


def karatsuba_trace(x: int, y: int, calls: list) -> tuple[int, int | None]:
    """Recursive decimal Karatsuba; returns (product, call number or None for a base case)."""
    n = max(len(str(x)), len(str(y)))
    if n <= 2:
        return x * y, None
    k = n // 2
    x1, x0 = divmod(x, 10**k)
    y1, y0 = divmod(y, 10**k)
    z2, r2 = karatsuba_trace(x1, y1, calls)
    z0, r0 = karatsuba_trace(x0, y0, calls)
    zs, rs = karatsuba_trace(x1 + x0, y1 + y0, calls)
    z1 = zs - z2 - z0
    res = z2 * 10 ** (2 * k) + z1 * 10**k + z0
    calls.append({"no": len(calls) + 1, "x": x, "y": y, "k": k, "x1": x1, "x0": x0, "y1": y1, "y0": y0,
                  "z2": z2, "z0": z0, "zs": zs, "z1": z1, "s1": x1 + x0, "s2": y1 + y0,
                  "r2": r2, "r0": r0, "rs": rs, "res": res})
    return res, len(calls)


class Karatsuba(Task):
    id = "arithmetic.karatsuba"
    title_ru = "Умножение методом Карацубы"
    topics = ("arithmetic.multiplication",)
    complexity = 1
    family = "karatsuba"
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"lo": 10**6 + 1, "hi": 10**8},
               "kontrolnaya04": {"lo": 10**6 + 1, "hi": 10**8}}
    statement = (r"Вычислить произведение целых чисел \[\VAR{a} \cdot \VAR{b}\] с помощью метода "
                 r"Карацубы. Применять метод рекурсивно, база рекурсии — двузначные числа, которые "
                 r"можно умножать любым способом.\\ Использовать десятичную систему счисления.")
    solution = (r"Для $x \cdot y$ с $n$-значными (по большему) сомножителями, $n > 2$: $k = \lfloor n/2 \rfloor$, "
                r"$x = x_1 10^k + x_0$, $y = y_1 10^k + y_0$, $z_2 = x_1 y_1$, $z_0 = x_0 y_0$, "
                r"$z_1 = (x_1 + x_0)(y_1 + y_0) - z_2 - z_0$, $xy = z_2 10^{2k} + z_1 10^k + z_0$. "
                r"Вызовы пронумерованы в порядке завершения (ссылка [$i$] "
                r"--- результат вызова $i$, без ссылки --- база рекурсии)."
                r"\BLOCK{for c in calls}"
                r"\par\noindent [\VAR{c.no}]~$\VAR{c.x} \cdot \VAR{c.y}$: $k = \VAR{c.k}$; "
                r"$z_2 = \VAR{c.x1} \cdot \VAR{c.y1} = \VAR{c.z2}$\BLOCK{if c.r2} [\VAR{c.r2}]\BLOCK{endif}, "
                r"$z_0 = \VAR{c.x0} \cdot \VAR{c.y0} = \VAR{c.z0}$\BLOCK{if c.r0} [\VAR{c.r0}]\BLOCK{endif}, "
                r"$\VAR{c.s1} \cdot \VAR{c.s2} = \VAR{c.zs}$\BLOCK{if c.rs} [\VAR{c.rs}]\BLOCK{endif}, "
                r"$z_1 = \VAR{c.zs} - \VAR{c.z2} - \VAR{c.z0} = \VAR{c.z1}$; "
                r"$\VAR{c.z2} \cdot 10^{\VAR{2 * c.k}} + \VAR{c.z1} \cdot 10^{\VAR{c.k}} + \VAR{c.z0} "
                r"= \VAR{c.res}$."
                r"\BLOCK{endfor}"
                r"\[\VAR{a} \cdot \VAR{b} = \VAR{answer}.\]")

    def sample(self, rng):
        a = rng.randrange(self.cfg.lo, self.cfg.hi)
        b = rng.randrange(self.cfg.lo, self.cfg.hi)
        calls: list = []
        karatsuba_trace(a, b, calls)
        return {"a": a, "b": b, "calls": calls, "answer": a * b}

    def check(self, p):
        assert p["answer"] == p["a"] * p["b"] == p["calls"][-1]["res"]
        assert all(c["z2"] * 10 ** (2 * c["k"]) + c["z1"] * 10 ** c["k"] + c["z0"] == c["x"] * c["y"]
                   for c in p["calls"])


def karatsuba_sub_trace(x: int, y: int, calls: list) -> tuple[int, int | None]:
    """Subtractive-variant Karatsuba; the middle product recurses on |x1 - x0| * |y1 - y0|."""
    n = max(len(str(x)), len(str(y)))
    if n <= 2:
        return x * y, None
    k = n // 2
    x1, x0 = divmod(x, 10**k)
    y1, y0 = divmod(y, 10**k)
    z2, r2 = karatsuba_sub_trace(x1, y1, calls)
    z0, r0 = karatsuba_sub_trace(x0, y0, calls)
    d1, d2 = x1 - x0, y1 - y0
    zda, rd = karatsuba_sub_trace(abs(d1), abs(d2), calls)
    zd = zda if (d1 < 0) == (d2 < 0) else -zda
    z1 = z2 + z0 - zd
    res = z2 * 10 ** (2 * k) + z1 * 10**k + z0
    calls.append({"no": len(calls) + 1, "x": x, "y": y, "k": k, "x1": x1, "x0": x0, "y1": y1,
                  "y0": y0, "z2": z2, "z0": z0, "d1": d1, "d2": d2, "zd": zd, "z1": z1,
                  "r2": r2, "r0": r0, "rd": rd, "res": res})
    return res, len(calls)


class KaratsubaSub(Task):
    id = "arithmetic.karatsuba_sub"
    title_ru = "Умножение методом Карацубы (вычитательный вариант)"
    topics = ("arithmetic.multiplication",)
    complexity = 2
    family = "karatsuba"
    solution_detail = SolutionDetail.FULL
    notes = ("Implementation-grade variant: z1 = z2 + z0 - (x1 - x0)(y1 - y0). The middle product "
             "may be negative; recursion runs on the absolute differences (no carry growth).")
    presets = {"default": {"lo": 10**6 + 1, "hi": 10**8}}
    statement = (r"Вычислить произведение целых чисел \[\VAR{a} \cdot \VAR{b}\] вычитательным "
                 r"вариантом метода Карацубы: $z_1 = z_2 + z_0 - (x_1 - x_0)(y_1 - y_0)$ "
                 r"(разности не выходят за разрядную сетку половинок, в отличие от сумм). "
                 r"Применять метод рекурсивно (рекурсивный вызов — для модулей разностей, знак "
                 r"учитывать отдельно), база рекурсии — двузначные числа. "
                 r"Использовать десятичную систему счисления.")
    solution = (r"Для $x \cdot y$ с $n$-значными (по большему) сомножителями, $n > 2$: $k = \lfloor n/2 \rfloor$, "
                r"$x = x_1 10^k + x_0$, $y = y_1 10^k + y_0$, $z_2 = x_1 y_1$, $z_0 = x_0 y_0$, "
                r"$z_1 = z_2 + z_0 - (x_1 - x_0)(y_1 - y_0)$, $xy = z_2 10^{2k} + z_1 10^k + z_0$. "
                r"Среднее произведение вычисляется рекурсивно для модулей $|x_1 - x_0| \cdot |y_1 - y_0|$, "
                r"знак восстанавливается по знакам разностей. Вызовы пронумерованы в порядке завершения "
                r"(ссылка [$i$] --- результат вызова $i$, без ссылки --- база рекурсии)."
                r"\BLOCK{for c in calls}"
                r"\par\noindent [\VAR{c.no}]~$\VAR{c.x} \cdot \VAR{c.y}$: $k = \VAR{c.k}$; "
                r"$z_2 = \VAR{c.x1} \cdot \VAR{c.y1} = \VAR{c.z2}$\BLOCK{if c.r2} [\VAR{c.r2}]\BLOCK{endif}, "
                r"$z_0 = \VAR{c.x0} \cdot \VAR{c.y0} = \VAR{c.z0}$\BLOCK{if c.r0} [\VAR{c.r0}]\BLOCK{endif}, "
                r"$(x_1 - x_0)(y_1 - y_0) = (\VAR{c.d1}) \cdot (\VAR{c.d2}) = \VAR{c.zd}$"
                r"\BLOCK{if c.rd} [\VAR{c.rd}]\BLOCK{endif}, "
                r"$z_1 = \VAR{c.z2} + \VAR{c.z0} - (\VAR{c.zd}) = \VAR{c.z1}$; "
                r"$\VAR{c.z2} \cdot 10^{\VAR{2 * c.k}} + \VAR{c.z1} \cdot 10^{\VAR{c.k}} + \VAR{c.z0} "
                r"= \VAR{c.res}$."
                r"\BLOCK{endfor}"
                r"\[\VAR{a} \cdot \VAR{b} = \VAR{answer}.\]")

    def sample(self, rng):
        a = rng.randrange(self.cfg.lo, self.cfg.hi)
        b = rng.randrange(self.cfg.lo, self.cfg.hi)
        calls: list = []
        karatsuba_sub_trace(a, b, calls)
        return {"a": a, "b": b, "calls": calls, "answer": a * b}

    def check(self, p):
        assert p["answer"] == p["a"] * p["b"] == p["calls"][-1]["res"]
        for c in p["calls"]:
            assert c["zd"] == c["d1"] * c["d2"] and c["z1"] == c["z2"] + c["z0"] - c["zd"]
            assert c["z2"] * 10 ** (2 * c["k"]) + c["z1"] * 10 ** c["k"] + c["z0"] == c["x"] * c["y"]


def karatsuba_square_trace(x: int, calls: list) -> tuple[int, int | None]:
    """Recursive decimal Karatsuba squaring; returns (square, call number or None for a base case)."""
    n = len(str(x))
    if n <= 2:
        return x * x, None
    k = n // 2
    x1, x0 = divmod(x, 10**k)
    z2, r2 = karatsuba_square_trace(x1, calls)
    z0, r0 = karatsuba_square_trace(x0, calls)
    zs, rs = karatsuba_square_trace(x1 + x0, calls)
    z1 = zs - z2 - z0
    res = z2 * 10 ** (2 * k) + z1 * 10**k + z0
    calls.append({"no": len(calls) + 1, "x": x, "k": k, "x1": x1, "x0": x0, "s": x1 + x0,
                  "z2": z2, "z0": z0, "zs": zs, "z1": z1, "r2": r2, "r0": r0, "rs": rs, "res": res})
    return res, len(calls)


class KaratsubaSquare(Task):
    id = "arithmetic.karatsuba_square"
    title_ru = "Возведение в квадрат методом Карацубы"
    topics = ("arithmetic.multiplication",)
    complexity = 1
    family = "karatsuba"
    solution_detail = SolutionDetail.FULL
    notes = "Squaring-only recursion: z1 = (x1 + x0)^2 - z2 - z0, three squarings per step."
    presets = {"default": {"lo": 10**6 + 1, "hi": 10**8}}
    statement = (r"Вычислить квадрат целого числа \[\VAR{a}^2\] вариантом метода Карацубы для "
                 r"возведения в квадрат: $z_2 = x_1^2$, $z_0 = x_0^2$, $z_1 = (x_1 + x_0)^2 - z_2 - z_0$ "
                 r"(три возведения в квадрат вдвое более коротких чисел). Применять метод рекурсивно, "
                 r"база рекурсии — двузначные числа. Использовать десятичную систему счисления.")
    solution = (r"Для $x^2$ с $n$-значным $x$, $n > 2$: $k = \lfloor n/2 \rfloor$, $x = x_1 10^k + x_0$, "
                r"$z_2 = x_1^2$, $z_0 = x_0^2$, $z_1 = (x_1 + x_0)^2 - z_2 - z_0$, "
                r"$x^2 = z_2 10^{2k} + z_1 10^k + z_0$. Вызовы пронумерованы в порядке завершения "
                r"(ссылка [$i$] --- результат вызова $i$, без ссылки --- база рекурсии)."
                r"\BLOCK{for c in calls}"
                r"\par\noindent [\VAR{c.no}]~$\VAR{c.x}^2$: $k = \VAR{c.k}$; "
                r"$z_2 = \VAR{c.x1}^2 = \VAR{c.z2}$\BLOCK{if c.r2} [\VAR{c.r2}]\BLOCK{endif}, "
                r"$z_0 = \VAR{c.x0}^2 = \VAR{c.z0}$\BLOCK{if c.r0} [\VAR{c.r0}]\BLOCK{endif}, "
                r"$(\VAR{c.x1} + \VAR{c.x0})^2 = \VAR{c.s}^2 = \VAR{c.zs}$"
                r"\BLOCK{if c.rs} [\VAR{c.rs}]\BLOCK{endif}, "
                r"$z_1 = \VAR{c.zs} - \VAR{c.z2} - \VAR{c.z0} = \VAR{c.z1}$; "
                r"$\VAR{c.z2} \cdot 10^{\VAR{2 * c.k}} + \VAR{c.z1} \cdot 10^{\VAR{c.k}} + \VAR{c.z0} "
                r"= \VAR{c.res}$."
                r"\BLOCK{endfor}"
                r"\[\VAR{a}^2 = \VAR{answer}.\]")

    def sample(self, rng):
        a = rng.randrange(self.cfg.lo, self.cfg.hi)
        calls: list = []
        karatsuba_square_trace(a, calls)
        return {"a": a, "calls": calls, "answer": a * a}

    def check(self, p):
        assert p["answer"] == p["a"] ** 2 == p["calls"][-1]["res"]
        assert all(c["z2"] * 10 ** (2 * c["k"]) + c["z1"] * 10 ** c["k"] + c["z0"] == c["x"] ** 2
                   for c in p["calls"])


def _poly_tex(coeffs, var: str = "x") -> str:
    """LaTeX for sum(coeffs[i] * var^i) (low-to-high), highest degree first; "0" when zero."""
    out = ""
    for i in range(len(coeffs) - 1, -1, -1):
        c = int(coeffs[i])
        if c == 0:
            continue
        mono = "" if i == 0 else (var if i == 1 else f"{var}^{{{i}}}")
        body = str(abs(c)) if i == 0 else (mono if abs(c) == 1 else f"{abs(c)} {mono}")
        out += (("-" if c < 0 else "") if not out else (" - " if c < 0 else " + ")) + body
    return out or "0"


def _lin_mul(u: list, v: list, p: int, lhs: str, rhs: str) -> dict:
    """(u[0] + u[1] x)(v[0] + v[1] x) with the three coefficient products (mod p when p > 0)."""
    c = [u[0] * v[0], u[1] * v[0] + u[0] * v[1], u[1] * v[1]]
    if p:
        c = [x % p for x in c]
    return {"lhs": lhs, "rhs": rhs, "u": list(u), "v": list(v), "c": c,
            "u_tex": _poly_tex(u), "v_tex": _poly_tex(v), "tex": _poly_tex(c)}


class KaratsubaPoly(Task):
    id = "arithmetic.karatsuba_poly"
    title_ru = "Умножение многочленов методом Карацубы"
    topics = ("arithmetic.multiplication",)
    complexity = 2
    family = "karatsuba"
    solution_detail = SolutionDetail.FULL
    notes = ("One Karatsuba step for cubic polynomials over Z (default, signed coefficients) "
             "or Z/pZ (@modp): no carries, the method works over any coefficient ring.")
    presets = {"default": {"lo": -9, "hi": 9, "ps": []}, "modp": {"ps": [5, 7, 11, 13]}}
    statement = (r"Вычислить произведение многочленов \[(\VAR{a_tex}) \cdot (\VAR{b_tex})\] "
                 r"\BLOCK{if p}над полем $\mathbb{Z}/\VAR{p}\mathbb{Z}$ (коэффициенты приводить по "
                 r"модулю $\VAR{p}$)\BLOCK{else}над кольцом $\mathbb{Z}$\BLOCK{endif}, применив один "
                 r"шаг метода Карацубы: разбить каждый многочлен на две части, $a = A_1 x^2 + A_0$, "
                 r"$b = B_1 x^2 + B_0$, и обойтись тремя умножениями линейных многочленов.")
    solution = (r"Разбиение: $A_1 = \VAR{a1_tex}$, $A_0 = \VAR{a0_tex}$, $B_1 = \VAR{b1_tex}$, "
                r"$B_0 = \VAR{b0_tex}$; $Z_2 = A_1 B_1$, $Z_0 = A_0 B_0$, "
                r"$Z_s = (A_1 + A_0)(B_1 + B_0)$, $Z_1 = Z_s - Z_2 - Z_0$, "
                r"$ab = Z_2 x^4 + Z_1 x^2 + Z_0$ (переносов нет: метод работает над любым кольцом "
                r"коэффициентов). Умножение линейных многочленов --- напрямую: "
                r"$(u_1 x + u_0)(v_1 x + v_0) = u_1 v_1 x^2 + (u_1 v_0 + u_0 v_1) x + u_0 v_0$."
                r"\par\noindent Суммы половинок: $A_1 + A_0 \VAR{eq} \VAR{sa_tex}$, "
                r"$B_1 + B_0 \VAR{eq} \VAR{sb_tex}$."
                r"\BLOCK{for m in prods}"
                r"\par\noindent $\VAR{m.lhs} = \VAR{m.rhs} = (\VAR{m.u_tex}) \cdot (\VAR{m.v_tex})$: "
                r"при $x^2$: $(\VAR{m.u[1]}) \cdot (\VAR{m.v[1]}) \VAR{eq} \VAR{m.c[2]}$, "
                r"при $x$: $(\VAR{m.u[1]}) \cdot (\VAR{m.v[0]}) + (\VAR{m.u[0]}) \cdot (\VAR{m.v[1]}) "
                r"\VAR{eq} \VAR{m.c[1]}$, "
                r"свободный: $(\VAR{m.u[0]}) \cdot (\VAR{m.v[0]}) \VAR{eq} \VAR{m.c[0]}$; "
                r"итого $\VAR{m.lhs} \VAR{eq} \VAR{m.tex}$."
                r"\BLOCK{endfor}"
                r"\par\noindent $Z_1 = Z_s - Z_2 - Z_0 \VAR{eq} (\VAR{zs_tex}) - (\VAR{z2_tex}) - "
                r"(\VAR{z0_tex}) \VAR{eq} \VAR{z1_tex}$. Сборка:"
                r"\[ab \VAR{eq} (\VAR{z2_tex})\,x^4 + (\VAR{z1_tex})\,x^2 + (\VAR{z0_tex}) "
                r"\VAR{eq} \VAR{res_tex}.\]")

    def sample(self, rng):
        p = rng.choice(self.cfg.ps) if self.cfg.ps else 0

        def coeffs():
            draw = ((lambda: rng.randrange(0, p)) if p
                    else (lambda: rng.randrange(self.cfg.lo, self.cfg.hi + 1)))
            c = [draw() for _ in range(4)]
            while c[3] == 0:
                c[3] = draw()
            return c

        pa, pb = coeffs(), coeffs()
        a1, a0, b1, b0 = pa[2:], pa[:2], pb[2:], pb[:2]
        sa = [(x + y) % p if p else x + y for x, y in zip(a1, a0)]
        sb = [(x + y) % p if p else x + y for x, y in zip(b1, b0)]
        z2 = _lin_mul(a1, b1, p, "Z_2", "A_1 B_1")
        z0 = _lin_mul(a0, b0, p, "Z_0", "A_0 B_0")
        zs = _lin_mul(sa, sb, p, "Z_s", "(A_1 + A_0)(B_1 + B_0)")
        z1 = [(s - x - y) % p if p else s - x - y for s, x, y in zip(zs["c"], z2["c"], z0["c"])]
        res = [0] * 7
        for shift, z in ((0, z0["c"]), (2, z1), (4, z2["c"])):
            for i, c in enumerate(z):
                res[shift + i] += c
        if p:
            res = [x % p for x in res]
        return {"p": p, "pa": pa, "pb": pb, "a_tex": _poly_tex(pa), "b_tex": _poly_tex(pb),
                "a1_tex": _poly_tex(a1), "a0_tex": _poly_tex(a0),
                "b1_tex": _poly_tex(b1), "b0_tex": _poly_tex(b0),
                "sa_tex": _poly_tex(sa), "sb_tex": _poly_tex(sb),
                "prods": [z2, z0, zs], "z2_tex": z2["tex"], "z0_tex": z0["tex"],
                "zs_tex": zs["tex"], "z1_tex": _poly_tex(z1), "res_tex": _poly_tex(res),
                "eq": r"\equiv" if p else "=", "answer": res}

    def check(self, inst):
        p, pa, pb = inst["p"], inst["pa"], inst["pb"]
        conv = [0] * 7
        for i, x in enumerate(pa):
            for j, y in enumerate(pb):
                conv[i + j] += x * y
        if p:
            conv = [x % p for x in conv]
            assert is_prime(p) and all(0 <= c < p for c in pa + pb)
        assert conv == inst["answer"] and inst["answer"][6] != 0


class ToomCook(Task):
    id = "arithmetic.toom_cook"
    title_ru = "Умножение методом Тоома-Кука"
    topics = ("arithmetic.multiplication",)
    complexity = 1
    family = "toom"
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"lo": 10**7 + 1, "hi": 10**9},
               "kontrolnaya04": {"lo": 10**6 + 1, "hi": 10**8}}
    statement = (r"Вычислить произведение целых чисел \[\VAR{a} \cdot \VAR{b}\] с помощью метода "
                 r"Тоома-Кука. Использовать полином 2-й степени и десятичную систему счисления.")
    solution = (r"Основание $B = 10^{\VAR{k}}$: "
                r"$p(t) = \VAR{pa[2]} t^2 + \VAR{pa[1]} t + \VAR{pa[0]}$, "
                r"$q(t) = \VAR{pb[2]} t^2 + \VAR{pb[1]} t + \VAR{pb[0]}$, $p(B) = \VAR{a}$, $q(B) = \VAR{b}$. "
                r"Произведение $r(t) = p(t)q(t) = c_4 t^4 + \dots + c_0$ определяется значениями в пяти точках:"
                r"\[\begin{array}{c|r|r|r}"
                r"t & p(t) & q(t) & r(t) = p(t)q(t) \\ \hline "
                r"\BLOCK{for v in values}\VAR{v.t} & \VAR{v.p} & \VAR{v.q} & \VAR{v.r} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"(значение в $\infty$ --- произведение старших коэффициентов). Восстановление коэффициентов:"
                r"\[\begin{aligned}"
                r"c_0 &= r(0) = \VAR{c[0]}, \quad c_4 = r(\infty) = \VAR{c[4]},\\"
                r"c_2 &= \tfrac{r(1) + r(-1)}{2} - c_0 - c_4 = \VAR{c[2]},\\"
                r"S &= c_1 + c_3 = \tfrac{r(1) - r(-1)}{2} = \VAR{S},\\"
                r"T &= c_1 + 4c_3 = \tfrac{r(2) - c_0 - 4c_2 - 16c_4}{2} = \VAR{T},\\"
                r"c_3 &= \tfrac{T - S}{3} = \VAR{c[3]}, \quad c_1 = S - c_3 = \VAR{c[1]}."
                r"\end{aligned}\]"
                r"Формирование результата:"
                r"\[\begin{aligned}r(B) &= \VAR{c[4]} \cdot 10^{\VAR{4 * k}} + \VAR{c[3]} \cdot 10^{\VAR{3 * k}} + "
                r"\VAR{c[2]} \cdot 10^{\VAR{2 * k}} \\ &\quad + \VAR{c[1]} \cdot 10^{\VAR{k}} + \VAR{c[0]} "
                r"= \VAR{answer}.\end{aligned}\]")

    def sample(self, rng):
        a = rng.randrange(self.cfg.lo, self.cfg.hi)
        b = rng.randrange(self.cfg.lo, self.cfg.hi)
        n = max(len(str(a)), len(str(b)))
        k = -(-n // 3)
        B = 10**k
        pa = [a % B, a // B % B, a // B**2]
        pb = [b % B, b // B % B, b // B**2]

        def ev(c, t):
            return c[0] + c[1] * t + c[2] * t * t

        pts = [0, 1, -1, 2]
        values = [{"t": t, "p": ev(pa, t), "q": ev(pb, t), "r": ev(pa, t) * ev(pb, t)} for t in pts]
        values.append({"t": r"\infty", "p": pa[2], "q": pb[2], "r": pa[2] * pb[2]})
        r = {v["t"]: v["r"] for v in values}
        c0, c4 = r[0], r[r"\infty"]
        c2 = (r[1] + r[-1]) // 2 - c0 - c4
        S = (r[1] - r[-1]) // 2
        T = (r[2] - c0 - 4 * c2 - 16 * c4) // 2
        c3 = (T - S) // 3
        c = [c0, S - c3, c2, c3, c4]
        return {"a": a, "b": b, "k": k, "pa": pa, "pb": pb, "values": values, "S": S, "T": T,
                "c": c, "answer": a * b}

    def check(self, p):
        B = 10 ** p["k"]
        assert sum(ci * B**i for i, ci in enumerate(p["c"])) == p["answer"] == p["a"] * p["b"]
        assert p["pa"][2] < B and p["pb"][2] < B


class ToomPoints(Task):
    id = "arithmetic.toom_points"
    title_ru = "Метод Тоома-Кука с другим набором точек"
    topics = ("arithmetic.multiplication",)
    complexity = 3
    family = "toom"
    solution_detail = SolutionDetail.FULL
    notes = ("Same Toom-3, but the five evaluation points are 0, 1, -1, 2, -2 (no infinity): the "
             "recovery formulas must be re-derived (even/odd split), not copied from the handout.")
    presets = {"default": {"lo": 10**7 + 1, "hi": 10**9}}
    statement = (r"Вычислить произведение целых чисел \[\VAR{a} \cdot \VAR{b}\] методом Тоома-Кука "
                 r"с полиномами 2-й степени, используя значения в точках $0, 1, -1, 2, -2$ "
                 r"(точка $\infty$ не используется). Вывести формулы восстановления коэффициентов "
                 r"произведения по значениям в этих точках. "
                 r"Использовать десятичную систему счисления.")
    solution = (r"Основание $B = 10^{\VAR{k}}$: "
                r"$p(t) = \VAR{pa[2]} t^2 + \VAR{pa[1]} t + \VAR{pa[0]}$, "
                r"$q(t) = \VAR{pb[2]} t^2 + \VAR{pb[1]} t + \VAR{pb[0]}$, $p(B) = \VAR{a}$, $q(B) = \VAR{b}$. "
                r"Произведение $r(t) = p(t)q(t) = c_4 t^4 + \dots + c_0$ определяется значениями в пяти точках:"
                r"\[\begin{array}{c|r|r|r}"
                r"t & p(t) & q(t) & r(t) = p(t)q(t) \\ \hline "
                r"\BLOCK{for v in values}\VAR{v.t} & \VAR{v.p} & \VAR{v.q} & \VAR{v.r} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"Вывод формул: при замене $t \to -t$ слагаемые с нечётными степенями меняют знак, "
                r"поэтому полусуммы значений в $\pm 1$, $\pm 2$ дают уравнения на чётные коэффициенты, "
                r"а полуразности --- на нечётные:"
                r"\[\tfrac{r(1) + r(-1)}{2} = c_0 + c_2 + c_4, \quad "
                r"\tfrac{r(2) + r(-2)}{2} = c_0 + 4c_2 + 16c_4, \quad "
                r"\tfrac{r(1) - r(-1)}{2} = c_1 + c_3, \quad "
                r"\tfrac{r(2) - r(-2)}{4} = c_1 + 4c_3.\]"
                r"Восстановление ($c_0 = r(0) = \VAR{c[0]}$):"
                r"\[\begin{aligned}"
                r"E_1 &= c_2 + c_4 = \tfrac{r(1) + r(-1)}{2} - c_0 = \VAR{E1}, \quad "
                r"E_2 = 4c_2 + 16c_4 = \tfrac{r(2) + r(-2)}{2} - c_0 = \VAR{E2},\\"
                r"c_4 &= \tfrac{E_2 - 4E_1}{12} = \VAR{c[4]}, \quad c_2 = E_1 - c_4 = \VAR{c[2]},\\"
                r"O_1 &= c_1 + c_3 = \tfrac{r(1) - r(-1)}{2} = \VAR{O1}, \quad "
                r"O_2 = c_1 + 4c_3 = \tfrac{r(2) - r(-2)}{4} = \VAR{O2},\\"
                r"c_3 &= \tfrac{O_2 - O_1}{3} = \VAR{c[3]}, \quad c_1 = O_1 - c_3 = \VAR{c[1]}."
                r"\end{aligned}\]"
                r"Формирование результата:"
                r"\[\begin{aligned}r(B) &= \VAR{c[4]} \cdot 10^{\VAR{4 * k}} + \VAR{c[3]} \cdot 10^{\VAR{3 * k}} + "
                r"\VAR{c[2]} \cdot 10^{\VAR{2 * k}} \\ &\quad + \VAR{c[1]} \cdot 10^{\VAR{k}} + \VAR{c[0]} "
                r"= \VAR{answer}.\end{aligned}\]")

    def sample(self, rng):
        a = rng.randrange(self.cfg.lo, self.cfg.hi)
        b = rng.randrange(self.cfg.lo, self.cfg.hi)
        n = max(len(str(a)), len(str(b)))
        k = -(-n // 3)
        B = 10**k
        pa = [a % B, a // B % B, a // B**2]
        pb = [b % B, b // B % B, b // B**2]

        def ev(c, t):
            return c[0] + c[1] * t + c[2] * t * t

        pts = [0, 1, -1, 2, -2]
        values = [{"t": t, "p": ev(pa, t), "q": ev(pb, t), "r": ev(pa, t) * ev(pb, t)} for t in pts]
        r = {v["t"]: v["r"] for v in values}
        c0 = r[0]
        E1 = (r[1] + r[-1]) // 2 - c0
        E2 = (r[2] + r[-2]) // 2 - c0
        c4 = (E2 - 4 * E1) // 12
        c2 = E1 - c4
        O1 = (r[1] - r[-1]) // 2
        O2 = (r[2] - r[-2]) // 4
        c3 = (O2 - O1) // 3
        c = [c0, O1 - c3, c2, c3, c4]
        return {"a": a, "b": b, "k": k, "pa": pa, "pb": pb, "values": values,
                "E1": E1, "E2": E2, "O1": O1, "O2": O2, "c": c, "answer": a * b}

    def check(self, p):
        B = 10 ** p["k"]
        conv = [0] * 5
        for i, x in enumerate(p["pa"]):
            for j, y in enumerate(p["pb"]):
                conv[i + j] += x * y
        assert conv == p["c"]
        assert p["answer"] == p["a"] * p["b"] == sum(ci * B**i for i, ci in enumerate(p["c"]))
        assert p["pa"][2] < B and p["pb"][2] < B


class ToomUnbalanced(Task):
    id = "arithmetic.toom_unbalanced"
    title_ru = "Метод Тоома-Кука для сомножителей разной длины"
    topics = ("arithmetic.multiplication",)
    complexity = 3
    family = "toom"
    solution_detail = SolutionDetail.FULL
    notes = ("Unbalanced Toom ('Toom-2.5', 3x2 split): r(t) has degree 3, the four points "
             "0, 1, -1, infinity suffice. b must span both base-B digits (B <= b < B^2).")
    presets = {"default": {"a_lo": 10**7 + 1, "a_hi": 10**9, "b_lo": 10**4 + 1, "b_hi": 10**6}}
    statement = (r"Вычислить произведение целых чисел \[\VAR{a} \cdot \VAR{b}\] методом Тоома-Кука "
                 r"для сомножителей разной длины: $a$ разбить на \emph{три} цифры, а $b$ — на "
                 r"\emph{две} по одному и тому же основанию $B = 10^k$. Подобрать число точек "
                 r"по степени многочлена-произведения. Использовать десятичную систему счисления.")
    solution = (r"Основание $B = 10^{\VAR{k}}$: "
                r"$p(t) = \VAR{pa[2]} t^2 + \VAR{pa[1]} t + \VAR{pa[0]}$ ($p(B) = \VAR{a}$), "
                r"$q(t) = \VAR{pb[1]} t + \VAR{pb[0]}$ ($q(B) = \VAR{b}$). "
                r"Произведение $r(t) = p(t)q(t) = c_3 t^3 + c_2 t^2 + c_1 t + c_0$ имеет четыре "
                r"коэффициента, поэтому достаточно значений в четырёх точках:"
                r"\[\begin{array}{c|r|r|r}"
                r"t & p(t) & q(t) & r(t) = p(t)q(t) \\ \hline "
                r"\BLOCK{for v in values}\VAR{v.t} & \VAR{v.p} & \VAR{v.q} & \VAR{v.r} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"(значение в $\infty$ --- произведение старших коэффициентов). "
                r"Восстановление коэффициентов:"
                r"\[\begin{aligned}"
                r"c_0 &= r(0) = \VAR{c[0]}, \quad c_3 = r(\infty) = \VAR{c[3]},\\"
                r"c_2 &= \tfrac{r(1) + r(-1)}{2} - c_0 = \VAR{c[2]}, \quad "
                r"c_1 = \tfrac{r(1) - r(-1)}{2} - c_3 = \VAR{c[1]}."
                r"\end{aligned}\]"
                r"Формирование результата:"
                r"\[r(B) = \VAR{c[3]} \cdot 10^{\VAR{3 * k}} + \VAR{c[2]} \cdot 10^{\VAR{2 * k}} + "
                r"\VAR{c[1]} \cdot 10^{\VAR{k}} + \VAR{c[0]} = \VAR{answer}.\]")

    def sample(self, rng):
        a = rng.randrange(self.cfg.a_lo, self.cfg.a_hi)
        b = rng.randrange(self.cfg.b_lo, self.cfg.b_hi)
        k = -(-len(str(a)) // 3)
        B = 10**k
        assert B <= b < B**2, "b must have exactly two base-B digits (fix the preset ranges)"
        pa = [a % B, a // B % B, a // B**2]
        pb = [b % B, b // B]

        def ev(c, t):
            return sum(ci * t**i for i, ci in enumerate(c))

        values = [{"t": t, "p": ev(pa, t), "q": ev(pb, t), "r": ev(pa, t) * ev(pb, t)}
                  for t in (0, 1, -1)]
        values.append({"t": r"\infty", "p": pa[2], "q": pb[1], "r": pa[2] * pb[1]})
        r = {v["t"]: v["r"] for v in values}
        c0, c3 = r[0], r[r"\infty"]
        c2 = (r[1] + r[-1]) // 2 - c0
        c1 = (r[1] - r[-1]) // 2 - c3
        return {"a": a, "b": b, "k": k, "pa": pa, "pb": pb, "values": values,
                "c": [c0, c1, c2, c3], "answer": a * b}

    def check(self, p):
        B = 10 ** p["k"]
        conv = [0] * 4
        for i, x in enumerate(p["pa"]):
            for j, y in enumerate(p["pb"]):
                conv[i + j] += x * y
        assert conv == p["c"]
        assert p["answer"] == p["a"] * p["b"] == sum(ci * B**i for i, ci in enumerate(p["c"]))
        assert p["pa"][2] > 0 and p["pb"][1] > 0 and p["b"] < B**2


class MontgomeryMul(Task):
    id = "arithmetic.montgomery_mul"
    title_ru = "Умножение по модулю методом Монтгомери"
    topics = ("arithmetic.montgomery",)
    complexity = 2
    family = "montgomery"
    solution_detail = SolutionDetail.FULL
    notes = "Odd modulus; the even-modulus version is arithmetic.montgomery_mul_even."
    presets = {"default": {"ab_lo": 10**4 + 1, "ab_hi": 10**6, "m_lo": 10**6 + 1, "m_hi": 10**7}}
    statement = (r"Вычислить произведение целых чисел по модулю: "
                 r"\[\VAR{a} \cdot \VAR{b}\ (\textrm{mod}\ \VAR{m})\] с помощью метода Монтгомери. "
                 r"Обосновать выбор параметра $R$.")
    solution = (M + r"\VAR{tx.montgomery_params(mo)} "
                r"$x = \mathrm{REDC}(ab) = ab R^{-1} \bmod m$, затем "
                r"$\mathrm{REDC}(x \cdot (R^2 \bmod m)) = ab \bmod m$ (условие $T < mR$ выполнено, "
                r"так как оба множителя меньше $m$)."
                r"\VAR{tx.redc_table(mo)}"
                r"\[\VAR{a} \cdot \VAR{b} \equiv \VAR{answer}\VAR{tx.mod(m)}.\]")

    def sample(self, rng):
        a = rng.randrange(self.cfg.ab_lo, self.cfg.ab_hi)
        b = rng.randrange(self.cfg.ab_lo, self.cfg.ab_hi)
        m = rng.randrange(self.cfg.m_lo, self.cfg.m_hi) | 1
        mo = steps.montgomery_mul(a, b, m)
        return {"a": a, "b": b, "m": m, "mo": mo, "answer": mo["result"]}

    def check(self, p):
        assert p["m"] % 2 == 1, "Montgomery modulus must be odd"
        assert p["answer"] == p["a"] * p["b"] % p["m"]


class MontgomeryMulEven(Task):
    id = "arithmetic.montgomery_mul_even"
    title_ru = "Умножение по модулю методом Монтгомери (чётный модуль)"
    topics = ("arithmetic.montgomery",)
    complexity = 3
    family = "montgomery"
    solution_detail = SolutionDetail.FULL
    notes = ("Harder version: m = 2^t s is even; reduce mod 2^t directly, mod s by Montgomery, "
             "combine by CRT. The legacy sem1 script always produced even moduli.")
    presets = {"default": MontgomeryMul.presets["default"]}
    statement = MontgomeryMul.statement
    solution = (M + r"Модуль чётный: $m = \VAR{m} = 2^{\VAR{t}} \cdot \VAR{s}$, и $R = 2^k$ не взаимно прост "
                r"с $m$. Решаем сравнение по модулям $2^{\VAR{t}}$ и $s = \VAR{s}$ и объединяем по КТО."
                r"\par По модулю $2^{\VAR{t}} = \VAR{pt}$ (младшие $\VAR{t}$ бит): "
                r"$\VAR{a} \cdot \VAR{b} \equiv \VAR{a % pt} \cdot \VAR{b % pt} \equiv \VAR{r1}\VAR{tx.mod(pt)}$."
                r"\par По модулю $s$ методом Монтгомери (по модулю $s$: $a \equiv \VAR{mo.a_r}$, "
                r"$b \equiv \VAR{mo.b_r}$). \VAR{tx.montgomery_params(mo)}"
                r"\VAR{tx.redc_table(mo)}"
                r"Итак, $ab \equiv \VAR{r2}\VAR{tx.mod(s)}$. КТО:"
                r"\VAR{tx.crt(c)}"
                r"\[\VAR{a} \cdot \VAR{b} \equiv \VAR{answer}\VAR{tx.mod(m)}.\]")

    def sample(self, rng):
        while True:
            a = rng.randrange(self.cfg.ab_lo, self.cfg.ab_hi)
            b = rng.randrange(self.cfg.ab_lo, self.cfg.ab_hi)
            m = rng.randrange(self.cfg.m_lo, self.cfg.m_hi) & ~1
            t, s = steps.split_even(m)
            if s > 1:
                break
        pt = 2**t
        mo = steps.montgomery_mul(a, b, s)
        c = steps.crt([a * b % pt, mo["result"]], [pt, s])
        return {"a": a, "b": b, "m": m, "t": t, "s": s, "pt": pt, "r1": a * b % pt,
                "r2": mo["result"], "mo": mo, "c": c, "answer": c["x"]}

    def check(self, p):
        assert p["m"] % 2 == 0 and p["pt"] * p["s"] == p["m"]
        assert p["answer"] == p["a"] * p["b"] % p["m"]


class FFTMul(Task):
    id = "arithmetic.fft_mul"
    title_ru = "Умножение с помощью БПФ в конечном поле"
    topics = ("arithmetic.multiplication", "arithmetic.convolution")
    complexity = 3
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"lo": 33, "hi": 1000}}
    statement = (r"Вычислить произведение целых чисел \[\VAR{a} \cdot \VAR{b}\] с помощью БПФ в поле "
                 r"вычетов $\mathbb{Z}/p\mathbb{Z}$. Обосновать выбор параметров алгоритма.")
    solution = (M + r"Цифры (младшие первыми): $a = (\VAR{da|join(', ')})$, $b = (\VAR{db|join(', ')})$. "
                r"Свёртка имеет $\VAR{la} + \VAR{lb} - 1 = \VAR{la + lb - 1}$ коэффициентов, поэтому длина "
                r"преобразования $N = \VAR{N}$ (степень двойки). Коэффициенты свёртки не превосходят "
                r"$81 \cdot \min(\VAR{la}, \VAR{lb}) = \VAR{bound}$, значит нужно $p > \VAR{bound}$ и $N \mid p - 1$ "
                r"(чтобы существовал корень степени $N$ из единицы): $p = \VAR{p}$. "
                r"$g = \VAR{g}$ --- первообразный корень, $\omega = g^{(p-1)/N} = \VAR{g}^{\VAR{(p - 1) // N}} "
                r"\equiv \VAR{w}$, $\omega^{-1} \equiv \VAR{wi}$, $N^{-1} \equiv \VAR{Ni}\VAR{tx.mod(p)}$. "
                r"Степени $\omega^j$: $\VAR{wpow|join(', ')}$."
                r"\par $A_k = \sum_j a_j \omega^{jk}$, $B_k = \sum_j b_j \omega^{jk}$, $C_k = A_k B_k$, "
                r"$c_j = N^{-1} \sum_k C_k \omega^{-jk}$ (всё по модулю $p$):"
                r"\[\begin{array}{c|\BLOCK{for _ in range(N)}r\BLOCK{endfor}}"
                r"k\BLOCK{for k in range(N)} & \VAR{k}\BLOCK{endfor} \\ \hline "
                r"A_k\BLOCK{for x in A} & \VAR{x}\BLOCK{endfor} \\ "
                r"B_k\BLOCK{for x in B} & \VAR{x}\BLOCK{endfor} \\ "
                r"C_k\BLOCK{for x in C} & \VAR{x}\BLOCK{endfor} \\ \hline "
                r"c_k\BLOCK{for x in conv} & \VAR{x}\BLOCK{endfor}"
                r"\end{array}\]"
                r"Переносы: $\sum_j c_j 10^j = \BLOCK{for x in conv}\VAR{x} \cdot 10^{\VAR{loop.index0}}"
                r"\BLOCK{if not loop.last} + \BLOCK{endif}\BLOCK{endfor} = \VAR{answer}$."
                r"\[\VAR{a} \cdot \VAR{b} = \VAR{answer}.\]")

    def sample(self, rng):
        a = rng.randrange(self.cfg.lo, self.cfg.hi)
        b = rng.randrange(self.cfg.lo, self.cfg.hi)
        da = [int(c) for c in str(a)[::-1]]
        db = [int(c) for c in str(b)[::-1]]
        la, lb = len(da), len(db)
        N = 1
        while N < la + lb - 1:
            N *= 2
        bound = 81 * min(la, lb)
        p = bound + 1
        while not (is_prime(p) and (p - 1) % N == 0):
            p += 1
        g = steps.primitive_root(p)
        w = pow(g, (p - 1) // N, p)
        wi, Ni = inverse(w, p), inverse(N, p)
        va, vb = da + [0] * (N - la), db + [0] * (N - lb)
        A = [sum(va[j] * pow(w, j * k, p) for j in range(N)) % p for k in range(N)]
        B = [sum(vb[j] * pow(w, j * k, p) for j in range(N)) % p for k in range(N)]
        C = [x * y % p for x, y in zip(A, B)]
        conv = [Ni * sum(C[k] * pow(wi, j * k, p) for k in range(N)) % p for j in range(N)]
        return {"a": a, "b": b, "da": da, "db": db, "la": la, "lb": lb, "N": N, "bound": bound,
                "p": p, "g": g, "w": w, "wi": wi, "Ni": Ni,
                "wpow": [pow(w, j, p) for j in range(N)], "A": A, "B": B, "C": C, "conv": conv,
                "answer": a * b}

    def check(self, p):
        assert sum(c * 10**j for j, c in enumerate(p["conv"])) == p["answer"] == p["a"] * p["b"]
        assert p["p"] > p["bound"] and (p["p"] - 1) % p["N"] == 0
