"""Difference of squares (lecture sem2/06): Fermat's method and the combination step of
the three-step procedure (Kraitchik / Dixon / quadratic sieve): a subset of relations
a_i^2 = c_i (mod N) with a square product, found by linear algebra over GF(2).
"""

import math
from math import gcd, isqrt

from taskgen.core.nt import factorize, is_prime
from taskgen.core.steps import factor_tex
from taskgen.core.task import SolutionDetail, Task


def _ceil_sqrt(n: int) -> int:
    s = isqrt(n)
    return s if s * s == n else s + 1


def fermat_rows(n: int) -> list[dict]:
    """Fermat's method for odd n: x = ceil(sqrt n), ceil(sqrt n) + 1, ... until x^2 - n = y^2."""
    x = _ceil_sqrt(n)
    rows = []
    while True:
        r = x * x - n
        s = isqrt(r)
        rows.append({"x": x, "r": r, "s": s, "sq": s * s == r, "inc": 2 * x + 1})
        if s * s == r:
            return rows
        x += 1


def fermat_steps(p: int, q: int) -> int:
    """Number of x values Fermat's method tries for n = p q (p, q odd): (p+q)/2 - ceil(sqrt n) + 1."""
    return (p + q) // 2 - _ceil_sqrt(p * q) + 1


class Fermat(Task):
    id = "factoring.fermat"
    title_ru = "Метод Ферма (разность квадратов)"
    topics = ("factoring.fermat",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("N = pq with close primes, so that the trace has min_steps..max_steps rows (the "
             "number of steps is drawn uniformly); with "
             "probability square_ratio N = p^2 (corner case: x = sqrt N, y = 0). Presets: far "
             "(longer traces), square (always N = p^2).")
    presets = {
        "default": {"plo": 30, "phi": 700, "min_steps": 2, "max_steps": 8, "square_ratio": 0.1},
        "sem2": {"plo": 100, "phi": 2000},
        "far": {"plo": 60, "phi": 1200, "min_steps": 9, "max_steps": 16, "square_ratio": 0.0},
        "square": {"square_ratio": 1.0},
    }
    statement = (r"Разложить на множители число $N = \VAR{n}$ методом Ферма: перебирать "
                 r"$x = \lceil\sqrt N\,\rceil, \lceil\sqrt N\,\rceil + 1, \dots$, пока $x^2 - N$ не станет "
                 r"полным квадратом $y^2$. Сколько значений $x$ пришлось перебрать? Сравнить с оценкой "
                 r"числа шагов через найденные множители.")
    solution = (r"$\lfloor\sqrt{\VAR{n}}\rfloor = \VAR{rows[0].x - (0 if square else 1)}$, "
                r"\BLOCK{if square}и $\VAR{rows[0].x}^2 = \VAR{n}$, т.\,е. $N$ "
                r"--- полный квадрат: уже при $x = \lceil\sqrt N\,\rceil = \VAR{rows[0].x}$ имеем "
                r"$x^2 - N = 0 = 0^2$, $y = 0$. Разложение $N = (x - y)(x + y) = \VAR{rows[0].x} \cdot \VAR{rows[0].x}$; "
                r"метод Ферма находит его за один шаг (множители совпадают, $p - q = 0$)."
                r"\BLOCK{else}$\VAR{rows[0].x - 1}^2 = \VAR{(rows[0].x - 1) ** 2} < N \le \VAR{rows[0].x}^2$, поэтому "
                r"начинаем с $x = \VAR{rows[0].x}$. Значения $r = x^2 - N$ удобно пересчитывать: "
                r"$r_{x+1} = r_x + 2x + 1$.\[\begin{array}{r|r|r|l}"
                r"x & x^2 - N & \lfloor\sqrt{x^2 - N}\rfloor & \text{квадрат?} \\ \hline "
                r"\BLOCK{for w in rows}\VAR{w.x} & \VAR{w.r} & \VAR{w.s} & "
                r"\BLOCK{if w.sq}\text{да}, y = \VAR{w.s}\BLOCK{else}\text{нет}\BLOCK{endif} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"При $x = \VAR{x}$: $x^2 - N = \VAR{y * y} = \VAR{y}^2$, поэтому "
                r"$N = x^2 - y^2 = (x - y)(x + y) = \VAR{x - y} \cdot \VAR{x + y}$. "
                r"Перебрано $s = \VAR{rows|length}$ значений $x$. Оценка: $s = \frac{p + q}{2} - \lceil\sqrt N\,\rceil + 1"
                r" = \VAR{x} - \VAR{rows[0].x} + 1 = \VAR{rows|length}$, причём "
                r"$\frac{p+q}{2} - \sqrt N = \frac{(q - p)^2}{2(\sqrt p + \sqrt q)^2} \le \frac{(q - p)^2}{8\sqrt N}"
                r" = \frac{\VAR{(2 * y) ** 2}}{8\sqrt{\VAR{n}}} \approx \VAR{bound}$: "
                r"множители близки ($q - p = \VAR{2 * y}$), поэтому метод сработал быстро."
                r"\BLOCK{endif}"
                r"\[N = \VAR{answer[0]} \cdot \VAR{answer[1]}.\]")

    def sample(self, rng):
        c = self.cfg
        primes = [k for k in range(max(c.plo, 3), c.phi + 1) if is_prime(k)]
        if rng.random() < c.square_ratio:
            p = rng.choice(primes)
            rows = fermat_rows(p * p)
            return {"n": p * p, "square": True, "rows": rows, "x": p, "y": 0, "bound": "0",
                    "answer": [p, p]}
        while True:  # the number of steps is uniform in [min_steps, max_steps]
            p, steps = rng.choice(primes), rng.randint(c.min_steps, c.max_steps)
            qs = [q for q in range(p + 2, 2 * c.phi) if is_prime(q) and fermat_steps(p, q) == steps]
            if qs:
                q = rng.choice(qs)
                break
        n = p * q
        rows = fermat_rows(n)
        x, y = rows[-1]["x"], rows[-1]["s"]
        bound = f"{(q - p) ** 2 / (8 * math.sqrt(n)):.2f}".replace(".", "{,}")
        return {"n": n, "square": False, "rows": rows, "x": x, "y": y, "bound": bound,
                "answer": [x - y, x + y]}

    def check(self, p):
        n, (a, b), rows = p["n"], p["answer"], p["rows"]
        assert 1 < a <= b < n and a * b == n and n % 2 == 1
        # Fermat finds the factor pair closest to sqrt(n): the largest divisor <= sqrt(n)
        assert a == max(d for d in range(1, isqrt(n) + 1) if n % d == 0)
        assert rows[0]["x"] ** 2 >= n > (rows[0]["x"] - 1) ** 2
        assert len(rows) == (a + b) // 2 - rows[0]["x"] + 1
        assert len(rows) <= 20
        for w in rows[:-1]:  # non-squares, checked through the factorization
            assert any(e % 2 for e in factorize(w["r"]).values())
        assert p["x"] ** 2 - p["y"] ** 2 == n
        assert p["square"] == (a == b)


# --- congruence of squares: the combination step ---------------------------------------


def gf2_eliminate(vecs: list[list[int]]) -> dict:
    """Gaussian elimination over GF(2) on the rows ``vecs`` (one row per relation).

    Columns are processed left to right; the pivot of a column is the first non-pivot row
    with a 1 there, and it is added to every other non-pivot row with a 1 in that column.
    Rows that never become pivots end up zero; their tracked combinations are the
    dependencies (in row order).
    """
    rows = [list(v) for v in vecs]
    combo = [{i} for i in range(len(vecs))]
    pivots: set[int] = set()
    steps = []
    for j in range(len(vecs[0]) if vecs else 0):
        piv = next((i for i in range(len(rows)) if i not in pivots and rows[i][j]), None)
        if piv is None:
            steps.append({"col": j, "piv": None, "adds": [], "adds1": []})
            continue
        pivots.add(piv)
        adds = []
        for i in range(len(rows)):
            if i not in pivots and rows[i][j]:
                rows[i] = [(u + w) % 2 for u, w in zip(rows[i], rows[piv])]
                combo[i] ^= combo[piv]
                adds.append(i)
        steps.append({"col": j, "piv": piv, "adds": adds, "adds1": [i + 1 for i in adds]})
    deps = [sorted(combo[i]) for i in range(len(rows)) if i not in pivots]
    assert all(not any(rows[i]) for i in range(len(rows)) if i not in pivots)
    return {"steps": steps, "deps": deps, "final": rows,
            "combos": [sorted(c) for c in combo], "pivots": sorted(pivots)}


def combine(n: int, fb: list[int], rels: list[dict], idx: list[int]) -> dict:
    tot = [sum(rels[i]["ex"][k] for i in idx) for k in range(len(fb))]
    assert all(t % 2 == 0 for t in tot)
    X = math.prod(rels[i]["a"] for i in idx) % n
    Y = math.prod(pr ** (t // 2) for pr, t in zip(fb, tot)) % n
    d = gcd(X - Y, n)
    kind = "ok" if 1 < d < n else ("same" if (X - Y) % n == 0 else "neg")
    return {"idx": idx, "idx1": [i + 1 for i in idx], "tot": tot, "X": X, "Y": Y, "diff": X - Y, "d": d, "kind": kind,
            "half": [t // 2 for t in tot]}


class CongruenceOfSquares(Task):
    id = "factoring.congruence_of_squares"
    title_ru = "Сравнение квадратов: комбинирование соотношений"
    topics = ("factoring.quadratic_sieve", "factoring.fermat")
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Relations a^2 = c (mod N) with a near sqrt(kN), c = a^2 - kN smooth over a small "
             "factor base, distinct and not perfect squares; Gaussian elimination over GF(2) traced; with probability "
             "trivial_first_ratio the first dependency gives a trivial gcd (X = Y or X = -Y) and "
             "the next one succeeds. Preset trivial: always so.")
    presets = {
        "default": {"plo": 40, "phi": 160, "fb": [2, 3, 5, 7, 11], "extra": 2, "kmax": 3,
                    "window": 40, "trivial_first_ratio": 0.5},
        "sem2": {"plo": 50, "phi": 200},
        "trivial": {"trivial_first_ratio": 1.0},
    }
    statement = (r"Для $N = \VAR{n}$ найдены соотношения $a_i^2 \equiv c_i \pmod{N}$, в которых числа "
                 r"$c_i$ раскладываются по факторной базе $\{\VAR{fb|join(', ')}\}$:"
                 r"\[\begin{array}{c|r|r|l}"
                 r"i & a_i & c_i & \\ \hline "
                 r"\BLOCK{for w in rels}\VAR{loop.index} & \VAR{w.a} & \VAR{w.c} & = \VAR{w.ftex} \\ \BLOCK{endfor}"
                 r"\end{array}\]"
                 r"С помощью исключения Гаусса над $\mathbb{F}_2$ найти наборы соотношений, произведение "
                 r"$c_i$ в которых "
                 r"--- полный квадрат, и для каждого (по порядку) вычислить $X = \prod a_i \bmod N$, "
                 r"$Y = \sqrt{\prod c_i} \bmod N$ и $\gcd(X - Y, N)$, пока не будет найден нетривиальный "
                 r"делитель $N$.")
    solution = (r"Векторы показателей по модулю $2$ (столбцы "
                r"--- простые $\VAR{fb|join(', ')}$):"
                r"\[\begin{array}{c|\BLOCK{for _ in fb}c\BLOCK{endfor}}"
                r"\BLOCK{for pr in fb} & \VAR{pr}\BLOCK{endfor} \\ \hline "
                r"\BLOCK{for w in rels}v_{\VAR{loop.index}}\BLOCK{for e in w.ex} & \VAR{e % 2}\BLOCK{endfor} \\ "
                r"\BLOCK{endfor}\end{array}\]"
                r"Исключение по столбцам слева направо (ведущая строка "
                r"--- первая ещё не использованная строка с единицей в столбце; её прибавляем к остальным "
                r"неиспользованным строкам с единицей в этом столбце, запоминая, из каких $v_i$ составлена строка):"
                r"\begin{itemize}"
                r"\BLOCK{for s in el.steps}\item столбец $\VAR{fb[s.col]}$: \BLOCK{if s.piv is none}единиц "
                r"в неиспользованных строках нет\BLOCK{else}ведущая строка $\VAR{s.piv + 1}$"
                r"\BLOCK{if s.adds}; к строкам $\VAR{s.adds1|join(', ')}$ прибавляем её\BLOCK{endif}"
                r"\BLOCK{endif};\BLOCK{endfor}"
                r"\end{itemize}"
                r"Не ставшие ведущими строки обнулились; они дают зависимости "
                r"\BLOCK{for d in el.deps}$\BLOCK{for i in d}v_{\VAR{i + 1}}\BLOCK{if not loop.last} + \BLOCK{endif}"
                r"\BLOCK{endfor} = 0$\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}."
                r"\BLOCK{for t in tries}\par\noindent \textbf{Набор $\{\VAR{t.idx1|join(', ')}\}$.} "
                r"$\prod c_i = \VAR{t.ctex}$, "
                r"$X = \BLOCK{for i in t.idx}\VAR{rels[i].a}\BLOCK{if not loop.last} \cdot \BLOCK{endif}\BLOCK{endfor}"
                r" \bmod \VAR{n} = \VAR{t.X}$, "
                r"$Y = \VAR{t.ytex} \bmod \VAR{n} = \VAR{t.Y}$; "
                r"$\gcd(X - Y, N) = \gcd(\VAR{t.diff}, \VAR{n}) = \VAR{t.d}$"
                r"\BLOCK{if t.kind == 'same'} "
                r"--- тривиальный делитель: $X \equiv Y \pmod{N}$, переходим к следующей зависимости."
                r"\BLOCK{elif t.kind == 'neg'} "
                r"--- тривиальный делитель: $X \equiv -Y \pmod{N}$ ($X + Y = \VAR{t.X + t.Y}$), "
                r"переходим к следующей зависимости."
                r"\BLOCK{else}: $X^2 \equiv Y^2$, но $X \not\equiv \pm Y \pmod{N}$, делитель найден."
                r"\BLOCK{endif}\BLOCK{endfor}"
                r"\[N = \VAR{answer[0]} \cdot \VAR{answer[1]}.\]")

    def _relations(self, rng, n: int) -> list[dict] | None:
        c, fb = self.cfg, self.cfg.fb
        r = len(fb) + c.extra
        cands = []
        for k in range(1, c.kmax + 1):
            a0 = _ceil_sqrt(k * n)
            for a in range(a0, a0 + c.window):
                cv = a * a % n
                if cv == 0:
                    continue
                v, ex = cv, []
                for pr in fb:
                    e = 0
                    while v % pr == 0:
                        v //= pr
                        e += 1
                    ex.append(e)
                # a square c is a Fermat hit (a^2 - kN = b^2), not a combination exercise
                if v == 1 and isqrt(cv) ** 2 != cv:
                    cands.append({"a": a, "c": cv, "ex": ex})
        # one relation per value of c (otherwise a pair of equal c's is an obvious dependency)
        uniq = {}
        for w in cands:
            uniq.setdefault(w["c"], w)
        cands = list(uniq.values())
        # a = t a', c = t^2 c' is a "scaled copy" of a relation: it always gives X = Y
        cands = [w for w in cands if not any(v is not w and w["a"] % v["a"] == 0 and
                                             w["c"] * v["a"] ** 2 == v["c"] * w["a"] ** 2
                                             for v in cands)]
        if len(cands) < r:
            return None
        rels = rng.sample(cands, r)
        for w in rels:
            w["ftex"] = factor_tex(w["c"])
        return rels

    def sample(self, rng):
        c = self.cfg
        primes = [k for k in range(c.plo, c.phi + 1) if is_prime(k)]
        want_trivial = rng.random() < c.trivial_first_ratio
        while True:
            p, q = sorted(rng.sample(primes, 2))
            n = p * q
            rels = self._relations(rng, n)
            if rels is None:
                continue
            el = gf2_eliminate([[e % 2 for e in w["ex"]] for w in rels])
            tries = []
            for dep in el["deps"]:
                t = combine(n, c.fb, rels, dep)
                tries.append(t)
                if t["kind"] == "ok":
                    break
            if tries[-1]["kind"] != "ok" or (tries[0]["kind"] != "ok") != want_trivial:
                continue
            if len(tries) > 2:
                continue
            for t in tries:
                t["ctex"] = " \\cdot ".join(f"{pr}^{{{e}}}" for pr, e in zip(c.fb, t["tot"]) if e) or "1"
                t["ytex"] = " \\cdot ".join((f"{pr}^{{{h}}}" if h > 1 else str(pr))
                                            for pr, h in zip(c.fb, t["half"]) if h) or "1"
            d = tries[-1]["d"]
            return {"n": n, "fb": list(c.fb), "rels": rels, "el": el, "tries": tries,
                    "answer": sorted([d, n // d])}

    def check(self, p):
        n, fb, rels = p["n"], p["fb"], p["rels"]
        a, b = p["answer"]
        assert a * b == n and 1 < a <= b
        assert set(factorize(n)) == {a, b}
        for w in rels:
            assert w["a"] ** 2 % n == w["c"]
            assert math.prod(pr ** e for pr, e in zip(fb, w["ex"])) == w["c"]
        assert len({w["c"] for w in rels}) == len(rels)
        assert all(isqrt(w["c"]) ** 2 != w["c"] for w in rels)
        for k, t in enumerate(p["tries"]):
            tot = [sum(rels[i]["ex"][j] for i in t["idx"]) for j in range(len(fb))]
            assert all(e % 2 == 0 for e in tot)
            X = math.prod(rels[i]["a"] for i in t["idx"]) % n
            assert X == t["X"] and (t["Y"] ** 2 - math.prod(rels[i]["c"] for i in t["idx"])) % n == 0
            assert (X * X - t["Y"] ** 2) % n == 0
            last = k == len(p["tries"]) - 1
            if last:
                assert t["d"] in (a, b)
            else:
                assert (X - t["Y"]) % n == 0 or (X + t["Y"]) % n == 0
