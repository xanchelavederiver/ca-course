"""Square roots modulo a prime: Cipolla's algorithm (ported from main-2sem.py)."""

from taskgen.core.nt import first_primes
from taskgen.core.task import SolutionDetail, Task


def cipolla(a: int, p: int) -> dict:
    tries, t = [], 1
    while True:
        n = (t * t - a) % p
        e = pow(n, (p - 1) // 2, p) if n else 0
        tries.append({"t": t, "n": n, "e": e})
        if e == p - 1:
            break
        t += 1

    def mul(u, v):
        return ((u[0] * v[0] + u[1] * v[1] * n) % p, (u[0] * v[1] + u[1] * v[0]) % p)

    r, base, rows = (1, 0), (t, 1), []
    for bit in format((p + 1) // 2, "b"):
        sq = mul(r, r)
        r = mul(sq, base) if bit == "1" else sq
        rows.append({"bit": bit, "sq": list(sq), "r": list(r)})
    return {"t": t, "n": n, "tries": tries, "rows": rows, "x": r[0], "y": r[1]}


class Cipolla(Task):
    id = "number_theory.sqrt_cipolla"
    title_ru = "Решение квадратичного сравнения методом Чиполлы"
    topics = ("number_theory.sqrt",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = "Both roots are given in the answer; the trivial case x^2 = 1 is excluded."
    presets = {"default": {"primes": list(first_primes(40)[10:])}}
    statement = r"Решить квадратичное сравнение методом Чиполлы: \[x^2 \equiv \VAR{a2}\ (\textrm{mod}\ \VAR{p}).\]"
    solution = (r"Критерий Эйлера: $\VAR{a2}^{(p-1)/2} = \VAR{a2}^{\VAR{(p - 1) // 2}} \equiv 1$ --- "
                r"квадратичный вычет. Ищем $t$, для которого $t^2 - \VAR{a2}$ --- невычет "
                r"(значение $(t^2 - a)^{\VAR{(p - 1) // 2}}$ равно $-1 \equiv \VAR{p - 1}$):"
                r"\BLOCK{for r in c.tries} $t = \VAR{r.t}$: $t^2 - a \equiv \VAR{r.n}$, "
                r"$\VAR{r.n}^{\VAR{(p - 1) // 2}} \equiv \VAR{r.e}$\BLOCK{if not loop.last};\BLOCK{else}.\BLOCK{endif}"
                r"\BLOCK{endfor}"
                r" Положим $\omega^2 = \VAR{c.n}$; в $\mathbb{F}_{\VAR{p}}(\omega)$ "
                r"$(u_1 + v_1\omega)(u_2 + v_2\omega) = (u_1u_2 + \VAR{c.n} v_1v_2) + (u_1v_2 + u_2v_1)\omega$. "
                r"Вычисляем $x = (\VAR{c.t} + \omega)^{(p+1)/2} = (\VAR{c.t} + \omega)^{\VAR{(p + 1) // 2}}$, "
                r"$\VAR{(p + 1) // 2} = \VAR{((p + 1) // 2)|bin}_2$, бинарным алгоритмом:"
                r"\[\begin{array}{c|c|c}"
                r"\text{бит} & r^2 & r \\ \hline "
                r"\BLOCK{for r in c.rows}\VAR{r.bit} & \VAR{r.sq[0]} + \VAR{r.sq[1]}\omega & "
                r"\VAR{r.r[0]} + \VAR{r.r[1]}\omega \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"Получили $x = \VAR{c.x}$ (коэффициент при $\omega$ равен $0$), второй корень $p - x = \VAR{p - c.x}$; "
                r"проверка: $\VAR{c.x}^2 = \VAR{c.x * c.x} \equiv \VAR{a2}$."
                r"\[x \equiv \pm \VAR{x}\ (\textrm{mod}\ \VAR{p}),\ \text{т.е.}\ x \in \{\VAR{answer[0]}, \VAR{answer[1]}\}.\]")

    def sample(self, rng):
        while True:
            p = rng.choice(self.cfg.primes)
            a = rng.randrange(2, p)
            a2 = a * a % p
            if a2 != 1:
                break
        x = min(a, p - a)
        return {"a2": a2, "p": p, "x": x, "c": cipolla(a2, p), "answer": [x, p - x]}

    def check(self, p):
        assert p["c"]["y"] == 0 and p["c"]["x"] in p["answer"]
        for r in p["answer"]:
            assert r * r % p["p"] == p["a2"]
