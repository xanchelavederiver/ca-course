"""Extended Euclid, inverses modulo n and linear congruences (lecture sem1/03).

Corner cases are kept on purpose: gcd > 1, a < b (the first quotient is 0), composite moduli,
non-invertible residues, congruences with no solution or with d = gcd(a, n) > 1 solutions.
"""

from math import gcd

from taskgen.core import steps
from taskgen.core.nt import factorize, is_prime, random_prime
from taskgen.core.task import SolutionDetail, Task

TX = r"\BLOCK{import 'macros.tex.j2' as tx}"


def random_composite(rng, lo: int, hi: int) -> int:
    while True:
        n = rng.randint(lo, hi)
        if not is_prime(n):
            return n


class ExtendedEuclid(Task):
    id = "number_theory.xgcd"
    title_ru = "Расширенный алгоритм Евклида"
    topics = ("number_theory.euclid",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("gcd > 1 with probability `gcd_ratio`, a < b (first quotient 0) with probability "
             "`swap_ratio`; 4..9 division steps. Preset `corner`: always gcd > 1.")
    presets = {
        "default": {"lo": 100, "hi": 3000, "gcd_ratio": 1 / 3, "swap_ratio": 1 / 3, "max_gcd": 40},
        "sem2": {"lo": 1000, "hi": 30000},
        "corner": {"gcd_ratio": 1.0, "swap_ratio": 0.5},
    }
    statement = (r"С помощью расширенного алгоритма Евклида найти $d = \gcd(a, b)$ и целые $u$, $v$ такие, "
                 r"что $ua + vb = d$, для $a = \VAR{a}$, $b = \VAR{b}$. Описать все пары $(u, v)$ "
                 r"с этим свойством.")
    solution = (TX + r"Строки таблицы: $r_0 = a$, $r_1 = b$, $q_i = \lfloor r_{i-2}/r_{i-1} \rfloor$, "
                r"$r_i = r_{i-2} - q_i r_{i-1}$, и так же $u_i = u_{i-2} - q_i u_{i-1}$, "
                r"$v_i = v_{i-2} - q_i v_{i-1}$; на каждом шаге $r_i = u_i a + v_i b$."
                r"\BLOCK{if a < b} Так как $a < b$, первое частное равно $0$: первый шаг просто меняет "
                r"числа местами.\BLOCK{endif}"
                r"\VAR{tx.xgcd_table(rows, a, b)}"
                r"Последний ненулевой остаток $d = \VAR{d}$; из его строки $u = \VAR{u}$, $v = \VAR{v}$. "
                r"Проверка: $\VAR{u} \cdot \VAR{a} \VAR{v|signed} \cdot \VAR{b} = \VAR{u * a} \VAR{(v * b)|signed} "
                r"= \VAR{d}$."
                r"\BLOCK{if d > 1} Здесь $d > 1$: числа $a/d = \VAR{a // d}$ и $b/d = \VAR{b // d}$ взаимно "
                r"просты.\BLOCK{endif}"
                r"\par Все решения: если $ua + vb = d = u'a + v'b$, то $(u - u')\frac{a}{d} = (v' - v)\frac{b}{d}$, "
                r"и так как $\gcd(\frac{a}{d}, \frac{b}{d}) = 1$, то $\frac{b}{d} \mid u - u'$. Поэтому"
                r"\[d = \VAR{d}, \qquad u = \VAR{u} + \VAR{b // d}k, \quad v = \VAR{v} - \VAR{a // d}k, "
                r"\quad k \in \mathbb{Z}.\]")

    def sample(self, rng):
        cfg = self.cfg
        while True:
            g = rng.randint(2, cfg.max_gcd) if rng.random() < cfg.gcd_ratio else 1
            a = rng.randint(cfg.lo // g + 1, cfg.hi // g) * g
            b = rng.randint(cfg.lo // g + 1, cfg.hi // g) * g
            if a == b:
                continue
            a, b = max(a, b), min(a, b)
            if rng.random() < cfg.swap_ratio:
                a, b = b, a
            if (g > 1) != (gcd(a, b) > 1):
                continue
            rows = steps.xgcd_rows(a, b)
            nsteps = len(rows) - 2 - (a < b)
            if 4 <= nsteps <= 9:
                break
        last = rows[-2]
        return {"a": a, "b": b, "rows": rows, "d": last["r"], "u": last["u"], "v": last["v"],
                "answer": {"d": last["r"], "u": last["u"], "v": last["v"]}}

    def check(self, p):
        a, b = p["a"], p["b"]
        d, u, v = p["answer"]["d"], p["answer"]["u"], p["answer"]["v"]
        assert d == gcd(a, b) and u * a + v * b == d
        # Bezout coefficients of the Euclidean algorithm are small: |u| <= b/d, |v| <= a/d
        assert abs(u) <= b // d and abs(v) <= a // d


class ModularInverse(Task):
    id = "number_theory.inverse"
    title_ru = "Обратный элемент в кольце вычетов"
    topics = ("number_theory.euclid",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("Prime or composite modulus; with probability `noninv_ratio` gcd(a, n) > 1 (the answer is "
             "'does not exist'); with probability `reduce_ratio` a is negative or exceeds n. "
             "Preset `noninvertible` forces gcd(a, n) > 1.")
    presets = {
        "default": {"lo": 100, "hi": 1000, "prime_ratio": 0.4, "noninv_ratio": 0.25,
                    "reduce_ratio": 0.2},
        "sem2": {"lo": 1000, "hi": 10000},
        "noninvertible": {"noninv_ratio": 1.0, "reduce_ratio": 0.4},
    }
    statement = (r"Найти элемент, обратный к $a = \VAR{a}$ в кольце вычетов по модулю $n = \VAR{n}$, "
                 r"или доказать, что его не существует.")
    solution = (TX + r"\BLOCK{if a != ar}Сначала приводим $a$ по модулю $n$: $\VAR{a} \equiv \VAR{ar}"
                r"\VAR{tx.mod(n)}$. \BLOCK{endif}"
                r"Обратный к $a$ существует тогда и только тогда, когда $\gcd(a, n) = 1$; "
                r"расширенный алгоритм Евклида для $(n, a)$ даёт $d = \gcd(n, a)$ и $u n + v a = d$."
                r"\VAR{tx.xgcd_table(rows, n, ar)}"
                r"\BLOCK{if inv}"
                r"$d = 1 = \VAR{rows[-2].u} \cdot \VAR{n} \VAR{rows[-2].v|signed} \cdot \VAR{ar}$, поэтому "
                r"$\VAR{ar}^{-1} \equiv \VAR{rows[-2].v}\BLOCK{if rows[-2].v != x} \equiv \VAR{x}\BLOCK{endif}"
                r"\VAR{tx.mod(n)}$ (столбец $u_i$ можно было не вычислять)."
                r"\par Проверка: $\VAR{ar} \cdot \VAR{x} = \VAR{ar * x} = \VAR{(ar * x) // n} \cdot \VAR{n} + 1$."
                r"\[\VAR{a}^{-1} \equiv \VAR{x}\VAR{tx.mod(n)}.\]"
                r"\BLOCK{else}"
                r"$d = \gcd(\VAR{n}, \VAR{ar}) = \VAR{d} > 1$. Если бы $a x \equiv 1 \pmod{n}$, то "
                r"$ax - kn = 1$ для некоторого $k$, но левая часть делится на $\VAR{d}$ "
                r"--- противоречие. Более того, $a$ "
                r"--- делитель нуля: $\VAR{ar} \cdot \VAR{n // d} = \VAR{ar // d} \cdot \VAR{n} \equiv 0"
                r"\VAR{tx.mod(n)}$."
                r"\[\text{обратного элемента не существует}.\]"
                r"\BLOCK{endif}")

    def sample(self, rng):
        cfg = self.cfg
        noninv = rng.random() < cfg.noninv_ratio
        while True:
            if not noninv and rng.random() < cfg.prime_ratio:
                n = random_prime(rng, cfg.lo, cfg.hi)
            else:
                n = random_composite(rng, cfg.lo, cfg.hi)
            ar = rng.randrange(2, n - 1)
            d = gcd(ar, n)
            if (d > 1) != noninv:
                if not noninv:
                    continue
                q = rng.choice(sorted(factorize(n)))
                ar = q * rng.randrange(1, n // q)
                d = gcd(ar, n)
            if ar < 2:
                continue
            rows = steps.xgcd_rows(n, ar)
            if len(rows) - 2 >= 3:
                break
        a = ar
        if rng.random() < cfg.reduce_ratio:
            a = ar - n * rng.randint(1, 3) if rng.random() < 0.5 else ar + n * rng.randint(1, 5)
        if d == 1:
            inv = steps.inverse_rows(ar, n)
            return {"a": a, "ar": ar, "n": n, "d": 1, "inv": inv, "rows": rows, "x": inv["inv"],
                    "answer": {"gcd": 1, "inverse": inv["inv"]}}
        return {"a": a, "ar": ar, "n": n, "d": d, "inv": None, "rows": rows, "x": None,
                "answer": {"gcd": d, "inverse": None}}

    def check(self, p):
        a, n = p["a"], p["n"]
        assert p["ar"] == a % n and 0 < p["ar"] < n
        d = gcd(a, n)
        assert p["answer"]["gcd"] == d
        if d == 1:
            x = p["answer"]["inverse"]
            assert x == pow(a, -1, n) and a * x % n == 1
        else:
            assert p["answer"]["inverse"] is None and p["rows"][-2]["r"] == d


class LinearCongruence(Task):
    id = "number_theory.linear_congruence"
    title_ru = "Линейное сравнение"
    topics = ("number_theory.euclid",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Three cases with equal probability: d = gcd(a, n) = 1 (one solution), d > 1 and d | b "
             "(d solutions, all listed), d > 1 and d does not divide b (no solutions). d <= max_d. "
             "Presets `many` / `none` force the corner cases.")
    presets = {
        "default": {"lo": 40, "hi": 400, "max_d": 8, "cases": ["one", "many", "none"]},
        "sem2": {"lo": 200, "hi": 2000, "max_d": 12},
        "many": {"cases": ["many"]},
        "none": {"cases": ["none"]},
    }
    statement = (r"Решить сравнение \[\VAR{a} x \equiv \VAR{b} \pmod{\VAR{n}},\] т.\,е. найти все его "
                 r"решения $0 \le x < \VAR{n}$ (или показать, что решений нет).")
    solution = (TX + r"Найдём $d = \gcd(a, n)$ и $v$ с $u n + v a = d$ расширенным алгоритмом Евклида "
                r"для $(n, a) = (\VAR{n}, \VAR{a})$:"
                r"\VAR{tx.xgcd_table(rows, n, a)}"
                r"$d = \VAR{d}$, $v = \VAR{v}$, т.\,е. $\VAR{a} \cdot \VAR{v} \equiv \VAR{d}\VAR{tx.mod(n)}$."
                r"\BLOCK{if not sols}"
                r" При любых целых $x$, $k$ число $ax - kn$ делится на $d = \VAR{d}$, а $b = \VAR{b}$ "
                r"на $\VAR{d}$ не делится ($\VAR{b} = \VAR{b // d} \cdot \VAR{d} + \VAR{b % d}$)."
                r"\[\text{решений нет}.\]"
                r"\BLOCK{else}"
                r"\BLOCK{if d == 1} Значит, $a^{-1} \equiv \VAR{v % n}$ и "
                r"$x \equiv a^{-1} b = \VAR{v % n} \cdot \VAR{b} \equiv \VAR{x0}\VAR{tx.mod(n)}$: решение единственно."
                r"\BLOCK{else} Так как $d \mid b$ ($b/d = \VAR{b // d}$), сравнение равносильно "
                r"$\VAR{a // d} x \equiv \VAR{b // d} \pmod{\VAR{n1}}$, $n' = n/d = \VAR{n1}$. Умножая "
                r"$a v \equiv d \pmod n$ на $b/d$: $x_0 \equiv v \cdot \frac{b}{d} = \VAR{v} \cdot \VAR{b // d} "
                r"\equiv \VAR{x0} \pmod{\VAR{n1}}$. По модулю $n$ получаем $d = \VAR{d}$ решений "
                r"$x_0 + k n'$, $k = 0, \dots, \VAR{d - 1}$."
                r"\BLOCK{endif}"
                r"\par Проверка: $\VAR{a} \cdot \VAR{x0} = \VAR{a * x0} \equiv \VAR{b}\VAR{tx.mod(n)}$."
                r"\[x \in \{\VAR{sols|join(', ')}\}.\]"
                r"\BLOCK{endif}")

    def sample(self, rng):
        cfg = self.cfg
        case = rng.choice(cfg.cases)
        while True:
            n = rng.randint(cfg.lo, cfg.hi)
            if case == "one":
                a = rng.randrange(2, n)
            else:
                divs = [q for q in range(2, cfg.max_d + 1) if n % q == 0]
                if not divs:
                    continue
                dd = rng.choice(divs)
                a = dd * rng.randrange(1, n // dd)
            d = gcd(a, n)
            if (d == 1) != (case == "one") or d > cfg.max_d or a < 2:
                continue
            if case == "none":
                b = rng.randrange(1, n)
                if b % d == 0:
                    continue
            else:
                b = d * rng.randrange(1, n // d)
            rows = steps.xgcd_rows(n, a)
            if len(rows) - 2 >= 3:
                break
        v = rows[-2]["v"]
        n1 = n // d
        if b % d:
            sols, x0 = [], None
        else:
            x0 = v * (b // d) % n1
            sols = [x0 + k * n1 for k in range(d)]
        return {"a": a, "b": b, "n": n, "d": d, "rows": rows, "v": v, "n1": n1, "x0": x0, "sols": sols,
                "case": case, "answer": {"d": d, "solutions": sols}}

    def check(self, p):
        a, b, n = p["a"], p["b"], p["n"]
        brute = [x for x in range(n) if (a * x - b) % n == 0]   # independent route
        assert p["answer"]["solutions"] == brute
        d = gcd(a, n)
        assert p["answer"]["d"] == d and len(brute) == (d if b % d == 0 else 0)
