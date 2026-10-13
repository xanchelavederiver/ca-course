"""2-dimensional lattices: CVP (Babai) and SVP (Gauss) (ported from main-2sem.py).

"Good" bases have Hadamard ratio HR > 0.9, "bad" ones HR < 0.4. Instances
where the intended method (Babai on the given basis for the good one, Babai
after Gauss reduction for the bad one) does not give the true closest vector
are rejected.
"""

import math

from taskgen.core import steps
from taskgen.core.task import SolutionDetail, Task

TX = r"\BLOCK{import 'macros.tex.j2' as tx}"
BASIS = (r"В решётке $\mathcal{L}$, заданной базисными векторами "
         r"\[v_1 = \begin{pmatrix}\VAR{v[0][0]} \\ \VAR{v[0][1]}\end{pmatrix}, "
         r"v_2 = \begin{pmatrix}\VAR{v[1][0]} \\ \VAR{v[1][1]}\end{pmatrix},\] ")
HR = (r"$\det \mathcal{L} = \VAR{det}$, $HR(\mathcal{L}) = \left(\frac{|\det\mathcal{L}|}"
      r"{\|v_1\|\|v_2\|}\right)^{1/2} = \VAR{hr}$ --- базис \BLOCK{if hr|float > 0.9}хороший (почти "
      r"ортогональный)\BLOCK{else}плохой\BLOCK{endif}.")
BABAI = (r"Решаем $w = t_1 u_1 + t_2 u_2$ (правило Крамера): $t_1 = \frac{\VAR{bb.t1_frac[0]}}{\VAR{bb.t1_frac[1]}} "
         r"\approx \VAR{bb.t1}$, $t_2 = \frac{\VAR{bb.t2_frac[0]}}{\VAR{bb.t2_frac[1]}} \approx \VAR{bb.t2}$; "
         r"округляем: $\VAR{bb.c1} u_1 \VAR{bb.c2|signed} u_2 = (\VAR{bb.r[0]}, \VAR{bb.r[1]})^T$, "
         r"$\|w - r\| \approx \VAR{bb.dist}$.")


def hadamard_ratio(v) -> float:
    det = abs(v[0][0] * v[1][1] - v[0][1] * v[1][0])
    return math.sqrt(det / (math.hypot(*v[0]) * math.hypot(*v[1])))


def gen_basis(rng, good: bool):
    """Random integer basis with entries in [-100, 100) and the requested HR (legacy gen_lattice)."""
    while True:
        v = [[rng.randrange(-100, 100) for _ in range(2)] for _ in range(2)]
        if v[0][0] * v[1][1] - v[0][1] * v[1][0] == 0:
            continue
        hr = hadamard_ratio(v)
        if (good and hr > 0.9) or (not good and hr < 0.4):
            return v, hr


def _lattice(v):
    from sage.all import ZZ, matrix
    from sage.modules.free_module_integer import IntegerLattice

    return IntegerLattice(matrix(ZZ, v), lll_reduce=False)


def _in_lattice(v, r) -> bool:
    """r is an integer combination of the rows of v (Cramer's rule)."""
    det = v[0][0] * v[1][1] - v[0][1] * v[1][0]
    c1 = r[0] * v[1][1] - r[1] * v[1][0]
    c2 = v[0][0] * r[1] - v[0][1] * r[0]
    return c1 % det == 0 and c2 % det == 0


def _det(v):
    return v[0][0] * v[1][1] - v[0][1] * v[1][0]


class _Babai(Task):
    topics = ("lattices.cvp",)
    solution_detail = SolutionDetail.FULL
    good: bool
    statement = BASIS + r"найти вектор, ближайший к вектору $w = (\VAR{w[0]}, \VAR{w[1]})^T$."
    solution = (TX + HR +
                r"\BLOCK{if not good} Алгоритм Бабаи на плохом базисе даёт далёкий вектор "
                r"(для исходного базиса получилось бы $(\VAR{bb0.r[0]}, \VAR{bb0.r[1]})^T$, "
                r"$\|w - r\| \approx \VAR{bb0.dist}$), поэтому сначала редуцируем базис. "
                r"\VAR{tx.gauss_table(gr)}"
                r"Редуцированный базис $u_1 = (\VAR{gr.v1[0]}, \VAR{gr.v1[1]})^T$, "
                r"$u_2 = (\VAR{gr.v2[0]}, \VAR{gr.v2[1]})^T$, $HR = \VAR{hr_red}$."
                r"\BLOCK{else} Применяем алгоритм Бабаи к исходному базису $u_i = v_i$.\BLOCK{endif} "
                + BABAI +
                r"\[r = (\VAR{answer[0]}, \VAR{answer[1]})^T,\quad HR(\mathcal{L}) = \VAR{hr}.\]")

    def sample(self, rng):
        while True:
            v, hr = gen_basis(rng, self.good)
            w = [rng.randrange(-100, 100) for _ in range(2)]
            cv = _lattice(v).closest_vector(w)
            cv = [int(cv[0]), int(cv[1])]
            bb0 = steps.babai(v, w)
            if self.good:
                gr, basis, hr_red = None, v, None
            else:
                gr = steps.gauss_reduce(v[0], v[1])
                basis = [gr["v1"], gr["v2"]]
                hr_red = f"{hadamard_ratio(basis):.3f}"
            bb = steps.babai(basis, w)
            if bb["r"] == cv:
                return {"v": v, "w": w, "det": _det(v), "hr": f"{hr:.3f}", "good": self.good,
                        "bb0": bb0, "gr": gr, "hr_red": hr_red, "bb": bb, "answer": cv}

    def check(self, p):
        assert _in_lattice(p["v"], p["answer"]) and p["bb"]["r"] == p["answer"]
        d = math.dist(p["answer"], p["w"])
        for i in range(-3, 4):
            for j in range(-3, 4):
                u = [p["answer"][k] + i * p["v"][0][k] + j * p["v"][1][k] for k in range(2)]
                assert math.dist(u, p["w"]) >= d - 1e-9


class BabaiEasy(_Babai):
    id = "lattices.babai_easy"
    title_ru = "Ближайший вектор: алгоритм Бабаи (хороший базис)"
    complexity = 1
    good = True


class BabaiHard(_Babai):
    id = "lattices.babai_hard"
    title_ru = "Ближайший вектор: алгоритм Бабаи (плохой базис)"
    complexity = 3
    good = False


class GaussReduction(Task):
    id = "lattices.gauss"
    title_ru = "Кратчайший вектор: метод Гаусса"
    topics = ("lattices.svp",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    statement = BASIS + r"найти кратчайший вектор методом Гаусса."
    solution = (TX + HR + r" \VAR{tx.gauss_table(gr)}"
                r"Кратчайший вектор --- $v_1$ последней строки, $\|v_1\|^2 = \VAR{gr.rows[-1].n1}$."
                r"\[r = \pm(\VAR{answer[0]}, \VAR{answer[1]})^T,\quad HR(\mathcal{L}) = \VAR{hr}.\]")

    def sample(self, rng):
        v, hr = gen_basis(rng, good=False)
        gr = steps.gauss_reduce(v[0], v[1])
        sv = _lattice(v).shortest_vector()
        assert int(sv[0]) ** 2 + int(sv[1]) ** 2 == gr["rows"][-1]["n1"]
        return {"v": v, "det": _det(v), "hr": f"{hr:.3f}", "gr": gr, "answer": gr["v1"]}

    def check(self, p):
        assert _in_lattice(p["v"], p["answer"]) and any(p["answer"])
        n2 = p["answer"][0] ** 2 + p["answer"][1] ** 2
        for i in range(-5, 6):
            for j in range(-5, 6):
                if i or j:
                    u = [i * p["v"][0][k] + j * p["v"][1][k] for k in range(2)]
                    assert u[0] ** 2 + u[1] ** 2 >= n2
