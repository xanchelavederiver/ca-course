"""Discrete logarithm in (Z/pZ)^* (ported from main-2sem.py).

Instances: g^x = h (mod p), x in [3, ord(g)), h != g; the answer is x mod ord(g).
"""

import math

from taskgen.core import steps
from taskgen.core.nt import factorize, first_primes, inverse, is_order
from taskgen.core.task import SolutionDetail, Task

PRIMES = first_primes(40)
STATEMENT_HEAD = r"\[\VAR{g}^x \equiv \VAR{h}\ (\textrm{mod}\ \VAR{p}).\]"
TX = r"\BLOCK{import 'macros.tex.j2' as tx}"
ORDER = (r"$\ord(\VAR{g}) = \VAR{o}$: $\VAR{g}^{\VAR{o}} \equiv 1$\BLOCK{for c in ord_checks}, "
         r"$\VAR{g}^{\VAR{c.e}} \equiv \VAR{c.v}$\BLOCK{endfor}.")


def _order(g: int, p: int) -> int:
    from sage.all import Mod

    return int(Mod(g, p).multiplicative_order())


def _ord_checks(g: int, o: int, p: int) -> list[dict]:
    return [{"e": o // q, "v": pow(g, o // q, p)} for q in sorted(factorize(o))]


def _check_dlp(p):
    assert pow(p["g"], p["answer"], p["p"]) == p["h"]
    assert is_order(p["g"], p["o"], p["p"])
    assert p["g"] != p["h"]


def bsgs(g: int, h: int, p: int) -> dict:
    n = p - 1
    m = math.isqrt(n - 1) + 1  # ceil(sqrt(n))
    baby = [pow(g, j, p) for j in range(m)]
    g_inv = inverse(g, p)
    gm = pow(g_inv, m, p)
    giant = []
    for i in range(m):
        y = h * pow(gm, i, p) % p
        giant.append(y)
        if y in baby:
            j = baby.index(y)
            return {"n": n, "m": m, "baby": baby, "g_inv": g_inv, "gm": gm, "giant": giant,
                    "i": i, "j": j, "x": i * m + j}
    raise AssertionError("no collision")


class Shanks(Task):
    id = "dlp.shanks"
    title_ru = "Алгоритм Шенкса (baby-step giant-step)"
    topics = ("dlp.generic",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"primes": list(PRIMES[15:30])}}
    statement = (r"Решить задачу дискретного логарифмирования методом Шенкса: " + STATEMENT_HEAD +
                 r" Обосновать выбор длины списков.")
    solution = (r"Порядок $g$ делит $p - 1 = \VAR{s.n}$; при длине списков $m = \lceil\sqrt{\VAR{s.n}}\rceil "
                r"= \VAR{s.m}$ любой показатель $x < m^2$ записывается как $x = im + j$, $0 \le i, j < m$ "
                r"(а $m^2 \ge p - 1$). Малые шаги $g^j$:"
                r"\[\begin{array}{c|\BLOCK{for _ in s.baby}r\BLOCK{endfor}}"
                r"j\BLOCK{for x in s.baby} & \VAR{loop.index0}\BLOCK{endfor} \\ \hline "
                r"g^j\BLOCK{for x in s.baby} & \VAR{x}\BLOCK{endfor}\end{array}\]"
                r"$g^{-1} \equiv \VAR{s.g_inv}$, $g^{-m} \equiv \VAR{s.g_inv}^{\VAR{s.m}} \equiv \VAR{s.gm}$. "
                r"Большие шаги $h \cdot g^{-im}$ до совпадения:"
                r"\[\begin{array}{c|\BLOCK{for _ in s.giant}r\BLOCK{endfor}}"
                r"i\BLOCK{for x in s.giant} & \VAR{loop.index0}\BLOCK{endfor} \\ \hline "
                r"hg^{-im}\BLOCK{for x in s.giant} & \VAR{x}\BLOCK{endfor}\end{array}\]"
                r"Совпадение $h g^{-\VAR{s.i} \cdot \VAR{s.m}} = g^{\VAR{s.j}}$, откуда $x = \VAR{s.i} \cdot \VAR{s.m} + \VAR{s.j} "
                r"= \VAR{s.x}$. " + ORDER +
                r"\[x = \VAR{answer}\ (\textrm{mod}\ \VAR{o}).\]")

    def sample(self, rng):
        while True:
            p = rng.choice(self.cfg.primes)
            g = rng.choice(list(range(2, p // 2)))
            o = _order(g, p)
            if o > min((p - 1) // 2, 2**5):
                x = rng.randrange(3, o)
                h = pow(g, x, p)
                if g != h:
                    return {"g": g, "h": h, "p": p, "o": o, "s": bsgs(g, h, p),
                            "ord_checks": _ord_checks(g, o, p), "answer": x}

    def check(self, p):
        _check_dlp(p)
        assert p["s"]["x"] % p["o"] == p["answer"]


class PohligHellman(Task):
    id = "dlp.pohlig_hellman"
    title_ru = "Алгоритм Полига-Хеллмана"
    topics = ("dlp.pohlig_hellman",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"primes": list(PRIMES[10:30]), "min_factors": 3}}
    statement = (r"Решить задачу дискретного логарифмирования с помощью алгоритма Полига-Хеллмана: "
                 + STATEMENT_HEAD +
                 r" Решения частных задач и мультипликативно обратные можно находить перебором "
                 r"(«на глазок»). Систему необходимо выписать и решить в явном виде.")
    solution = (TX + ORDER + r" $\VAR{o} = \VAR{o_factor}$. Для каждого $q^e \parallel \VAR{o}$: "
                r"$g_i = g^{\VAR{o}/q^e}$, $h_i = h^{\VAR{o}/q^e}$, решаем $g_i^{x_i} = h_i$ перебором, "
                r"тогда $x \equiv x_i\ (\textrm{mod}\ q^e)$."
                r"\BLOCK{for s in subs}\par\noindent $q^e = \VAR{s.qe}$: $g_i = \VAR{g}^{\VAR{s.exp}} \equiv \VAR{s.gi}$, "
                r"$h_i = \VAR{h}^{\VAR{s.exp}} \equiv \VAR{s.hi}$; степени $g_i^k$, $k = 0, 1, \dots$: "
                r"$\VAR{s.powers|join(', ')}$ $\Rightarrow x_i = \VAR{s.xi}$.\BLOCK{endfor}"
                r"\par Система и её решение по КТО:\VAR{tx.crt(c)}"
                r"\[x = \VAR{answer}\ (\textrm{mod}\ \VAR{o}),\quad \VAR{o} = \VAR{o_factor}.\]")

    def sample(self, rng):
        from sage.all import factor

        while True:
            p = rng.choice(self.cfg.primes)
            g = rng.choice(list(range(2, p // 2)))
            o = _order(g, p)
            # legacy: "len(str(factor(o)).split('*')) > 2", i.e. >= 3 distinct primes
            if o > 3 and len(factor(o)) >= self.cfg.min_factors:
                x = rng.randrange(3, o)
                h = pow(g, x, p)
                if g != h:
                    break
        subs = []
        for q, e in sorted(factorize(o).items()):
            qe = q**e
            gi, hi = pow(g, o // qe, p), pow(h, o // qe, p)
            powers = [1]
            while powers[-1] != hi:
                powers.append(powers[-1] * gi % p)
            subs.append({"qe": qe, "exp": o // qe, "gi": gi, "hi": hi, "powers": powers,
                         "xi": len(powers) - 1})
        c = steps.crt([s["xi"] for s in subs], [s["qe"] for s in subs])
        return {"g": g, "h": h, "p": p, "o": o, "o_factor": steps.factor_tex(o),
                "ord_checks": _ord_checks(g, o, p), "subs": subs, "c": c, "answer": x}

    def check(self, p):
        _check_dlp(p)
        assert p["c"]["x"] == p["answer"]


# --- index calculus ---------------------------------------------------------------------


def _solve_mod_prime_power(eqs: list[tuple[list[int], int]], n_vars: int, q: int, mod: int):
    """Gaussian elimination mod q^e with unit pivots; returns (triangular rows, solution) or None."""
    A = [[c % mod for c in row] + [rhs % mod] for row, rhs in eqs]
    tri, r = [], 0
    for col in range(n_vars):
        piv = next((i for i in range(r, len(A)) if A[i][col] % q), None)
        if piv is None:
            return None
        A[r], A[piv] = A[piv], A[r]
        inv = inverse(A[r][col], mod)
        A[r] = [x * inv % mod for x in A[r]]
        for i in range(len(A)):
            if i != r and A[i][col]:
                f = A[i][col]
                A[i] = [(x - f * y) % mod for x, y in zip(A[i], A[r])]
        tri.append(A[r][:])
        r += 1
    return tri, [A[i][n_vars] for i in range(n_vars)]


def _lin(ex: list[int], fb: list[int]) -> str:
    """'L_{2} + 3L_{5}' for the exponent vector ex over the factor base fb."""
    terms = [f"{e if e > 1 else ''}L_{{{q}}}" for e, q in zip(ex, fb) if e]
    return " + ".join(terms) or "0"


def _mono(ex: list[int], fb: list[int]) -> str:
    return r" \cdot ".join(f"{q}^{{{e}}}" if e > 1 else str(q) for e, q in zip(ex, fb) if e) or "1"


def index_calculus(g: int, h: int, p: int) -> dict | None:
    n = p - 1
    L = math.exp(math.sqrt(math.log(p) * math.log(math.log(p))))
    B_est = L ** (1 / math.sqrt(2))
    B = max(3, round(B_est))
    fb = [q for q in first_primes(10) if q <= B]

    def smooth(v):
        ex = []
        for q in fb:
            e = 0
            while v % q == 0:
                v //= q
                e += 1
            ex.append(e)
        return ex if v == 1 else None

    def solve_all(rels):
        parts = []
        for q, e in sorted(factorize(n).items()):
            res = _solve_mod_prime_power([(r["ex"], r["k"]) for r in rels], len(fb), q, q**e)
            if res is None:
                return None
            parts.append({"q": q, "mod": q**e, "tri": res[0], "sol": res[1]})
        return parts

    rels, tried = [], []
    for k in range(1, n):
        v = pow(g, k, p)
        ex = smooth(v)
        tried.append({"k": k, "v": v, "smooth": ex is not None})
        if ex is None:
            continue
        rels.append({"k": k, "v": v, "ex": ex, "lin": _lin(ex, fb), "mono": _mono(ex, fb)})
        parts = solve_all(rels)
        if parts is not None:
            break
    else:
        return None
    # keep a minimal system: drop relations that are not needed for solvability
    for r in list(rels[:-1]):
        rest = [x for x in rels if x is not r]
        if solve_all(rest) is not None:
            rels = rest
    parts = solve_all(rels)
    logs = [steps.crt([pt["sol"][i] for pt in parts], [pt["mod"] for pt in parts])["x"]
            for i in range(len(fb))]
    for s in range(n):
        v = h * pow(g, s, p) % p
        ex = smooth(v)
        if ex is not None:
            x = (sum(e * lg for e, lg in zip(ex, logs)) - s) % n
            return {"n": n, "n_factor": steps.factor_tex(n), "L": f"{L:.2f}", "B_est": f"{B_est:.2f}",
                    "B": B, "fb": fb, "tried": tried, "rels": rels, "parts": parts, "logs": logs,
                    "s": s, "hv": v, "hex": ex, "hlin": _lin(ex, fb), "hmono": _mono(ex, fb), "x": x}
    return None


class IndexCalculus(Task):
    id = "dlp.index_calculus"
    title_ru = "Метод исчисления индексов"
    topics = ("dlp.index_calculus",)
    complexity = 3
    solution_detail = SolutionDetail.FULL
    notes = "g is a primitive root (the factor base must lie in <g>); legacy only required ord(g) > 3."
    presets = {"default": {"primes": list(PRIMES[20:-10])}}
    statement = (r"Решить задачу дискретного логарифмирования методом Исчисления индексов: "
                 + STATEMENT_HEAD +
                 r" Обосновать выбор значения параметра $B$. Систему необходимо выписать и решить "
                 r"в явном виде.")
    solution = (r"$g = \VAR{g}$ --- первообразный корень, логарифмы берутся по модулю $p - 1 = \VAR{ic.n} = "
                r"\VAR{ic.n_factor}$. Выбор $B$: $L(p) = e^{\sqrt{\ln p \ln\ln p}} \approx \VAR{ic.L}$, "
                r"$B \approx L(p)^{1/\sqrt 2} \approx \VAR{ic.B_est}$; берём $B = \VAR{ic.B}$, факторная база "
                r"$\{\VAR{ic.fb|join(', ')}\}$, неизвестные $L_\ell = \log_g \ell$."
                r"\par Вычисляем $g^k \bmod p$, $k = 1, 2, \dots$ и оставляем $B$-гладкие значения "
                r"(не гладкие: \BLOCK{for t in ic.tried if not t.smooth}$g^{\VAR{t.k}} \equiv \VAR{t.v}$"
                r"\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}). Достаточная для однозначного решения система:"
                r"\[\begin{array}{rcl}"
                r"\BLOCK{for r in ic.rels}g^{\VAR{r.k}} \equiv \VAR{r.v} = \VAR{r.mono} & \Rightarrow & "
                r"\VAR{r.k} \equiv \VAR{r.lin} \\ \BLOCK{endfor}"
                r"\end{array}\pmod{\VAR{ic.n}}\]"
                r"Решаем систему по модулю каждого примарного делителя $p - 1$ (метод Гаусса; ведущие "
                r"коэффициенты обратимы), ступенчатая форма "
                r"(в строке --- коэффициенты при \BLOCK{for l in ic.fb}$L_{\VAR{l}}$\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor} и правая часть):"
                r"\BLOCK{for pt in ic.parts}\par\noindent по модулю $\VAR{pt.mod}$: "
                r"\BLOCK{for row in pt.tri}$(\VAR{row[:-1]|join(', ')} \mid \VAR{row[-1]})$\BLOCK{if not loop.last}, "
                r"\BLOCK{endif}\BLOCK{endfor} $\Rightarrow$ "
                r"\BLOCK{for l in ic.fb}$L_{\VAR{l}} \equiv \VAR{pt.sol[loop.index0]}$\BLOCK{if not loop.last}, "
                r"\BLOCK{endif}\BLOCK{endfor};\BLOCK{endfor}"
                r"\par\noindent по КТО: \BLOCK{for l in ic.fb}$L_{\VAR{l}} = \VAR{ic.logs[loop.index0]}$"
                r"\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor} (проверка: \BLOCK{for l in ic.fb}"
                r"$\VAR{g}^{\VAR{ic.logs[loop.index0]}} \equiv \VAR{l}$\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor})."
                r"\par Ищем $s$ с $B$-гладким $h g^{s}$: $s = \VAR{ic.s}$, $\VAR{h} \cdot \VAR{g}^{\VAR{ic.s}} \equiv "
                r"\VAR{ic.hv} = \VAR{ic.hmono}$, откуда "
                r"$x \equiv \VAR{ic.hlin} - \VAR{ic.s} "
                r"\equiv \VAR{ic.x}\ (\textrm{mod}\ \VAR{ic.n})$."
                r"\[x = \VAR{answer}\ (\textrm{mod}\ \VAR{o}).\]")

    def sample(self, rng):
        while True:
            p = rng.choice(self.cfg.primes)
            g = rng.choice(list(range(2, p // 2)))
            o = _order(g, p)
            if o == p - 1:
                x = rng.randrange(3, o)
                h = pow(g, x, p)
                if g != h:
                    ic = index_calculus(g, h, p)
                    if ic is not None:
                        return {"g": g, "h": h, "p": p, "o": o, "ic": ic, "answer": x}

    def check(self, p):
        _check_dlp(p)
        ic = p["ic"]
        assert ic["x"] == p["answer"]
        for lg, ell in zip(ic["logs"], ic["fb"]):
            assert pow(p["g"], lg, p["p"]) == ell
