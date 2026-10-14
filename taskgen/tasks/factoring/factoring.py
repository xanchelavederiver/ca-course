"""Integer factorization (ported from main-2sem.py)."""

import itertools
import math
from math import gcd

from taskgen.core import steps
from taskgen.core.nt import first_primes
from taskgen.core.task import SolutionDetail, Task

ANSWER = r"\[N = p \cdot q = \VAR{answer[0]} \cdot \VAR{answer[1]} = \VAR{n}.\]"


def _sample_pq(rng, primes):
    # Legacy allowed p == q; excluded here (N = p^2 is a degenerate instance).
    while True:
        p, q = rng.choice(primes), rng.choice(primes)
        if p != q:
            return sorted((p, q))


def pollard_pm1(n: int) -> dict:
    attempts = []
    for a in (2, 3, 5, 7, 11):
        rows, x = [], a
        for j in range(2, n):
            x = pow(x, j, n)
            d = gcd(x - 1, n)
            rows.append({"j": j, "x": x, "d": d})
            if d > 1:
                break
        attempts.append({"a": a, "rows": rows})
        if 1 < rows[-1]["d"] < n:
            return {"attempts": attempts, "d": rows[-1]["d"]}
    raise AssertionError("p-1 failed for all bases")


class PollardPm1(Task):
    id = "factoring.pollard_pm1"
    title_ru = "p-1 алгоритм Полларда"
    topics = ("factoring.pm1",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"primes": list(first_primes(40)[5:15])}}
    statement = r"Найти нетривиальный делитель числа $N = \VAR{n}$ с помощью $p-1$ алгоритма Полларда."
    solution = (r"Вычисляем $a_j = a_{j-1}^{\,j} \bmod N$ (т.е. $a^{j!}$) и $d_j = \gcd(a_j - 1, N)$, пока "
                r"$d_j = 1$; при $1 < d_j < N$ найден делитель (для $p \mid N$ с $(p-1) \mid j!$ имеем "
                r"$p \mid a^{j!} - 1$), при $d_j = N$ меняем основание."
                r"\BLOCK{for at in pm.attempts}\par\noindent $a = \VAR{at.a}$:"
                r"\[\begin{array}{c|\BLOCK{for _ in at.rows}r\BLOCK{endfor}}"
                r"j\BLOCK{for r in at.rows} & \VAR{r.j}\BLOCK{endfor} \\ \hline "
                r"a_j\BLOCK{for r in at.rows} & \VAR{r.x}\BLOCK{endfor} \\ "
                r"d_j\BLOCK{for r in at.rows} & \VAR{r.d}\BLOCK{endfor}\end{array}\]"
                r"\BLOCK{if not loop.last}$d = N$ --- неудача, берём следующее основание.\BLOCK{endif}"
                r"\BLOCK{endfor}"
                r"Делитель $\VAR{pm.d}$, $N / \VAR{pm.d} = \VAR{n // pm.d}$." + ANSWER)

    def sample(self, rng):
        p, q = _sample_pq(rng, self.cfg.primes)
        return {"n": p * q, "pm": pollard_pm1(p * q), "answer": [p, q]}

    def check(self, p):
        a, b = p["answer"]
        assert a * b == p["n"] and p["pm"]["d"] in (a, b)


def _legendre(a: int, p: int) -> int:
    a %= p
    if a == 0:
        return 0
    return 1 if pow(a, (p - 1) // 2, p) == 1 else -1


def quadratic_sieve(n: int, min_size: int = 1) -> dict:
    L = math.exp(math.sqrt(math.log(n) * math.log(math.log(n))))
    B_est = math.sqrt(L)
    B = max(3, round(B_est))
    x0 = math.isqrt(n - 1) + 1
    tried_B = []
    while True:
        fb = [p for p in first_primes(30) if p <= B and (p == 2 or _legendre(n, p) == 1)]
        roots = [{"p": p, "r": sorted({x for x in range(p) if (x * x - n) % p == 0})} for p in fb]
        rels, dep = [], None
        for x in range(x0, x0 + 60):
            f = x * x - n
            v, ex = f, []
            for p in fb:
                e = 0
                while v % p == 0:
                    v //= p
                    e += 1
                ex.append(e)
            if v != 1:
                continue
            rels.append({"x": x, "f": f, "ex": ex, "par": [e % 2 for e in ex]})
            # smallest subsets containing the new relation with all exponents even
            for size in range(min_size, len(rels) + 1):
                for sub in itertools.combinations(range(len(rels) - 1), size - 1):
                    idx = list(sub) + [len(rels) - 1]
                    tot = [sum(rels[i]["ex"][k] for i in idx) for k in range(len(fb))]
                    if any(t % 2 for t in tot):
                        continue
                    X = math.prod(rels[i]["x"] for i in idx) % n
                    Y = math.prod(p ** (t // 2) for p, t in zip(fb, tot)) % n
                    d = gcd(X - Y, n)
                    if 1 < d < n:
                        dep = {"idx": idx, "tot": tot, "X": X, "Y": Y, "d": d}
                        break
                if dep:
                    break
            if dep:
                break
        if dep:
            return {"L": f"{L:.2f}".replace(".", "{,}"), "B_est": f"{B_est:.2f}".replace(".", "{,}"), "B": B, "tried_B": tried_B, "x0": x0,
                    "fb": fb, "roots": roots, "rels": rels, "dep": dep}
        tried_B.append(B)
        B = next(p for p in first_primes(30) if p > B)


class QuadraticSieve(Task):
    id = "factoring.quadratic_sieve"
    title_ru = "Метод квадратичного решета"
    topics = ("factoring.quadratic_sieve",)
    complexity = 3
    solution_detail = SolutionDetail.FULL
    notes = ("sem2: larger N (primes 53..113) and a dependency of at least two relations (a single "
             "square F(x) is a Fermat hit, not the linear algebra step).")
    presets = {"default": {"primes": list(first_primes(40)[5:15]), "min_relations": 1},
               "sem2": {"primes": list(first_primes(40)[15:30]), "min_relations": 2}}
    statement = (r"Найти нетривиальный делитель числа $N = \VAR{n}$ методом Квадратичного решета. "
                 r"Обосновать выбор значения параметра $B$. Квадратичные сравнения можно решать "
                 r"любым способом.")
    solution = (r"Выбор $B$: $L(N) = e^{\sqrt{\ln N \ln\ln N}} \approx \VAR{qs.L}$, оптимум $B \approx L(N)^{1/2} "
                r"\approx \VAR{qs.B_est}$\BLOCK{if qs.tried_B}; при $B = \VAR{qs.tried_B|join(', ')}$ "
                r"на рассмотренном отрезке не набирается зависимость, поэтому\BLOCK{else};\BLOCK{endif}"
                r" берём $B = \VAR{qs.B}$. Факторная база --- простые $p \le B$, для которых $N$ --- квадратичный "
                r"вычет: $\{\VAR{qs.fb|join(', ')}\}$. Корни $x^2 \equiv N\ (\textrm{mod}\ p)$ (позиции просеивания): "
                r"\BLOCK{for r in qs.roots}$p = \VAR{r.p}$: $x \equiv \VAR{r.r|join(', ')}$"
                r"\BLOCK{if not loop.last}; \BLOCK{endif}\BLOCK{endfor}."
                r"\par Просеиваем $F(x) = x^2 - N$ при $x \ge \lceil\sqrt N\rceil = \VAR{qs.x0}$; $B$-гладкие значения "
                r"(показатели по базе $\VAR{qs.fb|join(', ')}$):"
                r"\[\begin{array}{r|r|l}"
                r"x & F(x) & \text{показатели} \\ \hline "
                r"\BLOCK{for r in qs.rels}\VAR{r.x} & \VAR{r.f} & (\VAR{r.ex|join(', ')}) \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"Произведение $F(x)$ для $x \in \{\BLOCK{for i in qs.dep.idx}\VAR{qs.rels[i].x}\BLOCK{if not loop.last}, "
                r"\BLOCK{endif}\BLOCK{endfor}\}$ имеет чётные показатели $(\VAR{qs.dep.tot|join(', ')})$ --- полный квадрат. "
                r"$X = \prod x \bmod N = \VAR{qs.dep.X}$, $Y = \prod p^{e/2} \bmod N = \VAR{qs.dep.Y}$, "
                r"$X^2 \equiv Y^2\ (\textrm{mod}\ N)$, $\gcd(X - Y, N) = \gcd(\VAR{qs.dep.X - qs.dep.Y}, \VAR{n}) = "
                r"\VAR{qs.dep.d}$." + ANSWER)

    def sample(self, rng):
        p, q = _sample_pq(rng, self.cfg.primes)
        return {"n": p * q, "qs": quadratic_sieve(p * q, self.cfg.min_relations), "answer": [p, q]}

    def check(self, p):
        a, b = p["answer"]
        dep = p["qs"]["dep"]
        assert a * b == p["n"] and dep["d"] in (a, b)
        assert (dep["X"] ** 2 - dep["Y"] ** 2) % p["n"] == 0
