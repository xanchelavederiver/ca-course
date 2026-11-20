"""Batch inversion and the binary GCD algorithm (lecture sem1/03)."""

from math import gcd

from taskgen.core import steps
from taskgen.core.nt import random_prime
from taskgen.core.task import SolutionDetail, Task

TX = r"\BLOCK{import 'macros.tex.j2' as tx}"


class BatchInverse(Task):
    id = "number_theory.batch_inverse"
    title_ru = "Пакетное обращение с одним вызовом расширенного алгоритма Евклида"
    topics = ("number_theory.euclid",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Montgomery's batch inversion: one extended Euclid call and 3(k-1) multiplications "
             "for k nonzero inputs. Preset `zeros` forces one zero entry; zero entries are skipped.")
    presets = {"default": {"lo": 30, "hi": 250, "sizes": [4, 5, 6], "zero_ratio": 0.15},
               "zeros": {"zero_ratio": 1.0}}
    statement = (r"Даны простое $p = \VAR{p}$ и элементы $a_i$ поля $\mathbb{Z}/p\mathbb{Z}$: "
                 r"\[\VAR{items|map(attribute='a')|join(', ')}.\] Найти обратные ко всем ненулевым "
                 r"элементам, используя приём Монтгомери: построить произведения с накоплением и "
                 r"выполнить расширенный алгоритм Евклида ровно один раз. Нули обрабатывать отдельно. "
                 r"Подсчитать число умножений по модулю $p$.")
    solution = (TX + r"\BLOCK{if has_zero}Нулевой элемент необратим; вычёркиваем нули, а их позиции "
                r"запоминаем. \BLOCK{endif}Для ненулевых элементов $a_1,\dots,a_{\VAR{k}}$ строим "
                r"$P_0=1$, $P_i=P_{i-1}a_i\bmod p$:"
                r"\[\begin{array}{c|r|r}i & a_i & P_i \\ \hline "
                r"\BLOCK{for r in prefix}\VAR{r.i} & \VAR{r.a} & \VAR{r.P} \\ \BLOCK{endfor}\end{array}\]"
                r"Это $k-1=\VAR{k - 1}$ умножений. Единственное обращение --- к $P_{\VAR{k}}$: "
                r"\VAR{tx.inverse(inv)}"
                r"Идём в обратном порядке. Если $z_i=P_i^{-1}$, то $a_i^{-1}=P_{i-1}z_i$, а затем "
                r"$z_{i-1}=z_i a_i$; на каждом шаге нужны два умножения:"
                r"\[\begin{array}{c|r|r|r|r|r}i & a_i & P_{i-1} & z_i & a_i^{-1} & z_{i-1} \\ \hline "
                r"\BLOCK{for r in back}\VAR{r.i} & \VAR{r.a} & \VAR{r.prevP} & \VAR{r.invP} & "
                r"\VAR{r.inv_a} & \VAR{r.next_invP} \\ \BLOCK{endfor}\end{array}\]"
                r"Обратный ход требует $2(k-1)=\VAR{2 * (k - 1)}$ умножений. Всего "
                r"$3(k-1)=\VAR{muls}$ умножений и одно обращение. Ответ в исходных позициях:"
                r"\[\begin{array}{c|\BLOCK{for x in items}r\BLOCK{endfor}}a_i"
                r"\BLOCK{for x in items} & \VAR{x.a}\BLOCK{endfor} \\ \hline a_i^{-1}"
                r"\BLOCK{for x in items} & \BLOCK{if x.inv is none}\text{---}\BLOCK{else}\VAR{x.inv}"
                r"\BLOCK{endif}\BLOCK{endfor}\end{array}\]")
    def sample(self, rng):
        cfg = self.cfg
        p = random_prime(rng, cfg.lo, cfg.hi)
        n = rng.choice(cfg.sizes)
        values = [rng.randrange(1, p) for _ in range(n)]
        if rng.random() < cfg.zero_ratio:
            values[rng.randrange(n)] = 0
        nz = [(i, a) for i, a in enumerate(values) if a]
        k = len(nz)
        prefix, prod = [], 1
        for i, (_, a) in enumerate(nz, 1):
            prod = prod * a % p
            prefix.append({"i": i, "a": a, "P": prod})
        inv = steps.inverse_rows(prod, p)
        back, z = [], inv["inv"]
        for i in range(k, 0, -1):
            a = nz[i - 1][1]
            prev = prefix[i - 2]["P"] if i > 1 else 1
            inv_a = prev * z % p
            next_z = z * a % p if i > 1 else 1
            back.append({"i": i, "a": a, "prevP": prev, "invP": z, "inv_a": inv_a,
                         "next_invP": next_z})
            z = next_z
        inverses = {i: row["inv_a"] for (i, _), row in zip(nz, reversed(back))}
        items = [{"a": a, "inv": inverses.get(i)} for i, a in enumerate(values)]
        return {"p": p, "items": items, "k": k, "prefix": prefix, "inv": inv, "back": back,
                "has_zero": k < n, "muls": 3 * (k - 1),
                "answer": [x["inv"] if x["inv"] is not None else "нет" for x in items]}

    def check(self, p):
        mod = p["p"]
        assert p["k"] == sum(x["a"] != 0 for x in p["items"]) >= 2
        for x, ans in zip(p["items"], p["answer"]):
            if x["a"] == 0:
                assert x["inv"] is None and ans == "нет"
            else:
                assert x["a"] * x["inv"] % mod == 1 and ans == x["inv"]
        prod = 1
        for row in p["prefix"]:
            prod = prod * row["a"] % mod
            assert row["P"] == prod
        assert p["inv"]["inv"] * prod % mod == 1 and p["muls"] == 3 * (p["k"] - 1)


def binary_gcd_trace(a: int, b: int) -> dict:
    u, v, shift, rows = a, b, 0, []

    def row(kind, op):
        rows.append({"i": len(rows) + 1, "u": u, "v": v, "kind": kind, "op": op})

    while u % 2 == 0 and v % 2 == 0:
        u, v = u // 2, v // 2
        shift += 1
        row("shift", r"u,v\gets u/2,v/2")
    while u % 2 == 0:
        u //= 2
        row("shift", r"u\gets u/2")
    while v:
        while v % 2 == 0:
            v //= 2
            row("shift", r"v\gets v/2")
        if not v:
            break
        if u > v:
            u, v = v, u
            row("swap", r"u\leftrightarrow v")
        v -= u
        row("sub", r"v\gets v-u")
    return {"rows": rows, "shift": shift, "gcd": u << shift,
            "subtractions": sum(r["kind"] == "sub" for r in rows),
            "shifts": sum(r["kind"] == "shift" for r in rows)}


class BinaryGCD(Task):
    id = "number_theory.binary_gcd"
    title_ru = "Бинарный алгоритм Евклида и сравнение с классическим"
    topics = ("number_theory.euclid",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "Full Stein trace; presets `common` (a shared power of two) and `odd`."
    presets = {"default": {"lo": 100, "hi": 3000, "mode": "mixed"},
               "common": {"mode": "common"}, "odd": {"mode": "odd"}}
    statement = (r"Для $a=\VAR{a}$, $b=\VAR{b}$ найти $\gcd(a,b)$ двумя способами: классическим "
                 r"алгоритмом Евклида и бинарным алгоритмом Штейна. Для бинарного алгоритма выписать "
                 r"все деления на $2$, перестановки и вычитания. Сравнить число делений с остатком в "
                 r"классическом алгоритме с числом вычитаний и сдвигов в бинарном.")
    solution = (r"Классический алгоритм: $r_{i-2}=q_i r_{i-1}+r_i$:"
                r"\[\begin{array}{r|r|r}r_{i-2} & q_i & r_i \\ \hline "
                r"\BLOCK{for r in classical}\VAR{r.prev} & \VAR{r.q} & \VAR{r.rem} \\ "
                r"\BLOCK{endfor}\end{array}\] Выполнено $\VAR{divisions}$ делений с остатком; последний "
                r"ненулевой остаток равен $\VAR{answer.d}$."
                r"\par Бинарный алгоритм. Общие степени двойки выносим отдельно: если после их удаления "
                r"получен НОД $u$, то исходный НОД равен $2^{\VAR{t.shift}}u$. Для нечётного $v$ при "
                r"$u>v$ меняем числа местами, после чего $v-u$ чётно и его можно делить на $2$:"
                r"\[\begin{array}{c|r|r|l}\text{шаг} & u & v & \text{операция} \\ \hline "
                r"\BLOCK{for r in t.rows}\VAR{r.i} & \VAR{r.u} & \VAR{r.v} & \VAR{r.op} \\ "
                r"\BLOCK{endfor}\end{array}\]"
                r"Получено $\gcd(a,b)=2^{\VAR{t.shift}}\cdot\VAR{t.u}=\VAR{answer.d}$. Здесь "
                r"$\VAR{t.subtractions}$ вычитаний и $\VAR{t.shifts}$ сдвигов (включая удаление общих "
                r"степеней двойки). В отличие от классического алгоритма, деления с остатком не нужны; "
                r"платой может быть большее число элементарных шагов."
                r"\[\gcd(\VAR{a},\VAR{b})=\VAR{answer.d}.\]")
    def sample(self, rng):
        cfg = self.cfg
        while True:
            g = rng.randrange(1, 30) | 1
            a = g * rng.randrange(max(2, cfg.lo // 100), max(3, cfg.hi // 100))
            b = g * rng.randrange(max(2, cfg.lo // 100), max(3, cfg.hi // 100))
            mode = rng.choice(["common", "plain"]) if cfg.mode == "mixed" else cfg.mode
            if mode == "common":
                s = rng.randrange(1, 4)
                a, b = a << s, b << s
            elif mode == "odd":
                a, b = a | 1, b | 1
            if a == b or not (cfg.lo <= max(a, b) <= cfg.hi * 2):
                continue
            eu = steps.xgcd_rows(a, b)
            trace = binary_gcd_trace(a, b)
            if len(eu) - 2 >= 3 and len(trace["rows"]) <= 35:
                break
        classical = [{"prev": eu[i - 2]["r"], "q": eu[i]["q"], "rem": eu[i]["r"]}
                     for i in range(2, len(eu))]
        return {"a": a, "b": b, "classical": classical, "divisions": len(classical),
                "t": {**trace, "u": trace["gcd"] >> trace["shift"]},
                "answer": {"d": trace["gcd"], "divisions": len(classical),
                           "subtractions": trace["subtractions"], "shifts": trace["shifts"]}}

    def check(self, p):
        a, b, t = p["a"], p["b"], p["t"]
        assert p["answer"]["d"] == gcd(a, b) == t["gcd"]
        assert p["answer"]["divisions"] == len(p["classical"])
        assert p["answer"]["subtractions"] == t["subtractions"]
        assert p["answer"]["shifts"] == t["shifts"]
        u, v = a, b
        for row in t["rows"]:
            if row["kind"] == "shift":
                if row["op"] == r"u,v\gets u/2,v/2":
                    u, v = u // 2, v // 2
                elif row["op"] == r"u\gets u/2":
                    u //= 2
                else:
                    v //= 2
            elif row["kind"] == "swap":
                u, v = v, u
            else:
                v -= u
            assert (u, v) == (row["u"], row["v"])
        assert u << t["shift"] == gcd(a, b) and v == 0
