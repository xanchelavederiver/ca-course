"""Probabilistic primality tests (ported from main-{1,2}sem.py).

N is prime or composite (``composite_ratio``). Composites come from the same
range as the primes and are not trivially detectable: odd, smallest prime
factor >= 7, or a Fermat pseudoprime to base 2 (e.g. Carmichael numbers).
Bases are tried in the order 2, 3, 5, 7, ...: two passed rounds suffice for a
prime (error <= 1/4 for Solovay–Strassen, <= 1/16 for Miller–Rabin); for a
composite rounds continue until a witness is found.
"""

from math import gcd

from taskgen.core import steps
from taskgen.core.nt import factorize, first_primes, is_prime
from taskgen.core.task import SolutionDetail, Task

SEM2_PRIMES = list(first_primes(40)[10:-5])
# Hand-picked in the legacy sem1 script (N - 1 divisible by a large power of 2).
PRIMES_FOR_MR = [113, 137, 193, 233, 241, 257, 281, 313, 337, 353, 401, 409, 433, 449, 457, 521,
                 569, 577, 593, 601, 617, 641, 673, 761, 769, 809, 857, 881, 929, 937, 953, 977]
BASES = list(first_primes(30))
TX = r"\BLOCK{import 'macros.tex.j2' as tx}"


def hard_composites(lo: int, hi: int) -> list[int]:
    return [n for n in range(lo | 1, hi + 1, 2)
            if not is_prime(n) and (min(factorize(n)) >= 7 or pow(2, n - 1, n) == 1)]


def _pick(rng, cfg) -> int:
    if rng.random() < cfg.composite_ratio:
        return rng.choice(hard_composites(min(cfg.candidates), max(cfg.candidates)))
    return rng.choice(cfg.candidates)


def _check_rounds(p, rounds_needed):
    n = p["n"]
    assert p["answer"] == ("prime" if is_prime(n) else "composite")
    if p["answer"] == "prime":
        assert len(p["rounds"]) == rounds_needed and all(r["verdict"] == "pass" for r in p["rounds"])
    else:
        assert p["rounds"][-1]["verdict"] == "witness"


ANSWER = (r"\BLOCK{if answer == 'prime'}Пройдено \VAR{rounds|length} раунда, вероятность ошибки не более "
          r"$\VAR{err}$: $N = \VAR{n}$ --- простое."
          r"\BLOCK{else}Найден свидетель $a = \VAR{rounds[-1].a}$: $N = \VAR{n}$ --- составное"
          r" ($\VAR{n} = \VAR{factors}$).\BLOCK{endif}")


class SolovayStrassen(Task):
    id = "number_theory.solovay_strassen"
    title_ru = "Тест простоты Соловея-Штрассена"
    topics = ("number_theory.primality",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    presets = {
        "default": {"candidates": list(first_primes(100)[-25:]), "composite_ratio": 0.5},
        "sem2": {"candidates": SEM2_PRIMES},
    }
    statement = (r"С помощью теста Соловея-Штрассена определить, является ли простым число "
                 r"$N = \VAR{n}$. Требуется дать ответ с вероятностью ошибки не~более~$\frac14$.")
    solution = (TX + r"Для простого $N$ при любом $a$, $\gcd(a, N) = 1$: "
                r"$a^{(N-1)/2} \equiv \left(\frac{a}{N}\right)\ (\textrm{mod}\ N)$; для составного $N$ "
                r"это выполнено не более чем для половины $a$, поэтому нужно два раунда "
                r"($(1/2)^2 = 1/4$). $(N-1)/2 = \VAR{(n - 1) // 2}$."
                r"\BLOCK{for r in rounds}\par\noindent $a = \VAR{r.a}$: "
                r"\BLOCK{if r.g > 1}$\gcd(\VAR{r.a}, N) = \VAR{r.g} > 1$ --- свидетель."
                r"\BLOCK{else}$\VAR{tx.jacobi(r.j)}$; "
                r"$\VAR{r.a}^{\VAR{(n - 1) // 2}} \equiv \VAR{r.e}\BLOCK{if r.e == n - 1} \equiv -1\BLOCK{endif}$ "
                r"--- \BLOCK{if r.verdict == 'pass'}совпадает (раунд пройден)"
                r"\BLOCK{else}не совпадает, $a$ --- свидетель составности\BLOCK{endif}.\BLOCK{endif}"
                r"\BLOCK{endfor}\par\noindent " + ANSWER)

    def sample(self, rng):
        n = _pick(rng, self.cfg)
        rounds = []
        for a in BASES:
            if a >= n:
                break
            g = gcd(a, n)
            if g > 1:
                rounds.append({"a": a, "g": g, "verdict": "witness"})
                break
            j = steps.jacobi_chain(a, n)
            e = pow(a, (n - 1) // 2, n)
            ok = e == j["value"] % n
            rounds.append({"a": a, "g": 1, "j": j, "e": e, "verdict": "pass" if ok else "witness"})
            if not ok or (is_prime(n) and len(rounds) == 2):
                break
        prime = is_prime(n)
        return {"n": n, "rounds": rounds, "err": r"\frac14",
                "factors": steps.factor_tex(n) if not prime else str(n),
                "answer": "prime" if prime else "composite"}

    def check(self, p):
        _check_rounds(p, 2)


class MillerRabin(Task):
    id = "number_theory.miller_rabin"
    title_ru = "Тест простоты Миллера-Рабина"
    topics = ("number_theory.primality",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    presets = {
        "default": {"candidates": PRIMES_FOR_MR, "composite_ratio": 0.5},
        "sem2": {"candidates": SEM2_PRIMES},
    }
    statement = (r"С помощью теста Миллера-Рабина определить, является ли простым число "
                 r"$N = \VAR{n}$. Требуется дать ответ с вероятностью ошибки не~более~$\frac{1}{16}$.")
    solution = (r"$N - 1 = \VAR{n - 1} = 2^{\VAR{s}} \cdot \VAR{d}$. Для основания $a$ вычисляем "
                r"$x_0 = a^{\VAR{d}}$, $x_i = x_{i-1}^2$; $a$ --- не свидетель, если $x_0 = 1$ или "
                r"$x_i = N - 1 = \VAR{n - 1}$ при некотором $i < \VAR{s}$. Для составного $N$ "
                r"не-свидетелей не более $1/4$, поэтому нужно два раунда ($(1/4)^2 = 1/16$)."
                r"\BLOCK{for r in rounds}\par\noindent $a = \VAR{r.a}$: "
                r"\BLOCK{if r.g > 1}$\gcd(\VAR{r.a}, N) = \VAR{r.g} > 1$ --- свидетель."
                r"\BLOCK{else}$x_i$: $\VAR{r.xs|join(', ')}$ --- "
                r"\BLOCK{if r.verdict == 'pass'}раунд пройден\BLOCK{else}$a$ --- свидетель составности"
                r"\BLOCK{endif}.\BLOCK{endif}\BLOCK{endfor}\par\noindent " + ANSWER)

    def sample(self, rng):
        n = _pick(rng, self.cfg)
        s, d = 0, n - 1
        while d % 2 == 0:
            s, d = s + 1, d // 2
        rounds = []
        for a in BASES:
            if a >= n:
                break
            g = gcd(a, n)
            if g > 1:
                rounds.append({"a": a, "g": g, "verdict": "witness"})
                break
            xs = [pow(a, d, n)]
            ok = xs[0] in (1, n - 1)
            while not ok and len(xs) < s:
                xs.append(xs[-1] ** 2 % n)
                ok = xs[-1] == n - 1
            rounds.append({"a": a, "g": 1, "xs": xs, "verdict": "pass" if ok else "witness"})
            if not ok or (is_prime(n) and len(rounds) == 2):
                break
        prime = is_prime(n)
        return {"n": n, "s": s, "d": d, "rounds": rounds, "err": r"\frac{1}{16}",
                "factors": steps.factor_tex(n) if not prime else str(n),
                "answer": "prime" if prime else "composite"}

    def check(self, p):
        _check_rounds(p, 2)
        assert 2 ** p["s"] * p["d"] == p["n"] - 1 and p["d"] % 2 == 1
