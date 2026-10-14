"""LLL lattice basis reduction (lecture sem2/12): Gram--Schmidt orthogonalisation and the
LLL algorithm with delta = 3/4 and a full trace, in exact rational arithmetic.

Conventions (as in Hoffstein--Pipher--Silverman, sect. 7.13): basis vectors are rows,
b_i^* = b_i - sum_{j<i} mu_{ij} b_j^*, mu_{ij} = <b_i, b_j^*> / B_j, B_j = ||b_j^*||^2.
Size reduction rounds mu to the nearest integer and leaves |mu| <= 1/2 untouched (so a
size-reduced basis is never changed); the Lovasz condition is B_k >= (3/4 - mu_{k,k-1}^2) B_{k-1}.

LLL instances are built from an LLL-reduced basis by a few random unimodular operations,
so the traces stay short; presets control the shape of the trace:

* ``default`` -- a generic basis (some swaps);
* ``noswap`` -- corner case: only size reductions (or nothing at all: the basis is already
  LLL-reduced), no swaps;
* ``swaps`` -- corner case: many swaps (k goes back and forth).
"""

from __future__ import annotations

import math
from fractions import Fraction

from taskgen.core.task import SolutionDetail, Task

DELTA = Fraction(3, 4)


# --- exact helpers --------------------------------------------------------------------


def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def gram_schmidt(basis):
    """Rows -> (b^* as Fraction vectors, mu (lower triangular, mu[i][j] for j < i), B)."""
    n = len(basis)
    bs, B = [], []
    mu = [[Fraction(0)] * n for _ in range(n)]
    for i in range(n):
        v = [Fraction(x) for x in basis[i]]
        for j in range(i):
            mu[i][j] = _dot(basis[i], bs[j]) / B[j]
            v = [a - mu[i][j] * c for a, c in zip(v, bs[j])]
        bs.append(v)
        B.append(_dot(v, v))
    return bs, mu, B


def nearest(m: Fraction) -> int:
    """Rounding used by size reduction: 0 if |m| <= 1/2, else the nearest integer."""
    return 0 if abs(m) <= Fraction(1, 2) else math.floor(m + Fraction(1, 2))


def det(a) -> int:
    if len(a) == 2:
        return a[0][0] * a[1][1] - a[0][1] * a[1][0]
    return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
            - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
            + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))


def is_lll_reduced(basis, delta=DELTA) -> bool:
    _, mu, B = gram_schmidt(basis)
    n = len(basis)
    size = all(abs(mu[i][j]) <= Fraction(1, 2) for i in range(n) for j in range(i))
    lovasz = all(B[k] >= (delta - mu[k][k - 1] ** 2) * B[k - 1] for k in range(1, n))
    return size and lovasz


def lll_trace(basis, delta=DELTA) -> dict:
    """LLL (HPS, fig. 7.8) with the trace: one entry per pass of the main loop."""
    b = [list(r) for r in basis]
    n = len(b)
    bs, mu, B = gram_schmidt(b)
    k, steps = 1, []
    while k < n:
        st = {"k": k + 1, "red": [], "ops": []}
        for j in range(k - 1, -1, -1):
            m = mu[k][j]
            q = nearest(m)
            st["red"].append({"j": j + 1, "mu": m, "q": q})
            if q:
                b[k] = [x - q * y for x, y in zip(b[k], b[j])]
                for i in range(j):
                    mu[k][i] -= q * mu[j][i]
                mu[k][j] -= q
                st["ops"].append((j + 1, q))
        st["bk"] = list(b[k])
        assert gram_schmidt(b)[1] == mu  # incremental update of mu is right
        m = mu[k][k - 1]
        rhs = (delta - m * m) * B[k - 1]
        st.update(mu=m, Bk=B[k], Bk1=B[k - 1], rhs=rhs, ok=B[k] >= rhs)
        if st["ok"]:
            k += 1
        else:
            b[k - 1], b[k] = b[k], b[k - 1]
            bs, mu, B = gram_schmidt(b)
            st["gs"] = ([v[:] for v in bs], [row[:] for row in mu], B[:])  # mu mutates later
            k = max(k - 1, 1)
        st["basis"] = [list(r) for r in b]
        st["k_next"] = k + 1
        steps.append(st)
    return {"steps": steps, "basis": b}


# --- TeX formatting -------------------------------------------------------------------


def fr(x) -> str:
    """Rational number in inline math: 5, -\\tfrac{3}{7}."""
    x = Fraction(x)
    if x.denominator == 1:
        return str(x.numerator)
    return ("-" if x < 0 else "") + rf"\tfrac{{{abs(x.numerator)}}}{{{x.denominator}}}"


def frp(x) -> str:
    """Like fr(), parenthesised if negative (for products)."""
    s = fr(x)
    return f"({s})" if Fraction(x) < 0 else s


def sq(x) -> str:
    """mu^2 as written in the Lovasz test: 0, 4, (\tfrac{1}{3})^2, (-\tfrac{1}{2})^2."""
    x = Fraction(x)
    if x == 0:
        return "0"
    return f"{fr(x)}^2" if x.denominator == 1 and x > 0 else f"({fr(x)})^2"


def ivec(v) -> str:
    return "(" + ", ".join(str(int(x)) for x in v) + ")"


def fvec(v) -> str:
    """Rational vector with the common denominator taken out: \\tfrac{1}{14}(5, -3, 2)."""
    d = math.lcm(*(Fraction(x).denominator for x in v))
    if d == 1:
        return ivec(v)
    return rf"\tfrac{{1}}{{{d}}}" + ivec([Fraction(x) * d for x in v])


def comb_tex(k: int, ops) -> str:
    """'b_3 - 2b_2 + b_1' for the size-reduction operations [(j, q), ...]."""
    s = f"b_{k}"
    for j, q in ops:
        c = -q
        coef = "" if abs(c) == 1 else str(abs(c))
        s += (" + " if c > 0 else " - ") + f"{coef}b_{j}"
    return s


def gs_tex(basis, gs) -> dict:
    bs, mu, B = gs
    n = len(basis)
    return {"rows": [{"i": i + 1, "b": ivec(basis[i]), "bs": fvec(bs[i]), "B": fr(B[i])}
                     for i in range(n)],
            "mu": [{"i": i + 1, "j": j + 1, "v": fr(mu[i][j])} for i in range(n) for j in range(i)]}


def _maxden(gs) -> int:
    bs, mu, B = gs
    vals = [x for row in mu for x in row] + list(B) + [x for v in bs for x in v]
    return max(Fraction(x).denominator for x in vals)


GS_MACRO = (r"\BLOCK{macro gstable(g, mus=True)}"
            r"\[\begin{array}{c|c|c|c}"
            r"i & b_i & b_i^* & B_i = \|b_i^*\|^2 \\ \hline "
            r"\BLOCK{for r in g.rows}\VAR{r.i} & \VAR{r.b} & \VAR{r.bs} & \VAR{r.B} \\ \noalign{\vspace{2pt}} \BLOCK{endfor}"
            r"\end{array}\]"
            r"\BLOCK{if mus}\BLOCK{for m in g.mu}$\mu_{\VAR{m.i}\VAR{m.j}} = \VAR{m.v}$\BLOCK{if not loop.last}, "
            r"\BLOCK{else}.\BLOCK{endif}\BLOCK{endfor}\BLOCK{endif}"
            r"\BLOCK{endmacro}")

BASIS_STMT = (r"\BLOCK{for v in basis}$b_{\VAR{loop.index}} = \VAR{v}$\BLOCK{if loop.revindex == 2} и "
              r"\BLOCK{elif not loop.last}, \BLOCK{endif}\BLOCK{endfor}")


# --- Gram--Schmidt --------------------------------------------------------------------


class GramSchmidt(Task):
    id = "lattices.gram_schmidt"
    title_ru = "Ортогонализация Грама--Шмидта"
    topics = ("lattices.lll",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("3x3 integer basis, exact rational mu_ij and B_i; det L checked via prod B_i = det^2. "
             "Orthogonal pairs (mu = 0) and |mu| > 1/2 are both allowed.")
    presets = {"default": {"n": 3, "entry": 3, "maxden": 60}}
    statement = (r"Выполнить ортогонализацию Грама--Шмидта базиса " + BASIS_STMT +
                 r" решётки $\mathcal{L} \subset \mathbb{Z}^{\VAR{n}}$: найти коэффициенты $\mu_{ij}$, "
                 r"векторы $b_i^*$ и числа $B_i = \|b_i^*\|^2$. Найти $\det \mathcal{L}$ "
                 r"и проверить, что $\det \mathcal{L} = \prod_i \|b_i^*\|$.")
    solution = (GS_MACRO +
                r"$b_1^* = b_1 = \VAR{basis[0]}$, $B_1 = \VAR{steps[0].B}$. "
                r"\BLOCK{for s in steps[1:]}\par "
                r"\BLOCK{for m in s.mu}$\mu_{\VAR{s.i}\VAR{m.j}} = \frac{\langle b_{\VAR{s.i}}, b_{\VAR{m.j}}^*"
                r"\rangle}{B_{\VAR{m.j}}} = \VAR{m.v}$, \BLOCK{endfor}"
                r"$b_{\VAR{s.i}}^* = b_{\VAR{s.i}}\BLOCK{for m in s.mu} \VAR{m.term}\BLOCK{endfor} = \VAR{s.bs}$, "
                r"$B_{\VAR{s.i}} = \VAR{s.B}$.\BLOCK{endfor}"
                r"\par Проверка ортогональности: \BLOCK{for c in ortho}$\langle b_{\VAR{c[0]}}^*, b_{\VAR{c[1]}}^*"
                r"\rangle = 0$\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}. Итог:"
                r"\VAR{gstable(gs, False)}"
                r"\par $\det \mathcal{L} = |\det(b_{ij})| = \VAR{d}$; \quad "
                r"$B_1 \cdots B_{\VAR{n}} = \VAR{prodB} = \VAR{d}^2$, т.\,е. $\prod_i \|b_i^*\| = \VAR{d}$."
                r"\BLOCK{if zero_mu} Обратите внимание: $\VAR{zero_mu}$ "
                r"(соответствующие векторы ортогональны).\BLOCK{endif}"
                r"\[\BLOCK{for m in gs.mu}\mu_{\VAR{m.i}\VAR{m.j}} = \VAR{m.v},\ \BLOCK{endfor}"
                r"\BLOCK{for r in gs.rows}B_{\VAR{r.i}} = \VAR{r.B}\BLOCK{if not loop.last},\ \BLOCK{endif}"
                r"\BLOCK{endfor};\quad \det\mathcal{L} = \VAR{d}.\]")

    def sample(self, rng):
        n, e = self.cfg.n, self.cfg.entry
        while True:
            a = [[rng.randint(-e, e) for _ in range(n)] for _ in range(n)]
            d = det(a)
            if d == 0 or any(not any(r) for r in a):
                continue
            gs = gram_schmidt(a)
            if _maxden(gs) <= self.cfg.maxden:
                break
        bs, mu, B = gs
        steps = []
        for i in range(n):
            terms = [{"j": j + 1, "v": fr(mu[i][j]),
                      "term": "" if mu[i][j] == 0 else
                      ("-" if mu[i][j] > 0 else "+") + " "
                      + ("" if abs(mu[i][j]) == 1 else fr(abs(mu[i][j])) + r"\,") + f"b_{j + 1}^*"}
                     for j in range(i)]
            steps.append({"i": i + 1, "mu": terms, "bs": fvec(bs[i]), "B": fr(B[i])})
        zero = [rf"\mu_{{{i + 1}{j + 1}}} = 0" for i in range(n) for j in range(i) if mu[i][j] == 0]
        return {"n": n, "basis": [ivec(r) for r in a], "a": a, "steps": steps, "gs": gs_tex(a, gs),
                "ortho": [[j + 1, i + 1] for i in range(n) for j in range(i)],
                "d": abs(d), "prodB": fr(math.prod(B)),
                "zero_mu": ",\\ ".join(zero),
                "answer": {"mu": {f"{i + 1}{j + 1}": mu[i][j] for i in range(n) for j in range(i)},
                           "B": B, "det": abs(d)}}

    def check(self, p):
        from sage.all import QQ, matrix

        a = p["a"]
        G, M = matrix(QQ, a).gram_schmidt()  # a = M * G, rows of G orthogonal
        n = len(a)
        B = [Fraction(x) for x in p["answer"]["B"]]
        for i in range(n):
            assert Fraction(str(G.row(i) * G.row(i))) == B[i]
            for j in range(i):
                assert Fraction(str(M[i, j])) == Fraction(p["answer"]["mu"][f"{i + 1}{j + 1}"])
        assert math.prod(B) == p["answer"]["det"] ** 2 == abs(int(matrix(QQ, a).det())) ** 2


# --- LLL ------------------------------------------------------------------------------


def _unimodular_ops(rng, b, nops: int, lower_only: bool):
    """Apply nops random operations b_i += c b_j (c = +-1, +-2); lower_only: j < i only."""
    n = len(b)
    b = [list(r) for r in b]
    for _ in range(nops):
        i, j = rng.sample(range(n), 2)
        if lower_only and j > i:
            i, j = j, i
        c = rng.choice([-2, -1, 1, 2])
        b[i] = [x + c * y for x, y in zip(b[i], b[j])]
    return b


class _LLL(Task):
    topics = ("lattices.lll",)
    solution_detail = SolutionDetail.FULL
    statement = (r"Применить алгоритм LLL с параметром $\delta = \tfrac34$ к базису " + BASIS_STMT +
                 r" решётки $\mathcal{L} \subset \mathbb{Z}^{\VAR{n}}$. Привести трассу: на каждом шаге "
                 r"уменьшение размера $b_k$, проверку условия Ловаса и обмен (если он нужен).")
    solution = (GS_MACRO +
                r"Условие Ловаса: $B_k \ge (\tfrac34 - \mu_{k,k-1}^2)\,B_{k-1}$; уменьшение размера: "
                r"$b_k \gets b_k - q\,b_j$, $q = \lfloor \mu_{kj} \rceil$ для $j = k - 1, \dots, 1$ "
                r"(при $|\mu_{kj}| \le \tfrac12$ полагаем $q = 0$). Исходная ортогонализация:"
                r"\VAR{gstable(gs0)}"
                r"\begin{enumerate}"
                r"\BLOCK{for s in steps}\item $k = \VAR{s.k}$. "
                r"\BLOCK{for r in s.red}$\mu_{\VAR{s.k}\VAR{r.j}} = \VAR{r.mu}$, $q = \VAR{r.q}$"
                r"\BLOCK{if not loop.last}; \BLOCK{else}. \BLOCK{endif}\BLOCK{endfor}"
                r"\BLOCK{if s.comb}$b_{\VAR{s.k}} \gets \VAR{s.comb} = \VAR{s.bk}$, "
                r"$\mu_{\VAR{s.k}\VAR{s.k - 1}} = \VAR{s.mu}$. \BLOCK{endif}"
                r"Ловас: $B_{\VAR{s.k}} = \VAR{s.Bk}\ \BLOCK{if s.ok}\ge\BLOCK{else}<\BLOCK{endif}\ "
                r"\bigl(\tfrac34 - \VAR{s.mu2}\bigr) \cdot \VAR{s.Bk1} = \VAR{s.rhs}$"
                r"\BLOCK{if s.ok} "
                r"--- выполнено, $k \gets \VAR{s.k_next}$.\BLOCK{else} --- нарушено: "
                r"$b_{\VAR{s.k - 1}} \leftrightarrow b_{\VAR{s.k}}$, $k \gets \VAR{s.k_next}$. "
                r"Базис: \BLOCK{for v in s.basis}$\VAR{v}$\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}; "
                r"новая ортогонализация: "
                r"\BLOCK{for r in s.gs.rows}$B_{\VAR{r.i}} = \VAR{r.B}$, \BLOCK{endfor}"
                r"\BLOCK{for m in s.gs.mu}$\mu_{\VAR{m.i}\VAR{m.j}} = \VAR{m.v}$\BLOCK{if not loop.last}, "
                r"\BLOCK{else}.\BLOCK{endif}\BLOCK{endfor}"
                r"\BLOCK{endif}"
                r"\BLOCK{endfor}"
                r"\end{enumerate}"
                r"Шагов: $\VAR{steps|length}$, обменов: $\VAR{nswaps}$."
                r"\BLOCK{if nswaps == 0} Обменов не было: \BLOCK{if nred == 0}базис уже был LLL-приведённым"
                r"\BLOCK{else}условие Ловаса выполнялось сразу, понадобилось только уменьшение размера"
                r"\BLOCK{endif}.\BLOCK{endif} "
                r"Приведённый базис и его ортогонализация:"
                r"\VAR{gstable(gs1)}"
                r"\par Проверка: $\det \mathcal{L} = \VAR{d}$ не изменился ($B_1 \cdots B_{\VAR{n}} = \VAR{d}^2$); "
                r"$\|b_1\|^2 = \VAR{n1} \le 2^{\VAR{n - 1}} \lambda_1(\mathcal{L})^2$."
                r"\[\BLOCK{for v in basis1}b_{\VAR{loop.index}} = \VAR{v}\BLOCK{if not loop.last},\quad "
                r"\BLOCK{endif}\BLOCK{endfor}.\]")

    def accept(self, tr, gsmax: int) -> bool:
        c = self.cfg
        nsw = sum(not s["ok"] for s in tr["steps"])
        return (c.min_steps <= len(tr["steps"]) <= c.max_steps and c.min_swaps <= nsw <= c.max_swaps
                and gsmax <= c.maxden)

    def sample(self, rng):
        c = self.cfg
        n = c.n
        while True:
            r = [[rng.randint(-c.entry, c.entry) for _ in range(n)] for _ in range(n)]
            if det(r) == 0 or not 1 < abs(det(r)) <= c.maxdet:
                continue
            r = lll_trace(r)["basis"]
            if max(abs(x) for v in r for x in v) > c.entry:
                continue
            nops = rng.randint(c.min_ops, c.max_ops)
            b = _unimodular_ops(rng, r, nops, lower_only=c.noswap)
            if c.reverse:
                b = b[::-1]
            if max(abs(x) for v in b for x in v) > c.max_entry:
                continue
            tr = lll_trace(b)
            gss = [gram_schmidt(b)] + [s["gs"] for s in tr["steps"] if "gs" in s]
            den = max(max(_maxden(g) for g in gss),
                      max(Fraction(x["mu"]).denominator for s in tr["steps"] for x in s["red"]),
                      max(Fraction(s["rhs"]).denominator for s in tr["steps"]))
            if self.accept(tr, den):
                break
        steps = []
        for s in tr["steps"]:
            st = {"k": s["k"], "red": [{"j": x["j"], "mu": fr(x["mu"]), "q": x["q"]} for x in s["red"]],
                  "comb": comb_tex(s["k"], s["ops"]) if s["ops"] else "", "bk": ivec(s["bk"]),
                  "mu": fr(s["mu"]), "mu2": sq(s["mu"]),
                  "Bk": fr(s["Bk"]), "Bk1": frp(s["Bk1"]), "rhs": fr(s["rhs"]), "ok": s["ok"],
                  "k_next": s["k_next"], "basis": [ivec(v) for v in s["basis"]]}
            if "gs" in s:
                st["gs"] = gs_tex(s["basis"], s["gs"])
            steps.append(st)
        res = tr["basis"]
        return {"n": n, "b": b, "basis": [ivec(v) for v in b], "gs0": gs_tex(b, gram_schmidt(b)),
                "steps": steps, "nswaps": sum(not s["ok"] for s in tr["steps"]),
                "nred": sum(len(s["ops"]) for s in tr["steps"]),
                "gs1": gs_tex(res, gram_schmidt(res)), "basis1": [ivec(v) for v in res],
                "d": abs(det(b)), "n1": _dot(res[0], res[0]), "answer": res}

    def check(self, p):
        from sage.all import QQ, ZZ, matrix

        b, res, n = p["b"], p["answer"], p["n"]
        A, R = matrix(ZZ, b), matrix(ZZ, res)
        # reduced (Sage's own test), same lattice (unimodular transition matrix)
        assert R.is_LLL_reduced(delta=QQ(3) / 4, eta=QQ(1) / 2) and is_lll_reduced(res)
        U = R * A.inverse()
        assert all(x in ZZ for x in U.list()) and abs(U.det()) == 1
        # Sage's LLL gives a (possibly different) reduced basis of the same lattice
        S = A.LLL(delta=QQ(3) / 4)
        V = R * S.inverse()
        assert all(x in ZZ for x in V.list()) and abs(V.det()) == 1
        # ||b_1||^2 <= 2^(n-1) lambda_1^2, via min_i B_i of the result (Sage GS)
        G, _ = matrix(QQ, R).gram_schmidt()
        lam2_lower = min(G.row(i) * G.row(i) for i in range(n))
        assert p["n1"] == int(R.row(0) * R.row(0)) <= 2 ** (n - 1) * lam2_lower
        assert abs(A.det()) == p["d"]
        c = self.cfg
        assert c.min_steps <= len(p["steps"]) <= c.max_steps
        assert c.min_swaps <= p["nswaps"] <= c.max_swaps
        assert p["steps"][-1]["k_next"] == n + 1


_LLL3 = {"n": 3, "entry": 3, "maxdet": 40, "max_entry": 20, "maxden": 150, "min_ops": 2, "max_ops": 4,
         "noswap": False, "reverse": False, "min_steps": 4, "max_steps": 10, "min_swaps": 1,
         "max_swaps": 4}


class LLL(_LLL):
    id = "lattices.lll"
    title_ru = "Алгоритм LLL (размерность 3)"
    complexity = 3
    notes = ("delta = 3/4, a 3x3 basis a few unimodular operations away from a reduced one. "
             "Presets: default (4-10 steps, 1-4 swaps), noswap (corner case: only size reduction, "
             "or an already LLL-reduced basis), swaps (corner case: 4-6 swaps, up to 14 steps).")
    presets = {
        "default": _LLL3,
        "noswap": {"min_ops": 0, "max_ops": 3, "noswap": True, "min_steps": 2, "max_steps": 2,
                   "min_swaps": 0, "max_swaps": 0},
        "swaps": {"min_ops": 2, "max_ops": 5, "reverse": True, "min_steps": 8, "max_steps": 14,
                  "min_swaps": 4, "max_swaps": 6, "max_entry": 25},
    }


class LLL2(_LLL):
    id = "lattices.lll_2d"
    title_ru = "Алгоритм LLL (размерность 2)"
    complexity = 2
    notes = "Warm-up: delta = 3/4 in dimension 2 (compare with the Gauss reduction)."
    presets = {"default": {**_LLL3, "n": 2, "entry": 5, "maxdet": 40, "max_entry": 40, "min_ops": 2,
                           "max_ops": 5, "min_steps": 2, "max_steps": 8, "min_swaps": 1, "max_swaps": 4,
                           "maxden": 400}}
