"""Pollard p - 1 with a smoothness bound B (lecture sem2/05): the corner case where both
p - 1 and q - 1 are B-power-smooth, so gcd(a^M - 1, N) = N for M = lcm(1, ..., B), and the
factor is recovered by backtracking over the prime powers of M (or by changing the base).
"""

from math import gcd, lcm

from taskgen.core.nt import first_primes, is_prime
from taskgen.core.steps import factor_tex
from taskgen.core.task import SolutionDetail, Task


def prime_powers(B: int) -> list[dict]:
    """[(l, e, l^e)] for primes l <= B, l^e the largest power of l not exceeding B."""
    out = []
    for ell in first_primes(B):
        if ell > B:
            break
        e = 1
        while ell ** (e + 1) <= B:
            e += 1
        out.append({"l": ell, "e": e, "pe": ell**e})
    return out


def pm1_backtrack(n: int, B: int, bases=(2, 3, 5, 7)) -> dict:
    pps = prime_powers(B)
    attempts = []
    for a in bases:
        rows, x = [], a
        for pp in pps:
            x = pow(x, pp["pe"], n)
            rows.append({**pp, "x": x, "g": gcd(x - 1, n)})
        k = next(i for i, r in enumerate(rows) if r["g"] > 1)
        at = {"a": a, "rows": rows, "k": k, "sub": [], "start": rows[k - 1]["x"] if k else a}
        attempts.append(at)
        if rows[k]["g"] < n:
            return {"pps": pps, "M": lcm(*range(1, B + 1)), "attempts": attempts, "d": rows[k]["g"]}
        # both orders are completed by the same prime power l^e: raise to l one step at a time
        y = at["start"]
        for j in range(1, rows[k]["e"] + 1):
            y = pow(y, rows[k]["l"], n)
            g = gcd(y - 1, n)
            at["sub"].append({"j": j, "x": y, "g": g})
            if g > 1:
                break
        if g < n:
            return {"pps": pps, "M": lcm(*range(1, B + 1)), "attempts": attempts, "d": g}
    raise AssertionError("p-1 backtracking failed for all bases")


class PollardPm1Backtrack(Task):
    id = "factoring.pm1_backtrack"
    title_ru = "Алгоритм p-1 Полларда: случай gcd = N"
    topics = ("factoring.pm1",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Always the corner case: both p - 1 and q - 1 are B-power-smooth, so the plain "
             "algorithm returns gcd = N; backtracking over prime powers, then over a single prime, "
             "then the next base (all three outcomes occur).")
    presets = {"default": {"B_lo": 7, "B_hi": 13, "p_lo": 23, "p_hi": 160}}
    statement = (r"Число $N = \VAR{n}$ раскладывается алгоритмом $p - 1$ Полларда с основанием $a = 2$ и "
                 r"границей $B = \VAR{B}$, т.\,е. с показателем $M = \operatorname{lcm}(1, \ldots, \VAR{B}) "
                 r"= \VAR{M_tex} = \VAR{M}$. Вычисляя $a^M$ последовательным возведением в степени "
                 r"$\ell^{e_\ell}$, показать, что $\gcd(a^M - 1, N) = N$, и всё же найти нетривиальный "
                 r"делитель $N$ (возвратом к промежуточным значениям; при неудаче --- следующее "
                 r"основание $a = 3, 5, \ldots$).")
    solution = (r"$x_0 = a$, $x_i = x_{i-1}^{\ell_i^{e_i}} \bmod N$ по простым $\ell_i \le B$, "
                r"$g_i = \gcd(x_i - 1, N)$. Если $p \mid N$ и $\operatorname{ord}_p a \mid \ell_1^{e_1} \cdots "
                r"\ell_i^{e_i}$, то $p \mid g_i$; $g = N$ означает, что порядки $a$ по модулю обоих "
                r"простых делителей разделили показатель одновременно."
                r"\BLOCK{for at in pm.attempts}\par\noindent $a = \VAR{at.a}$:"
                r"\[\begin{array}{c|\BLOCK{for _ in at.rows}r\BLOCK{endfor}}"
                r"\ell^{e}\BLOCK{for r in at.rows} & \VAR{r.pe}\BLOCK{endfor} \\ \hline "
                r"x_i\BLOCK{for r in at.rows} & \VAR{r.x}\BLOCK{endfor} \\ "
                r"g_i\BLOCK{for r in at.rows} & \VAR{r.g}\BLOCK{endfor}\end{array}\]"
                r"\BLOCK{set r = at.rows[at.k]}"
                r"\BLOCK{if at.rows[-1].g == n}$\gcd(a^M - 1, N) = N$. \BLOCK{endif}"
                r"Первое $g_i > 1$ --- при $\ell^e = \VAR{r.pe}$: $g = \VAR{r.g}$"
                r"\BLOCK{if r.g < n}, это и есть делитель (возврат к промежуточному значению).\BLOCK{else}"
                r", т.\,е. $g = N$. Возвращаемся к $x = \VAR{at.start}$ и возводим в степень $\VAR{r.l}$ по одному разу: "
                r"\BLOCK{for s in at.sub}$x^{\VAR{r.l}^{\VAR{s.j}}} \equiv \VAR{s.x}$, "
                r"$\gcd(\VAR{s.x} - 1, N) = \VAR{s.g}$\BLOCK{if not loop.last}; \BLOCK{endif}\BLOCK{endfor}."
                r"\BLOCK{if at.sub[-1].g == n} Снова $N$: при этом основании оба порядка дописываются "
                r"одним и тем же множителем $\VAR{r.l}$ --- меняем основание.\BLOCK{else} Делитель найден."
                r"\BLOCK{endif}\BLOCK{endif}"
                r"\BLOCK{endfor}"
                r"\par $N / \VAR{pm.d} = \VAR{n // pm.d}$; действительно, "
                r"$\VAR{answer[0]} - 1 = \VAR{pf[0]}$ и $\VAR{answer[1]} - 1 = \VAR{pf[1]}$ "
                r"--- оба $\VAR{B}$-гладкие (делят $M$)."
                r"\[N = \VAR{answer[0]} \cdot \VAR{answer[1]} = \VAR{n}.\]")

    def sample(self, rng):
        cfg = self.cfg
        while True:
            B = rng.randint(cfg.B_lo, cfg.B_hi)
            M = lcm(*range(1, B + 1))
            good = [p for p in range(max(cfg.p_lo, B + 1), cfg.p_hi) if is_prime(p) and M % (p - 1) == 0]
            if len(good) < 2:
                continue
            p, q = sorted(rng.sample(good, 2))
            try:
                pm = pm1_backtrack(p * q, B, bases=(2, 3, 5))
            except AssertionError:
                continue
            break
        M_tex = r" \cdot ".join(f"{pp['l']}^{{{pp['e']}}}" if pp["e"] > 1 else str(pp["l"])
                                for pp in pm["pps"])
        return {"n": p * q, "B": B, "M": M, "M_tex": M_tex, "pm": pm,
                "pf": [factor_tex(p - 1), factor_tex(q - 1)], "answer": [p, q]}

    def check(self, p):
        a, b = p["answer"]
        n, pm = p["n"], p["pm"]
        assert a * b == n and pm["d"] in (a, b)
        M = p["M"]
        assert M % (a - 1) == 0 and M % (b - 1) == 0
        assert gcd(pow(2, M, n) - 1, n) == n  # the corner case really occurs
