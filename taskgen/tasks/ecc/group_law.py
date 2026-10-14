"""Group law on elliptic curves over F_p (lecture sem2/08): point addition and doubling,
point counting with Legendre symbols (+ Hasse), order of a point by repeated addition.

Corner cases are kept on purpose: Q = -P (result O), points of order 2 (y = 0, 2P = O),
Q = P, Q = O, singular "curves" (Delta = 0) that must be rejected, points of order 2 and 3.
"""

import math

from taskgen.core import steps
from taskgen.core.nt import first_primes, inverse
from taskgen.core.task import SolutionDetail, Task

# --- helpers -------------------------------------------------------------------------------


def curve_tex(a: int, b: int) -> str:
    """Right-hand side x^3 + ax + b (a, b already reduced mod p)."""
    s = "x^3"
    if a:
        s += " + x" if a == 1 else f" + {a}x"
    if b:
        s += f" + {b}"
    return s


def disc_part(a: int, b: int, p: int) -> int:
    """4a^3 + 27b^2 mod p (Delta = -16 times this)."""
    return (4 * a**3 + 27 * b**2) % p


def all_points(p: int, a: int, b: int) -> list[list[int]]:
    """All affine points of y^2 = x^3 + ax + b over F_p, sorted."""
    sq: dict[int, list[int]] = {}
    for y in range(p):
        sq.setdefault(y * y % p, []).append(y)
    return [[x, y] for x in range(p) for y in sq.get((x**3 + a * x + b) % p, [])]


def neg(P, p: int):
    return None if P is None else [P[0], (-P[1]) % p]


def _inv_info(d: int, p: int) -> dict:
    inv = inverse(d, p)
    return {"d": d, "inv": inv, "prod": d * inv, "q": d * inv // p}


def add_trace(P, Q, a: int, p: int) -> dict:
    """P + Q with everything a hand computation writes down.

    kind: 'left_O' (P = O), 'right_O' (Q = O), 'opposite' (Q = -P, incl. 2P with y = 0),
    'double', 'add'.
    """
    st = steps.ec_add_step(P, Q, a, p)
    t = {"P": P, "Q": Q, "R": st["R"], "lam": st["lam"]}
    if P is None or Q is None:
        t["kind"] = "left_O" if P is None else "right_O"
        return t
    (x1, y1), (x2, y2) = P, Q
    if x1 == x2 and (y1 + y2) % p == 0:
        t["kind"] = "opposite"
        t["self"] = y1 == y2  # P = Q with y = 0
        return t
    if (x1, y1) == (x2, y2):
        t["kind"] = "double"
        t["num_expr"] = f"3 \\cdot {x1}^2 + {a}"
        t["den_expr"] = f"2 \\cdot {y1}"
        num, den = (3 * x1 * x1 + a) % p, 2 * y1 % p
    else:
        t["kind"] = "add"
        t["num_expr"] = f"{y2} - {y1}"
        t["den_expr"] = f"{x2} - {x1}"
        num, den = (y2 - y1) % p, (x2 - x1) % p
    lam = st["lam"]
    x3, y3 = st["R"]
    t.update(num=num, den=den, inv=_inv_info(den, p),
             x3_raw=lam * lam - x1 - x2, dx=x1 - x3, y3_raw=lam * (x1 - x3) - y1,
             x1=x1, y1=y1, x2=x2, y2=y2, x3=x3, y3=y3,
             rhs=(x3**3 + a * x3) % p, check=y3 * y3 % p)
    return t


def _sage_point(p: int, a: int, b: int, P):
    from sage.all import GF, EllipticCurve

    E = EllipticCurve(GF(p), [a, b])
    return E(0) if P is None else E(P[0], P[1])


def _as_list(R):
    return None if R.is_zero() else [int(R[0]), int(R[1])]


def _sqrt_tex(n: int) -> str:
    return f"{2 * math.sqrt(n):.2f}".replace(".", "{,}")


# One LaTeX macro body for an add_trace dict `t`, shared by the templates below.
_TRACE = (
    r"\BLOCK{macro trace(t)}"
    r"\BLOCK{if t.kind == 'left_O'}$\mathcal{O}$ "
    r"--- нейтральный элемент: результат равен второму слагаемому."
    r"\BLOCK{elif t.kind == 'right_O'}$\mathcal{O}$ --- нейтральный элемент: результат равен первому "
    r"слагаемому."
    r"\BLOCK{elif t.kind == 'opposite'}\BLOCK{if t.self}$y = 0$: касательная к кривой в этой точке "
    r"вертикальна, точка имеет порядок~$2$, результат $\mathcal{O}$."
    r"\BLOCK{else}$x$-координаты равны, а $y$-координаты противоположны "
    r"($\VAR{t.P[1]} + \VAR{t.Q[1]} \equiv 0$): слагаемые противоположны, прямая через них "
    r"вертикальна, результат $\mathcal{O}$.\BLOCK{endif}"
    r"\BLOCK{else}"
    r"\BLOCK{if t.kind == 'double'}$\lambda = \frac{3x_1^2 + a}{2y_1} = "
    r"\BLOCK{else}$\lambda = \frac{y_2 - y_1}{x_2 - x_1} = \BLOCK{endif}"
    r"\frac{\VAR{t.num_expr}}{\VAR{t.den_expr}} \equiv \frac{\VAR{t.num}}{\VAR{t.den}} "
    r"\equiv \VAR{t.num} \cdot \VAR{t.inv.inv} \equiv \VAR{t.lam}$, "
    r"где $\VAR{t.den}^{-1} \equiv \VAR{t.inv.inv}$, так как "
    r"$\VAR{t.den} \cdot \VAR{t.inv.inv} = \VAR{t.inv.prod} = \VAR{t.inv.q} \cdot p + 1$;"
    r"\par $x_3 = \lambda^2 - x_1 - x_2 = \VAR{t.lam}^2 - \VAR{t.x1} - \VAR{t.x2} = \VAR{t.x3_raw}"
    r"\BLOCK{if t.x3_raw != t.x3} \equiv \VAR{t.x3}\BLOCK{endif}$,\quad "
    r"$y_3 = \lambda(x_1 - x_3) - y_1 = \VAR{t.lam} \cdot \BLOCK{if t.dx < 0}(\VAR{t.dx})\BLOCK{else}"
    r"\VAR{t.dx}\BLOCK{endif} - \VAR{t.y1} = \VAR{t.y3_raw}"
    r"\BLOCK{if t.y3_raw != t.y3} \equiv \VAR{t.y3}\BLOCK{endif}$."
    r"\BLOCK{endif}"
    r"\BLOCK{endmacro}"
)

# --- P + Q, 2P, P - Q ----------------------------------------------------------------------


class PointAddition(Task):
    id = "ecc.point_addition"
    title_ru = "Сложение и удвоение точек эллиптической кривой"
    topics = ("ecc.group_law",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("Corner cases with probability corner_ratio (default 1/4): Q = -P (P + Q = O, P - Q = 2P), "
             "P of order 2 (y = 0, 2P = O), Q = P (P - Q = O), Q = O. Presets 'opposite' and 'order2' "
             "force the first two.")
    presets = {
        "default": {"primes": [p for p in first_primes(15) if 11 <= p <= 47], "corner_ratio": 0.25,
                    "corners": ["opposite", "opposite", "order2", "order2", "equal", "infinity"]},
        "opposite": {"corner_ratio": 1.0, "corners": ["opposite"]},
        "order2": {"corner_ratio": 1.0, "corners": ["order2"]},
    }
    statement = (r"\BLOCK{import 'macros.tex.j2' as tx}"
                 r"На эллиптической кривой \[E\colon\ y^2 = \VAR{curve}\quad\text{над } "
                 r"\mathbb{F}_{\VAR{p}}\] даны точки $P = \VAR{tx.pt(P)}$ и $Q = \VAR{tx.pt(Q)}$. "
                 r"Вычислить $P + Q$, $2P$ и $P - Q$.")
    solution = (r"\BLOCK{import 'macros.tex.j2' as tx}" + _TRACE +
                r"Всё по модулю $p = \VAR{p}$, $a = \VAR{a}$; формулы: $x_3 = \lambda^2 - x_1 - x_2$, "
                r"$y_3 = \lambda(x_1 - x_3) - y_1$."
                r"\BLOCK{for op in ops}\par\smallskip\noindent \VAR{loop.index}) $\VAR{op.label}"
                r"\BLOCK{if op.rewrite} = \VAR{op.rewrite}\BLOCK{endif}$"
                r"\BLOCK{if op.neg_note}, где $-Q = (\VAR{Q[0]}, -\VAR{Q[1]}) = \VAR{tx.pt(negQ)}$"
                r"\BLOCK{endif}. "
                r"\BLOCK{if op.same_as}Это уже вычислено в п.~\VAR{op.same_as}.\BLOCK{else}"
                r"\VAR{trace(op.t)}\BLOCK{endif}"
                r"\BLOCK{if op.t.R is not none and op.t.kind in ('add', 'double') and not op.same_as} "
                r"Проверка: $\VAR{op.t.y3}^2 \equiv \VAR{op.t.check}$, "
                r"$\VAR{op.t.x3}^3 + \VAR{a} \cdot \VAR{op.t.x3} + \VAR{b} \equiv \VAR{op.t.check}$."
                r"\BLOCK{endif}\BLOCK{endfor}"
                r"\[P + Q = \VAR{tx.pt(answer[0])}, \qquad 2P = \VAR{tx.pt(answer[1])}, \qquad "
                r"P - Q = \VAR{tx.pt(answer[2])}.\]")

    def _curve(self, rng, p, need_root: bool):
        while True:
            a = rng.randrange(p)
            if need_root:
                x0 = rng.randrange(p)
                b = (-x0**3 - a * x0) % p
            else:
                b = rng.randrange(p)
            if disc_part(a, b, p) and len(all_points(p, a, b)) >= 4:
                return a, b

    def sample(self, rng):
        corner = rng.choice(self.cfg.corners) if rng.random() < self.cfg.corner_ratio else None
        p = rng.choice(self.cfg.primes)
        while True:
            a, b = self._curve(rng, p, corner == "order2")
            pts = all_points(p, a, b)
            if corner == "order2":
                P = rng.choice([pt for pt in pts if pt[1] == 0])
            else:
                P = rng.choice([pt for pt in pts if pt[1] != 0] or [None])
                if P is None:
                    continue
            if corner == "opposite":
                Q = neg(P, p)
            elif corner == "equal":
                Q = list(P)
            elif corner == "infinity":
                Q = None
            else:
                cand = [pt for pt in pts if pt[0] != P[0]]
                if not cand:
                    continue
                Q = rng.choice(cand)
            break
        negQ = neg(Q, p)
        raw = [("P + Q", None, P, Q), ("2P", "P + P", P, P), ("P - Q", "P + (-Q)", P, negQ)]
        ops, seen = [], {}
        for i, (label, rewrite, X, Y) in enumerate(raw, 1):
            key = tuple(sorted([tuple(X) if X else (), tuple(Y) if Y else ()]))
            op = {"label": label, "rewrite": rewrite, "neg_note": label == "P - Q" and Q is not None,
                  "same_as": seen.get(key), "t": add_trace(X, Y, a, p)}
            seen.setdefault(key, i)
            ops.append(op)
        if Q is not None and Q == P:
            ops[0]["rewrite"] = "P + P"  # Q = P: the sum is a doubling
        if Q is not None and Q[1] == 0:
            ops[2]["rewrite"] = r"P + (-Q) = P + Q"  # -Q = Q: Q has order 2
        return {"p": p, "a": a, "b": b, "curve": curve_tex(a, b), "P": P, "Q": Q, "negQ": negQ,
                "corner": corner, "ops": ops, "answer": [op["t"]["R"] for op in ops]}

    def check(self, p):
        m, a, b = p["p"], p["a"], p["b"]
        assert disc_part(a, b, m) != 0, "singular curve"
        P, Q = _sage_point(m, a, b, p["P"]), _sage_point(m, a, b, p["Q"])
        assert [_as_list(P + Q), _as_list(2 * P), _as_list(P - Q)] == p["answer"]
        for R in p["answer"]:
            if R is not None:
                assert (R[1] ** 2 - R[0] ** 3 - a * R[0] - b) % m == 0


# --- point counting ------------------------------------------------------------------------


class PointCounting(Task):
    id = "ecc.point_counting"
    title_ru = "Точки эллиптической кривой над конечным полем, теорема Хассе"
    topics = ("ecc.group_law",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Corner case (singular_ratio, default 1/6): Delta = 0, the equation is not an elliptic "
             "curve and must be rejected (singular point (x0, 0), x0 the double root). "
             "Preset 'singular' forces it.")
    presets = {
        "default": {"primes": [7, 11, 13, 17, 19, 23], "singular_ratio": 1 / 6},
        "singular": {"singular_ratio": 1.0},
    }
    statement = (r"Проверить, задаёт ли уравнение \[y^2 = \VAR{curve}\] эллиптическую кривую над "
                 r"$\mathbb{F}_{\VAR{p}}$. Если да, перечислить все точки $E(\mathbb{F}_{\VAR{p}})$ "
                 r"(с помощью символов Лежандра), найти $\#E(\mathbb{F}_{\VAR{p}})$ и проверить оценку "
                 r"Хассе; если нет, указать особую точку.")
    solution = (r"$4a^3 + 27b^2 = 4 \cdot \VAR{a}^3 + 27 \cdot \VAR{b}^2 = \VAR{d4_raw} "
                r"\equiv \VAR{d4}\pmod{\VAR{p}}$"
                r"\BLOCK{if singular}, т.\,е. $\Delta = -16(4a^3 + 27b^2) = 0$: кубический многочлен "
                r"$f(x) = \VAR{curve}$ имеет кратный корень "
                r"\BLOCK{if a == 0}$x_0 = 0$ (здесь $a = b = 0$, $f = x^3$, корень тройной)"
                r"\BLOCK{else}$x_0 = -\frac{3b}{2a} \equiv \frac{\VAR{(-3 * b) % p}}{\VAR{(2 * a) % p}} "
                r"\equiv \VAR{x0}$, $f(x) = (x - \VAR{x0})^2 (x - \VAR{x1})$\BLOCK{endif}. "
                r"В точке $(\VAR{x0}, 0)$ обе частные производные $F(x, y) = y^2 - f(x)$ равны нулю: "
                r"$2y = 0$, $f'(\VAR{x0}) = 3 \cdot \VAR{x0}^2 + \VAR{a} \equiv 0$ --- это особая точка "
                r"(касательная в ней не определена). Уравнение \emph{не задаёт} эллиптическую кривую, "
                r"закон сложения точек на ней не определён."
                r"\BLOCK{else}, т.\,е. $\Delta = -16(4a^3 + 27b^2) \ne 0$ и уравнение задаёт эллиптическую кривую."
                r"\par Квадраты в $\mathbb{F}_{\VAR{p}}$: "
                r"$\BLOCK{for s in squares}\VAR{s[0]}^2 \equiv \VAR{s[1]}\BLOCK{if not loop.last},\ \allowbreak "
                r"\BLOCK{endif}\BLOCK{endfor}$; "
                r"$\left(\frac{c}{\VAR{p}}\right) = 1$ для $c$ из этого списка и $-1$ для остальных "
                r"$c \ne 0$. Для каждого $x$ вычисляем $f(x) = \VAR{curve}$; при "
                r"$\left(\frac{f(x)}{p}\right) = 1$ получаем две точки $(x, \pm y)$, при $f(x) = 0$ "
                r"--- одну (точку порядка~$2$):"
                r"\[\BLOCK{for half in halves}\begin{array}{r|r|r|l}"
                r"x & f(x) & \left(\frac{f(x)}{p}\right) & y \\ \hline "
                r"\BLOCK{for r in half}\VAR{r.x} & \VAR{r.f} & \VAR{r.leg} & "
                r"\BLOCK{if r.ys}\VAR{r.ys|join(',\\ ')}\BLOCK{else}\text{---}\BLOCK{endif} \\ "
                r"\BLOCK{endfor}\end{array}\BLOCK{if not loop.last}\qquad\BLOCK{endif}\BLOCK{endfor}\]"
                r"$E(\mathbb{F}_{\VAR{p}}) = \{\mathcal{O},\ \BLOCK{for P in points}(\VAR{P[0]}, \VAR{P[1]})"
                r"\BLOCK{if not loop.last},\ \allowbreak \BLOCK{endif}\BLOCK{endfor}\}$."
                r"\par $\#E = p + 1 + \sum_x \left(\frac{f(x)}{p}\right) = \VAR{p} + 1 \BLOCK{if leg_sum < 0}- \BLOCK{else}+ \BLOCK{endif}\VAR{leg_sum|abs} "
                r"= \VAR{n}$. Оценка Хассе: $t = p + 1 - \#E = \VAR{t}$, "
                r"$\abs{t} = \VAR{t|abs} \le 2\sqrt{\VAR{p}} \approx \VAR{bound}$ "
                r"(равносильно $t^2 = \VAR{t * t} \le 4p = \VAR{4 * p}$) --- выполнена."
                r"\BLOCK{endif}"
                r"\[\BLOCK{if singular}\Delta = 0,\ \text{особая точка } (\VAR{x0}, 0)"
                r"\BLOCK{else}\#E(\mathbb{F}_{\VAR{p}}) = \VAR{n}\BLOCK{endif}.\]")

    def sample(self, rng):
        p = rng.choice(self.cfg.primes)
        singular = rng.random() < self.cfg.singular_ratio
        if singular:
            x0 = rng.randrange(p)
            a, b = (-3 * x0 * x0) % p, (2 * x0**3) % p
        else:
            while True:
                a, b = rng.randrange(p), rng.randrange(p)
                if disc_part(a, b, p):
                    break
        ctx = {"p": p, "a": a, "b": b, "curve": curve_tex(a, b), "d4": disc_part(a, b, p),
               "d4_raw": 4 * a**3 + 27 * b**2,
               "singular": singular}
        if singular:
            ctx.update(x0=x0, x1=(-2 * x0) % p, answer={"singular_point": [x0, 0]})
            return ctx
        sq = {}
        for y in range(p):
            sq.setdefault(y * y % p, []).append(y)
        rows = []
        for x in range(p):
            f = (x**3 + a * x + b) % p
            ys = sq.get(f, [])
            rows.append({"x": x, "f": f, "leg": 0 if f == 0 else (1 if ys else -1), "ys": ys})
        h = (p + 1) // 2 if p > 11 else p
        leg_sum = sum(r["leg"] for r in rows)
        n = p + 1 + leg_sum
        ctx.update(squares=[[y, y * y % p] for y in range(1, (p + 1) // 2)],
                   halves=[rows[:h], rows[h:]] if h < p else [rows],
                   points=all_points(p, a, b), leg_sum=leg_sum, n=n, t=p + 1 - n,
                   bound=_sqrt_tex(p), answer={"order": n})
        return ctx

    def check(self, p):
        m, a, b = p["p"], p["a"], p["b"]
        if p["singular"]:
            x0 = p["answer"]["singular_point"][0]
            assert disc_part(a, b, m) == 0
            assert (x0**3 + a * x0 + b) % m == 0 and (3 * x0 * x0 + a) % m == 0
            assert (x0 - p["x1"]) % m == (3 * x0) % m  # roots x0, x0, -2x0
            return
        from sage.all import GF, EllipticCurve

        n = int(EllipticCurve(GF(m), [a, b]).order())
        assert n == p["answer"]["order"] == 1 + len(p["points"])
        assert (m + 1 - n) ** 2 <= 4 * m
        assert sum(len(r["ys"]) for half in p["halves"] for r in half) == len(p["points"])


# --- order of a point ------------------------------------------------------------------------


def multiples_trace(P, a: int, p: int) -> dict:
    """kP = (k-1)P + P for k = 2, 3, ... until y(kP) = 0 (ord = 2k) or kP = -(k-1)P (ord = 2k - 1)."""
    if P[1] == 0:
        return {"rows": [], "stop": "y0", "k": 1, "order": 2}
    rows, prev = [], P
    k = 1
    while True:
        k += 1
        t = add_trace(prev, P, a, p)
        R = t["R"]
        assert R is not None
        rows.append({"k": k, "t": t, "R": R})
        if R[1] == 0:
            return {"rows": rows, "stop": "y0", "k": k, "order": 2 * k}
        if R[0] == prev[0]:
            return {"rows": rows, "stop": "neg", "k": k, "order": 2 * k - 1}
        prev = R


class PointOrder(Task):
    id = "ecc.point_order"
    title_ru = "Порядок точки эллиптической кривой"
    topics = ("ecc.group_law",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("kP by repeated addition, stopping at y(kP) = 0 (order 2k) or kP = -(k-1)P (order 2k - 1), "
             "so about ord/2 additions; Lagrange check ord | #E. Points of order 2 and 3 "
             "(small_ratio, default 1/5; preset 'small' forces them) are corner cases.")
    presets = {"default": {"primes": [7, 11, 13, 17, 19, 23, 29], "min_order": 4, "max_order": 18,
                           "small_ratio": 0.2},
               "small": {"small_ratio": 1.0}}
    statement = (r"\BLOCK{import 'macros.tex.j2' as tx}"
                 r"Найти порядок точки $P = \VAR{tx.pt(P)}$ эллиптической кривой "
                 r"\[E\colon\ y^2 = \VAR{curve}\quad\text{над } \mathbb{F}_{\VAR{p}},\qquad "
                 r"\#E(\mathbb{F}_{\VAR{p}}) = \VAR{N},\] последовательно вычисляя кратные $kP$. "
                 r"Согласуется ли ответ с теоремой Лагранжа?")
    solution = (r"\BLOCK{import 'macros.tex.j2' as tx}"
                r"Если $\ord P = n$, то $(n - k)P = -kP$. Поэтому достаточно вычислять "
                r"$kP = (k - 1)P + P$, пока не встретится точка с $y = 0$ (тогда $2kP = \mathcal{O}$ и "
                r"$n = 2k$) или $x(kP) = x((k-1)P)$, т.\,е. $kP = -(k-1)P$ (тогда $n = 2k - 1$): "
                r"раньше этого ни одно из равенств $n \mid 2k$, $n \mid 2k - 1$ выполняться не может. "
                r"Всё по модулю $\VAR{p}$, $a = \VAR{a}$."
                r"\BLOCK{if not tr.rows}\par У точки $P$ координата $y = 0$: касательная в $P$ вертикальна, "
                r"$2P = \mathcal{O}$, $P \ne \mathcal{O}$, т.\,е. $\ord P = 2$."
                r"\BLOCK{else}"
                r"\[\begin{array}{r|l|r|c}"
                r"k & \lambda & \lambda \bmod \VAR{p} & kP \\ \hline "
                r"1 & & & \VAR{tx.pt(P)} \\ "
                r"\BLOCK{for r in tr.rows}\VAR{r.k} & \frac{\VAR{r.t.num_expr}}{\VAR{r.t.den_expr}} "
                r"\equiv \frac{\VAR{r.t.num}}{\VAR{r.t.den}} & \VAR{r.t.lam} & \VAR{tx.pt(r.R)} \\ "
                r"\BLOCK{endfor}\end{array}\]"
                r"(Строка $k = 2$ --- удвоение, $\lambda = \frac{3x^2 + a}{2y}$; остальные --- сложение "
                r"с $P$, $\lambda = \frac{y_2 - y_1}{x_2 - x_1}$. Обратные: "
                r"\BLOCK{for r in tr.rows}$\VAR{r.t.inv.d}^{-1} \equiv \VAR{r.t.inv.inv}$"
                r"\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}.)\par "
                r"\BLOCK{if tr.stop == 'y0'}У точки $\VAR{tr.k}P$ координата $y = 0$, поэтому "
                r"$\VAR{2 * tr.k}P = \mathcal{O}$ и $\ord P = 2 \cdot \VAR{tr.k} = \VAR{answer}$."
                r"\BLOCK{else}$x(\VAR{tr.k}P) = x(\VAR{tr.k - 1}P)$, т.\,е. $\VAR{tr.k}P = -\VAR{tr.k - 1}P$ "
                r"и $\VAR{2 * tr.k - 1}P = \mathcal{O}$: $\ord P = 2 \cdot \VAR{tr.k} - 1 = \VAR{answer}$."
                r"\BLOCK{endif}\BLOCK{endif}"
                r"\par Теорема Лагранжа: порядок точки делит порядок группы, "
                r"$\VAR{N} = \VAR{answer} \cdot \VAR{N // answer}$ --- согласуется."
                r"\[\ord P = \VAR{answer}.\]")

    def sample(self, rng):
        from sage.all import GF, EllipticCurve

        small = rng.random() < self.cfg.small_ratio
        while True:
            p = rng.choice(self.cfg.primes)
            a, b = rng.randrange(p), rng.randrange(p)
            if not disc_part(a, b, p):
                continue
            E = EllipticCurve(GF(p), [a, b])
            pts = all_points(p, a, b)
            if small:
                cand = [P for P in pts if int(E(P).order()) in (2, 3)]
            else:
                cand = [P for P in pts if self.cfg.min_order <= int(E(P).order()) <= self.cfg.max_order]
            if not cand:
                continue
            P = rng.choice(cand)
            tr = multiples_trace(P, a, p)
            return {"p": p, "a": a, "b": b, "curve": curve_tex(a, b), "P": P, "N": len(pts) + 1,
                    "tr": tr, "answer": tr["order"]}

    def check(self, p):
        m, a, b = p["p"], p["a"], p["b"]
        assert disc_part(a, b, m) != 0
        P = _sage_point(m, a, b, p["P"])
        assert int(P.order()) == p["answer"]
        assert int(P.curve().order()) == p["N"] and p["N"] % p["answer"] == 0
        # independent: n P = O and (n/q) P != O for every prime q | n
        n = p["answer"]
        assert (n * P).is_zero()
        assert all(not ((n // q) * P).is_zero() for q in range(2, n + 1)
                   if n % q == 0 and all(q % r for r in range(2, q)))
