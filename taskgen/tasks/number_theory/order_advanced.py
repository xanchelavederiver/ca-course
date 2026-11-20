"""Orders modulo composite integers, generic order finding, and factoring from an order."""

from math import gcd, isqrt, lcm

from taskgen.core.nt import factorize, first_primes, is_order, is_prime
from taskgen.core.steps import factor_tex
from taskgen.core.task import SolutionDetail, Task


def euler_phi(n: int) -> int:
    out = n
    for q in factorize(n):
        out = out // q * (q - 1)
    return out


def lambda_part(q: int, e: int) -> int:
    return 2 ** (e - 2) if q == 2 and e >= 3 else q ** (e - 1) * (q - 1)


def carmichael(n: int) -> int:
    return lcm(*(lambda_part(q, e) for q, e in factorize(n).items()))


def order_naive(g: int, n: int) -> int:
    x, r = g % n, 1
    while x != 1 % n:
        x, r = x * g % n, r + 1
    return r


def order_reduction(g: int, exponent: int, n: int) -> tuple[int, list[dict]]:
    order, tests = exponent, []
    for q, e in sorted(factorize(exponent).items()):
        for _ in range(e):
            value = pow(g, order // q, n)
            tests.append({"q": q, "order": order, "exp": order // q, "value": value})
            if value != 1:
                break
            order //= q
    return order, tests


class CompositeOrder(Task):
    id = "number_theory.order_composite"
    title_ru = "Порядок элемента по составному модулю"
    topics = ("number_theory.order",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "Uses ord_n(g)=lcm(ord_{p^e}(g)); nonunits and cyclic/ noncyclic unit groups are included."
    presets = {"default": {"moduli": [36, 40, 45, 48, 49, 56, 60, 63, 72, 75, 80, 81, 84, 90,
                                                96, 100, 108, 120, 121, 125, 128, 144],
                           "nonunit_ratio": 0.15},
               "nonunit": {"nonunit_ratio": 1.0}}
    statement = (r"Для $n=\VAR{n}$ и $g=\VAR{g}$ вычислить $\varphi(n)$ и функцию Кармайкла "
                 r"$\lambda(n)$. Найти $\operatorname{ord}_n(g)$ или объяснить, почему он не определён. "
                 r"Использовать $\operatorname{ord}_n(g)=\operatorname{lcm}_i\operatorname{ord}_{p_i^{e_i}}(g)$ "
                 r"и последовательное снижение порядка по компонентам. Является ли $g$ первообразным корнем?")
    solution = (r"Разложение $n=\VAR{nfac}$. Для $\lambda(p^e)$ используем $\varphi(p^e)=p^{e-1}(p-1)$, "
                r"кроме $\lambda(2^e)=2^{e-2}$ при $e\ge3$; затем берём НОК:"
                r"\[\begin{array}{r|r|r|r}p^e & \lambda(p^e) & \operatorname{ord}_{p^e}(g) & "
                r"\text{снижение} \\ \hline \BLOCK{for c in parts}\VAR{c.pe} & \VAR{c.lam} & "
                r"\BLOCK{if unit}\VAR{c.order}\BLOCK{else}\text{---}\BLOCK{endif} & "
                r"\BLOCK{if unit}\BLOCK{for t in c.tests}\VAR{t.value}\BLOCK{if t.value == 1}\,(=1)"
                r"\BLOCK{else}\,(\ne1)\BLOCK{endif}\BLOCK{if not loop.last};\ \BLOCK{endif}"
                r"\BLOCK{endfor}\BLOCK{else}\text{---}\BLOCK{endif} \\ \BLOCK{endfor}\end{array}\]"
                r"В последнем столбце выписаны значения $g^{o/q}$ при последовательных кандидатах $o$; "
                r"если значение равно $1$, заменяем $o\gets o/q$."
                r"\[\varphi(n)=\VAR{phi},\qquad \lambda(n)=\VAR{lam}.\]"
                r"\BLOCK{if not unit} Здесь $\gcd(g,n)=\VAR{d}>1$, поэтому $g$ не является элементом "
                r"мультипликативной группы и мультипликативный порядок не определён."
                r"\[\operatorname{ord}_{\VAR{n}}(\VAR{g})\ \text{не определён}.\]"
                r"\BLOCK{else} По китайской теореме об остатках $g^r\equiv1\pmod n$ тогда и только тогда, "
                r"когда оно выполняется по всем примарным модулям. Поэтому"
                r"\[\operatorname{ord}_n(g)=\operatorname{lcm}(\VAR{orders|join(', ')})=\VAR{order}.\]"
                r"\BLOCK{if primitive} Так как порядок равен $\varphi(n)$, $g$ --- первообразный корень."
                r"\BLOCK{else} Это не первообразный корень: его порядок меньше $\varphi(n)=\VAR{phi}$"
                r"\BLOCK{if lam < phi}; более того, первообразных корней по модулю $n$ нет, поскольку "
                r"$\lambda(n)<\varphi(n)$\BLOCK{endif}.\BLOCK{endif}\BLOCK{endif}")
    def sample(self, rng):
        n = rng.choice(self.cfg.moduli)
        if rng.random() < self.cfg.nonunit_ratio:
            q = rng.choice(list(factorize(n)))
            while True:
                g = q * rng.randrange(2, n // q)
                if g < n and gcd(g, n) > 1:
                    break
        else:
            while True:
                g = rng.randrange(2, n)
                if gcd(g, n) == 1:
                    break
        d = gcd(g, n)
        parts, orders = [], []
        for q, e in sorted(factorize(n).items()):
            pe, lam = q**e, lambda_part(q, e)
            order, tests = order_reduction(g, lam, pe) if d == 1 else (None, [])
            parts.append({"pe": pe, "lam": lam, "order": order, "tests": tests})
            if order is not None:
                orders.append(order)
        ph, lam = euler_phi(n), carmichael(n)
        order = lcm(*orders) if orders else None
        return {"n": n, "g": g, "d": d, "unit": d == 1, "nfac": factor_tex(n), "parts": parts,
                "orders": orders, "phi": ph, "lam": lam, "order": order,
                "primitive": order == ph, "answer": {"order": order, "lambda": lam, "phi": ph}}

    def check(self, p):
        n, g = p["n"], p["g"]
        assert p["phi"] == euler_phi(n) == sum(gcd(x, n) == 1 for x in range(1, n + 1))
        assert p["lam"] == carmichael(n)
        if not p["unit"]:
            assert gcd(g, n) > 1 and p["answer"]["order"] is None
            return
        order = order_naive(g, n)
        assert p["order"] == p["answer"]["order"] == order
        assert order == lcm(*(c["order"] for c in p["parts"]))
        for c in p["parts"]:
            assert is_order(g, c["order"], c["pe"])
        assert p["primitive"] == (order == p["phi"])


class OrderBSGS(Task):
    id = "number_theory.order_bsgs"
    title_ru = "Порядок элемента без разложения p-1 методом больших и малых шагов"
    topics = ("number_theory.order",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "All giant steps and all baby-step collisions are retained, so the minimum candidate is proved."
    presets = {"default": {"primes": list(first_primes(70)[15:]), "max_order": 0},
               "small_order": {"max_order": 20}}
    statement = (r"Дано простое $p=\VAR{p}$ и элемент $g=\VAR{g}$; известно лишь, что "
                 r"$\operatorname{ord}(g)\le B=\VAR{B}$. Найти порядок методом малых и больших шагов за "
                 r"$O(\sqrt B)$ операций, не раскладывая $p-1$ на множители. Объяснить, почему найденный "
                 r"показатель --- наименьший положительный.")
    solution = (r"Пусть $m=\lceil\sqrt B\rceil=\VAR{m}$, $I=\lceil B/m\rceil=\VAR{I}$. Строим малые "
                r"шаги $g^j$, $0\le j<m$:"
                r"\[\begin{array}{c|\BLOCK{for b in baby}r\BLOCK{endfor}}j"
                r"\BLOCK{for b in baby} & \VAR{b.j}\BLOCK{endfor} \\ \hline g^j"
                r"\BLOCK{for b in baby} & \VAR{b.v}\BLOCK{endfor}\end{array}\]"
                r"Для $i=1,\dots,I$ вычисляем большие шаги $y_i=g^{im}$ и все совпадения $y_i=g^j$. "
                r"Каждое совпадение даёт кандидата $r=im-j$:"
                r"\[\begin{array}{c|r|r|r|r}i & y_i & j & im-j \\ \hline "
                r"\BLOCK{for row in giant}\VAR{row.i} & \VAR{row.y} & "
                r"\BLOCK{if row.hits}\VAR{row.hits|join(', ')}\BLOCK{else}\text{---}\BLOCK{endif} & "
                r"\BLOCK{if row.candidates}\VAR{row.candidates|join(', ')}\BLOCK{else}\text{---}"
                r"\BLOCK{endif} \\ \BLOCK{endfor}\end{array}\]"
                r"Минимальный кандидат равен $\VAR{answer}$. Если истинный порядок $r\le B$, положим "
                r"$i=\lceil r/m\rceil$ и $j=im-r$; тогда $1\le i\le I$, $0\le j<m$ и $g^{im}=g^j$, "
                r"поэтому этот $r$ обязательно встречается в таблице. Мы просмотрели все большие шаги и "
                r"все совпадения, включая случай повторов при порядке меньше $m$, поэтому меньший кандидат "
                r"пропущен быть не может. Проверка: $g^{\VAR{answer}}\equiv1\pmod p$."
                r"\[\operatorname{ord}(\VAR{g})=\VAR{answer}.\] Использовано $m+I=\VAR{ops}$ шагов, "
                r"то есть $O(\sqrt B)$; разложение $p-1$ нигде не потребовалось.")
    def sample(self, rng):
        while True:
            p = rng.choice(self.cfg.primes)
            g = rng.randrange(2, p - 1)
            order = order_naive(g, p)
            if not self.cfg.max_order or order <= self.cfg.max_order:
                break
        B = p - 1
        m = isqrt(B - 1) + 1
        baby, lookup = [], {}
        value = 1
        for j in range(m):
            baby.append({"j": j, "v": value})
            lookup.setdefault(value, []).append(j)
            value = value * g % p
        I = (B + m - 1) // m
        giant, candidates = [], []
        y = pow(g, m, p)
        for i in range(1, I + 1):
            hits = lookup.get(y, [])
            found = [i * m - j for j in hits if 1 <= i * m - j <= B]
            giant.append({"i": i, "y": y, "hits": hits, "candidates": found})
            candidates.extend(found)
            y = y * pow(g, m, p) % p
        assert candidates and min(candidates) == order
        return {"p": p, "g": g, "B": B, "m": m, "I": I, "baby": baby, "giant": giant,
                "ops": m + I, "answer": order}

    def check(self, p):
        P, g, B = p["p"], p["g"], p["B"]
        assert is_prime(P) and p["answer"] == order_naive(g, P) <= B
        assert [b["v"] for b in p["baby"]] == [pow(g, b["j"], P) for b in p["baby"]]
        candidates = []
        for row in p["giant"]:
            assert row["y"] == pow(g, row["i"] * p["m"], P)
            for j in row["hits"]:
                r = row["i"] * p["m"] - j
                assert pow(g, r, P) == 1
                assert (r in row["candidates"]) == (1 <= r <= B)
            candidates.extend(row["candidates"])
        assert min(candidates) == p["answer"]


class RSAFactorFromOrder(Task):
    id = "number_theory.order_factor_rsa"
    title_ru = "Разложение модуля RSA по известному порядку элемента"
    topics = ("number_theory.order", "crypto.rsa")
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "Success, odd-order failure, and a^{r/2}=-1 failure; presets force each branch."
    presets = {"default": {"primes": list(first_primes(25)[1:]), "mode": "mixed"},
               "success": {"mode": "success"}, "odd": {"mode": "odd"}, "minus": {"mode": "minus"}}
    statement = (r"Число $N=\VAR{n}$ --- произведение двух различных нечётных простых, $\gcd(a,N)=1$ "
                 r"для $a=\VAR{a}$, и утверждается, что $\operatorname{ord}_N(a)=r=\VAR{r}$. Проверить "
                 r"порядок по разложению $r$ на простые множители. Если $r$ чётен и "
                 r"$a^{r/2}\not\equiv\pm1\pmod N$, разложить $N$ с помощью $\gcd(a^{r/2}\pm1,N)$. "
                 r"Если метод неприменим, объяснить причину.")
    solution = (r"Разложение $r=\VAR{rfac}$. Условие $a^r\equiv1$ даёт "
                r"$\VAR{a}^{\VAR{r}}\bmod\VAR{n}=\VAR{ar}$. Для доказательства точности порядка проверяем "
                r"$a^{r/q}\not\equiv1$ для каждого простого $q\mid r$:"
                r"\[\begin{array}{r|r|r}q & r/q & a^{r/q}\bmod N \\ \hline "
                r"\BLOCK{for t in tests}\VAR{t.q} & \VAR{t.exp} & \VAR{t.value} \\ \BLOCK{endfor}"
                r"\end{array}\] Значит, порядок действительно равен $r=\VAR{r}$."
                r"\BLOCK{if kind == 'odd'} Порядок нечётен, поэтому показатель $r/2$ не является целым и "
                r"метод нетривиального квадратного корня из $1$ неприменим. Нужно выбрать другое основание."
                r"\BLOCK{else} Вычисляем $x=a^{r/2}\bmod N=\VAR{x}$."
                r"\BLOCK{if kind == 'minus'} Здесь $x\equiv-1\pmod N$, то есть корень тривиален: "
                r"$\gcd(x-1,N)$ или $\gcd(x+1,N)$ дают лишь тривиальные делители. Это неудачное основание; "
                r"нужно попробовать другое."
                r"\BLOCK{else} Имеем $x^2=a^r\equiv1\pmod N$, но $x\not\equiv\pm1\pmod N$. Следовательно, "
                r"$N\mid(x-1)(x+1)$, причём $N$ не делит ни один из сомножителей:"
                r"\[\begin{gathered}\gcd(x-1,N)=\gcd(\VAR{x - 1},\VAR{n})=\VAR{g1},\\ "
                r"\gcd(x+1,N)=\gcd(\VAR{x + 1},\VAR{n})=\VAR{g2}.\end{gathered}\]"
                r"Отсюда $N=\VAR{factor}\cdot\VAR{cofactor}$."
                r"\[\VAR{n}=\VAR{factor}\cdot\VAR{cofactor}.\]\BLOCK{endif}\BLOCK{endif}"
                r"\par Именно это классическое сведение факторизации к нахождению порядка используется в "
                r"алгоритме Шора; само нахождение большого порядка классически остаётся трудной частью.")
    def sample(self, rng):
        cfg = self.cfg
        wanted = cfg.mode
        while True:
            mode = rng.choice(["success", "success", "success", "odd", "minus"]) if wanted == "mixed" else wanted
            p, q = rng.sample(cfg.primes, 2)
            n = p * q
            a = rng.randrange(2, n)
            if gcd(a, n) != 1:
                continue
            r = lcm(order_naive(a, p), order_naive(a, q))
            kind = "odd" if r % 2 else ("minus" if pow(a, r // 2, n) == n - 1 else "success")
            if kind != mode:
                continue
            x = pow(a, r // 2, n) if r % 2 == 0 else None
            if kind == "success":
                g1 = gcd(x - 1, n)
                if not 1 < g1 < n:
                    continue
            else:
                g1 = None
            break
        tests = [{"q": q, "exp": r // q, "value": pow(a, r // q, n)} for q in factorize(r)]
        factor = g1 if kind == "success" else None
        return {"n": n, "a": a, "r": r, "p": p, "q": q, "kind": kind, "rfac": factor_tex(r),
                "ar": pow(a, r, n), "tests": tests, "x": x, "g1": g1,
                "g2": n // g1 if g1 else None, "factor": factor,
                "cofactor": n // g1 if g1 else None,
                "answer": {"kind": kind, "factor": factor, "cofactor": n // g1 if g1 else None}}

    def check(self, p):
        n, a, r = p["n"], p["a"], p["r"]
        assert p["p"] * p["q"] == n and gcd(a, n) == 1
        assert order_naive(a, n) == r
        assert pow(a, r, n) == 1 and all(t["value"] != 1 for t in p["tests"])
        kind = p["kind"]
        if kind == "odd":
            assert r % 2 == 1 and p["answer"]["factor"] is None
        elif kind == "minus":
            assert r % 2 == 0 and p["x"] == n - 1 and p["answer"]["factor"] is None
        else:
            assert r % 2 == 0 and p["x"] not in (1, n - 1)
            assert p["x"] * p["x"] % n == 1
            assert 1 < p["factor"] < n and p["factor"] * p["cofactor"] == n
