"""PRNG tasks on predictability, ambiguous LCG recovery, RANDU and Blum--Blum--Shub."""

from math import gcd

from taskgen.core.task import SolutionDetail, Task


class LCGPredictableFullPeriod(Task):
    id = "crypto.lcg_full_period_predictable"
    title_ru = "Максимальный период не означает непредсказуемость"
    topics = ("crypto.prng",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"k_lo": 4, "k_hi": 7}}
    statement = (r"Линейный конгруэнтный генератор задан формулой "
                 r"$x_{n+1}=x_n+1\pmod{2^{\VAR{k}}}$, $x_0=\VAR{x0}$. "
                 r'а)~Доказать с помощью теоремы Халла~--~Добелла, что период максимален. '
                 r"б)~Вычислить $x_{\VAR{N}}$. в)~Объяснить, сколько наблюдений достаточно для предсказания "
                 r"всей последовательности и почему максимальный период не обеспечивает криптографической стойкости.")
    solution = (r'Здесь $a=c=1$, $m=2^{\VAR{k}}=\VAR{m}$. Условия теоремы Халла~--~Добелла выполнены: '
                 r"$\gcd(c,m)=1$; единственный простой делитель $2$ модуля делит $a-1=0$; "
                 r"наконец, $4\mid m$ и $4\mid a-1=0$. Следовательно, период равен $m=\VAR{m}$ при любом seed. "
                 r"Индукция даёт $x_n=x_0+n\bmod m$, поэтому "
                 r"\[x_{\VAR{N}}=\VAR{x0}+\VAR{N}\equiv\VAR{answer.value}\pmod{\VAR{m}}.\] "
                 r"Для предсказания достаточно знать лишь одно состояние (а при неизвестном начальном состоянии "
                 r"и известной формуле --- один выход). Более того, два последовательных выхода различаются ровно на $1$. "
                 r"Таким образом, период $\VAR{m}$ максимален, но генератор полностью предсказуем и непригоден "
                 r"для ключей, nonce или других секретных значений. "
                 r"\[\boxed{T=\VAR{m},\quad x_{\VAR{N}}=\VAR{answer.value}}.\]")

    def sample(self, rng):
        k = rng.randint(self.cfg.k_lo, self.cfg.k_hi)
        m = 1 << k
        x0 = rng.randrange(m)
        N = rng.randrange(2 * m, 7 * m)
        value = (x0 + N) % m
        return {"k": k, "m": m, "x0": x0, "N": N,
                "answer": {"period": m, "value": value}}

    def check(self, p):
        assert p["m"] == 1 << p["k"]
        assert p["answer"]["period"] == p["m"]
        assert p["answer"]["value"] == (p["x0"] + p["N"]) % p["m"]


class LCGAmbiguousRecovery(Task):
    id = "crypto.lcg_recover_ambiguous"
    title_ru = "Неоднозначное восстановление параметров ЛКГ"
    topics = ("crypto.prng",)
    complexity = 3
    solution_detail = SolutionDetail.FULL
    notes = ("The gcd is a proper multiple of the true modulus. Non-invertibility is checked only after "
             "enumerating candidate moduli and holds for every consistent candidate.")
    presets = {"default": {"moduli": [6, 8, 9, 10, 12, 14, 15, 16, 18, 20]}}
    statement = (r"Выходы неизвестного ЛКГ $x_{i+1}=ax_i+c\bmod m$ подряд: $\VAR{xs_tex}$. "
                 r"Попытаться восстановить $a,c,m$ через разности $t_i=x_{i+1}-x_i$ и величины "
                 r"$u_i=t_{i+2}t_i-t_{i+1}^2$. Показать, почему здесь нельзя полагать $m=\gcd(u_i)$ "
                 r"и почему стандартную формулу $a=t_1t_0^{-1}$ нельзя применять без проверки "
                 r"обратимости $t_0$ по каждому возможному модулю. Найти \emph{все} тройки $(a,c,m)$, "
                 r"согласованные с шестью наблюдениями. Что потребуется для однозначного ответа?")
    solution = (r"Разности: $t=\VAR{ts_tex}$. Тогда $u=\VAR{us_tex}$ и $G=\gcd(u_0,u_1,u_2)=\VAR{G}$. "
                 r"Из теории следует только $m\mid G$, а не обязательно $m=G$. Имеем "
                 r"$\gcd(t_0,G)=\VAR{gcd_G}>1$, поэтому $t_0$ не обратим по модулю $G$. Однако отсюда "
                 r"нельзя вычислить $\gcd(t_0,m)$ для неизвестного делителя $m\mid G$: например, "
                 r"при $t_0=2$, $G=34$ и $m=17$ получилось бы $\gcd(t_0,G)=2$, но $\gcd(t_0,m)=1$. "
                 r"Поэтому до проверки конкретных модулей формула $a=t_1t_0^{-1}$ не обоснована. "
                 r"Перебираем делители $d\mid G$ с $d>\max x_i$ и для каждого $a\in\mathbb Z/d\mathbb Z$ "
                 r"вычисляем $c=x_1-ax_0\bmod d$, после чего проверяем все рекуррентности. Остаются тройки:"
                 r"\[\begin{array}{c|c|c|c|c}a & c & m & \gcd(t_0,m) & "
                 r"\text{проверка всех пяти переходов}\\\hline "
                 r"\BLOCK{for r in triples}\VAR{r.a} & \VAR{r.c} & \VAR{r.m} & \VAR{r.gcd_t0} & \text{выполнены}"
                 r"\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}\end{array}.\] "
                 r"Модуль $G$ отсутствует среди согласованных кандидатов, значит, равенство $m=G$ неверно. "
                 r"Теперь обратимость проверяется по каждому найденному модулю отдельно: во всех строках "
                 r"$\gcd(t_0,m)>1$, поэтому для любой согласованной с наблюдениями тройки $t_0^{-1}\bmod m$ "
                 r"не существует и стандартная формула действительно неприменима. "
                 r"Наблюдаемый префикс не определяет генератор однозначно. Нужны дополнительные выходы, "
                 r"априорные ограничения на параметры или другое независимое условие; каждый новый переход "
                 r"позволяет отбросить часть кандидатов. "
                 r"\[\boxed{\text{количество согласованных троек: }\VAR{triples|length}}.\]")

    def sample(self, rng):
        for _ in range(10000):
            m = rng.choice(self.cfg.moduli)
            a, c, x0 = rng.randrange(m), rng.randrange(m), rng.randrange(m)
            xs = [x0]
            for _ in range(5):
                xs.append((a * xs[-1] + c) % m)
            ts = [xs[i + 1] - xs[i] for i in range(5)]
            us = [ts[i + 2] * ts[i] - ts[i + 1]**2 for i in range(3)]
            G = gcd(*us)
            if not (m < G <= 200 and gcd(ts[0], m) > 1):
                continue
            triples = []
            for d in range(max(xs) + 1, G + 1):
                if G % d:
                    continue
                for aa in range(d):
                    cc = (xs[1] - aa * xs[0]) % d
                    if all(xs[i + 1] == (aa * xs[i] + cc) % d for i in range(5)):
                        triples.append({"a": aa, "c": cc, "m": d, "gcd_t0": gcd(ts[0], d)})
            if len(triples) >= 2 and all(r["gcd_t0"] > 1 and r["m"] < G for r in triples):
                return {"secret": {"a": a, "c": c, "m": m}, "xs": xs,
                        "xs_tex": "(" + ", ".join(map(str, xs)) + ")",
                        "ts": ts, "ts_tex": "(" + ", ".join(map(str, ts)) + ")",
                        "us": us, "us_tex": "(" + ", ".join(map(str, us)) + ")",
                        "G": G, "gcd_G": gcd(ts[0], G), "triples": triples, "answer": triples}
        raise ValueError("failed to generate an ambiguous LCG instance")

    def check(self, p):
        xs, G = p["xs"], p["G"]
        assert p["secret"]["m"] < G <= 200 and p["gcd_G"] == gcd(p["ts"][0], G) > 1
        assert len(p["triples"]) >= 2
        for r in p["triples"]:
            assert r["m"] > max(xs) and G % r["m"] == 0 and r["m"] < G
            assert r["gcd_t0"] == gcd(p["ts"][0], r["m"]) > 1
            assert all(xs[i + 1] == (r["a"] * xs[i] + r["c"]) % r["m"] for i in range(5))
        assert any(r["a"] == p["secret"]["a"] and r["c"] == p["secret"]["c"]
                   and r["m"] == p["secret"]["m"] for r in p["triples"])


class RANDUStructure(Task):
    id = "crypto.randu_structure"
    title_ru = "Линейная структура генератора RANDU"
    topics = ("crypto.prng",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    presets = {"default": {}}
    statement = (r"Генератор RANDU задаётся рекуррентностью $x_{n+1}=65539x_n\bmod2^{31}$. "
                 r"Известны $x_0=\VAR{x0}$, $x_1=\VAR{x1}$, $x_2=\VAR{x2}$. "
                 r"Доказать тождество $x_{n+2}\equiv6x_{n+1}-9x_n\pmod{2^{31}}$ и с его помощью "
                 r"вычислить $x_3$ и $x_4$. Найти также целые $k_0,k_1,k_2$, для которых "
                 r"$x_{n+2}-6x_{n+1}+9x_n=k_n2^{31}$, и объяснить геометрическую слабость троек "
                 r"последовательных выходов.")
    solution = (r"Поскольку $a=65539=2^{16}+3$, имеем "
                 r"\[a^2=(2^{16}+3)^2=2^{32}+6\cdot2^{16}+9"
                 r"=2\cdot2^{31}+6(2^{16}+3)-9\equiv6a-9\pmod{2^{31}}.\] "
                 r"Умножение на $x_n$ даёт требуемое тождество. Следовательно, "
                 r"$x_3=6x_2-9x_1\bmod2^{31}=\VAR{x3}$ и "
                 r"$x_4=6x_3-9x_2\bmod2^{31}=\VAR{x4}$. Коэффициенты переноса: "
                 r"\[(k_0,k_1,k_2)=(\VAR{k0},\VAR{k1},\VAR{k2}),\] "
                 r"что проверяется непосредственной подстановкой. Поэтому точки $(x_n,x_{n+1},x_{n+2})$ "
                 r"лежат на плоскостях $z-6y+9x=k2^{31}$ с целым $k$: трёхмерные выходы образуют "
                 r"решётчатую структуру, а не заполняют пространство равномерно. Два последовательных "
                 r"состояния позволяют предсказывать дальнейшие выходы. "
                 r"\[\boxed{x_3=\VAR{x3},\quad x_4=\VAR{x4}}.\]")

    def sample(self, rng):
        m, a = 1 << 31, 65539
        x0 = rng.randrange(1, 100000) | 1
        xs = [x0]
        for _ in range(4):
            xs.append(a * xs[-1] % m)
        ks = [(xs[i + 2] - 6 * xs[i + 1] + 9 * xs[i]) // m for i in range(3)]
        return {"x0": xs[0], "x1": xs[1], "x2": xs[2], "x3": xs[3], "x4": xs[4],
                "k0": ks[0], "k1": ks[1], "k2": ks[2],
                "answer": {"x3": xs[3], "x4": xs[4], "k": ks}}

    def check(self, p):
        m = 1 << 31
        xs = [p[f"x{i}"] for i in range(5)]
        assert all(xs[i + 1] == 65539 * xs[i] % m for i in range(4))
        assert all(xs[i + 2] - 6 * xs[i + 1] + 9 * xs[i] == p["answer"]["k"][i] * m for i in range(3))


class BlumBlumShub(Task):
    id = "crypto.bbs"
    title_ru = 'Генератор Блюма~--~Блюма~--~Шуба'
    topics = ("crypto.prng",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"primes": [7, 11, 19, 23, 31, 43, 47]}}
    statement = (r'Игрушечный генератор Блюма~--~Блюма~--~Шуба использует $N=pq=\VAR{N}$, '
                 r"где $p=\VAR{p}$, $q=\VAR{q}$ (оба простых сравнимы с $3$ по модулю $4$), "
                 r"и правило $x_{i+1}=x_i^2\bmod N$, $x_0=\VAR{x0}$. На каждом шаге $i\geq1$ "
                 r"выдаётся младший бит $x_i$. Вычислить состояния $x_1,\ldots,x_{\VAR{steps}}$, "
                 r"выходную битовую строку и следующее состояние $x_{\VAR{steps}+1}$. "
                 r"Объяснить роль знания разложения $N$ и почему этот малый пример не является безопасным генератором.")
    solution = (r"Последовательно возводим предыдущее состояние в квадрат по модулю $\VAR{N}$:"
                 r"\[\begin{array}{c|c|c|c|c}i & x_{i-1} & x_{i-1}^2 & x_i & \text{выходной бит}\\\hline "
                 r"\BLOCK{for r in rows}\VAR{r.i} & \VAR{r.prev} & \VAR{r.square} & \VAR{r.value} & "
                 r"\BLOCK{if r.i <= steps}\VAR{r.bit}\BLOCK{else}---\BLOCK{endif}"
                 r"\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}\end{array}.\] "
                 r"Выход: $\VAR{bits_tex}$; следующее состояние $x_{\VAR{steps}+1}=\VAR{next}$. "
                 r"Знание $p,q$ позволяет вычислять по отдельным модулям и исследовать периоды через "
                 r"порядки элементов. Для настоящего BBS выбирают большой модуль, секретное квадратичное "
                 r"начальное состояние и обосновывают непредсказуемость через теоретико-числовые предположения. "
                 r"Здесь $N$ и факторы даны и мгновенно перебираются, поэтому пример демонстрирует только алгебру. "
                 r"\[\boxed{b_1\ldots b_{\VAR{steps}}=\VAR{bits_str},\quad x_{\VAR{steps}+1}=\VAR{next}}.\]")

    def sample(self, rng):
        p, q = rng.sample(self.cfg.primes, 2)
        N = p * q
        r = rng.randrange(2, N)
        while gcd(r, N) != 1:
            r = rng.randrange(2, N)
        x0 = r * r % N
        steps = 8
        rows, states, bits = [], [], []
        prev = x0
        for i in range(1, steps + 2):
            square = prev * prev
            value = square % N
            bit = value & 1
            rows.append({"i": i, "prev": prev, "square": square, "value": value, "bit": bit})
            if i <= steps:
                states.append(value)
                bits.append(bit)
            prev = value
        return {"p": p, "q": q, "N": N, "x0": x0, "steps": steps, "rows": rows,
                "states": states, "bits": bits, "bits_tex": "(" + ", ".join(map(str, bits)) + ")",
                "bits_str": "".join(map(str, bits)), "next": prev,
                "answer": {"states": states, "bits": bits, "next": prev}}

    def check(self, p):
        assert p["N"] == p["p"] * p["q"] and p["p"] % 4 == p["q"] % 4 == 3
        x = p["x0"]
        for i, state in enumerate(p["states"], start=1):
            x = x * x % p["N"]
            assert x == state and p["bits"][i - 1] == (x & 1)
        assert p["next"] == x * x % p["N"]
