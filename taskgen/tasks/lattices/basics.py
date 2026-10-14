"""Lattice basics (lecture sem2/11): determinant, Hadamard ratio, change of basis;
Babai rounding with a good and a bad basis of the same lattice.

Bases are written by rows: B = (v_1; ...; v_n), L(B) = {xB : x in Z^n}; two bases
generate the same lattice iff B' = U B with U in GL_n(Z) (integral, det U = +-1).
"""

import math
from fractions import Fraction

from taskgen.core import steps
from taskgen.core.task import SolutionDetail, Task
from taskgen.tasks.lattices.lattices_2d import hadamard_ratio

# --- small exact linear algebra (pure Python, rows = vectors) ------------------------------


def det(m) -> int:
    if len(m) == 2:
        return m[0][0] * m[1][1] - m[0][1] * m[1][0]
    return sum((-1) ** j * m[0][j] * det([r[:j] + r[j + 1:] for r in m[1:]]) for j in range(len(m)))


def adjugate(m):
    """adj(M) = transposed cofactor matrix, M adj(M) = det(M) I."""
    n = len(m)
    if n == 2:
        return [[m[1][1], -m[0][1]], [-m[1][0], m[0][0]]]
    cof = [[(-1) ** (i + j) * det([r[:j] + r[j + 1:] for k, r in enumerate(m) if k != i])
            for j in range(n)] for i in range(n)]
    return [[cof[j][i] for j in range(n)] for i in range(n)]


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))]
            for i in range(len(a))]


def frac_tex(x: Fraction) -> str:
    if x.denominator == 1:
        return str(x.numerator)
    sign = "-" if x < 0 else ""
    return rf"{sign}\tfrac{{{abs(x.numerator)}}}{{{x.denominator}}}"


def pmatrix(m) -> str:
    rows = [" & ".join(frac_tex(Fraction(x)) if isinstance(x, Fraction) else str(x) for x in r)
            for r in m]
    return r"\begin{pmatrix}" + r" \\ ".join(rows) + r"\end{pmatrix}"


def vec_tex(v) -> str:
    return "(" + ", ".join(str(x) for x in v) + ")"


def hr_n(b) -> float:
    """Hadamard ratio (|det B| / prod ||v_i||)^(1/n)."""
    n = len(b)
    return (abs(det(b)) / math.prod(math.sqrt(sum(x * x for x in v)) for v in b)) ** (1 / n)


def random_unimodular(rng, n: int, ops: int = 3, mult: int = 2):
    """Product of `ops` random elementary row operations (+ an optional sign flip / swap)."""
    u = [[int(i == j) for j in range(n)] for i in range(n)]
    for _ in range(ops):
        i, j = rng.sample(range(n), 2)
        c = rng.choice([c for c in range(-mult, mult + 1) if c])
        u[i] = [u[i][k] + c * u[j][k] for k in range(n)]
    if rng.random() < 0.3:
        i = rng.randrange(n)
        u[i] = [-x for x in u[i]]
    if rng.random() < 0.3:
        i, j = rng.sample(range(n), 2)
        u[i], u[j] = u[j], u[i]
    return u


def _par(x) -> str:
    return f"({x})" if x < 0 else str(x)


def det_expr(m) -> str:
    """The expansion of det M as a TeX product sum (along the first row for n = 3)."""
    if len(m) == 2:
        return rf"{m[0][0]} \cdot {_par(m[1][1])} - {_par(m[0][1])} \cdot {_par(m[1][0])}"
    minors = [det([r[:j] + r[j + 1:] for r in m[1:]]) for j in range(3)]
    return (rf"{m[0][0]} \cdot {_par(minors[0])} - {_par(m[0][1])} \cdot {_par(minors[1])} + "
            rf"{_par(m[0][2])} \cdot {_par(minors[2])}")


def _maxabs(m) -> int:
    return max(abs(x) for r in m for x in r)


def _is_signed_permutation(u) -> bool:
    return all(sum(x != 0 for x in r) == 1 for r in u)


def _hnf(m):
    from sage.all import ZZ, matrix

    return matrix(ZZ, m).echelon_form()


# --- determinant, Hadamard ratio, change of basis ------------------------------------------


class DeterminantHadamard(Task):
    id = "lattices.determinant_hadamard"
    title_ru = "Определитель решётки, коэффициент Адамара, смена базиса"
    topics = ("lattices.svp",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("Three cases: B' = U B with U unimodular (same lattice, det U = -1 allowed); "
             "U integral with det U = +-2 (a sublattice of index 2); |det B'| = |det B| but U "
             "non-integral (a different lattice with the same determinant: equal determinants "
             "do not suffice). Dimension 2 or 3.")
    presets = {"default": {"dims": [2, 2, 3], "case_weights": [4, 3, 3],
                           "entry": {2: 7, 3: 3}, "entry_p": {2: 30, 3: 12}}}
    statement = (r"Решётка $L \subset \mathbb{R}^{\VAR{n}}$ порождена строками матрицы "
                 r"\[B = \VAR{B_tex}.\] Найти $\det L$ и коэффициент Адамара $\mathcal{H}(B)$ этого "
                 r"базиса. Порождают ли строки матрицы \[B' = \VAR{Bp_tex}\] ту же решётку? Найти матрицу "
                 r"перехода $U$, $B' = UB$.")
    solution = (r"$\det B = \VAR{det_expr} = \VAR{d}$, "
                r"$\det L = |\det B| = \VAR{d|abs}$. Длины: "
                r"\BLOCK{for v in B}$\|v_{\VAR{loop.index}}\| = \sqrt{\VAR{norms2[loop.index0]}} "
                r"\approx \VAR{norms[loop.index0]}$\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}; "
                r"\[\mathcal{H}(B) = \left(\frac{\det L}{\BLOCK{for v in B}\|v_{\VAR{loop.index}}\|\BLOCK{endfor}}"
                r"\right)^{1/\VAR{n}} \approx \VAR{hr}.\]"
                r"Для $B'$: $\det B' = \VAR{dp}$. "
                r"Матрица перехода $U = B' B^{-1} = \frac{1}{\det B} B' \operatorname{adj} B$, где "
                r"\[\operatorname{adj} B = \VAR{adj_tex},\] "
                r"\[U = \BLOCK{if d < 0}-\BLOCK{endif}\frac{1}{\VAR{d|abs}}\VAR{num_tex} = \VAR{U_tex},\] "
                r"$\det U = \det B' / \det B = \VAR{detU_tex}$. "
                r"\BLOCK{if case == 'same'}Матрица $U$ целочисленная и $\det U = \pm 1$, т.\,е. $U \in "
                r"\mathrm{GL}_{\VAR{n}}(\mathbb{Z})$: строки $B'$ порождают \textbf{ту же} решётку "
                r"(и $B = U^{-1} B'$ с целочисленной $U^{-1}$).\BLOCK{elif case == 'index'}"
                r"Матрица $U$ целочисленная, поэтому $L(B') \subseteq L$, но $\det U = \VAR{detU_tex} \ne \pm 1$: "
                r"$L(B')$ "
                r"--- \textbf{собственная подрешётка} индекса $|\det U| = \VAR{detU|abs}$ "
                r"(например, $v_{\VAR{miss + 1}} = \VAR{miss_vec}$ не лежит в $L(B')$).\BLOCK{else}"
                r"Хотя $|\det B'| = |\det B|$, матрица $U$ не целочисленная: $L(B') \ne L$ --- это \textbf{другая} "
                r"решётка с тем же определителем (например, строка $v'_{\VAR{miss + 1}}$ матрицы $B'$ не лежит "
                r"в $L$).\BLOCK{endif}"
                r"\[\det L = \VAR{d|abs},\quad \mathcal{H}(B) \approx \VAR{hr},\quad L(B') \BLOCK{if same}= "
                r"L\BLOCK{else}\ne L\BLOCK{endif}.\]")

    def sample(self, rng):
        n = rng.choice(self.cfg.dims)
        e, ep = self.cfg.entry[n], self.cfg.entry_p[n]
        case = rng.choices(["same", "index", "other"], weights=self.cfg.case_weights)[0]
        while True:
            if case == "other":
                c = [[rng.randint(-2, 2) for _ in range(n)] for _ in range(n)]
                if det(c) == 0:
                    continue
                k = rng.choice([2, 2, 3])
                d1 = [[(k if i == j == 0 else int(i == j)) for j in range(n)] for i in range(n)]
                d2 = [[(k if i == j == 1 else int(i == j)) for j in range(n)] for i in range(n)]
                b = matmul(random_unimodular(rng, n, 2, 1), matmul(d1, c))
                bp = matmul(random_unimodular(rng, n, 2, 1), matmul(d2, c))
            else:
                b = [[rng.randint(-e, e) for _ in range(n)] for _ in range(n)]
                if det(b) == 0 or any(not any(v) for v in b):
                    continue
                u = random_unimodular(rng, n, rng.randint(2, 3), 2)
                if case == "index":
                    t = rng.randrange(n)
                    two = [[(2 if i == j == t else int(i == j)) for j in range(n)] for i in range(n)]
                    u = matmul(random_unimodular(rng, n, 1, 1), matmul(two, u))
                bp = matmul(u, b)
            d, dp = det(b), det(bp)
            if not (2 <= abs(d) <= (60 if n == 2 else 40)) or _maxabs(b) > e + (2 if case == "other" else 0):
                continue
            if _maxabs(bp) > ep or b == bp or any(not any(v) for v in bp):
                continue
            adj = adjugate(b)
            num = matmul(bp, adj)
            umat = [[Fraction(x, d) for x in r] for r in num]
            if case == "same" and _is_signed_permutation(umat):
                continue
            break
        same = case == "same"
        detu = Fraction(dp, d)
        # a witness of L(B') != L: for "index" a row of B not in L(B'), for "other" a row of B' not in L
        miss, miss_vec = None, None
        if case == "index":
            inv_u = [[Fraction(x, dp) for x in r] for r in matmul(b, adjugate(bp))]  # B B'^{-1}
            miss = next(i for i, r in enumerate(inv_u) if any(x.denominator != 1 for x in r))
            miss_vec = vec_tex(b[miss])
        elif case == "other":
            miss = next(i for i, r in enumerate(umat) if any(x.denominator != 1 for x in r))
        norms2 = [sum(x * x for x in v) for v in b]
        ctx = {
            "n": n, "B": b, "Bp": bp, "case": case, "same": same, "d": d, "dp": dp,
            "det_expr": det_expr(b),
            "norms2": norms2, "norms": [f"{math.sqrt(x):.3f}" for x in norms2],
            "hr": f"{hr_n(b):.3f}", "B_tex": pmatrix(b), "Bp_tex": pmatrix(bp),
            "adj_tex": pmatrix(adj), "num_tex": pmatrix(num), "U_tex": pmatrix(umat),
            "U": [[str(x) for x in r] for r in umat], "detU": int(detu) if detu.denominator == 1 else None,
            "detU_tex": frac_tex(detu), "miss": miss, "miss_vec": miss_vec,
        }
        ctx["answer"] = {"det": abs(d), "hr": ctx["hr"], "same": same}
        return ctx

    def check(self, p):
        b, bp, ans = p["B"], p["Bp"], p["answer"]
        n = len(b)
        from sage.all import QQ, ZZ, matrix

        mb, mbp = matrix(ZZ, b), matrix(ZZ, bp)
        assert ans["det"] == abs(mb.det()) > 0
        # Hadamard ratio via the Gram matrix: det L = sqrt(det(B B^T))
        gram = mb * mb.transpose()
        hr = (math.sqrt(float(gram.det())) / math.prod(math.sqrt(float(gram[i, i])) for i in range(n))) ** (1 / n)
        assert abs(hr - float(ans["hr"])) < 2e-3 and 0 < hr <= 1 + 1e-9
        # same lattice <=> equal Hermite normal forms
        assert ans["same"] == (_hnf(b) == _hnf(bp))
        u = mbp * mb.change_ring(QQ).inverse()
        assert [[str(x) for x in r] for r in u.rows()] == p["U"]
        integral = all(x in ZZ for x in u.list())
        if p["case"] == "same":
            assert integral and abs(u.det()) == 1
        elif p["case"] == "index":
            assert integral and abs(u.det()) == 2
        else:
            assert not integral and abs(u.det()) == 1


# --- Babai rounding: a good basis vs a bad basis of the same lattice ------------------------


class BabaiCompare(Task):
    id = "lattices.babai_compare"
    title_ru = "Алгоритм Бабаи: хороший и плохой базисы одной решётки"
    topics = ("lattices.cvp",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Bad basis = U * good basis with a unimodular U; only instances where rounding in the "
             "good basis gives the closest vector and rounding in the bad one gives a different "
             "(farther) lattice vector are kept.")
    presets = {"default": {"good_entry": 25, "w_box": 150, "bad_entry": 400}}
    statement = (r"Решётка $L \subset \mathbb{R}^2$ задана базисом $v_1 = \VAR{rows.G_0}$, "
                 r"$v_2 = \VAR{rows.G_1}$. Проверить, что $u_1 = \VAR{rows.B_0}$, $u_2 = \VAR{rows.B_1}$ "
                 r"--- тоже базис $L$. Применить алгоритм Бабаи (округление координат) к вектору "
                 r"$w = \VAR{rows.w}$ сначала в базисе $\{v_1, v_2\}$, затем в базисе $\{u_1, u_2\}$; сравнить "
                 r"расстояния $\|w - r\|$ и коэффициенты Адамара базисов. Какой из найденных векторов ближе к $w$?")
    solution = (r"Выражаем $u_i$ через $v_1, v_2$ (правило Крамера): $u_1 = \VAR{U[0][0]} v_1 \VAR{U[0][1]|signed} v_2$, "
                r"$u_2 = \VAR{U[1][0]} v_1 \VAR{U[1][1]|signed} v_2$, "
                r"матрица перехода $U$ целочисленная и $\det U = \VAR{detU_expr} = \VAR{detU}$, т.\,е. $U \in \mathrm{GL}_2(\mathbb{Z})$ и базисы порождают одну решётку; "
                r"$\det L = \VAR{d|abs}$. "
                r"Коэффициенты Адамара: $\mathcal{H}(v_1, v_2) = \VAR{hr_g}$ (хороший базис), "
                r"$\mathcal{H}(u_1, u_2) = \VAR{hr_b}$ (плохой базис)."
                r"\par \textbf{Базис $\{v_1, v_2\}$.} Решаем $w = t_1 v_1 + t_2 v_2$ (правило Крамера): "
                r"$t_1 = \frac{\VAR{bg.t1_frac[0]}}{\VAR{bg.t1_frac[1]}} \approx \VAR{bg.t1}$, "
                r"$t_2 = \frac{\VAR{bg.t2_frac[0]}}{\VAR{bg.t2_frac[1]}} \approx \VAR{bg.t2}$; "
                r"$r = \VAR{bg.c1} v_1 \VAR{bg.c2|signed} v_2 = \VAR{rows.bg_r}$, "
                r"$\|w - r\| \approx \VAR{bg.dist}$."
                r"\par \textbf{Базис $\{u_1, u_2\}$.} $w = s_1 u_1 + s_2 u_2$: "
                r"$s_1 = \frac{\VAR{bb.t1_frac[0]}}{\VAR{bb.t1_frac[1]}} \approx \VAR{bb.t1}$, "
                r"$s_2 = \frac{\VAR{bb.t2_frac[0]}}{\VAR{bb.t2_frac[1]}} \approx \VAR{bb.t2}$; "
                r"$r' = \VAR{bb.c1} u_1 \VAR{bb.c2|signed} u_2 = \VAR{rows.bb_r}$, "
                r"$\|w - r'\| \approx \VAR{bb.dist}$."
                r"\par Ошибка округления $w - r = \sum_i (t_i - \lfloor t_i \rceil) b_i$ с "
                r"$|t_i - \lfloor t_i \rceil| \le \frac12$ ограничена величиной $\frac12(\|b_1\| + \|b_2\|)$: "
                r"$\approx \VAR{bound_g}$ для $\{v_1, v_2\}$ и $\approx \VAR{bound_b}$ для длинных почти "
                r"параллельных $u_1, u_2$. Вектор $r$ ближе к $w$, и это ближайший вектор решётки "
                r"(сравните с $r \pm v_1$, $r \pm v_2$, $r \pm v_1 \pm v_2$); $r' = r \VAR{diff_g[0]|signed} v_1 "
                r"\VAR{diff_g[1]|signed} v_2$ --- другой, далёкий вектор."
                r"\[\begin{aligned} r &= \VAR{rows.answer_good}, & \|w - r\| &\approx \VAR{bg.dist};\\ "
                r"r' &= \VAR{rows.answer_bad}, & \|w - r'\| &\approx \VAR{bb.dist}.\end{aligned}\]")

    def sample(self, rng):
        cfg = self.cfg
        while True:
            g = [[rng.randint(-cfg.good_entry, cfg.good_entry) for _ in range(2)] for _ in range(2)]
            d = det(g)
            if abs(d) < 50 or hadamard_ratio(g) <= 0.9:
                continue
            u = random_unimodular(rng, 2, 3, 3)
            b = matmul(u, g)
            if _maxabs(b) > cfg.bad_entry or hadamard_ratio(b) >= 0.35:
                continue
            w = [rng.randint(-cfg.w_box, cfg.w_box) for _ in range(2)]
            bg, bb = steps.babai(g, w), steps.babai(b, w)
            cv = _closest(g, w)
            if bg["r"] != cv or bb["r"] == cv:
                continue
            # coordinates of r' - r in the good basis
            diff = [bb["r"][0] - bg["r"][0], bb["r"][1] - bg["r"][1]]
            dg = [Fraction(diff[0] * g[1][1] - diff[1] * g[1][0], d),
                  Fraction(g[0][0] * diff[1] - g[0][1] * diff[0], d)]
            nb = [math.hypot(*v) for v in g], [math.hypot(*v) for v in b]
            rows = {"G_0": vec_tex(g[0]), "G_1": vec_tex(g[1]), "B_0": vec_tex(b[0]),
                    "B_1": vec_tex(b[1]), "w": vec_tex(w), "bg_r": vec_tex(bg["r"]),
                    "bb_r": vec_tex(bb["r"]), "answer_good": vec_tex(bg["r"]),
                    "answer_bad": vec_tex(bb["r"])}
            return {"G": g, "B": b, "U": u, "detU": det(u), "detU_expr": det_expr(u), "d": d,
                    "w": w, "bg": bg, "bb": bb, "rows": rows,
                    "hr_g": f"{hadamard_ratio(g):.3f}", "hr_b": f"{hadamard_ratio(b):.3f}",
                    "bound_g": f"{sum(nb[0]) / 2:.1f}", "bound_b": f"{sum(nb[1]) / 2:.1f}",
                    "diff_g": [int(dg[0]), int(dg[1])],
                    "answer": {"good": bg["r"], "bad": bb["r"], "closest": cv}}

    def check(self, p):
        g, b, w, ans = p["G"], p["B"], p["w"], p["answer"]
        assert matmul(p["U"], g) == b and abs(det(p["U"])) == 1
        # independent: brute-force search around the answer in the good basis
        best = math.dist(ans["closest"], w)
        for i in range(-4, 5):
            for j in range(-4, 5):
                v = [ans["closest"][k] + i * g[0][k] + j * g[1][k] for k in range(2)]
                assert math.dist(v, w) >= best - 1e-9
        assert ans["good"] == ans["closest"] and ans["bad"] != ans["closest"]
        # r' is a lattice vector of L(G) (coordinates are integers)
        diff = [ans["bad"][0] - ans["good"][0], ans["bad"][1] - ans["good"][1]]
        assert diff == [p["diff_g"][0] * g[0][k] + p["diff_g"][1] * g[1][k] for k in range(2)]
        assert math.dist(ans["bad"], w) > best


def _closest(g, w):
    from sage.all import ZZ, matrix
    from sage.modules.free_module_integer import IntegerLattice

    cv = IntegerLattice(matrix(ZZ, g), lll_reduce=False).closest_vector(w)
    return [int(cv[0]), int(cv[1])]
