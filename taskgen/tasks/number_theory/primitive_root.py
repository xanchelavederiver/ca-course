"""Primitive roots modulo n (lecture sem1/07): the smallest primitive root modulo
n = p, p^k, 2p^k (and 4), or a proof that none exists; all primitive roots from one.

A primitive root modulo n exists iff n in {1, 2, 4, p^k, 2p^k} (p odd prime). The test:
g with gcd(g, n) = 1 is a primitive root iff g^{phi(n)/q} != 1 (mod n) for every prime
q | phi(n). Squares are skipped (for n > 2 a square h^2 has h^{phi(n)} = 1 at exponent
phi(n)/2).
"""

from math import gcd, isqrt, lcm

from taskgen.core import steps
from taskgen.core.nt import factorize, first_primes, is_order, is_prime
from taskgen.core.task import SolutionDetail, Task


def phi(n: int) -> int:
    r = n
    for q in factorize(n):
        r = r // q * (q - 1)
    return r


def carmichael(n: int) -> int:
    """Carmichael function lambda(n)."""
    out = 1
    for q, e in factorize(n).items():
        if q == 2 and e >= 3:
            lam = 2 ** (e - 2)
        else:
            lam = q ** (e - 1) * (q - 1)
        out = lcm(out, lam)
    return out


def has_primitive_root(n: int) -> bool:
    if n in (1, 2, 4):
        return True
    m = n // 2 if n % 2 == 0 else n
    if m % 2 == 0:
        return False
    f = factorize(m)
    return len(f) == 1


def kind_of(n: int) -> str:
    """'prime', 'prime_power' (p^k, k >= 2, and 4), 'twice' (2p^k) or 'none'."""
    if not has_primitive_root(n):
        return "none"
    if is_prime(n):
        return "prime"
    if n % 2 == 0 and n != 4:
        return "twice"
    return "prime_power"


def is_square_coprime(g: int, n: int) -> int | None:
    """h with h^2 = g (as integers), if g is a perfect square."""
    h = isqrt(g)
    return h if h * h == g else None


def root_search(n: int) -> dict:
    """Trace of the search for the smallest primitive root modulo n (n has one)."""
    ph = phi(n)
    qs = sorted(factorize(ph))
    rows, g = [], 1
    while True:
        g += 1
        if gcd(g, n) > 1:
            rows.append({"g": g, "skip": "gcd", "d": gcd(g, n), "vals": [], "ok": False})
            continue
        h = is_square_coprime(g, n)
        if h is not None and n > 2:
            rows.append({"g": g, "skip": "square", "h": h, "vals": [], "ok": False})
            continue
        vals = []
        for q in qs:
            v = pow(g, ph // q, n)
            vals.append(v)
            if v == 1:
                break
        ok = len(vals) == len(qs) and all(v != 1 for v in vals)
        rows.append({"g": g, "skip": "", "vals": vals, "ok": ok})
        if ok:
            return {"phi": ph, "qs": qs, "exps": [ph // q for q in qs], "rows": rows, "g": g}


def no_root_reason(n: int) -> dict:
    """Why (Z/nZ)^* is not cyclic: n = 2^k (k >= 3) or n = a * b, gcd(a, b) = 1, a, b > 2."""
    f = factorize(n)
    odd = [q for q in f if q > 2]
    if not odd:
        return {"case": "pow2", "k": f[2], "a": 0, "b": 0}
    q = max(odd)
    b = q ** f[q]
    a = n // b
    assert a > 2 and b > 2 and gcd(a, b) == 1
    return {"case": "split", "k": f.get(2, 0), "a": a, "b": b, "phia": phi(a), "phib": phi(b)}


def lambda_parts(n: int) -> list[dict]:
    out = []
    for q, e in sorted(factorize(n).items()):
        lam = 2 ** (e - 2) if (q == 2 and e >= 3) else q ** (e - 1) * (q - 1)
        out.append({"pe": f"{q}^{{{e}}}" if e > 1 else str(q), "lam": lam})
    return out


def _pk_tex(n: int) -> str:
    return steps.factor_tex(n)


class PrimitiveRoot(Task):
    id = "number_theory.primitive_root"
    title_ru = "Наименьший первообразный корень по модулю n"
    topics = ("number_theory.primitive_root",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("n = p (~2/5, half of them with the smallest root > 2), p^k or 4 (~1/5), 2p^k (~1/5) "
             "and (corner case, ~1/5) n without primitive roots, where the answer is a proof of "
             "non-existence. Presets prime_power / twice / none force one kind (corner-case "
             "sections). Candidates with gcd(g, n) > 1 and perfect squares are skipped with a reason.")
    presets = {"default": {
        "primes": [p for p in first_primes(46) if p >= 7],  # 7..199
        "max_root": 11,
        "hard_ratio": 0.5,
        "prime_power": [4, 9, 25, 27, 49, 81, 121, 125, 169],
        "twice": [2 * m for m in range(3, 126, 2) if len(factorize(m)) == 1],
        "none": [n for n in range(8, 101) if not has_primitive_root(n)],
        "weights": {"prime": 2, "prime_power": 1, "twice": 1, "none": 1},
    },
               # corner-case presets for the "corner cases" sections of sheets
               "prime_power": {"weights": {"prime": 0, "prime_power": 1, "twice": 0, "none": 0}},
               "twice": {"weights": {"prime": 0, "prime_power": 0, "twice": 1, "none": 0}},
               "none": {"weights": {"prime": 0, "prime_power": 0, "twice": 0, "none": 1}},
               }
    statement = (r"Найти наименьший первообразный корень по модулю $n = \VAR{n}$ или доказать, "
                 r"что первообразных корней по модулю $\VAR{n}$ нет.")
    solution = (
        r"\BLOCK{if kind == 'none'}"
        r"$n = \VAR{n} = \VAR{nfac}$, $\varphi(n) = \VAR{ph}$. Первообразные корни существуют только "
        r"по модулям $1, 2, 4, p^k, 2p^k$ ($p$ нечётное простое), а $\VAR{n}$ не такой. Докажем, что "
        r"порядок любого $x \in (\mathbb{Z}/\VAR{n}\mathbb{Z})^*$ меньше $\varphi(n)$."
        r"\BLOCK{if r.case == 'split'}\par Разложим $n = a b = \VAR{r.a} \cdot \VAR{r.b}$, "
        r"$\gcd(a, b) = 1$, $a, b > 2$; тогда $\varphi(a) = \VAR{r.phia}$ и $\varphi(b) = \VAR{r.phib}$ "
        r"чётны, и для $\gcd(x, n) = 1$ \[\begin{gathered}x^{\varphi(n)/2} = "
        r"\bigl(x^{\varphi(a)}\bigr)^{\varphi(b)/2} \equiv 1 \pmod{a},\\ x^{\varphi(n)/2} = "
        r"\bigl(x^{\varphi(b)}\bigr)^{\varphi(a)/2} \equiv 1 \pmod{b},\end{gathered}\] т.\,е. $x^{\VAR{ph // 2}} \equiv 1 \pmod{\VAR{n}}$ и "
        r"$\ord(x) \le \VAR{ph // 2} < \VAR{ph}$."
        r"\BLOCK{else}\par $n = 2^{\VAR{r.k}}$, $k \ge 3$. Для нечётного $x$ имеем $x^2 \equiv 1 \pmod 8$, "
        r"и по индукции $x^{2^{j-2}} \equiv 1 \pmod{2^j}$: если $x^{2^{j-2}} = 1 + t 2^j$, то "
        r"$x^{2^{j-1}} = 1 + t 2^{j+1} + t^2 2^{2j} \equiv 1 \pmod{2^{j+1}}$. Значит, "
        r"$\ord(x) \mid 2^{\VAR{r.k - 2}} = \VAR{ph // 2} < \VAR{ph}$.\BLOCK{endif}"
        r"\par Точнее, максимальный порядок равен функции Кармайкла "
        r"$\lambda(n) = \operatorname{lcm}(\BLOCK{for l in lam}\lambda(\VAR{l.pe})"
        r"\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}) = \operatorname{lcm}("
        r"\VAR{lam|map(attribute='lam')|join(', ')}) = \VAR{lambda_n} < \VAR{ph}$."
        r"\[\text{первообразных корней по модулю } \VAR{n} \text{ нет}.\]"
        r"\BLOCK{else}"
        r"\BLOCK{if kind == 'prime'}$n = \VAR{n}$ "
        r"--- простое\BLOCK{elif kind == 'twice'}$n = \VAR{nfac}$ имеет вид $2p^k$\BLOCK{else}"
        r"$n = \VAR{nfac}$\BLOCK{endif}, поэтому первообразные корни существуют. "
        r"$\varphi(n) = \VAR{ph}\BLOCK{if phfac != ph|string} = \VAR{phfac}\BLOCK{endif}$; $g$ ($\gcd(g, n) = 1$) "
        r"--- первообразный корень $\iff g^{\varphi(n)/q} \not\equiv 1$ для всех простых "
        r"$q \mid \varphi(n)$, т.\,е. для показателей "
        r"\BLOCK{for q in t.qs}$\VAR{t.phi}/\VAR{q} = \VAR{t.exps[loop.index0]}$"
        r"\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}. Перебираем $g = 2, 3, \dots$ "
        r"(квадраты $h^2$ пропускаем: $(h^2)^{\varphi(n)/2} = h^{\varphi(n)} \equiv 1$"
        r"\BLOCK{if kind == 'twice'}; чётные $g$ не взаимно просты с $n$\BLOCK{endif}):"
        r"\[\begin{array}{c|\BLOCK{for q in t.qs}c\BLOCK{endfor}|l}"
        r"g\BLOCK{for e in t.exps} & g^{\VAR{e}}\BLOCK{endfor} & \\ \hline "
        r"\BLOCK{for row in t.rows}\VAR{row.g}"
        r"\BLOCK{if row.skip == 'gcd'}\BLOCK{for q in t.qs} & \BLOCK{endfor} & \gcd = \VAR{row.d}"
        r"\BLOCK{elif row.skip == 'square'}\BLOCK{for q in t.qs} & \BLOCK{endfor} & = \VAR{row.h}^2"
        r"\BLOCK{else}\BLOCK{for q in t.qs} & \BLOCK{if loop.index0 < row.vals|length}"
        r"\VAR{row.vals[loop.index0]}\BLOCK{endif}\BLOCK{endfor} & "
        r"\BLOCK{if row.ok}\text{корень}\BLOCK{else}\text{нет}\BLOCK{endif}"
        r"\BLOCK{endif} \\ \BLOCK{endfor}"
        r"\end{array}\]"
        r"(вычисление прекращаем на первом показателе, дающем $1$.)"
        r"\BLOCK{if kind == 'prime_power' and n != 4}\par Проверка: $\VAR{answer}$ --- первообразный "
        r"корень по модулю $\VAR{p}$ и $\VAR{answer}^{\VAR{p - 1}} \equiv \VAR{lift} "
        r"\not\equiv 1 \pmod{\VAR{p * p}}$, что согласуется с критерием подъёма.\BLOCK{endif}"
        r"\BLOCK{if kind == 'twice'}\par Проверка: $\VAR{answer}$ нечётно и "
        r"\BLOCK{if answer > n // 2}$\VAR{answer} \equiv \VAR{answer % (n // 2)} \pmod{\VAR{n // 2}}$ "
        r"\BLOCK{else}$\VAR{answer}$ \BLOCK{endif}--- первообразный корень по "
        r"модулю $\VAR{n // 2}$ (см. теорему о модулях $2p^k$).\BLOCK{endif}"
        r"\[g = \VAR{answer}; \quad \text{всего первообразных корней } \varphi(\varphi(n)) = "
        r"\varphi(\VAR{ph}) = \VAR{count}.\]"
        r"\BLOCK{endif}")

    def sample(self, rng):
        w = self.cfg.weights
        kinds = [k for k in ("prime", "prime_power", "twice", "none") for _ in range(w[k])]
        kind = rng.choice(kinds)
        if kind == "prime":
            pool = [p for p in self.cfg.primes if steps.primitive_root(p) <= self.cfg.max_root]
            if rng.random() < self.cfg.hard_ratio:  # smallest root > 2: a longer search
                pool = [p for p in pool if steps.primitive_root(p) > 2]
        else:
            pool = getattr(self.cfg, kind)
        n = rng.choice(pool)
        ph = phi(n)
        ctx = {"n": n, "kind": kind, "nfac": _pk_tex(n), "ph": ph, "phfac": _pk_tex(ph),
               "p": max(factorize(n)), "lift": 0}
        if kind == "none":
            return {**ctx, "r": no_root_reason(n), "lam": lambda_parts(n), "lambda_n": carmichael(n),
                    "answer": "нет"}
        t = root_search(n)
        g = t["g"]
        if kind == "prime_power" and n != 4:
            ctx["lift"] = pow(g, ctx["p"] - 1, ctx["p"] ** 2)
        return {**ctx, "t": t, "count": phi(ph), "answer": g}

    def check(self, p):
        n, ph = p["n"], p["ph"]
        assert ph == sum(1 for x in range(1, n + 1) if gcd(x, n) == 1)
        # independent route: brute-force orders of all units
        orders = {}
        for x in range(1, n):
            if gcd(x, n) == 1:
                y, k = x % n, 1
                while y != 1 % n:
                    y, k = y * x % n, k + 1
                orders[x] = k
        roots = sorted(x for x, o in orders.items() if o == ph)
        if p["kind"] == "none":
            assert p["answer"] == "нет" and not roots
            assert max(orders.values()) == p["lambda_n"] < ph
        else:
            assert roots and roots[0] == p["answer"]
            assert len(roots) == p["count"]
            assert is_order(p["answer"], ph, n)
            assert len(p["t"]["rows"]) <= 12


class AllPrimitiveRoots(Task):
    id = "number_theory.all_primitive_roots"
    title_ru = "Все первообразные корни по модулю n"
    topics = ("number_theory.primitive_root",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("n = p, and (corner cases, ~1/3) n = p^2, 2p, 2p^2, 4 (any cyclic (Z/nZ)^*). "
             "g is the smallest primitive root.")
    presets = {"default": {
        "primes": [11, 13, 17, 19, 23, 29, 31, 37, 41, 43],
        "others": [9, 25, 49, 27, 10, 14, 18, 22, 26, 34, 38, 50],
        "others_ratio": 1 / 3,
    }}
    statement = (r"Известно, что $g = \VAR{g}$ --- первообразный корень по модулю $n = \VAR{n}$. "
                 r"Найти все первообразные корни по модулю $\VAR{n}$ и их число.")
    solution = (r"Группа $(\mathbb{Z}/\VAR{n}\mathbb{Z})^* = \langle \VAR{g} \rangle$ циклическая "
                r"порядка $\varphi(\VAR{n}) = \VAR{ph} = \VAR{phfac}$, и "
                r"$\ord(g^k) = \VAR{ph} / \gcd(k, \VAR{ph})$. Поэтому первообразные корни --- это "
                r"$g^k$ с $1 \le k < \VAR{ph}$, $\gcd(k, \VAR{ph}) = 1$: "
                r"$k \in \{\VAR{ks|join(', ')}\}$, их $\varphi(\VAR{ph}) = \VAR{ks|length}$. "
                r"Степени $g^k$ (каждая получается из предыдущей умножением на $g$; нужные "
                r"выделены):"
                r"\[\begin{array}{c|\BLOCK{for c in cols}c\BLOCK{endfor}}"
                r"\BLOCK{for blk in blocks}k\BLOCK{for c in blk} & \VAR{c.k}\BLOCK{endfor} \\ "
                r"g^k\BLOCK{for c in blk} & \BLOCK{if c.sel}\mathbf{\VAR{c.v}}\BLOCK{else}\VAR{c.v}"
                r"\BLOCK{endif}\BLOCK{endfor} \\ \BLOCK{if not loop.last}\hline \BLOCK{endif}"
                r"\BLOCK{endfor}\end{array}\]"
                r"\[\VAR{answer|join(',\\ ')}\quad (\text{всего } \VAR{answer|length}).\]")

    def sample(self, rng):
        if rng.random() < self.cfg.others_ratio:
            n = rng.choice(self.cfg.others)
        else:
            n = rng.choice(self.cfg.primes)
        ph = phi(n)
        g = root_search(n)["g"]
        ks = [k for k in range(1, ph) if gcd(k, ph) == 1]
        cells, v = [], 1
        for k in range(1, ph):
            v = v * g % n
            cells.append({"k": k, "v": v, "sel": gcd(k, ph) == 1})
        width = 11
        blocks = [cells[i:i + width] for i in range(0, len(cells), width)]
        return {"n": n, "g": g, "ph": ph, "phfac": _pk_tex(ph), "ks": ks, "blocks": blocks,
                "cols": blocks[0], "answer": sorted(c["v"] for c in cells if c["sel"])}

    def check(self, p):
        n, ph = p["n"], p["ph"]
        assert is_order(p["g"], ph, n)
        roots = [x for x in range(1, n) if gcd(x, n) == 1 and is_order(x, ph, n)]
        assert roots == p["answer"]
        assert len(roots) == phi(ph)
