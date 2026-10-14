"""Collision algorithms for the DLP (lecture sem2/03): Pollard's rho with Floyd's cycle
finding, the distinguished-points variant, and numeric collision-probability estimates.

Iteration function (HAC 3.60 / Pollard 1978), x in <g> < (Z/pZ)^*, x = g^a h^b:
    x = 0 (mod 3): x -> x^2,  (a, b) -> (2a, 2b)
    x = 1 (mod 3): x -> h x,  (a, b) -> (a, b + 1)
    x = 2 (mod 3): x -> g x,  (a, b) -> (a + 1, b)
exponents mod n = ord(g). A collision g^a h^b = g^a' h^b' gives (b - b') x = a' - a (mod n).
"""

from __future__ import annotations

import math
from math import gcd

from taskgen.core import steps
from taskgen.core.nt import first_primes, is_order, is_prime
from taskgen.core.task import SolutionDetail, Task

TX = r"\BLOCK{import 'macros.tex.j2' as tx}"
MOD = r"\ (\textrm{mod}\ \VAR{n})"


def _order(g: int, p: int) -> int:
    from sage.all import Mod

    return int(Mod(g, p).multiplicative_order())


def rho_step(x: int, a: int, b: int, g: int, h: int, p: int, n: int) -> tuple[int, int, int]:
    r = x % 3
    if r == 0:
        return x * x % p, 2 * a % n, 2 * b % n
    if r == 1:
        return h * x % p, a, (b + 1) % n
    return g * x % p, (a + 1) % n, b


def solve_collision(a1: int, b1: int, a2: int, b2: int, g: int, h: int, p: int, n: int) -> dict | None:
    """g^a1 h^b1 = g^a2 h^b2  =>  (b1 - b2) x = a2 - a1 (mod n); all candidates, checked."""
    u, v = (b1 - b2) % n, (a2 - a1) % n
    if u == 0:
        return None
    d = gcd(u, n)
    assert v % d == 0, "h is not in <g>"
    nd = n // d
    inv = steps.inverse_rows(u // d, nd)
    x0 = (v // d) * inv["inv"] % nd
    cands = [{"x": x0 + k * nd, "v": pow(g, x0 + k * nd, p)} for k in range(d)]
    good = [c["x"] for c in cands if c["v"] == h]
    assert len(good) == 1
    return {"u": u, "v": v, "d": d, "nd": nd, "ud": u // d, "vd": v // d, "inv": inv, "x0": x0,
            "cands": cands, "x": good[0], "trivial_inv": u // d % nd == 1}


def floyd_trace(g: int, h: int, p: int, n: int, a0: int, b0: int, max_rows: int) -> list[dict] | None:
    """Rows (x_i, a_i, b_i, x_2i, a_2i, b_2i), i = 0..m, x_m = x_2m (m >= 1)."""
    t = (pow(g, a0, p) * pow(h, b0, p) % p, a0, b0)
    rows = [{"i": 0, "t": t, "h": t}]
    hare = t
    for i in range(1, max_rows):
        t = rho_step(*t, g, h, p, n)
        hare = rho_step(*rho_step(*hare, g, h, p, n), g, h, p, n)
        rows.append({"i": i, "t": t, "h": hare})
        if t[0] == hare[0]:
            return rows
    return None


def _orbit(g, h, p, n, a0, b0) -> tuple[int, int]:
    """Tail length T and cycle length M of the orbit of x_0 (on the x values)."""
    x = pow(g, a0, p) * pow(h, b0, p) % p
    seen, t, i = {}, (x, a0, b0), 0
    while t[0] not in seen:
        seen[t[0]] = i
        t = rho_step(*t, g, h, p, n)
        i += 1
    return seen[t[0]], i - seen[t[0]]


def _floyd_params(g, h, p, n, x, rng, max_rows, min_rows, need_gcd, max_d):
    for _ in range(200):
        a0, b0 = rng.randrange(n), rng.randrange(n)
        rows = floyd_trace(g, h, p, n, a0, b0, max_rows)
        if rows is None or len(rows) - 1 < min_rows:
            continue
        (xm, a1, b1), (_, a2, b2) = rows[-1]["t"], rows[-1]["h"]
        s = solve_collision(a1, b1, a2, b2, g, h, p, n)
        if s is None or s["d"] > max_d or (need_gcd and s["d"] == 1) or s["x"] != x:
            continue
        T, M = _orbit(g, h, p, n, a0, b0)
        return {"a0": a0, "b0": b0, "x0": rows[0]["t"][0], "rows": rows, "m": len(rows) - 1,
                "a1": a1, "b1": b1, "a2": a2, "b2": b2, "xm": xm, "sol": s, "T": T, "M": M}
    return None


ITER_TEX = (r"\[f(x) = \begin{cases} x^2, & x \equiv 0,\\ \VAR{h}\, x, & x \equiv 1,\\ "
            r"\VAR{g}\, x, & x \equiv 2 \end{cases} \pmod 3, \qquad "
            r"(\alpha, \beta) \mapsto \begin{cases} (2\alpha, 2\beta),\\ (\alpha, \beta + 1),\\ "
            r"(\alpha + 1, \beta), \end{cases}\]")

# Shared: the linear congruence after a collision g^{a1} h^{b1} = g^{a2} h^{b2}.
SOLVE_TEX = (
    r"\par Из $g^{\VAR{c.a1}} h^{\VAR{c.b1}} = g^{\VAR{c.a2}} h^{\VAR{c.b2}}$ и $h = g^x$ получаем "
    r"$(\VAR{c.b1} - \VAR{c.b2})\, x \equiv \VAR{c.a2} - \VAR{c.a1}" + MOD + r"$, т.\,е. "
    r"$\VAR{s.u}\, x \equiv \VAR{s.v}" + MOD + r"$. "
    r"\BLOCK{if s.d == 1}$\gcd(\VAR{s.u}, \VAR{n}) = 1$, решение единственно: $x \equiv \VAR{s.v} \cdot "
    r"\VAR{s.u}^{-1}$.\BLOCK{else}$d = \gcd(\VAR{s.u}, \VAR{n}) = \VAR{s.d} > 1$ и $d \mid \VAR{s.v}$: "
    r"сокращаем на $d$: $\BLOCK{if s.ud != 1}\VAR{s.ud}\, \BLOCK{endif}x \equiv \VAR{s.vd}\ (\textrm{mod}\ \VAR{s.nd})$; "
    r"по модулю $\VAR{n}$ получится $d = \VAR{s.d}$ кандидатов.\BLOCK{endif}"
    r"\BLOCK{if s.trivial_inv}\par $\tilde x \equiv \VAR{s.x0}\ (\textrm{mod}\ \VAR{s.nd})$.\BLOCK{else} "
    r"\VAR{tx.inverse(s.inv)}"
    r"\par $\tilde x \equiv \VAR{s.vd} \cdot \VAR{s.inv.inv} \equiv \VAR{s.x0}\ (\textrm{mod}\ \VAR{s.nd})$.\BLOCK{endif}"
    r"\BLOCK{if s.d > 1} Кандидаты $x = \tilde x + k \cdot \VAR{s.nd}$, $k = 0, \dots, \VAR{s.d - 1}$; "
    r"проверяем $g^x \equiv h$: \BLOCK{for t in s.cands}$\VAR{g}^{\VAR{t.x}} \equiv \VAR{t.v}$"
    r"\BLOCK{if t.x == s.x}\ (\checkmark)\BLOCK{endif}\BLOCK{if not loop.last}, \BLOCK{else}.\BLOCK{endif}"
    r"\BLOCK{endfor}\BLOCK{else} Проверка: $\VAR{g}^{\VAR{s.x}} \equiv \VAR{h}\ (\textrm{mod}\ \VAR{p})$."
    r"\BLOCK{endif}")


def _subgroup(rng, cfg) -> tuple[int, int, int]:
    """(p, q, g): prime q in [qlo, qhi], prime p = kq + 1 <= pmax, ord(g) = q."""
    qs = [q for q in first_primes(60) if cfg.qlo <= q <= cfg.qhi]
    while True:
        q = rng.choice(qs)
        ks = [k for k in range(2, cfg.pmax // q + 1, 2) if is_prime(k * q + 1)]
        if not ks:
            continue
        p = q * rng.choice(ks) + 1
        a = rng.randrange(2, p - 1)
        g = pow(a, (p - 1) // q, p)
        if g != 1:
            return p, q, g


class PollardRhoFloyd(Task):
    id = "dlp.rho"
    title_ru = "ρ-алгоритм Полларда для DLP (цикл Флойда)"
    topics = ("dlp.rho",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Default/sem2: subgroup of prime order q in (Z/pZ)^*. Preset 'composite': g of composite "
             "order n (often a primitive root), the final congruence has d = gcd(b - b', n) > 1 "
             "candidates. Starts are random; traces longer than max_rows are rejected, and so are "
             "useless collisions (b = b' mod n).")
    presets = {
        "default": {"mode": "prime", "qlo": 11, "qhi": 60, "pmax": 400, "max_rows": 16, "min_rows": 3,
                    "max_d": 1},
        "sem2": {"qlo": 19, "qhi": 100, "pmax": 700, "max_rows": 16},
        "composite": {"mode": "composite", "plo": 29, "phi": 140, "max_rows": 16, "max_d": 6},
    }
    statement = (r"Решить задачу дискретного логарифмирования $\VAR{g}^x \equiv \VAR{h}\ (\textrm{mod}\ \VAR{p})$ "
                 r"$\rho$-алгоритмом Полларда с поиском цикла по Флойду; $\ord(\VAR{g}) = \VAR{n}"
                 r"\BLOCK{if n_factor != n|string} = \VAR{n_factor}\BLOCK{endif}$. Последовательность "
                 r"$x_{i+1} = f(x_i)$, $x_i = \VAR{g}^{\alpha_i} \cdot \VAR{h}^{\beta_i} \bmod \VAR{p}$ "
                 r"(показатели по модулю $\VAR{n}$), где" + ITER_TEX +
                 r"начиная с $x_0 = \VAR{g}^{\VAR{c.a0}} \cdot \VAR{h}^{\VAR{c.b0}} \equiv \VAR{c.x0}$ "
                 r"($\alpha_0 = \VAR{c.a0}$, $\beta_0 = \VAR{c.b0}$). Выписать таблицу "
                 r"$(x_i, \alpha_i, \beta_i)$, $(x_{2i}, \alpha_{2i}, \beta_{2i})$ до совпадения "
                 r"$x_i = x_{2i}$ и найти $x$.")
    solution = (TX + r"Вычисляем «черепаху» $x_i = f(x_{i-1})$ и «зайца» $x_{2i} = f(f(x_{2i-2}))$:"
                r"\[\begin{array}{r|rrr|rrr}"
                r"i & x_i & \alpha_i & \beta_i & x_{2i} & \alpha_{2i} & \beta_{2i} \\ \hline "
                r"\BLOCK{for r in c.rows}\VAR{r.i} & \VAR{r.t[0]} & \VAR{r.t[1]} & \VAR{r.t[2]} & "
                r"\VAR{r.h[0]} & \VAR{r.h[1]} & \VAR{r.h[2]} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"Совпадение при $i = \VAR{c.m}$: $x_{\VAR{c.m}} = x_{\VAR{2 * c.m}} = \VAR{c.xm}$ "
                r"(у орбиты $x_0$ предпериод $T = \VAR{c.T}$ и период $M = \VAR{c.M}$; "
                r"$i = \VAR{c.m}$ "
                r"--- наименьшее кратное $M$, не меньшее $T$\BLOCK{if c.T == 0}, т.\,е. $i = M$\BLOCK{endif})."
                + SOLVE_TEX + r"\[x = \VAR{answer}.\]")

    def sample(self, rng):
        cfg = self.cfg
        while True:
            if cfg.mode == "prime":
                p, n, g = _subgroup(rng, cfg)
            else:
                ps = [q for q in first_primes(40) if cfg.plo <= q <= cfg.phi]
                p = rng.choice(ps)
                g = rng.randrange(2, p - 1)
                n = _order(g, p)
                if n < 12 or is_prime(n):
                    continue
            x = rng.randrange(2, n)
            h = pow(g, x, p)
            if h == g:
                continue
            c = _floyd_params(g, h, p, n, x, rng, cfg.max_rows + 1, cfg.min_rows,
                              cfg.mode == "composite", cfg.max_d)
            if c is not None:
                return {"p": p, "g": g, "h": h, "n": n, "n_factor": steps.factor_tex(n), "c": c,
                        "s": c["sol"], "answer": x}

    def check(self, p):
        g, h, P, n, c = p["g"], p["h"], p["p"], p["n"], p["c"]
        assert is_order(g, n, P) and pow(g, p["answer"], P) == h and 0 <= p["answer"] < n
        # replay the walk independently (single steps, no hare) and check the table
        xs = [(c["x0"], c["a0"], c["b0"])]
        for _ in range(2 * c["m"]):
            xs.append(rho_step(*xs[-1], g, h, P, n))
        for i, r in enumerate(c["rows"]):
            assert tuple(r["t"]) == xs[i] and tuple(r["h"]) == xs[2 * i]
            assert pow(g, r["t"][1], P) * pow(h, r["t"][2], P) % P == r["t"][0]
        assert xs[c["m"]][0] == xs[2 * c["m"]][0]
        assert all(xs[i][0] != xs[2 * i][0] for i in range(1, c["m"]))
        assert c["m"] % c["M"] == 0 and c["m"] >= c["T"] and c["m"] - c["M"] < max(c["T"], 1)
        if self.cfg.mode == "composite":
            assert p["s"]["d"] > 1


# --- distinguished points --------------------------------------------------------------


def dp_trace(g, h, p, n, starts, mask, max_rows) -> dict | None:
    """Walks run in lockstep; each distinguished point (x = 0 mod mask) goes to a shared table;
    stop when a distinguished point is reported for the second time."""
    walks = [[(pow(g, a, p) * pow(h, b, p) % p, a, b)] for a, b in starts]
    table: dict[int, dict] = {}
    log = []
    for t in range(max_rows):
        if t > 0:
            for w in walks:
                w.append(rho_step(*w[-1], g, h, p, n))
        for k, w in enumerate(walks):
            x, a, b = w[-1]
            if x % mask:
                continue
            if x in table:
                old = table[x]
                return {"rows": [{"t": i, "w": [wk[i] for wk in walks]} for i in range(t + 1)],
                        "log": log, "hit": {"x": x, "walk": k + 1, "t": t, "a": a, "b": b},
                        "old": old}
            table[x] = {"x": x, "walk": k + 1, "t": t, "a": a, "b": b}
            log.append(table[x])
    return None


class PollardRhoDistinguished(Task):
    id = "dlp.rho_distinguished"
    title_ru = "ρ-алгоритм Полларда с выделенными точками"
    topics = ("dlp.rho",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Two walks in lockstep share a table of distinguished points (x = 0 mod 2^k). The "
             "collision may come from the other walk (merge) or from the same walk (cycle). "
             "Traces longer than max_rows are rejected (e.g. a cycle without distinguished points).")
    presets = {
        "default": {"qlo": 23, "qhi": 70, "pmax": 500, "ks": [2], "max_rows": 14, "min_rows": 4},
        "sem2": {"qlo": 29, "qhi": 100, "pmax": 700, "ks": [2, 3], "max_rows": 16},
    }
    statement = (r"Решить задачу дискретного логарифмирования $\VAR{g}^x \equiv \VAR{h}\ (\textrm{mod}\ \VAR{p})$, "
                 r"$\ord(\VAR{g}) = \VAR{n}$, $\rho$-методом с выделенными точками. Два вычислителя "
                 r"параллельно (по одному шагу за такт) строят последовательности "
                 r"$x_{t+1} = f(x_t)$ и $y_{t+1} = f(y_t)$, где" + ITER_TEX +
                 r"с показателями по модулю $\VAR{n}$; $x_0 = \VAR{g}^{\VAR{c.starts[0][0]}} \cdot "
                 r"\VAR{h}^{\VAR{c.starts[0][1]}} \equiv \VAR{c.x0}$, $y_0 = \VAR{g}^{\VAR{c.starts[1][0]}} "
                 r"\cdot \VAR{h}^{\VAR{c.starts[1][1]}} \equiv \VAR{c.y0}$. Точка \emph{выделенная}, если "
                 r"её \VAR{c.k} младших двоичных разряда нулевые, т.\,е. она делится на $\VAR{c.mask}$. "
                 r"Выделенные точки (с показателями) отправляются на сервер; работа прекращается, как "
                 r"только какая-то выделенная точка придёт на сервер повторно. Выписать таблицу "
                 r"вычислений и найти $x$.")
    solution = (TX + r"Таблица (выделенные точки подчёркнуты; показатели $x_t = g^{\alpha_t} h^{\beta_t}$, "
                r"$y_t = g^{\gamma_t} h^{\delta_t}$):"
                r"\[\begin{array}{r|rrr|rrr}"
                r"t & x_t & \alpha_t & \beta_t & y_t & \gamma_t & \delta_t \\ \hline "
                r"\BLOCK{for r in c.rows}\VAR{r.t}\BLOCK{for w in r.w} & \BLOCK{if w[0] % c.mask == 0}"
                r"\underline{\VAR{w[0]}}\BLOCK{else}\VAR{w[0]}\BLOCK{endif} & \VAR{w[1]} & \VAR{w[2]}"
                r"\BLOCK{endfor} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"Содержимое сервера до совпадения: \BLOCK{for e in c.log}$\VAR{e.x}$ "
                r"(\BLOCK{if e.walk == 1}$x_{\VAR{e.t}}$: $\alpha = \VAR{e.a}$, $\beta = \VAR{e.b}$"
                r"\BLOCK{else}$y_{\VAR{e.t}}$: $\gamma = \VAR{e.a}$, $\delta = \VAR{e.b}$\BLOCK{endif})"
                r"\BLOCK{if not loop.last}; \BLOCK{endif}\BLOCK{endfor}. "
                r"При $t = \VAR{c.hit.t}$ точка $\VAR{c.hit.x}$ приходит повторно "
                r"(от \BLOCK{if c.hit.walk == 1}первого\BLOCK{else}второго\BLOCK{endif} вычислителя"
                r"\BLOCK{if c.hit.walk == c.old.walk}: его последовательность зациклилась"
                r"\BLOCK{else}: последовательности слились\BLOCK{endif})."
                r"\BLOCK{for w in c.loops} Последовательность $\VAR{w}$ зациклилась, не встретив "
                r"выделенных точек: на практике такой вычислитель перезапускают с новой начальной "
                r"точкой, когда число его шагов превышает заданный предел.\BLOCK{endfor}"
                + SOLVE_TEX + r"\[x = \VAR{answer}.\]")

    def sample(self, rng):
        cfg = self.cfg
        while True:
            p, n, g = _subgroup(rng, cfg)
            x = rng.randrange(2, n)
            h = pow(g, x, p)
            if h == g:
                continue
            k = rng.choice(cfg.ks)
            mask = 2**k
            for _ in range(100):
                starts = [(rng.randrange(n), rng.randrange(n)) for _ in range(2)]
                xs = [pow(g, a, p) * pow(h, b, p) % p for a, b in starts]
                if xs[0] == xs[1]:
                    continue
                tr = dp_trace(g, h, p, n, starts, mask, cfg.max_rows + 1)
                if tr is None or len(tr["rows"]) - 1 < cfg.min_rows:
                    continue
                hit, old = tr["hit"], tr["old"]
                s = solve_collision(old["a"], old["b"], hit["a"], hit["b"], g, h, p, n)
                if s is None:
                    continue
                loops = [name for name, col in zip("xy", zip(*[r["w"] for r in tr["rows"]]))
                         if len({v[0] for v in col}) < len(col) and not any(v[0] % mask == 0 for v in col)]
                c = {"starts": starts, "x0": xs[0], "y0": xs[1], "k": k, "mask": mask, "loops": loops,
                     "a1": old["a"], "b1": old["b"], "a2": hit["a"], "b2": hit["b"], **tr}
                return {"p": p, "g": g, "h": h, "n": n, "c": c, "s": s, "answer": s["x"]}

    def check(self, p):
        g, h, P, n, c = p["g"], p["h"], p["p"], p["n"], p["c"]
        assert is_order(g, n, P) and pow(g, p["answer"], P) == h and h != g
        for r in c["rows"]:
            for x, a, b in r["w"]:
                assert pow(g, a, P) * pow(h, b, P) % P == x
        for k in range(2):
            col = [r["w"][k] for r in c["rows"]]
            assert all(tuple(rho_step(*col[i], g, h, P, n)) == tuple(col[i + 1]) for i in range(len(col) - 1))
        assert c["hit"]["x"] == c["old"]["x"] and c["hit"]["x"] % c["mask"] == 0
        assert (c["hit"]["walk"], c["hit"]["t"]) != (c["old"]["walk"], c["old"]["t"])


# --- collision probability ------------------------------------------------------------


def _dec(x: float, k: int = 4) -> str:
    """Decimal comma; thin spaces between thousands for numbers >= 10^4."""
    s = f"{x:,.{k}f}" if abs(x) >= 10**4 else f"{x:.{k}f}"
    return s.replace(",", r"\,").replace(".", "{,}")


def _dec_vs(x: float, P: float) -> str:
    """x with the fewest digits (>= 4) that still show on which side of P it lies."""
    for k in range(4, 15):
        r = (math.floor if x >= P else math.ceil)(x * 10**k) / 10**k
        if (r >= P) == (x >= P):
            return _dec(r, k)
    return _dec(x, 15)


def _num(n: int) -> str:
    """Thousands separated by thin spaces."""
    return f"{n:,}".replace(",", r"\,")


def _N_tex(ctx: dict) -> str:
    return rf"2^{{{ctx['k']}}} = {_num(ctx['N'])}" if ctx.get("k") else _num(ctx["N"])


class CollisionProbability(Task):
    id = "dlp.collision_probability"
    title_ru = "Теорема о коллизиях: вероятность и длина списков"
    topics = ("dlp.collisions",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("Variants: two lists (probability bound / equal lengths for probability P / second "
             "list for a given first one) and one list (birthday: probability / length). Contexts: "
             "birthdays (N = 365), k-bit hashes (N = 2^k), a DLP group of order N.")
    presets = {"default": {"variants": ["two_prob", "two_len", "two_len_m", "one_prob", "one_len"],
                           "probs": [0.5, 0.9, 0.95, 0.99, 0.999]}}
    statement = (r"\VAR{intro} "
                 r"\BLOCK{if v == 'two_prob'}Оценить снизу вероятность того, что в двух списках из "
                 r"$n = \VAR{n_tex}$ и $m = \VAR{m_tex}$ случайных элементов множества из "
                 r"$N = \VAR{N_tex}$ элементов найдётся общий элемент (первый список состоит из "
                 r"различных элементов, элементы второго выбираются независимо и равновероятно)."
                 r"\BLOCK{elif v == 'two_len'}Какой длины $n$ взять два списка (одинаковой длины) "
                 r"случайных элементов множества из $N = \VAR{N_tex}$ элементов, чтобы по теореме "
                 r"о коллизиях вероятность общего элемента была не меньше $\VAR{P_tex}$?"
                 r"\BLOCK{elif v == 'two_len_m'}Первый список (различные элементы) содержит "
                 r"$n = \VAR{n_tex}$ элементов множества из $N = \VAR{N_tex}$ элементов. Сколько "
                 r"случайных элементов $m$ нужно взять во второй список, чтобы по теореме о коллизиях "
                 r"вероятность общего элемента была не меньше $\VAR{P_tex}$?"
                 r"\BLOCK{elif v == 'one_prob'}Оценить снизу вероятность того, что среди $n = \VAR{n_tex}$ "
                 r"независимых случайных элементов множества из $N = \VAR{N_tex}$ элементов есть "
                 r"два совпадающих."
                 r"\BLOCK{else}Сколько независимых случайных элементов $n$ множества из "
                 r"$N = \VAR{N_tex}$ элементов нужно взять, чтобы (по приближённой формуле "
                 r"$1 - e^{-n(n-1)/2N}$) вероятность совпадения каких-то двух была не меньше "
                 r"$\VAR{P_tex}$?\BLOCK{endif} Вычисления провести с логарифмами "
                 r"(4 знака после запятой).")
    solution = (r"\BLOCK{if v == 'two_prob'}По теореме о коллизиях "
                r"$\Pr = 1 - \left(1 - \frac{n}{N}\right)^{m} \ge 1 - e^{-nm/N}$. "
                r"Здесь $\frac{nm}{N} = \frac{\VAR{n_tex} \cdot \VAR{m_tex}}{\VAR{N_num}} \approx \VAR{t_tex}$, "
                r"$e^{-\VAR{t_tex}} \le \VAR{e_tex}$, т.\,е. $\Pr \ge 1 - \VAR{e_tex} = \VAR{ans_tex}$. "
                r"Точное значение: $\ln(1 - n/N) \approx \VAR{l1_tex}$, "
                r"$(1 - n/N)^m = e^{m \ln(1 - n/N)} \approx e^{\VAR{ml_tex}} \approx \VAR{ex_tex}$, "
                r"$\Pr \approx \VAR{exact_tex}$."
                r"\[\Pr \ge \VAR{ans_tex}.\]"
                r"\BLOCK{elif v == 'two_len'}При $n = m$: $1 - e^{-n^2/N} \ge P \iff "
                r"n^2 \ge N \ln\frac{1}{1 - P} \iff n \ge \sqrt{N \ln\frac{1}{1-P}}$. "
                r"$\ln\frac{1}{1 - \VAR{P_tex}} = \ln \VAR{inv_tex} \approx \VAR{L_tex}$, "
                r"$N \ln\frac{1}{1-P} \approx \VAR{NL_tex}$, $\sqrt{\VAR{NL_tex}} \approx \VAR{root_tex}$. "
                r"Проверка: $1 - e^{-\VAR{ans_tex}^2/N} \approx \VAR{chk_tex} \ge \VAR{P_tex}$, а при "
                r"$n = \VAR{prev_tex}$: $\approx \VAR{chk0_tex} < \VAR{P_tex}$ "
                r"(для сравнения, $\sqrt N \approx \VAR{sqrtN_tex}$)."
                r"\[n = m = \VAR{ans_tex}.\]"
                r"\BLOCK{elif v == 'two_len_m'}$1 - e^{-nm/N} \ge P \iff m \ge \frac{N}{n} \ln\frac{1}{1-P}$. "
                r"$\ln\frac{1}{1 - \VAR{P_tex}} = \ln \VAR{inv_tex} \approx \VAR{L_tex}$, "
                r"$\frac{N}{n} \approx \VAR{Nn_tex}$, $m \ge \VAR{Nn_tex} \cdot \VAR{L_tex} \approx \VAR{root_tex}$. "
                r"Проверка: $1 - e^{-n \cdot \VAR{ans_tex}/N} \approx \VAR{chk_tex} \ge \VAR{P_tex}$, а при "
                r"$m = \VAR{prev_tex}$: $\approx \VAR{chk0_tex} < \VAR{P_tex}$. Всего элементов "
                r"$n + m = \VAR{total_tex}$ (при $n = m$ хватило бы $2\sqrt{N \ln\frac{1}{1-P}} \approx "
                r"\VAR{bal_tex}$)."
                r"\[m = \VAR{ans_tex}.\]"
                r"\BLOCK{elif v == 'one_prob'}Вероятность отсутствия совпадений "
                r"$\prod_{i=1}^{n-1}\left(1 - \frac{i}{N}\right) \le \prod_{i=1}^{n-1} e^{-i/N} = "
                r"e^{-n(n-1)/2N}$, поэтому $\Pr \ge 1 - e^{-n(n-1)/2N}$, причём при $n \ll N$ это "
                r"и хорошее приближение. $\frac{n(n-1)}{2N} = \frac{\VAR{n_tex} \cdot \VAR{nm1_tex}}{2 \cdot "
                r"\VAR{N_num}} \approx \VAR{t_tex}$, $e^{-\VAR{t_tex}} \le \VAR{e_tex}$, $\Pr \ge 1 - \VAR{e_tex} = \VAR{ans_tex}$. "
                r"\BLOCK{if exact_tex}Точное значение (на компьютере): "
                r"$1 - \prod_{i=1}^{n-1}(1 - i/N) \approx \VAR{exact_tex}$.\BLOCK{endif}"
                r"\[\Pr \ge \VAR{ans_tex}.\]"
                r"\BLOCK{else}$1 - e^{-n(n-1)/2N} \ge P \iff n^2 - n - 2N\ln\frac{1}{1-P} \ge 0 \iff "
                r"n \ge \frac{1 + \sqrt{1 + 8N\ln\frac{1}{1-P}}}{2}$. "
                r"$\ln\frac{1}{1 - \VAR{P_tex}} = \ln \VAR{inv_tex} \approx \VAR{L_tex}$, "
                r"$1 + 8N\ln\frac{1}{1-P} \approx \VAR{NL_tex}$, $\frac{1 + \sqrt{\VAR{NL_tex}}}{2} \approx "
                r"\VAR{root_tex}$. Проверка: при $n = \VAR{ans_tex}$ $1 - e^{-n(n-1)/2N} \approx "
                r"\VAR{chk_tex} \ge \VAR{P_tex}$, при $n = \VAR{prev_tex}$: $\approx \VAR{chk0_tex} < \VAR{P_tex}$ "
                r"(ср. $\sqrt{2N\ln\frac{1}{1-P}} \approx \VAR{approx_tex}$)."
                r"\[n = \VAR{ans_tex}.\]\BLOCK{endif}")

    CONTEXTS = {
        "birthday": "Дни рождения людей независимы и равновероятны ($N = 365$).",
        "hash": "Хеш-функция выдаёт $k = {k}$-битные значения; считаем их случайными.",
        "dlp": "Решаем DLP в группе простого порядка $N$ поиском коллизии списков $g^{{y_i}}$ и "
               "$h \\cdot g^{{z_j}}$ со случайными показателями.",
        "rho": "Точки $x_0, x_1, \\dots$ последовательности $\\rho$-метода в группе простого порядка $N$ "
               "считаем независимыми и равновероятными.",
    }

    def sample(self, rng):
        v = rng.choice(self.cfg.variants)
        ctx = rng.choice(["birthday", "hash", "rho"] if v.startswith("one") else ["hash", "dlp"])
        P = rng.choice(self.cfg.probs)
        if ctx == "birthday":
            N, k = 365, None
        elif ctx == "hash":
            k = rng.choice([16, 20, 24, 32, 40] if v.startswith("one") else [16, 20, 24, 32])
            N = 2**k
        else:  # dlp, rho
            k = None
            N = rng.randrange(*rng.choice([(10**5, 10**6), (10**6, 10**7), (10**8, 10**9)]))
            while not is_prime(N):
                N += 1
        ctx_d = {"N": N, "k": k}
        L = -math.log1p(-P)
        out = {"v": v, "ctx": ctx, "N": N, "k": k, "P": P, "N_tex": _N_tex(ctx_d),
               "P_tex": str(P).replace(".", "{,}"), "N_num": _num(N),
               "L": L, "L_tex": _dec(L), "inv_tex": _num(round(1 / (1 - P)))}
        sq = math.sqrt(N)

        def bound2(n, m):
            return -math.expm1(-n * m / N)

        def bound1(n):
            return -math.expm1(-n * (n - 1) / (2 * N))

        if v == "two_prob":
            n = max(2, round(sq * rng.choice([0.3, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0])))
            m = max(2, round(sq * rng.choice([0.5, 1.0, 1.5, 2.0])))
            t = n * m / N
            ml = m * math.log1p(-n / N)
            e_up = math.ceil(math.exp(-t) * 1e4) / 1e4
            out.update(n=n, m=m, n_tex=_num(n), m_tex=_num(m), t_tex=_dec(t), e_tex=_dec(e_up),
                       l1_tex=_dec(math.log1p(-n / N), 8), ml_tex=_dec(ml), ex_tex=_dec(math.exp(ml)),
                       exact_tex=_dec(-math.expm1(ml)), answer=round(1 - e_up, 4), ans_tex=_dec(1 - e_up))
        elif v == "two_len":
            root = math.sqrt(N * L)
            n = math.ceil(root)
            while bound2(n - 1, n - 1) >= P:
                n -= 1
            while bound2(n, n) < P:
                n += 1
            out.update(NL_tex=_dec(N * L, 2), root_tex=_dec(root, 2), answer=n, ans_tex=_num(n),
                       prev_tex=_num(n - 1), chk_tex=_dec_vs(bound2(n, n), P), chk0_tex=_dec_vs(bound2(n - 1, n - 1), P),
                       sqrtN_tex=_dec(sq, 2))
        elif v == "two_len_m":
            n = max(2, round(sq * rng.choice([0.1, 0.25, 0.5, 2, 4])))
            root = N / n * L
            m = math.ceil(root)
            while m > 1 and bound2(n, m - 1) >= P:
                m -= 1
            while bound2(n, m) < P:
                m += 1
            out.update(n=n, n_tex=_num(n), Nn_tex=_dec(N / n, 2), root_tex=_dec(root, 2), answer=m,
                       ans_tex=_num(m), prev_tex=_num(m - 1), chk_tex=_dec_vs(bound2(n, m), P),
                       chk0_tex=_dec_vs(bound2(n, m - 1), P), total_tex=_num(n + m),
                       bal_tex=_dec(2 * math.sqrt(N * L), 2))
        elif v == "one_prob":
            n = max(3, round(sq * rng.choice([0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0])))
            t = n * (n - 1) / (2 * N)
            exact = None
            if N <= 10**7:
                lp = sum(math.log1p(-i / N) for i in range(1, n))
                exact = -math.expm1(lp)
            e_up = math.ceil(math.exp(-t) * 1e4) / 1e4
            out.update(n=n, n_tex=_num(n), nm1_tex=_num(n - 1), t_tex=_dec(t), e_tex=_dec(e_up),
                       exact_tex=_dec(exact) if exact is not None else "", answer=round(1 - e_up, 4),
                       ans_tex=_dec(1 - e_up))
        else:
            root = (1 + math.sqrt(1 + 8 * N * L)) / 2
            n = math.ceil(root)
            while bound1(n - 1) >= P:
                n -= 1
            while bound1(n) < P:
                n += 1
            out.update(NL_tex=_dec(1 + 8 * N * L, 2), root_tex=_dec(root, 2), answer=n, ans_tex=_num(n),
                       prev_tex=_num(n - 1), chk_tex=_dec_vs(bound1(n), P), chk0_tex=_dec_vs(bound1(n - 1), P),
                       approx_tex=_dec(math.sqrt(2 * N * L), 2))
        out["intro"] = self.CONTEXTS[ctx].format(k=k)
        return out

    def check(self, p):
        N, P, v = p["N"], p["P"], p["v"]
        # independent route: exact products/powers instead of exp/log1p
        if v == "two_prob":
            b = 1 - math.exp(-p["n"] * p["m"] / N)
            assert 0 <= b - p["answer"] < 1.5e-4
            assert 1 - (1 - p["n"] / N) ** p["m"] >= p["answer"] - 1e-4  # bound holds
        elif v == "one_prob":
            n = p["n"]
            assert 0 <= 1 - math.exp(-n * (n - 1) / (2 * N)) - p["answer"] < 1.5e-4
        else:
            a = p["answer"]

            def ok(x):
                if v == "two_len":
                    return 1 - math.exp(-x * x / N) >= P
                if v == "two_len_m":
                    return 1 - math.exp(-p["n"] * x / N) >= P
                return 1 - math.exp(-x * (x - 1) / (2 * N)) >= P

            assert ok(a) and not ok(a - 1)
        if p["ctx"] == "hash":
            assert N == 2 ** p["k"]
        if p["ctx"] == "dlp":
            assert is_prime(N)
