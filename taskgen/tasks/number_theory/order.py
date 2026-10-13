"""Order of an element of (Z/pZ)^* (ported from main-{1,2}sem.py).

Primitive roots (order p - 1) are allowed.
"""

from taskgen.core import steps
from taskgen.core.nt import factorize, first_primes, is_order
from taskgen.core.task import SolutionDetail, Task


def mult_order(g: int, p: int) -> int:
    from sage.all import Mod

    return int(Mod(g, p).multiplicative_order())


def successive_reduction(g: int, p: int) -> list[dict]:
    """o = p - 1; for every prime q | o: while g^{o/q} = 1, o /= q."""
    o, tests = p - 1, []
    for q, e in sorted(factorize(p - 1).items()):
        for _ in range(e):
            val = pow(g, o // q, p)
            tests.append({"q": q, "o": o, "exp": o // q, "val": val})
            if val != 1:
                break
            o //= q
    return tests


def product_tree_order(g: int, p: int) -> dict:
    """Order via a product tree over the prime powers q^e || p - 1.

    Going down the tree, a node with element h = g^{N / prod(node)} passes
    h^{prod(right)} to the left child and h^{prod(left)} to the right one, so
    each leaf q^e receives g^{N/q^e}; its order q^k is found by repeated
    q-th powers. ord(g) = prod q^k.
    """
    leaves = [q**e for q, e in sorted(factorize(p - 1).items())]
    qs = sorted(factorize(p - 1).items())
    levels = [leaves]
    while len(levels[-1]) > 1:
        lv = levels[-1]
        levels.append([lv[i] * lv[i + 1] if i + 1 < len(lv) else lv[i] for i in range(0, len(lv), 2)])
    down, leaf_elems = [], {}

    def walk(lo, hi, h, depth):
        node = leaves[lo:hi]
        if hi - lo == 1:
            leaf_elems[leaves[lo]] = h
            return
        mid = (lo + hi + 1) // 2
        pl = 1
        for x in leaves[lo:mid]:
            pl *= x
        pr = 1
        for x in leaves[mid:hi]:
            pr *= x
        hl, hr = pow(h, pr, p), pow(h, pl, p)
        down.append({"node": node, "h": h, "pl": pl, "pr": pr, "hl": hl, "hr": hr, "depth": depth})
        walk(lo, mid, hl, depth + 1)
        walk(mid, hi, hr, depth + 1)

    walk(0, len(leaves), g, 0)
    leaf_rows, order = [], 1
    for (q, e), qe in zip(qs, leaves):
        h = leaf_elems[qe]
        seq = [h]
        while seq[-1] != 1:
            seq.append(pow(seq[-1], q, p))
        k = len(seq) - 1
        order *= q**k
        leaf_rows.append({"q": q, "e": e, "qe": qe, "h": h, "seq": seq, "k": k})
    return {"levels": levels[::-1], "down": down, "leaves": leaf_rows, "order": order}


class Order(Task):
    id = "number_theory.order"
    title_ru = "Порядок элемента кольца вычетов (последовательное снижение)"
    topics = ("number_theory.order",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = "sem1: ord(g) >= p/4 (legacy); primitive roots allowed."
    presets = {
        "default": {"primes": list(first_primes(100)[-40:]), "g_range": None,
                    "min_ratio": 0.25, "phrase": ""},
        "sem2": {"primes": list(first_primes(40)[5:15]), "g_range": [2, 10],
                 "min_ratio": 0, "phrase": r"без перебора -- "},
    }
    statement = (r"Определить порядок элемента $\VAR{g}$ поля вычетов $\mathbb{Z}/\VAR{p}\mathbb{Z}$ "
                 r"\VAR{cfg.phrase}методом «последовательного снижения максимально возможного порядка».")
    solution = (r"$\ord(\VAR{g}) \mid p - 1 = \VAR{p - 1} = \VAR{factor}$. Начинаем с $o = \VAR{p - 1}$ и для "
                r"каждого простого $q \mid o$, пока $\VAR{g}^{o/q} \equiv 1$, заменяем $o \gets o/q$:"
                r"\BLOCK{for t in tests}\par\noindent $q = \VAR{t.q}$: $\VAR{g}^{\VAR{t.o}/\VAR{t.q}} = "
                r"\VAR{g}^{\VAR{t.exp}} \equiv \VAR{t.val}$"
                r"\BLOCK{if t.val == 1} $\Rightarrow o = \VAR{t.exp}$\BLOCK{else} $\ne 1$, $q$ больше не "
                r"снижаем\BLOCK{endif};\BLOCK{endfor}"
                r"\[\ord(\VAR{g}) = \VAR{answer}.\]")

    def sample(self, rng):
        while True:
            p = rng.choice(self.cfg.primes)
            lo, hi = self.cfg.g_range or (2, p - 1)
            g = rng.choice(list(range(lo, hi)))
            o = mult_order(g, p)
            if o >= p * self.cfg.min_ratio:
                return {"g": g, "p": p, "factor": steps.factor_tex(p - 1),
                        "tests": successive_reduction(g, p), "answer": o}

    def check(self, p):
        assert is_order(p["g"], p["answer"], p["p"])
        o = p["p"] - 1
        for t in p["tests"]:
            if t["val"] == 1:
                o //= t["q"]
        assert o == p["answer"]


class OrderProductTree(Task):
    id = "number_theory.order_product_tree"
    title_ru = "Порядок элемента кольца вычетов (дерево произведений)"
    topics = ("number_theory.order",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "Complexity not set in the legacy scripts (sem1 only): 2 is a guess. Primitive roots allowed."
    presets = {"default": {"primes": [211, 331, 421, 463, 547, 571, 631, 661, 691, 859, 911, 967, 991]}}
    statement = (r"Определить порядок элемента $\VAR{g}$ поля вычетов $\mathbb{Z}/\VAR{p}\mathbb{Z}$ "
                 r"с помощью построения дерева произведений.")
    solution = (r"$N = p - 1 = \VAR{p - 1} = \VAR{factor}$. Листья дерева --- примарные делители "
                r"$\VAR{t.levels[-1]|join(', ')}$; дерево произведений (от корня к листьям): "
                r"\BLOCK{for lv in t.levels}$\VAR{lv|join(',\\ ')}$\BLOCK{if not loop.last}; \BLOCK{endif}\BLOCK{endfor}."
                r"\par Спуск: корню соответствует $h = g = \VAR{g}$; узел с элементом $h$ передаёт левому "
                r"потомку $h^{P_R}$, правому $h^{P_L}$ ($P_L, P_R$ --- произведения в поддеревьях), так что "
                r"лист $q^e$ получает $g^{N/q^e}$:"
                r"\BLOCK{for d in t.down}\par\noindent узел $\{\VAR{d.node|join(', ')}\}$, $h = \VAR{d.h}$: "
                r"$h^{\VAR{d.pr}} \equiv \VAR{d.hl}$, $h^{\VAR{d.pl}} \equiv \VAR{d.hr}$;\BLOCK{endfor}"
                r"\par Порядок элемента листа $q^e$ равен $q^k$, где $k$ --- первый шаг, на котором "
                r"последовательность $h, h^q, h^{q^2}, \dots$ достигает $1$:"
                r"\BLOCK{for l in t.leaves}\par\noindent $\VAR{l.qe}$: $\VAR{l.seq|join(' \\to ')}$, "
                r"$k = \VAR{l.k}$;\BLOCK{endfor}"
                r"\[\ord(\VAR{g}) = \BLOCK{for l in t.leaves}\VAR{l.q}^{\VAR{l.k}}\BLOCK{if not loop.last} "
                r"\cdot \BLOCK{endif}\BLOCK{endfor} = \VAR{answer}.\]")

    def sample(self, rng):
        while True:
            p = rng.choice(self.cfg.primes)
            g = rng.choice(list(range(2, p - 1)))
            o = mult_order(g, p)
            if p / 4 <= o:
                return {"g": g, "p": p, "factor": steps.factor_tex(p - 1),
                        "t": product_tree_order(g, p), "answer": o}

    def check(self, p):
        assert is_order(p["g"], p["answer"], p["p"])
        assert p["t"]["order"] == p["answer"]
