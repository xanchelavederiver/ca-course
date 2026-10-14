"""Chinese remainder theorem (lecture sem2/02): systems of linear congruences.

* number_theory.crt — pairwise coprime moduli, the formula x = sum r_i M_i y_i with the
  inverses y_i = M_i^{-1} mod m_i found by the extended Euclidean algorithm;
* number_theory.crt_general — moduli that are NOT pairwise coprime: the solvability criterion
  r_i = r_j (mod gcd(m_i, m_j)) and the solution modulo lcm(m_i) by successive merging;
  unsolvable systems (~1/4 by default) and a modulus dividing another one are kept.
"""

import math

from taskgen.core import steps
from taskgen.core.task import SolutionDetail, Task

TX = r"\BLOCK{import 'macros.tex.j2' as tx}"
SYSTEM = (r"\[\left\{\begin{array}{l}\BLOCK{for e in eqs}x \equiv \VAR{e.r}\ (\textrm{mod}\ \VAR{e.m})"
          r"\BLOCK{if not loop.last} \\ \BLOCK{endif}\BLOCK{endfor}\end{array}\right.\]")
CHECK = (r"Проверка: \BLOCK{for e in eqs}$\VAR{x} = \VAR{e.m} \cdot \VAR{e.q} + \VAR{e.rem}$"
         r"\BLOCK{if e.r != e.rem}, $\VAR{e.rem} \equiv \VAR{e.r}$\BLOCK{endif}"
         r"\BLOCK{if not loop.last}; \BLOCK{else}.\BLOCK{endif}\BLOCK{endfor}")


def _check_rows(x: int, eqs: list[dict]) -> list[dict]:
    return [{"r": e["r"], "m": e["m"], "q": x // e["m"], "rem": x % e["m"]} for e in eqs]


def _inv(a: int, m: int) -> dict | None:
    """Euclid trace of a^{-1} mod m (None when the inverse is obvious: a = 1 or m <= 2)."""
    a %= m
    if m <= 2 or a == 1:
        return None
    return steps.inverse_rows(a, m)


# --- pairwise coprime moduli ------------------------------------------------------------


class CRT(Task):
    id = "number_theory.crt"
    title_ru = "Китайская теорема об остатках"
    topics = ("number_theory.crt",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("2-3 congruences, pairwise coprime (also composite) moduli; a residue may be given "
             "negative or unreduced (~1/5), so it must be reduced first.")
    presets = {"default": {"sizes": [2, 3, 3], "lo": 3, "hi": 30, "max_M": 6000,
                           "unreduced_ratio": 0.2}}
    statement = (r"Решить систему сравнений с помощью китайской теоремы об остатках "
                 r"(обратные элементы $y_i = M_i^{-1} \bmod m_i$ найти расширенным алгоритмом "
                 r"Евклида):" + SYSTEM)
    solution = (TX + r"Модули попарно взаимно просты: \BLOCK{for g in gcds}$\gcd(\VAR{g.a}, \VAR{g.b}) = 1$"
                r"\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}; поэтому решение существует "
                r"и единственно по модулю $M = \BLOCK{for e in eqs}\VAR{e.m}\BLOCK{if not loop.last} \cdot "
                r"\BLOCK{endif}\BLOCK{endfor} = \VAR{M}$."
                r"\BLOCK{if unreduced} Сначала приведём остатки: \BLOCK{for e in eqs if e.r != e.rr}"
                r"$\VAR{e.r} \equiv \VAR{e.rr}\ (\textrm{mod}\ \VAR{e.m})$\BLOCK{if not loop.last}, "
                r"\BLOCK{endif}\BLOCK{endfor}.\BLOCK{endif}"
                r"\BLOCK{for e in eqs}\par\noindent $i = \VAR{loop.index}$: $M_{\VAR{loop.index}} = M/\VAR{e.m} = "
                r"\VAR{e.Mi} \equiv \VAR{e.Mi_mod}\ (\textrm{mod}\ \VAR{e.m})$"
                r"\BLOCK{if e.inv is none}, $y_{\VAR{loop.index}} = \VAR{e.y}$ (очевидно: "
                r"$\VAR{e.Mi_mod} \cdot \VAR{e.y} \equiv 1$).\BLOCK{else}. \VAR{tx.inverse(e.inv)} "
                r"Итак, $y_{\VAR{loop.index}} = \VAR{e.y}$ (проверка: $\VAR{e.Mi_mod} \cdot \VAR{e.y} = "
                r"\VAR{e.Mi_mod * e.y} \equiv 1$).\BLOCK{endif}\BLOCK{endfor}"
                r"\par По формуле $x \equiv \sum_i r_i M_i y_i \pmod M$:"
                r"\[x \equiv \BLOCK{for e in eqs}\VAR{e.rr} \cdot \VAR{e.Mi} \cdot \VAR{e.y}\BLOCK{if not loop.last}"
                r" + \BLOCK{endif}\BLOCK{endfor} = \VAR{total} \equiv \VAR{x}\ (\textrm{mod}\ \VAR{M}).\]"
                + CHECK.replace("eqs", "chk") +
                r"\[x \equiv \VAR{x}\ (\textrm{mod}\ \VAR{M}).\]")

    def sample(self, rng):
        while True:
            k = rng.choice(self.cfg.sizes)
            ms = [rng.randrange(self.cfg.lo, self.cfg.hi + 1) for _ in range(k)]
            if len(set(ms)) < k or any(math.gcd(a, b) > 1 for i, a in enumerate(ms) for b in ms[i + 1:]):
                continue
            M = math.prod(ms)
            # at least one non-trivial inverse, and M stays hand-sized
            if M <= self.cfg.max_M and any((M // m) % m not in (0, 1) for m in ms if m > 2):
                break
        ms.sort()
        x = rng.randrange(M)
        eqs = []
        for m in ms:
            rr = x % m
            r = rr
            if rng.random() < self.cfg.unreduced_ratio:
                r = rr - m if rr and rng.random() < 0.6 else rr + m * rng.randrange(1, 4)
            Mi = M // m
            y = pow(Mi % m, -1, m) if m > 1 else 0
            eqs.append({"r": r, "rr": rr, "m": m, "Mi": Mi, "Mi_mod": Mi % m, "y": y,
                        "inv": _inv(Mi, m)})
        total = sum(e["rr"] * e["Mi"] * e["y"] for e in eqs)
        gcds = [{"a": a, "b": b} for i, a in enumerate(ms) for b in ms[i + 1:]]
        return {"eqs": eqs, "M": M, "gcds": gcds, "total": total, "x": x,
                "unreduced": any(e["r"] != e["rr"] for e in eqs),
                "chk": _check_rows(x, eqs), "answer": {"x": x, "mod": M}}

    def check(self, p):
        x, M, eqs = p["answer"]["x"], p["answer"]["mod"], p["eqs"]
        ms = [e["m"] for e in eqs]
        assert M == math.prod(ms) and 0 <= x < M
        assert all(math.gcd(a, b) == 1 for i, a in enumerate(ms) for b in ms[i + 1:])
        # independent: brute force over Z/MZ -- exactly one solution
        sols = [t for t in range(M) if all((t - e["r"]) % e["m"] == 0 for e in eqs)]
        assert sols == [x], sols
        for e in eqs:
            assert e["Mi_mod"] * e["y"] % e["m"] == 1 % e["m"]
        assert p["total"] % M == x


# --- arbitrary moduli -----------------------------------------------------------------


def merge_steps(eqs: list[dict]) -> dict:
    """Successive merging x = a + L t of x = a (mod L) with x = r (mod m)."""
    a, L = eqs[0]["r"] % eqs[0]["m"], eqs[0]["m"]
    rows = []
    for e in eqs[1:]:
        r, m = e["r"], e["m"]
        d = math.gcd(L, m)
        diff = r - a
        assert diff % d == 0
        L1, m1, c = L // d, m // d, diff // d
        row = {"a": a, "L": L, "r": r, "m": m, "d": d, "diff": diff, "L1": L1, "m1": m1, "c": c,
               "L1_mod": L1 % m1, "c_mod": c % m1, "trivial": m1 == 1}
        if m1 == 1:
            t = 0
            row.update({"inv": None, "y": 0})
        else:
            y = pow(L1 % m1, -1, m1)
            row.update({"inv": _inv(L1, m1), "y": y})
            t = c * y % m1
        newL = L * m1
        newa = (a + L * t) % newL
        row.update({"t": t, "x": a + L * t, "newL": newL, "newa": newa})
        rows.append(row)
        a, L = newa, newL
    return {"rows": rows, "x": a, "L": L}


class CRTGeneral(Task):
    id = "number_theory.crt_general"
    title_ru = "Система сравнений с не взаимно простыми модулями"
    topics = ("number_theory.crt",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Moduli are not pairwise coprime; ~1/4 of the systems are unsolvable (presets "
             "'solvable' / 'unsolvable' force the outcome); a modulus may divide another one "
             "(then the congruence is redundant or contradictory).")
    presets = {
        "default": {"sizes": [2, 3], "lo": 4, "hi": 60, "max_L": 1500, "unsolvable_ratio": 0.25,
                    "divides_ratio": 0.15},
        "solvable": {"unsolvable_ratio": 0.0},
        "unsolvable": {"unsolvable_ratio": 1.0},
    }
    statement = (r"Выяснить, совместна ли система сравнений, и если да, найти все её решения "
                 r"(модули не обязательно попарно взаимно просты):" + SYSTEM)
    solution = (TX + r"Критерий: система $x \equiv r_i \pmod{m_i}$ совместна тогда и только тогда, когда "
                r"$r_i \equiv r_j \pmod{\gcd(m_i, m_j)}$ для всех $i < j$; решение единственно по модулю "
                r"$\operatorname{lcm}(m_1, \dots, m_k)$."
                r"\[\begin{array}{c|c|r|c}"
                r"(m_i, m_j) & \gcd & r_i - r_j & \gcd \mid r_i - r_j? \\ \hline "
                r"\BLOCK{for c in pairs}(\VAR{c.mi}, \VAR{c.mj}) & \VAR{c.d} & \VAR{c.diff} & "
                r"\BLOCK{if c.ok}\text{да}\BLOCK{else}\text{нет}\BLOCK{endif} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"\BLOCK{if not solvable}\BLOCK{set c = bad}Для пары модулей $\VAR{c.mi}$, $\VAR{c.mj}$: "
                r"из первого сравнения $x \equiv \VAR{c.ri} \equiv \VAR{c.ri % c.d}\ (\textrm{mod}\ \VAR{c.d})$, "
                r"из второго $x \equiv \VAR{c.rj} \equiv \VAR{c.rj % c.d}\ (\textrm{mod}\ \VAR{c.d})$ "
                r'"--- противоречие. Система несовместна.'
                r"\[\text{решений нет}.\]"
                r"\BLOCK{else}Все условия выполнены, система совместна. Решаем последовательно: из первого "
                r"сравнения $x = \VAR{m.rows[0].a} + \VAR{m.rows[0].L}t$."
                r"\BLOCK{for s in m.rows}\par\noindent Присоединяем $x \equiv \VAR{s.r}\ (\textrm{mod}\ \VAR{s.m})$: "
                r"$\VAR{s.L}t \equiv \VAR{s.r} - \VAR{s.a} = \VAR{s.diff}\ (\textrm{mod}\ \VAR{s.m})$, "
                r"$d = \gcd(\VAR{s.L}, \VAR{s.m}) = \VAR{s.d}$"
                r"\BLOCK{if s.trivial}, $\VAR{s.m} \mid \VAR{s.L}$ и $\VAR{s.d} \mid \VAR{s.diff}$: сравнение "
                r"выполнено при любом $t$ (оно следует из предыдущих), модуль не меняется: "
                r"$x \equiv \VAR{s.newa}\ (\textrm{mod}\ \VAR{s.newL})$."
                r"\BLOCK{else}\BLOCK{if s.d > 1}; делим на $d$: "
                r"$\VAR{s.L1}t \equiv \VAR{s.c}\ (\textrm{mod}\ \VAR{s.m1})$\BLOCK{endif}"
                r"\BLOCK{if s.L1_mod != s.L1 or s.c_mod != s.c}, т.\,е. $\VAR{s.L1_mod}t \equiv \VAR{s.c_mod}\ "
                r"(\textrm{mod}\ \VAR{s.m1})$\BLOCK{endif}. "
                r"\BLOCK{if s.inv is none}Обратный: $\VAR{s.L1_mod}^{-1} \equiv \VAR{s.y}\ (\textrm{mod}\ \VAR{s.m1})$. "
                r"\BLOCK{else}\VAR{tx.inverse(s.inv)} \BLOCK{endif}"
                r"$t \equiv \VAR{s.c_mod} \cdot \VAR{s.y} \equiv \VAR{s.t}\ (\textrm{mod}\ \VAR{s.m1})$, "
                r"$x = \VAR{s.a} + \VAR{s.L} \cdot \VAR{s.t} = \VAR{s.x}$, новый модуль "
                r"$\operatorname{lcm}(\VAR{s.L}, \VAR{s.m}) = \VAR{s.L} \cdot \VAR{s.m1} = \VAR{s.newL}$: "
                r"$x \equiv \VAR{s.newa}\ (\textrm{mod}\ \VAR{s.newL})$.\BLOCK{endif}\BLOCK{endfor}"
                r"\par " + CHECK.replace("eqs", "chk").replace(r"\VAR{x}", r"\VAR{m.x}") +
                r"\[x \equiv \VAR{m.x}\ (\textrm{mod}\ \VAR{m.L}).\]\BLOCK{endif}")

    def _moduli(self, rng) -> list[int]:
        cfg = self.cfg
        forced = rng.random() < cfg.divides_ratio
        while True:
            k = rng.choice(cfg.sizes)
            ms = [rng.randrange(cfg.lo, cfg.hi + 1) for _ in range(k)]
            if forced:  # corner case: m_j | m_i
                i = rng.randrange(k)
                divs = [d for d in range(3, ms[i]) if ms[i] % d == 0]
                if not divs:
                    continue
                ms[(i + 1) % k] = rng.choice(divs)
            if len(set(ms)) < k:
                continue
            divides = any(a % b == 0 for a in ms for b in ms if a != b)
            if divides != forced:  # keep the corner case at its nominal rate
                continue
            pairs_g = [math.gcd(a, b) for i, a in enumerate(ms) for b in ms[i + 1:]]
            L = math.lcm(*ms)
            if max(pairs_g) > 1 and L <= cfg.max_L:
                return ms

    def sample(self, rng):
        unsolvable = rng.random() < self.cfg.unsolvable_ratio
        while True:
            ms = self._moduli(rng)
            L = math.lcm(*ms)
            x0 = rng.randrange(L)
            rs = [x0 % m for m in ms]
            if unsolvable:
                bad = [(i, j) for i in range(len(ms)) for j in range(i + 1, len(ms))
                       if math.gcd(ms[i], ms[j]) > 1]
                i, j = rng.choice(bad)
                if rng.random() < 0.5:
                    i, j = j, i
                d = math.gcd(ms[i], ms[j])
                rs[j] = (rs[j] + rng.randrange(1, d)) % ms[j]
            eqs = [{"r": r, "m": m} for r, m in zip(rs, ms)]
            pairs = []
            for i in range(len(ms)):
                for j in range(i + 1, len(ms)):
                    d = math.gcd(ms[i], ms[j])
                    pairs.append({"mi": ms[i], "mj": ms[j], "ri": rs[i], "rj": rs[j], "d": d,
                                  "diff": rs[i] - rs[j], "ok": (rs[i] - rs[j]) % d == 0})
            solvable = all(c["ok"] for c in pairs)
            if solvable == (not unsolvable):
                break
        ctx = {"eqs": eqs, "pairs": pairs, "solvable": solvable, "lcm": L}
        if solvable:
            m = merge_steps(eqs)
            ctx.update({"m": m, "chk": _check_rows(m["x"], eqs), "bad": None,
                        "answer": {"x": m["x"], "mod": m["L"]}})
        else:
            ctx.update({"m": None, "chk": [], "bad": next(c for c in pairs if not c["ok"]),
                        "answer": "нет решений"})
        return ctx

    def check(self, p):
        eqs = p["eqs"]
        ms = [e["m"] for e in eqs]
        L = math.lcm(*ms)
        assert any(math.gcd(a, b) > 1 for i, a in enumerate(ms) for b in ms[i + 1:])
        # independent: brute force over one period lcm(m_i)
        sols = [t for t in range(L) if all((t - e["r"]) % e["m"] == 0 for e in eqs)]
        if p["solvable"]:
            assert p["answer"] == {"x": sols[0], "mod": L} and len(sols) == 1, sols
        else:
            assert sols == [] and p["answer"] == "нет решений"
