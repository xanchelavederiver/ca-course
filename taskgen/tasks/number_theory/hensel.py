"""Square roots modulo prime powers and composite moduli (lecture sem2/07).

* ``number_theory.sqrt_p34``      x^2 = a (mod p), p = 3 (mod 4): x = a^{(p+1)/4};
* ``number_theory.hensel_sqrt``   x^2 = a (mod p^k): a root mod p, then Hensel lifting;
* ``number_theory.sqrt_composite`` x^2 = a (mod n), n = pq, p^2 q or pqr: roots modulo the
  prime-power factors and the CRT (2^r roots, fewer when gcd(a, n) > 1, none when a is a
  non-residue modulo some factor).

Corner cases are kept on purpose: non-residues (no solutions), a = -1 for p = 3 (mod 4),
a sharing a factor with n (root 0 modulo that factor, half as many roots).
"""

import itertools
import math

from taskgen.core import steps
from taskgen.core.nt import first_primes, inverse, is_square_mod
from taskgen.core.task import SolutionDetail, Task

MOD = r"\ (\textrm{mod}\ \VAR{p})"


def _euler(a: int, p: int) -> int:
    return pow(a % p, (p - 1) // 2, p)


def _brute_roots(a: int, n: int) -> list[int]:
    return [x for x in range(n) if (x * x - a) % n == 0]


# --- p = 3 (mod 4) ----------------------------------------------------------------------


class SqrtP34(Task):
    id = "number_theory.sqrt_p34"
    title_ru = "Квадратный корень по модулю простого p = 3 (mod 4)"
    topics = ("number_theory.sqrt",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("Non-residues (no solutions; detected by x^2 = -a) with probability 1/4, "
             "a = -1 included.")
    presets = {"default": {"primes": [p for p in first_primes(46)[7:] if p % 4 == 3],
                           "nonresidue_ratio": 0.25}}
    statement = (r"Решить сравнение $x^2 \equiv \VAR{a}\ (\textrm{mod}\ \VAR{p})$, "
                 r"пользуясь тем, что $\VAR{p} \equiv 3\ (\textrm{mod}\ 4)$ "
                 r"(или доказать, что решений нет).")
    solution = (r"При $p \equiv 3\ (\textrm{mod}\ 4)$ кандидат в корни "
                r"$x = a^{(p+1)/4} = \VAR{a}^{\VAR{e}}$, и $x^2 = a^{(p+1)/2} = "
                r"a \cdot a^{(p-1)/2} \equiv \pm a$ (критерий Эйлера). "
                r"$\VAR{e} = \VAR{e|bin}_2$; бинарный алгоритм:"
                r"\[\begin{array}{c|r|r}"
                r"\text{бит} & r^2 & r \\ \hline "
                r"\BLOCK{for s in pw}\VAR{s.bit} & \VAR{s.sq} & \VAR{s.r} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"$x = \VAR{x}$, $x^2 = \VAR{x * x} \equiv \VAR{x2}" + MOD + r"$. "
                r"\BLOCK{if residue}Это $a$, значит $a$ --- квадратичный вычет и $x$ --- корень; "
                r"второй корень $p - x = \VAR{p - x}$."
                r"\[x \equiv \pm \VAR{x}" + MOD + r",\ \text{т.\,е.}\ "
                r"x \in \{\VAR{answer[0]}, \VAR{answer[1]}\}.\]"
                r"\BLOCK{else}Это $-a$, т.\,е. $\VAR{a}^{(p-1)/2} \equiv -1$: по критерию Эйлера "
                r"$\VAR{a}$ --- квадратичный невычет по модулю $\VAR{p}$."
                r"\[\text{Решений нет}.\]\BLOCK{endif}")

    def sample(self, rng):
        p = rng.choice(self.cfg.primes)
        if rng.random() < self.cfg.nonresidue_ratio:
            a = rng.choice([b for b in range(2, p) if not is_square_mod(b, p)])
        else:
            # a = y^2 in Z (4, 9, 16, ...) would show the root at once
            squares = {b * b % p for b in range(1, p)}
            a = rng.choice(sorted(r for r in squares if math.isqrt(r) ** 2 != r))
        e = (p + 1) // 4
        pw = steps.binary_pow_steps(a, e, p)
        x = pw[-1]["r"]
        x = min(x, p - x)
        residue = x * x % p == a
        return {"p": p, "a": a, "e": e, "pw": pw, "x": x, "x2": x * x % p, "residue": residue,
                "answer": sorted([x, p - x]) if residue else []}

    def check(self, p):
        assert p["p"] % 4 == 3 and 0 < p["a"] < p["p"]
        assert p["answer"] == _brute_roots(p["a"], p["p"])
        assert p["residue"] == (_euler(p["a"], p["p"]) == 1)


# --- Hensel lifting ----------------------------------------------------------------------


def hensel_sqrt_lift(a: int, p: int, k: int, x1: int) -> dict:
    """Lift a root x1 of x^2 = a (mod p) to mod p^k: x_{j+1} = x_j + t p^j,
    t = -((x_j^2 - a) / p^j) * (2 x_1)^{-1} mod p."""
    c = inverse(2 * x1 % p, p)
    x, rows = x1, []
    for j in range(1, k):
        pj, pj1 = p**j, p ** (j + 1)
        f = (x * x - a) % pj1
        assert f % pj == 0
        s = f // pj
        t = -s * c % p
        nx = x + t * pj
        rows.append({"j": j, "pj": pj, "pj1": pj1, "x": x, "f": f, "s": s, "t": t, "nx": nx})
        x = nx
    return {"c": c, "rows": rows, "x": x}


class HenselSqrt(Task):
    id = "number_theory.hensel_sqrt"
    title_ru = "Квадратичное сравнение по модулю степени простого (лемма Гензеля)"
    topics = ("number_theory.hensel",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("p odd prime <= 13, p^k <= max_mod; a coprime to p and not a square in Z. "
             "Non-residues mod p (no solutions, Euler's criterion) with probability 1/6.")
    presets = {"default": {"primes": [3, 5, 7, 11, 13], "kmax": 4, "max_mod": 3000,
                           "nonresidue_ratio": 1 / 6},
               # corner-case section of a sheet: half of the instances have no solutions
               "corner": {"nonresidue_ratio": 0.5}}
    statement = (r"Решить сравнение $x^2 \equiv \VAR{a}\ (\textrm{mod}\ \VAR{p}^{\VAR{k}})$, "
                 r"т.\,е. по модулю $\VAR{p**k}$: найти корень по модулю $\VAR{p}$ "
                 r"и поднять его с помощью леммы Гензеля (или доказать, что решений нет).")
    solution = (r"\BLOCK{import 'macros.tex.j2' as tx}"
                r"$a = \VAR{a} \equiv \VAR{r}" + MOD + r"$. Критерий Эйлера: "
                r"$\VAR{r}^{(p-1)/2} = \VAR{r}^{\VAR{(p - 1) // 2}} \equiv "
                r"\BLOCK{if euler == 1}1" + MOD + r"$ --- вычет. "
                r"Квадраты по модулю $\VAR{p}$:"
                r"\[\begin{array}{c|\BLOCK{for s in squares}c\BLOCK{endfor}}"
                r"y\BLOCK{for s in squares} & \VAR{s[0]}\BLOCK{endfor} \\ \hline "
                r"y^2 \bmod \VAR{p}\BLOCK{for s in squares} & \VAR{s[1]}\BLOCK{endfor}"
                r"\end{array}\]"
                r"Корень по модулю $\VAR{p}$: $x_1 = \VAR{x1}$ (и $-x_1 = \VAR{p - x1}$). "
                r"Так как $f(x) = x^2 - a$, $f'(x_1) = 2x_1 = \VAR{2 * x1} \not\equiv 0" + MOD + r"$, "
                r"корень поднимается однозначно: $x_{j+1} = x_j + t_j p^j$, "
                r"$t_j \equiv -\bigl((x_j^2 - a)/p^j\bigr) \cdot (2x_1)^{-1}" + MOD + r"$, где "
                r"$(2x_1)^{-1} \equiv \VAR{2 * x1 % p}^{-1} \equiv \VAR{h.c}" + MOD + r"$ "
                r"($\VAR{2 * x1 % p} \cdot \VAR{h.c} = \VAR{(2 * x1 % p) * h.c} \equiv 1$)."
                r"\[\begin{array}{c|r|r|r|r|r}"
                r"j & x_j & x_j^2 - a \bmod p^{j+1} & (x_j^2 - a)/p^j & t_j & x_{j+1} \\ \hline "
                r"\BLOCK{for s in h.rows}\VAR{s.j} & \VAR{s.x} & \VAR{s.f} & \VAR{s.s} & \VAR{s.t} & "
                r"\VAR{s.nx} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"Проверка: $\VAR{x}^2 = \VAR{x * x} \equiv \VAR{a}\ (\textrm{mod}\ \VAR{p**k})$. "
                r"Второй корень $-x = \VAR{p**k - x}$ (он получается подъёмом $-x_1$); "
                r"других корней нет, так как по модулю $\VAR{p}$ их ровно два, и каждый поднимается "
                r"единственным образом."
                r"\[x \equiv \pm \VAR{x}\ (\textrm{mod}\ \VAR{p**k}),\ \text{т.\,е.}\ "
                r"x \in \{\VAR{answer[0]}, \VAR{answer[1]}\}.\]"
                r"\BLOCK{else}-1" + MOD + r"$, т.\,е. $\VAR{a}$ --- квадратичный невычет "
                r"по модулю $\VAR{p}$. Если бы $x^2 \equiv a\ (\textrm{mod}\ \VAR{p**k})$, то и "
                r"$x^2 \equiv a" + MOD + r"$, поэтому \[\text{решений нет}.\]\BLOCK{endif}")

    def sample(self, rng):
        cfg = self.cfg
        p = rng.choice(cfg.primes)
        k = rng.choice([j for j in range(2, cfg.kmax + 1) if p**j <= cfg.max_mod])
        m = p**k
        units = [b for b in range(2, m) if b % p]
        if rng.random() < cfg.nonresidue_ratio:
            a = rng.choice([b for b in units if not is_square_mod(b, p)])
        else:
            while True:
                a = rng.choice(units) ** 2 % m
                if math.isqrt(a) ** 2 != a:  # a = y^2 in Z: the roots +-y are seen at once
                    break
        r = a % p
        euler = _euler(a, p)
        squares = [(y, y * y % p) for y in range(1, (p - 1) // 2 + 1)]
        ctx = {"p": p, "k": k, "a": a, "r": r, "euler": euler, "squares": squares,
               "x1": 0, "h": {"c": 0, "rows": []}, "x": 0, "answer": []}
        if euler == 1:
            x1 = next(y for y, s in squares if s == r)
            h = hensel_sqrt_lift(a, p, k, x1)
            x = h["x"]
            ctx.update(x1=x1, h=h, x=x, answer=sorted([x, m - x]))
        return ctx

    def check(self, p):
        m = p["p"] ** p["k"]
        assert p["a"] % p["p"] and 2 <= p["a"] < m
        assert p["answer"] == _brute_roots(p["a"], m)
        assert (p["euler"] == 1) == bool(p["answer"])
        if p["answer"]:
            assert len(p["h"]["rows"]) == p["k"] - 1 and p["x"] in p["answer"]


# --- composite modulus ------------------------------------------------------------------


def _prime_root_info(a: int, p: int, e: int) -> dict:
    """Roots of x^2 = a modulo p^e (e in {1, 2}) with the steps a student writes down."""
    m = p**e
    ap = a % p
    info = {"p": p, "e": e, "m": m, "am": a % m, "ap": ap, "euler": None, "method": "",
            "r1": None, "lift": None, "roots": []}
    if ap == 0:
        assert e == 1
        info.update(method="zero", roots=[0])
        return info
    info["euler"] = _euler(ap, p)
    if info["euler"] != 1:
        info["method"] = "none"
        return info
    if ap == 1:
        r1 = 1
        info["method"] = "one"
    elif p % 4 == 3:
        r1 = pow(ap, (p + 1) // 4, p)
        info["method"] = "p34"
    else:
        r1 = next(y for y in range(1, p) if y * y % p == ap)
        info["method"] = "search"
    r1 = min(r1, p - r1)
    info["r1"] = r1
    r = r1
    if e == 2:
        info["lift"] = hensel_sqrt_lift(a, p, 2, r1)
        r = info["lift"]["x"]
    info["roots"] = sorted([r, m - r])
    return info


class SqrtComposite(Task):
    id = "number_theory.sqrt_composite"
    title_ru = "Квадратные корни по составному модулю (КТО)"
    topics = ("number_theory.sqrt",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("n = pq (1/2), p^2 q (1/4), pqr (1/4: 8 roots). Corner cases (1/3; always in preset "
             "'corner'): a non-residue modulo a factor (no roots) or, for square-free n, p | a "
             "(root 0 mod p, 2^{r-1} roots). Preset 'eight': n = pqr, 8 roots.")
    presets = {"default": {
        "pq_primes": [7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43], "pq_max": 1000,
        "p2q_primes": [3, 5, 7], "q_primes": [3, 5, 7, 11, 13, 17, 19], "p2q_max": 1000,
        "pqr_primes": [3, 5, 7, 11, 13], "pqr_max": 1001,
        "kinds": ["pq", "pq", "p2q", "pqr"], "corner_ratio": 1 / 3},
        # always a corner case: no roots (non-residue modulo a factor) or gcd(a, n) > 1
        "corner": {"corner_ratio": 1.0},
        # n = pqr, gcd(a, n) = 1: eight roots
        "eight": {"kinds": ["pqr"], "corner_ratio": 0.0}}
    statement = (r"Найти все решения сравнения $x^2 \equiv \VAR{a}\ (\textrm{mod}\ \VAR{n})$, "
                 r"$\VAR{n} = \VAR{n_tex}$ (или доказать, что решений нет).")
    solution = (r"\BLOCK{import 'macros.tex.j2' as tx}"
                r"По китайской теореме об остатках сравнение равносильно системе сравнений по модулям "
                r"$\VAR{mods|join(', ')}$. Решаем каждое:"
                r"\BLOCK{for f in facs}\par\noindent $\bullet$ "
                r"$x^2 \equiv \VAR{a} \equiv \VAR{f.am}\ (\textrm{mod}\ \VAR{f.m})$: "
                r"\BLOCK{if f.method == 'zero'}$\VAR{f.p} \mid a$, единственный корень $x \equiv 0$ "
                r"($\VAR{f.p}$ --- простое, $\VAR{f.p} \mid x^2 \Rightarrow \VAR{f.p} \mid x$)."
                r"\BLOCK{else}\BLOCK{if f.e == 2}по модулю $\VAR{f.p}$: $a \equiv \VAR{f.ap}$, \BLOCK{endif}"
                r"$\VAR{f.ap}^{\VAR{(f.p - 1) // 2}} \equiv "
                r"\BLOCK{if f.euler == 1}1$ (вычет); "
                r"\BLOCK{if f.method == 'p34'}$\VAR{f.p} \equiv 3\ (\textrm{mod}\ 4)$, "
                r"$r = \VAR{f.ap}^{(p+1)/4} = \VAR{f.ap}^{\VAR{(f.p + 1) // 4}} \equiv \VAR{f.r1}"
                r"\BLOCK{elif f.method == 'one'}очевидный корень $r = 1"
                r"\BLOCK{else}подбором $r = \VAR{f.r1}"
                r"\BLOCK{endif}$, $r^2 = \VAR{f.r1 * f.r1} \equiv \VAR{f.ap}\ (\textrm{mod}\ \VAR{f.p})$"
                r"\BLOCK{if f.e == 2}; подъём Гензеля до $\VAR{f.m}$: "
                r"$r^2 - a \equiv \VAR{f.lift.rows[0].f}\ (\textrm{mod}\ \VAR{f.m})$, "
                r"$t \equiv -\VAR{f.lift.rows[0].s} \cdot (2r)^{-1} \equiv "
                r"-\VAR{f.lift.rows[0].s} \cdot \VAR{f.lift.c} \equiv \VAR{f.lift.rows[0].t}"
                r"\ (\textrm{mod}\ \VAR{f.p})$, $r + t\cdot\VAR{f.p} = \VAR{f.lift.x}$\BLOCK{endif}"
                r". Корни: $x \equiv \pm \VAR{f.roots[0]}$, т.\,е. "
                r"$\VAR{f.roots|join(', ')}\ (\textrm{mod}\ \VAR{f.m})$."
                r"\BLOCK{else}\VAR{f.p - 1} \equiv -1$: невычет по модулю $\VAR{f.p}$, решений нет."
                r"\BLOCK{endif}\BLOCK{endif}\BLOCK{endfor}"
                r"\par \BLOCK{if not answer}Сравнение по одному из модулей неразрешимо, поэтому "
                r"\[\text{решений нет}.\]"
                r"\BLOCK{else}Число решений равно произведению чисел корней по каждому модулю: "
                r"$\VAR{counts|join(' \\cdot ')} = \VAR{answer|length}$. "
                r"Для КТО найдём базис $e_i$ ($e_i \equiv 1$ по модулю $m_i$ и $\equiv 0$ по остальным): "
                r"$e_i = M_i y_i$, $M_i = n/m_i$, $y_i = M_i^{-1} \bmod m_i$:"
                r"\BLOCK{for b in basis}\par\noindent $m_{\VAR{loop.index}} = \VAR{b.m}$: "
                r"$M_{\VAR{loop.index}} = \VAR{b.Mi} \equiv \VAR{b.Mi_mod}$, "
                r"$y_{\VAR{loop.index}} = \VAR{b.y}$, $e_{\VAR{loop.index}} = \VAR{b.Mi} \cdot \VAR{b.y} "
                r"\equiv \VAR{b.e}\ (\textrm{mod}\ \VAR{n})$;\BLOCK{endfor}"
                r"\par Тогда $x \equiv \sum_i (x \bmod m_i)\, e_i\ (\textrm{mod}\ \VAR{n})$:"
                r"\[\begin{array}{\BLOCK{for m in mods}c|\BLOCK{endfor}r}"
                r"\BLOCK{for m in mods}x \bmod \VAR{m} & \BLOCK{endfor}x \\ \hline "
                r"\BLOCK{for c in combos}\BLOCK{for v in c.res}\VAR{v} & \BLOCK{endfor}\VAR{c.x} \\ "
                r"\BLOCK{endfor}"
                r"\end{array}\]"
                r"Проверка: $\VAR{answer[-1]}^2 = \VAR{answer[-1] * answer[-1]} \equiv \VAR{a}"
                r"\ (\textrm{mod}\ \VAR{n})$."
                r"\[x \in \{\VAR{answer|join(', ')}\}.\]\BLOCK{endif}")

    def _modulus(self, rng, kind):
        cfg = self.cfg
        while True:
            if kind == "pq":
                ps = rng.sample(cfg.pq_primes, 2)
                fac, lim = [(p, 1) for p in sorted(ps)], cfg.pq_max
            elif kind == "p2q":
                p = rng.choice(cfg.p2q_primes)
                q = rng.choice([q for q in cfg.q_primes if q != p])
                fac, lim = sorted([(p, 2), (q, 1)]), cfg.p2q_max
            else:
                fac, lim = [(p, 1) for p in sorted(rng.sample(cfg.pqr_primes, 3))], cfg.pqr_max
            n = math.prod(p**e for p, e in fac)
            if n <= lim:
                return fac, n

    def sample(self, rng):
        kind = rng.choice(self.cfg.kinds)
        fac, n = self._modulus(rng, kind)
        corner = rng.random() < self.cfg.corner_ratio
        mode = "regular"
        if corner:
            mode = "nonresidue" if kind == "p2q" or rng.random() < 0.5 else "gcd"
        primes = [p for p, _ in fac]
        while True:
            if mode == "nonresidue":
                a = rng.randrange(2, n)
                ok = math.gcd(a, n) == 1 and not all(is_square_mod(a, p) for p in primes)
            elif mode == "gcd":
                zp = rng.choice(primes)
                x = rng.randrange(1, n)
                ok = x % zp == 0 and all(x % p for p in primes if p != zp)
                a = x * x % n
                ok = ok and a not in (0, 1)
            else:
                x = rng.randrange(2, n)
                a = x * x % n
                ok = math.gcd(x, n) == 1 and a != 1
            if ok:
                break
        facs = [_prime_root_info(a, p, e) for p, e in fac]
        mods = [f["m"] for f in facs]
        n_tex = r" \cdot ".join(f"{p}^{{{e}}}" if e > 1 else str(p) for p, e in fac)
        basis, combos, answer = [], [], []
        if all(f["roots"] for f in facs):
            c = steps.crt([0] * len(mods), mods)
            for eq in c["eqs"]:
                basis.append({"m": eq["m"], "Mi": eq["Mi"], "Mi_mod": eq["Mi_mod"], "y": eq["y"],
                              "e": eq["Mi"] * eq["y"] % n})
            for res in itertools.product(*[f["roots"] for f in facs]):
                x = sum(r * b["e"] for r, b in zip(res, basis)) % n
                combos.append({"res": list(res), "x": x})
            answer = sorted(c["x"] for c in combos)
        return {"a": a, "n": n, "n_tex": n_tex, "kind": kind, "mode": mode, "facs": facs,
                "mods": mods, "counts": [len(f["roots"]) for f in facs], "basis": basis,
                "combos": combos, "answer": answer}

    def check(self, p):
        n, a = p["n"], p["a"]
        assert math.prod(p["mods"]) == n and 2 <= a < n
        assert p["answer"] == _brute_roots(a, n)
        assert len(p["answer"]) == math.prod(p["counts"])
        for c in p["combos"]:
            assert all(c["x"] % m == r for m, r in zip(p["mods"], c["res"]))
        if p["mode"] == "regular":
            assert len(p["answer"]) == 2 ** len(p["mods"])
