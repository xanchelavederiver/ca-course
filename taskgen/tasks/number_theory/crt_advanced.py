"""Garner reconstruction and rational reconstruction (CRT and extended Euclid)."""

import math
from math import gcd

from taskgen.core import steps
from taskgen.core.task import SolutionDetail, Task

TX = r"\BLOCK{import 'macros.tex.j2' as tx}"
SYSTEM = (r"\[\left\{\begin{array}{l}\BLOCK{for e in eqs}x \equiv \VAR{e.r}\ (\textrm{mod}\ \VAR{e.m})"
          r"\BLOCK{if not loop.last} \\ \BLOCK{endif}\BLOCK{endfor}\end{array}\right.\]")


def garner_step(x: int, P: int, r: int, m: int, i: int) -> dict:
    y = pow(P, -1, m)
    diff = (r - x) % m
    t = diff * y % m
    new_x = x + P * t
    return {"i": i, "x": x, "P": P, "r": r, "m": m, "diff": diff, "y": y, "t": t,
            "new_x": new_x, "new_P": P * m, "check": new_x % m}


class CRTGarner(Task):
    id = "number_theory.crt_garner"
    title_ru = "Пошаговое восстановление по КТО методом Гарнера"
    topics = ("number_theory.crt",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "The last congruence is appended after the initial system has been solved."
    presets = {"default": {"sizes": [2, 3], "lo": 3, "hi": 20, "max_M": 15000}}
    statement = (r"Модули попарно взаимно просты. Сначала решить методом Гарнера систему" + SYSTEM +
                 r"Затем, не решая систему заново, присоединить сравнение $x\equiv\VAR{extra.r}"
                 r"\pmod{\VAR{extra.m}}$ и найти ответ по модулю произведения всех модулей.")
    solution = (r"Пусть перед добавлением $i$-го сравнения найдено $x_{i-1}$ с модулем "
                r"$P_{i-1}=m_1\cdots m_{i-1}$ ($x_0=0$, $P_0=1$). Полагаем $x_i=x_{i-1}+P_{i-1}t_i$, где"
                r"\[t_i\equiv(r_i-x_{i-1})P_{i-1}^{-1}\pmod{m_i},\qquad P_i=P_{i-1}m_i.\]"
                r"Для начальной системы:"
                r"\[\begin{array}{c|r|r|r|r|r|r|r}i & P_{i-1} & x_{i-1} & (r_i-x_{i-1})\bmod m_i & "
                r"P_{i-1}^{-1} & t_i & x_i & P_i \\ \hline "
                r"\BLOCK{for s in rows}\VAR{s.i} & \VAR{s.P} & \VAR{s.x} & \VAR{s.diff} & \VAR{s.y} & "
                r"\VAR{s.t} & \VAR{s.new_x} & \VAR{s.new_P} \\ \BLOCK{endfor}\end{array}\]"
                r"Проверка: $x_i$ сохраняет все прежние сравнения, поскольку добавка делится на их модули; "
                r"для нового модуля $x_i\bmod m_i=r_i$."
                r"\par Теперь присоединяем последнее сравнение с $P=\VAR{extra.P}$: "
                r"$y=\VAR{extra.P}^{-1}\equiv\VAR{extra.y}\pmod{\VAR{extra.m}}$, "
                r"$t\equiv\VAR{extra.diff}\cdot\VAR{extra.y}\equiv\VAR{extra.t}\pmod{\VAR{extra.m}}$, "
                r"\[x=\VAR{extra.x}+\VAR{extra.P}\cdot\VAR{extra.t}=\VAR{extra.new_x},\qquad "
                r"M=\VAR{extra.new_P}.\]"
                r"В отличие от формулы со слагаемыми $r_i(M/m_i)y_i$, здесь не требуется заново вычислять "
                r"все коэффициенты при добавлении модуля. Проверка всех сравнений: "
                r"\BLOCK{for e in all_eqs}$\VAR{extra.new_x}\bmod\VAR{e.m}=\VAR{extra.new_x % e.m}$"
                r"\BLOCK{if not loop.last}, \BLOCK{else}.\BLOCK{endif}\BLOCK{endfor}"
                r"\[x\equiv\VAR{answer.x}\pmod{\VAR{answer.mod}}.\]")
    def sample(self, rng):
        while True:
            n = rng.choice(self.cfg.sizes) + 1
            ms = [rng.randrange(self.cfg.lo, self.cfg.hi + 1) for _ in range(n)]
            if len(set(ms)) < n or any(math.gcd(a, b) > 1 for i, a in enumerate(ms) for b in ms[i + 1:]):
                continue
            M = math.prod(ms)
            if M <= self.cfg.max_M:
                break
        ms.sort()
        target = rng.randrange(M)
        eqs = [{"r": target % m, "m": m} for m in ms]
        rows, x, P = [], 0, 1
        for i, e in enumerate(eqs[:-1], 1):
            row = garner_step(x, P, e["r"], e["m"], i)
            rows.append(row)
            x, P = row["new_x"], row["new_P"]
        e = eqs[-1]
        extra = garner_step(x, P, e["r"], e["m"], n)
        return {"eqs": eqs[:-1], "extra": extra, "rows": rows, "all_eqs": eqs,
                "answer": {"x": extra["new_x"], "mod": M}}

    def check(self, p):
        x, M = p["answer"]["x"], p["answer"]["mod"]
        assert M == math.prod(e["m"] for e in p["all_eqs"])
        assert all((x - e["r"]) % e["m"] == 0 for e in p["all_eqs"])
        assert 0 <= x < M
        old_x, old_P = 0, 1
        for row in p["rows"] + [p["extra"]]:
            assert row["x"] == old_x and row["P"] == old_P
            assert row["P"] * row["y"] % row["m"] == 1
            assert row["new_x"] == old_x + old_P * row["t"]
            assert row["new_x"] % row["m"] == row["r"]
            old_x, old_P = row["new_x"], row["new_P"]
        assert (old_x, old_P) == (x, M)


def rational_reconstruct(m: int, r: int, A: int, B: int) -> dict:
    rows = steps.xgcd_rows(m, r)
    stop = len(rows) - 2
    for i in range(1, len(rows) - 1):
        if abs(rows[i]["r"]) <= A:
            stop = i
            break
    row = rows[stop]
    a, b = row["r"], row["v"]
    if b < 0:
        a, b = -a, -b
    valid = (a != 0 and abs(a) <= A and 0 < b <= B and gcd(a, b) == 1 and gcd(b, m) == 1
             and (r * b - a) % m == 0)
    return {"rows": rows[:stop + 1], "stop": stop, "a": a, "b": b, "valid": valid}


class RationalReconstruction(Task):
    id = "number_theory.rational_reconstruction"
    title_ru = "Рациональное восстановление расширенным алгоритмом Евклида"
    topics = ("number_theory.crt", "number_theory.euclid")
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Bound 2AB<m; stop at the first |r_i|<=A. Preset `none` forces an unrepresentable residue.")
    presets = {"default": {"lo": 101, "hi": 500, "none_ratio": 0.2},
               "none": {"none_ratio": 1.0}}
    statement = (r"Даны $m=\VAR{m}$, $r=\VAR{r}$ и границы $A=\VAR{A}$, $B=\VAR{B}$, причём $2AB<m$. "
                 r"Найти несократимую дробь $a/b$ такую, что"
                 r"\[r\equiv a b^{-1}\pmod m,\qquad |a|\le A,\quad 0<b\le B,\quad \gcd(b,m)=1,\]"
                 r"или показать, что такой дроби нет. Использовать остатки и коэффициенты Безу из "
                 r"расширенного алгоритма Евклида для $(m,r)$; доказать единственность ответа.")
    solution = (TX + r"Выполняем расширенный алгоритм Евклида до первого $|r_i|\le A$; на каждой строке "
                r"$r_i=u_i m+v_i r$, поэтому $r_i/v_i\equiv r\pmod m$, если $v_i$ обратимо:"
                r"\VAR{tx.xgcd_table(t.rows, m, r)}"
                r"На последней строке получаем кандидата $a=\VAR{t.a}$, $b=\VAR{t.b}$ (при необходимости "
                r"меняем знаки, чтобы $b>0$)."
                r"\BLOCK{if t.valid} Он удовлетворяет всем границам, $\gcd(\VAR{t.a},\VAR{t.b})=1$ и "
                r"$\VAR{r}\cdot\VAR{t.b}\equiv\VAR{t.a}\pmod{\VAR{m}}$."
                r"\[\frac ab=\frac{\VAR{t.a}}{\VAR{t.b}}.\]"
                r"\BLOCK{else} У кандидата нарушено по крайней мере одно условие на знаменатель, взаимную "
                r"простоту или сравнение; поэтому подходящей дроби нет."
                r"\[\text{решения нет}.\]\BLOCK{endif}"
                r"\par Единственность. Если $a/b$ и $a'/b'$ удовлетворяют условиям, то "
                r"$m\mid ab'-a'b$. Но $|ab'-a'b|\le 2AB<m$, следовательно $ab'=a'b$. Обе дроби "
                r"несократимы и имеют положительные знаменатели, поэтому они совпадают.")
    def sample(self, rng):
        cfg = self.cfg
        m = rng.randrange(cfg.lo | 1, cfg.hi + 1, 2)
        A = max(3, math.isqrt(m // 2) * 3 // 4)
        B = max(3, (m - 1) // (2 * A))
        while 2 * A * B >= m:
            B -= 1
        force_none = rng.random() < cfg.none_ratio
        if force_none:
            while True:
                r = rng.randrange(2, m)
                t = rational_reconstruct(m, r, A, B)
                if not t["valid"]:
                    break
        else:
            while True:
                a = rng.randint(-A, A)
                b = rng.randint(2, B)
                if a and gcd(a, b) == gcd(b, m) == 1:
                    break
            r = a * pow(b, -1, m) % m
            t = rational_reconstruct(m, r, A, B)
        return {"m": m, "r": r, "A": A, "B": B, "t": t,
                "answer": {"a": t["a"], "b": t["b"]} if t["valid"] else "нет"}

    def check(self, p):
        m, r, A, B = p["m"], p["r"], p["A"], p["B"]
        assert 2 * A * B < m
        sols = []
        for b in range(1, B + 1):
            if gcd(b, m) != 1:
                continue
            a0 = r * b % m
            for a in {a0, a0 - m}:
                if 0 < abs(a) <= A and gcd(a, b) == 1:
                    sols.append((a, b))
        assert len(sols) <= 1
        if p["t"]["valid"]:
            assert p["answer"] == {"a": sols[0][0], "b": sols[0][1]}
            assert p["t"]["a"] * pow(p["t"]["b"], -1, m) % m == r
        else:
            assert not sols and p["answer"] == "нет"
