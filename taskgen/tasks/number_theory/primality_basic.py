"""Elementary primality tests (lecture sem1/08): Wilson's test, the Fermat test,
Carmichael numbers (Korselt's criterion) and the Fermat test vs Miller–Rabin.

Corner cases are the point of these tasks: n = 4 in Wilson's test, Fermat
pseudoprimes to base 2 and Carmichael numbers in the Fermat test (it passes for
every coprime base; only a base sharing a factor with N reveals it), squarefree
near-misses and non-squarefree numbers in Korselt's criterion, strong liars
(2047 = 23 * 89 to base 2) in Miller–Rabin.
"""

from functools import lru_cache
from math import factorial, gcd, prod

from taskgen.core import steps
from taskgen.core.nt import factorize, inverse, is_prime
from taskgen.core.task import SolutionDetail, Task

FERMAT_BASES = (2, 3, 5)


def _korselt_divisible(n: int) -> bool:
    return all((n - 1) % (p - 1) == 0 for p in factorize(n))


def is_carmichael(n: int) -> bool:
    """Korselt: n composite, squarefree, p - 1 | n - 1 for every p | n."""
    f = factorize(n)
    return n > 2 and not is_prime(n) and all(e == 1 for e in f.values()) and _korselt_divisible(n)


def carmichael_numbers(hi: int) -> list[int]:
    return [n for n in range(3, hi + 1, 2) if is_carmichael(n)]


def psp2_non_carmichael(hi: int) -> list[int]:
    """Odd composite Fermat pseudoprimes to base 2 that are not Carmichael numbers."""
    return [n for n in range(3, hi + 1, 2)
            if not is_prime(n) and pow(2, n - 1, n) == 1 and not is_carmichael(n)]


CARMICHAEL = carmichael_numbers(100_000)            # 561, 1105, 1729, ..., 75361
CARMICHAEL_SMALL = [n for n in CARMICHAEL if n < 16_000]
PSP2 = psp2_non_carmichael(10_000)                    # 341, 645, 1387, 1905, 2047, ...


def _mr_split(n: int) -> tuple[int, int]:
    s, d = 0, n - 1
    while d % 2 == 0:
        s, d = s + 1, d // 2
    return s, d


def _korselt_rows(n: int) -> list[dict]:
    return [{"p": p, "e": e, "pm1": p - 1, "rem": (n - 1) % (p - 1), "g": gcd(n - 1, p - 1)}
            for p, e in sorted(factorize(n).items())]


# --- Wilson's test ------------------------------------------------------------------------


class Wilson(Task):
    id = "number_theory.wilson"
    title_ru = "Тест простоты на основе теоремы Вильсона"
    topics = ("number_theory.primality",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("n in [4, 30]: primes and composites; n = 4 (the only composite with (n-1)! != 0 mod n) "
             "with probability four_ratio. For a prime n the solution pairs 2..n-2 into inverses.")
    presets = {"default": {"lo": 5, "hi": 30, "composite_ratio": 0.45, "four_ratio": 0.1}}
    statement = (r"С помощью теоремы Вильсона определить, является ли простым число $n = \VAR{n}$: "
                 r"вычислить $(n - 1)! \bmod n$, приводя по модулю $n$ после каждого умножения. "
                 r"Если $n$ окажется простым, разбить числа $2, 3, \ldots, n - 2$ на пары взаимно "
                 r"обратных по модулю $n$ и объяснить с их помощью полученный ответ.")
    solution = (r"Теорема Вильсона: $n > 1$ простое $\iff (n - 1)! \equiv -1 \pmod n$. "
                r"Вычисляем $f_k = k! \bmod \VAR{n}$ по правилу $f_k = f_{k-1} \cdot k \bmod \VAR{n}$"
                r"\BLOCK{if stopped} (как только $f_k = 0$, все дальнейшие $f_k$ тоже равны $0$)\BLOCK{endif}:"
                r"\BLOCK{for chunk in rows|batch(10)}\[\begin{array}{c|\BLOCK{for r in chunk}r\BLOCK{endfor}}"
                r"k\BLOCK{for r in chunk} & \VAR{r.k}\BLOCK{endfor} \\ \hline "
                r"k! \bmod \VAR{n}\BLOCK{for r in chunk} & \VAR{r.f}\BLOCK{endfor}"
                r"\end{array}\]\BLOCK{endfor}"
                r"\BLOCK{if prime}Получили $(\VAR{n} - 1)! \equiv \VAR{n - 1} \equiv -1 \pmod{\VAR{n}}$, "
                r"т.\,е. $n = \VAR{n}$ "
                r"--- простое. Пары $\{a, a^{-1}\}$, $a \ne a^{-1}$: "
                r"\BLOCK{for pr in pairs}$\{\VAR{pr[0]}, \VAR{pr[1]}\}$\BLOCK{if not loop.last}, "
                r"\BLOCK{endif}\BLOCK{endfor}\BLOCK{if not pairs}пар нет ($n - 2 < 2$)\BLOCK{endif}. "
                r"Произведение каждой пары $\equiv 1$; из сомножителей $(n - 1)!$ остаются $1$ и $n - 1$ "
                r"(единственные решения $x^2 \equiv 1$), поэтому $(n - 1)! \equiv 1 \cdot (n - 1) \equiv -1$."
                r"\BLOCK{elif n == 4}Получили $3! = 6 \equiv 2 \not\equiv -1 \pmod 4$: $n = 4$ --- составное. "
                r"Это единственное составное $n$, для которого $(n - 1)! \not\equiv 0 \pmod n$: "
                r"$4 = 2 \cdot 2$, а множитель $2$ входит в $3!$ лишь один раз."
                r"\BLOCK{else}Уже $\VAR{k0}! = \VAR{k0_fact} = \VAR{n} \cdot \VAR{k0_fact // n}$ делится на "
                r"$\VAR{n}$, поэтому "
                r"$(\VAR{n} - 1)! \equiv 0 \not\equiv -1 \pmod{\VAR{n}}$: $n = \VAR{n} = \VAR{factors}$ "
                r"--- составное. \BLOCK{if square}Здесь $n = p^2$, $p = \VAR{p}$: множители $p = \VAR{p}$ и "
                r"$2p = \VAR{2 * p}$ различны и меньше $n$ (при $p > 2$), поэтому $p^2 \mid (n - 1)!$."
                r"\BLOCK{else}Здесь $n = ab$ с $1 < a < b < n$ (например, $a = \VAR{a}$, $b = \VAR{b}$): "
                r"оба множителя входят в $(n - 1)!$, поэтому $n \mid (n - 1)!$.\BLOCK{endif}\BLOCK{endif}")

    def sample(self, rng):
        cfg = self.cfg
        if rng.random() < cfg.four_ratio:
            n = 4
        elif rng.random() < cfg.composite_ratio:
            n = rng.choice([k for k in range(max(cfg.lo, 6), cfg.hi + 1) if not is_prime(k)])
        else:
            n = rng.choice([k for k in range(cfg.lo, cfg.hi + 1) if is_prime(k)])
        rows, f, stopped = [], 1, False
        for k in range(1, n):
            f = f * k % n
            rows.append({"k": k, "f": f})
            if f == 0:
                stopped = k < n - 1
                break
        prime = is_prime(n)
        ctx = {"n": n, "rows": rows, "stopped": stopped, "prime": prime, "pairs": [],
               "k0": None, "k0_fact": None, "a": None, "b": None, "square": False, "p": None,
               "factors": steps.factor_tex(n), "residue": factorial(n - 1) % n}
        if prime:
            ctx["pairs"] = [[a, inverse(a, n)] for a in range(2, n - 1) if a < inverse(a, n)]
        elif n != 4:
            k0 = rows[-1]["k"]
            p = min(factorize(n))
            square = n == p * p
            a, b = (p, 2 * p) if square else (p, n // p)
            if not square and a == b:      # n = p^2 * m: split off p^2 instead
                a, b = p * p, n // (p * p)
            a, b = min(a, b), max(a, b)
            ctx.update({"k0": k0, "k0_fact": factorial(k0), "a": a, "b": b, "square": square, "p": p})
        ctx["answer"] = {"prime": prime, "residue": ctx["residue"]}
        return ctx

    def check(self, p):
        n = p["n"]
        res = factorial(n - 1) % n
        assert p["answer"]["residue"] == res
        assert p["answer"]["prime"] == is_prime(n) == (res == n - 1)
        if not p["answer"]["prime"]:
            assert res == (2 if n == 4 else 0)
            if n != 4:
                k0 = p["k0"]
                assert factorial(k0) % n == 0 and factorial(k0 - 1) % n != 0
                if p["square"]:
                    assert p["b"] == 2 * p["a"] and p["a"] ** 2 == n
                else:
                    assert 1 < p["a"] < p["b"] < n and p["a"] * p["b"] == n
        else:
            paired = sorted(x for pr in p["pairs"] for x in pr)
            assert paired == list(range(2, n - 1))
            assert all(x * y % n == 1 for x, y in p["pairs"])
        f = 1
        for r in p["rows"]:
            f = f * r["k"] % n
            assert r["f"] == f


# --- the Fermat test ---------------------------------------------------------------------


def _fermat_candidates(cfg, kind: str) -> list[int]:
    return _fermat_pool(cfg.lo, cfg.hi, kind)


@lru_cache(maxsize=None)
def _fermat_pool(lo: int, hi: int, kind: str) -> list[int]:
    if kind == "prime":
        return [n for n in range(lo | 1, hi + 1, 2) if is_prime(n)]
    if kind == "composite":
        return [n for n in range(lo | 1, hi + 1, 2) if not is_prime(n) and min(factorize(n)) >= 7
                and pow(2, n - 1, n) != 1]
    if kind == "psp2":
        return list(PSP2)
    return list(CARMICHAEL_SMALL)


class FermatTest(Task):
    id = "number_theory.fermat_test"
    title_ru = "Тест простоты Ферма; числа Кармайкла"
    topics = ("number_theory.primality",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("N: prime / ordinary composite (smallest factor >= 7) / Fermat pseudoprime to base 2 that is "
             "not Carmichael (341, 645, 1387, 2047, ...) / Carmichael number < 16000. Bases 2, 3, 5: "
             "1729, 2821, 6601, 8911, 15841 pass all three (the test is fooled), 561, 1105, 2465, 10585 "
             "are caught only by a base sharing a factor. Preset 'carmichael': Carmichael numbers only.")
    presets = {
        "default": {"lo": 300, "hi": 3000,
                    "kinds": {"prime": 0.3, "composite": 0.2, "psp2": 0.2, "carmichael": 0.3}},
        "carmichael": {"kinds": {"carmichael": 1.0}},
    }
    statement = (r"Выполнить тест Ферма для числа $N = \VAR{n}$ с основаниями $a = 2, 3, 5$ (по порядку; "
                 r"остановиться на первом свидетеле составности). Каков вердикт теста? Затем проверить "
                 r"его, разложив $N$ на множители, и, если $N$ составное, проверить для $N$ критерий "
                 r"Корсельта: является ли $N$ числом Кармайкла?")
    solution = (r"Для простого $N$ и $\gcd(a, N) = 1$ по малой теореме Ферма $a^{N-1} \equiv 1 \pmod N$; "
                r"если $\gcd(a, N) > 1$ или $a^{N-1} \not\equiv 1$, то $a$ --- свидетель составности. "
                r"$N - 1 = \VAR{n - 1} = (\VAR{bits})_2$. "
                r"\BLOCK{for r in rounds}\BLOCK{if r.g > 1}$\gcd(\VAR{r.a}, \VAR{n}) = \VAR{r.g} > 1$: "
                r"$a = \VAR{r.a}$ --- свидетель. \BLOCK{else}$\gcd(\VAR{r.a}, \VAR{n}) = 1$. \BLOCK{endif}"
                r"\BLOCK{endfor}"
                r"\BLOCK{if powered}Возведение в степень $N - 1$ слева направо ($r \gets r^2$, "
                r"при бите $1$ ещё $r \gets r a$; $e$ --- уже обработанная часть показателя):"
                r"\[\begin{array}{c|r\BLOCK{for r in powered}|r\BLOCK{endfor}}"
                r"\text{бит} & e\BLOCK{for r in powered} & \VAR{r.a}^{e} \bmod N\BLOCK{endfor} \\ \hline "
                r"\BLOCK{for i in range(bits|length)}\VAR{bits[i]} & \VAR{powered[0].steps[i].e}"
                r"\BLOCK{for r in powered} & \VAR{r.steps[i].r}\BLOCK{endfor} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"\BLOCK{for r in powered}$\VAR{r.a}^{\VAR{n - 1}} \equiv \VAR{r.value}$"
                r"\BLOCK{if r.value == 1} --- раунд пройден\BLOCK{else} $\ne 1$ --- $a = \VAR{r.a}$ свидетель "
                r"составности\BLOCK{endif}\BLOCK{if not loop.last}; \BLOCK{else}.\BLOCK{endif}\BLOCK{endfor}"
                r"\BLOCK{endif}\par\noindent "
                r"\textbf{Вердикт:} \BLOCK{if verdict == 'composite'}$N$ составное (свидетель $a = \VAR{rounds[-1].a}$)."
                r"\BLOCK{else}$N$ --- вероятно простое по основаниям $2, 3, 5$.\BLOCK{endif}"
                r"\par\noindent \textbf{Проверка.} \BLOCK{if prime}Пробное деление на простые "
                r"$p \le \sqrt{N} \approx \VAR{sqrt_n}$ делителей не даёт: $N$ простое, вердикт верен."
                r"\BLOCK{else}$N = \VAR{factors}$ --- составное"
                r"\BLOCK{if verdict != 'composite'}: тест Ферма \emph{ошибся}\BLOCK{endif}. "
                r"Критерий Корсельта: $N$ --- число Кармайкла $\iff$ $N$ свободно от квадратов и $p - 1 \mid N - 1$ "
                r"для всех $p \mid N$. \BLOCK{if not squarefree}$N$ делится на квадрат простого: $N$ не является "
                r"числом Кармайкла.\BLOCK{else}"
                r"\BLOCK{for k in korselt}$\VAR{n - 1} \bmod \VAR{k.pm1} = \VAR{k.rem}$\BLOCK{if not loop.last}, "
                r"\BLOCK{endif}\BLOCK{endfor}"
                r"\BLOCK{if carmichael} --- все делимости выполнены: $N$ --- \textbf{число Кармайкла}, "
                r"$a^{N-1} \equiv 1$ для \emph{всех} $a$, взаимно простых с $N$; выявить составность тестом "
                r"Ферма может только основание, имеющее общий делитель с $N$"
                r"\BLOCK{if verdict == 'composite'} (так и произошло при $a = \VAR{rounds[-1].a}$)\BLOCK{endif}."
                r"\BLOCK{else} --- не все делимости выполнены: $N$ не является числом Кармайкла "
                r"(свидетели Ферма, взаимно простые с $N$, составляют не менее половины $\Znx{N}$)."
                r"\BLOCK{endif}\BLOCK{endif}\BLOCK{endif}")

    def sample(self, rng):
        kinds = self.cfg.kinds
        u, acc, kind = rng.random(), 0.0, None
        for k, w in kinds.items():
            acc += w
            if u < acc:
                kind = k
                break
        kind = kind or list(kinds)[-1]
        n = rng.choice(_fermat_candidates(self.cfg, kind))
        rounds, powered = [], []
        for a in FERMAT_BASES:
            g = gcd(a, n)
            if g > 1:
                rounds.append({"a": a, "g": g, "value": None})
                break
            st = steps.binary_pow_steps(a, n - 1, n)
            r = {"a": a, "g": 1, "steps": st, "value": st[-1]["r"]}
            rounds.append(r)
            powered.append(r)
            if r["value"] != 1:
                break
        last = rounds[-1]
        verdict = "composite" if (last["g"] > 1 or last["value"] != 1) else "probable_prime"
        prime = is_prime(n)
        f = factorize(n)
        return {"n": n, "kind": kind, "bits": format(n - 1, "b"), "rounds": rounds, "powered": powered,
                "verdict": verdict, "prime": prime, "factors": steps.factor_tex(n),
                "sqrt_n": int(n ** 0.5), "squarefree": all(e == 1 for e in f.values()),
                "korselt": _korselt_rows(n) if not prime else [],
                "carmichael": is_carmichael(n),
                "answer": {"verdict": verdict, "prime": prime, "carmichael": is_carmichael(n)}}

    def check(self, p):
        n, ans = p["n"], p["answer"]
        assert ans["prime"] == is_prime(n)
        # independent Fermat test
        verdict = "probable_prime"
        for a in FERMAT_BASES:
            if pow(a, n - 1, n) != 1:
                verdict, wit = "composite", a
                break
        assert ans["verdict"] == verdict
        if verdict == "composite":
            assert p["rounds"][-1]["a"] == wit
        if ans["prime"]:
            assert verdict == "probable_prime" and not ans["carmichael"]
        else:
            # Carmichael by definition (brute force over the coprime bases)
            brute = all(pow(a, n - 1, n) == 1 for a in range(2, n) if gcd(a, n) == 1)
            assert ans["carmichael"] == brute
        for r in p["powered"]:
            assert pow(r["a"], n - 1, n) == r["value"]
            assert len(r["steps"]) == len(p["bits"])


# --- Korselt's criterion --------------------------------------------------------------------


@lru_cache(maxsize=None)
def _near_misses(hi: int) -> list[int]:
    """Odd squarefree n = pqr (p < q < r odd primes) <= hi, not Carmichael, but q-1 and r-1 or
    p-1 and one more divide n-1 (all but one condition hold)."""
    out = []
    for n in range(105, hi + 1, 2):
        f = factorize(n)
        if len(f) == 3 and all(e == 1 for e in f.values()) and not is_carmichael(n):
            if sum((n - 1) % (q - 1) == 0 for q in f) == 2:
                out.append(n)
    return out


@lru_cache(maxsize=None)
def _nonsquarefree_korselt(hi: int) -> list[int]:
    """Odd non-squarefree composite n <= hi with p - 1 | n - 1 for all p | n (e.g. 45 = 3^2 * 5)."""
    return [n for n in range(9, hi + 1, 2)
            if not is_prime(n) and any(e > 1 for e in factorize(n).values()) and len(factorize(n)) > 1
            and _korselt_divisible(n)]


class CarmichaelCheck(Task):
    id = "number_theory.carmichael_check"
    title_ru = "Числа Кармайкла: критерий Корсельта"
    topics = ("number_theory.primality",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("n: a Carmichael number < 70000, a squarefree pqr where exactly one Korselt divisibility "
             "fails, or (corner) a non-squarefree n where all divisibilities p - 1 | n - 1 hold "
             "(45, 225, 325, ...). For squarefree n the number of Fermat liars prod gcd(n-1, p-1) is asked.")
    presets = {"default": {"hi": 70_000, "carmichael_ratio": 0.45, "nonsquarefree_ratio": 0.15}}
    statement = (r"Является ли число $n = \VAR{n}$ числом Кармайкла? Воспользоваться критерием "
                 r"Корсельта. Если $n$ свободно от квадратов, найти число $L$ оснований "
                 r"$a \in \Znx{n}$, для которых тест Ферма ошибается ($a^{n-1} \equiv 1 \pmod n$), "
                 r"и долю $L / \varphi(n)$.")
    solution = (r"Разложение: $n = \VAR{factors}$, $n - 1 = \VAR{n - 1}$. Критерий Корсельта: составное $n$ "
                r"--- число Кармайкла $\iff$ $n$ свободно от квадратов и $p - 1 \mid n - 1$ для всех "
                r"простых $p \mid n$."
                r"\[\begin{array}{r|r|r|r}"
                r"p & p - 1 & (n - 1) \bmod (p - 1) & \gcd(n - 1, p - 1) \\ \hline "
                r"\BLOCK{for k in rows}\VAR{k.p}\BLOCK{if k.e > 1}^{\VAR{k.e}}\BLOCK{endif} & \VAR{k.pm1} & "
                r"\VAR{k.rem} & \VAR{k.g} \\ \BLOCK{endfor}\end{array}\]"
                r"\BLOCK{if not squarefree}Все делимости $p - 1 \mid n - 1$ выполнены, но $n$ делится на "
                r"$\VAR{sq_p}^2$: $n$ \textbf{не} число Кармайкла. Свидетель, взаимно простой с $n$: "
                r"$a = 1 + n/\VAR{sq_p} = \VAR{wit}$ (тогда $a^{k} \equiv 1 + k\,n/\VAR{sq_p} \pmod n$, "
                r"и $a^{n-1} \equiv \VAR{wit_pow} \ne 1$, так как $\VAR{sq_p} \nmid n - 1$)."
                r"\BLOCK{else}$n$ свободно от квадратов; "
                r"\BLOCK{if carmichael}все делимости выполнены: $n$ --- \textbf{число Кармайкла}."
                r"\BLOCK{else}$p - 1 \nmid n - 1$ при $p = \VAR{bad|join(', ')}$: $n$ \textbf{не} число "
                r"Кармайкла.\BLOCK{endif}"
                r" По китайской теореме об остатках $a^{n-1} \equiv 1 \pmod n$ $\iff$ "
                r"$a^{n-1} \equiv 1 \pmod p$ для всех $p \mid n$; группа $\Znx{p}$ циклическая порядка $p - 1$, "
                r"и уравнение $x^{n-1} = 1$ имеет в ней $\gcd(n - 1, p - 1)$ решений. Поэтому "
                r"\[L = \prod_{p \mid n} \gcd(n - 1, p - 1) = \VAR{gs|join(' \\cdot ')} = \VAR{liars},\]"
                r"\[\varphi(n) = \prod_{p \mid n} (p - 1) = \VAR{phis|join(' \\cdot ')} = \VAR{phi}, \qquad "
                r"\frac{L}{\varphi(n)} = \BLOCK{if liars == phi}1\BLOCK{else}\frac{1}{\VAR{phi // liars}}"
                r"\BLOCK{endif}.\]"
                r"\BLOCK{if carmichael}Тест Ферма ошибается для всех $a$, взаимно простых с $n$."
                r"\BLOCK{else}Лжесвидетели составляют подгруппу $\Znx{n}$ индекса $\VAR{phi // liars} \ge 2$."
                r"\BLOCK{endif}\BLOCK{endif}")

    def sample(self, rng):
        cfg = self.cfg
        u = rng.random()
        if u < cfg.nonsquarefree_ratio:
            n = rng.choice(_nonsquarefree_korselt(cfg.hi // 10))
        elif u < cfg.nonsquarefree_ratio + cfg.carmichael_ratio:
            n = rng.choice([c for c in CARMICHAEL if c <= cfg.hi])
        else:
            n = rng.choice(_near_misses(cfg.hi // 4))
        f = factorize(n)
        rows = _korselt_rows(n)
        squarefree = all(e == 1 for e in f.values())
        carm = is_carmichael(n)
        ctx = {"n": n, "factors": steps.factor_tex(n), "rows": rows, "squarefree": squarefree,
               "carmichael": carm, "bad": [r["p"] for r in rows if r["rem"]],
               "sq_p": None, "wit": None, "wit_pow": None, "gs": [], "phis": [], "liars": None, "phi": None}
        if squarefree:
            ctx["gs"] = [r["g"] for r in rows]
            ctx["phis"] = [r["pm1"] for r in rows]
            ctx["liars"] = prod(ctx["gs"])
            ctx["phi"] = prod(ctx["phis"])
        else:
            q = min(p for p, e in f.items() if e > 1)
            wit = 1 + n // q
            ctx.update({"sq_p": q, "wit": wit, "wit_pow": pow(wit, n - 1, n)})
        ctx["answer"] = {"carmichael": carm, "liars": ctx["liars"]}
        return ctx

    def check(self, p):
        n = p["n"]
        assert not is_prime(n) and n % 2 == 1
        coprime = [a for a in range(1, n) if gcd(a, n) == 1]
        liars = sum(pow(a, n - 1, n) == 1 for a in coprime)
        assert p["answer"]["carmichael"] == (liars == len(coprime))
        if p["squarefree"]:
            assert p["answer"]["liars"] == liars and p["phi"] == len(coprime)
            assert p["phi"] % liars == 0
        else:
            assert not p["answer"]["carmichael"]
            w = p["wit"]
            assert gcd(w, n) == 1 and pow(w, n - 1, n) == p["wit_pow"] != 1
            assert p["wit_pow"] == (1 + (n - 1) * (n // p["sq_p"])) % n


# --- Fermat liar vs Miller–Rabin --------------------------------------------------------------


class FermatVsMillerRabin(Task):
    id = "number_theory.fermat_vs_miller_rabin"
    title_ru = "Тест Ферма и тест Миллера-Рабина на псевдопростых числах"
    topics = ("number_theory.primality",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("N: a Carmichael number < 16000 or a Fermat pseudoprime to base 2 < 10000; the base a is a "
             "Fermat liar from {2, 3, 5, 7}. Usually Miller-Rabin finds a nontrivial square root of 1 and "
             "a factor gcd(x - 1, N); corner case: a strong liar (e.g. N = 2047, a = 2), where both tests fail.")
    presets = {"default": {"carmichael_ratio": 0.6}}
    statement = (r"Убедиться, что число $N = \VAR{n}$ проходит тест Ферма по основанию $a = \VAR{a}$. "
                 r"Выполнить для $N$ и $a$ тест Миллера-Рабина. Если найден нетривиальный квадратный корень "
                 r"из единицы по модулю $N$, найти с его помощью нетривиальный делитель $N$.")
    solution = (r"$N - 1 = \VAR{n - 1} = 2^{\VAR{s}} \cdot \VAR{d}$. Вычисляем $x_0 = \VAR{a}^{\VAR{d}} \bmod N$ "
                r"и $x_{i} = x_{i-1}^2 \bmod N$, $i = \BLOCK{if s > 1}1, \ldots, \BLOCK{endif}\VAR{s}$ "
                r"(тогда $x_{\VAR{s}} = a^{N-1}$). "
                r"Для $x_0$ --- бинарный метод слева направо, $d = (\VAR{dbits})_2$, $e$ --- обработанная "
                r"часть показателя:"
                r"\BLOCK{for chunk in dsteps|batch(5)}\[\begin{array}{c|\BLOCK{for t in chunk}r\BLOCK{endfor}}"
                r"e\BLOCK{for t in chunk} & \VAR{t.e}\BLOCK{endfor} \\ \hline "
                r"\VAR{a}^e \bmod N\BLOCK{for t in chunk} & \VAR{t.r}\BLOCK{endfor}\end{array}\]\BLOCK{endfor}"
                r"Последовательность $x_i$:"
                r"\[\begin{array}{c|\BLOCK{for x in xs}r\BLOCK{endfor}}"
                r"i\BLOCK{for x in xs} & \VAR{loop.index0}\BLOCK{endfor} \\ \hline "
                r"x_i\BLOCK{for x in xs} & \VAR{x}\BLOCK{endfor}\end{array}\]"
                r"$x_{\VAR{s}} = \VAR{a}^{N-1} \equiv 1 \pmod N$: тест Ферма пройден, хотя $N = \VAR{factors}$ "
                r"составное (\BLOCK{if carmichael}$N$ --- число Кармайкла\BLOCK{else}$N$ --- псевдопростое по "
                r"основанию $\VAR{a}$\BLOCK{endif}). "
                r"\BLOCK{if liar}Последовательность \BLOCK{if xs[0] == 1}начинается с $x_0 = 1$"
                r"\BLOCK{else}содержит $x_{\VAR{j}} = N - 1 \equiv -1$ ($\VAR{j} < s = \VAR{s}$)\BLOCK{endif}: "
                r"условие теста Миллера-Рабина выполнено, $a = \VAR{a}$ --- \textbf{сильный лжесвидетель}, "
                r"$N$ --- сильно псевдопростое по основанию $\VAR{a}$. Оба теста ошиблись; составность выявит "
                r"другое основание (для составного $N$ сильных лжесвидетелей не более $\varphi(N)/4$)."
                r"\BLOCK{else}Тест Миллера-Рабина: $x_0 \ne 1$ и $-1$ не встречается среди "
                r"$x_0, \ldots, x_{\VAR{s - 1}}$, значит, $a = \VAR{a}$ --- \textbf{свидетель Миллера}, $N$ составное. "
                r"При этом $x = x_{\VAR{j}} = \VAR{x}$: $x^2 \equiv 1$, $x \not\equiv \pm 1 \pmod N$ --- "
                r"нетривиальный корень из $1$. Так как $N \mid (x - 1)(x + 1)$, но $N$ не делит ни один "
                r"из сомножителей, \[\begin{gathered}\gcd(x - 1, N) = \gcd(\VAR{x - 1}, \VAR{n}) = \VAR{g1},\\ "
                r"\gcd(x + 1, N) = \gcd(\VAR{x + 1}, \VAR{n}) = \VAR{g2},\end{gathered}\] "
                r"$N = \VAR{g1} \cdot \VAR{g2}$.\BLOCK{endif}")

    def sample(self, rng):
        if rng.random() < self.cfg.carmichael_ratio:
            n = rng.choice(CARMICHAEL_SMALL)
        else:
            n = rng.choice(PSP2)
        bases = [a for a in (2, 3, 5, 7) if gcd(a, n) == 1 and pow(a, n - 1, n) == 1]
        a = rng.choice(bases)
        s, d = _mr_split(n)
        xs = [pow(a, d, n)]
        for _ in range(s):
            xs.append(xs[-1] ** 2 % n)
        liar = xs[0] == 1 or (n - 1) in xs[:s]
        ctx = {"n": n, "a": a, "s": s, "d": d, "xs": xs, "liar": liar, "factors": steps.factor_tex(n),
               "dbits": format(d, "b"), "dsteps": steps.binary_pow_steps(a, d, n),
               "carmichael": is_carmichael(n), "j": None, "x": None, "g1": None, "g2": None}
        if liar:
            ctx["j"] = None if xs[0] == 1 else xs.index(n - 1)
        else:
            j = next(i for i in range(s) if xs[i + 1] == 1 and xs[i] != 1)
            x = xs[j]
            ctx.update({"j": j, "x": x, "g1": gcd(x - 1, n), "g2": gcd(x + 1, n)})
        ctx["answer"] = {"miller_rabin": "liar" if liar else "witness", "factor": ctx["g1"]}
        return ctx

    def check(self, p):
        n, a = p["n"], p["a"]
        assert not is_prime(n) and pow(a, n - 1, n) == 1
        s, d = p["s"], p["d"]
        assert 2**s * d == n - 1 and d % 2 == 1
        x0 = pow(a, d, n)
        assert p["dsteps"][-1]["r"] == x0 == p["xs"][0]
        strong = x0 == 1 or any(pow(a, 2**i * d, n) == n - 1 for i in range(s))
        assert (p["answer"]["miller_rabin"] == "liar") == strong
        if not strong:
            g = p["answer"]["factor"]
            assert 1 < g < n and n % g == 0 and g * p["g2"] == n
            x = p["x"]
            assert x * x % n == 1 and x not in (1, n - 1)
