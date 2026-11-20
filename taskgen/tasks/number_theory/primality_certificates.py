"""Pocklington, Pratt, and Proth primality certificates (lecture sem1/08, advanced)."""

from math import gcd, isqrt

from taskgen.core import steps
from taskgen.core.nt import factorize, first_primes, is_order, is_prime
from taskgen.core.task import SolutionDetail, Task
from taskgen.tasks.number_theory.primitive_root import root_search

TX = r"\BLOCK{import 'macros.tex.j2' as tx}"


def _pocklington_options(n: int) -> list[int]:
    out = []
    for F in range(2, n - 1):
        if (n - 1) % F == 0 and F * F > n and 1 <= len(factorize(F)) <= 3:
            out.append(F)
    return out


class PocklingtonCertificate(Task):
    id = "number_theory.pocklington"
    title_ru = "Сертификат простоты Поклингтона"
    topics = ("number_theory.primality",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Partial factorization n-1=FR with F>sqrt(n), R>1. Preset `invalid` replaces one base by 1, "
             "so the certificate fails although the underlying n remains prime.")
    presets = {"default": {"primes": list(first_primes(90)[12:]), "invalid_ratio": 0.2},
               "invalid": {"invalid_ratio": 1.0}}
    statement = (r"Для числа $n=\VAR{n}$ предъявлена часть разложения $n-1=FR$, где $F=\VAR{F}$, "
                 r"$R=\VAR{R}$, $F>\sqrt n$, и основания из таблицы"
                 r"\[\begin{array}{r|r|r}q^e\parallel F & q & a_q \\ \hline "
                 r"\BLOCK{for row in rows}\VAR{row.qe} & \VAR{row.q} & \VAR{row.a} \\ "
                 r"\BLOCK{endfor}\end{array}\] Проверить сертификат Поклингтона: для каждого $q$ вычислить "
                 r"$a_q^{n-1}\bmod n$ и $\gcd(a_q^{(n-1)/q}-1,n)$. Если сертификат корректен, доказать "
                 r"простоту $n$; если нет, указать нарушенные условия.")
    solution = (r"Теорема Поклингтона: если $n-1=FR$, $F>\sqrt n$, и для каждого простого $q\mid F$ найдётся "
                r"$a_q$ с $a_q^{n-1}\equiv1\pmod n$ и $\gcd(a_q^{(n-1)/q}-1,n)=1$, то $n$ простое."
                r"\par Проверка данных: $FR=\VAR{F}\cdot\VAR{R}=\VAR{n - 1}$ и "
                r"$F^2=\VAR{F * F}>\VAR{n}$."
                r"\[\begin{array}{r|r|r|r|r|r}q & a_q & a_q^{n-1}\bmod n & (n-1)/q & "
                r"a_q^{(n-1)/q}\bmod n & \gcd(\cdot-1,n) \\ \hline "
                r"\BLOCK{for row in rows}\VAR{row.q} & \VAR{row.a} & \VAR{row.full} & \VAR{row.exp} & "
                r"\VAR{row.h} & \VAR{row.g} \\ \BLOCK{endfor}\end{array}\]"
                r"\BLOCK{if valid} Все условия выполнены. Докажем критерий. Пусть $p_0$ --- любой простой "
                r"делитель $n$. Для каждого $q\mid F$ порядок $a_q$ по модулю $p_0$ делит $n-1$, но не "
                r"делит $(n-1)/q$; значит, полная степень $q$, входящая в $n-1$, делит $p_0-1$. Перемножая "
                r"эти степени по всем $q\mid F$, получаем $F\mid p_0-1$, откуда $p_0>F>\sqrt n$. Любой "
                r"простой делитель $n$ больше $\sqrt n$, поэтому нетривиального разложения быть не может."
                r"\[\boxed{n=\VAR{n}\ \text{--- простое}}.\]"
                r"\BLOCK{else} По крайней мере одно из обязательных условий нарушено: в таблице есть "
                r"НОД, отличный от $1$, либо неверное первое сравнение. Такой набор не является сертификатом "
                r"Поклингтона и ничего не доказывает о простоте $n$; это не означает автоматически, что $n$ "
                r"составное.\[\text{сертификат неверен}.\]\BLOCK{endif}")
    def sample(self, rng):
        cfg = self.cfg
        candidates = [(n, F) for n in cfg.primes for F in _pocklington_options(n)]
        n, F = rng.choice(candidates)
        R = (n - 1) // F
        base = root_search(n)["g"]
        rows = []
        for q, e in sorted(factorize(F).items()):
            k = rng.choice([k for k in range(1, n - 1) if gcd(k, n - 1) == 1])
            a = pow(base, k, n)
            h = pow(a, (n - 1) // q, n)
            rows.append({"q": q, "e": e, "qe": q**e, "a": a, "full": pow(a, n - 1, n),
                         "exp": (n - 1) // q, "h": h, "g": gcd(h - 1, n)})
        invalid = rng.random() < cfg.invalid_ratio
        if invalid:
            row = rng.choice(rows)
            a = 1
            h = 1
            row.update({"a": a, "full": 1, "h": h, "g": gcd(h - 1, n)})
        valid = all(row["full"] == 1 and row["g"] == 1 for row in rows)
        return {"n": n, "F": F, "R": R, "rows": rows, "valid": valid,
                "answer": "простое" if valid else "сертификат неверен"}

    def check(self, p):
        n, F, R = p["n"], p["F"], p["R"]
        assert is_prime(n) and F * R == n - 1 and F * F > n and R > 1
        valid = True
        for row in p["rows"]:
            a, q = row["a"], row["q"]
            assert row["full"] == pow(a, n - 1, n)
            assert row["h"] == pow(a, (n - 1) // q, n)
            assert row["g"] == gcd(row["h"] - 1, n)
            valid &= row["full"] == 1 and row["g"] == 1
        assert p["valid"] == valid
        assert p["answer"] == ("простое" if valid else "сертификат неверен")


def _pratt_nodes(p: int, nodes: list[dict]) -> None:
    for q in sorted(factorize(p - 1)):
        if q > 2:
            _pratt_nodes(q, nodes)
    g = root_search(p)["g"]
    checks = [{"q": q, "exp": (p - 1) // q, "value": pow(g, (p - 1) // q, p)}
              for q in sorted(factorize(p - 1))]
    nodes.append({"p": p, "g": g, "factor": steps.factor_tex(p - 1), "full": pow(g, p - 1, p),
                  "checks": checks, "valid": all(c["value"] != 1 for c in checks)})


class PrattCertificate(Task):
    id = "number_theory.pratt_certificate"
    title_ru = "Рекурсивный сертификат простоты Пратта"
    topics = ("number_theory.primality",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "Certificate nodes are postordered; preset `invalid` replaces the root's primitive root by 1."
    presets = {"default": {"primes": [59, 83, 107, 109, 131, 157, 179, 193, 227, 229, 241, 257,
                                              277, 311, 313, 337, 421, 433, 457, 521, 541],
                           "invalid_ratio": 0.2},
               "invalid": {"invalid_ratio": 1.0}}
    statement = (r"Проверить рекурсивный сертификат Пратта для $N=\VAR{n}$. Строки таблицы расположены так, "
                 r"что простые делители $p-1$ встречаются раньше самого $p$; число $2$ --- базовый случай. "
                 r"Для каждой строки даны $p$, $g$ и полное разложение $p-1$:"
                 r"\[\begin{array}{r|r|l}p & g & p-1 \\ \hline "
                 r"\BLOCK{for row in nodes}\VAR{row.p} & \VAR{row.g} & \VAR{row.factor} \\ "
                 r"\BLOCK{endfor}\end{array}\] Для каждой строки проверить $g^{p-1}\equiv1\pmod p$ и "
                 r"$g^{(p-1)/q}\not\equiv1\pmod p$ для всех простых $q\mid p-1$. Можно ли на этом основании "
                 r"заключить, что $N$ простое?")
    solution = (r"В строке с простым $p$ перечисленные проверки доказывают, что порядок $g$ равен $p-1$: "
                r"если бы порядок был меньше, он делил бы $(p-1)/q$ для некоторого простого $q\mid p-1$. "
                r"Таким образом $g$ --- первообразный корень. Но по модулю составного $p$ порядок любого "
                r"элемента не превосходит $\varphi(p)<p-1$, поэтому $p$ обязано быть простым. "
                r"Рекурсия замыкается на базовом простом $2$."
                r"\[\begin{array}{r|r|r|l|c}p & g & g^{p-1}\bmod p & "
                r"g^{(p-1)/q}\bmod p\ \text{для }q\mid p-1 & \text{верно?} \\ \hline "
                r"\BLOCK{for row in nodes}\VAR{row.p} & \VAR{row.g} & \VAR{row.full} & "
                r"\BLOCK{for c in row.checks}\VAR{c.q}:\,\VAR{c.value}\BLOCK{if not loop.last};\ \BLOCK{endif}"
                r"\BLOCK{endfor} & \BLOCK{if row.valid}\text{да}\BLOCK{else}\text{нет}\BLOCK{endif} \\ "
                r"\BLOCK{endfor}\end{array}\]"
                r"\BLOCK{if valid} Все листья и затем корень сертификата проверены. Следовательно,"
                r"\[\boxed{N=\VAR{n}\ \text{--- простое}}.\] Сертификат компактно связывает тест простоты с "
                r"поиском первообразных корней; в отличие от сертификата Поклингтона здесь требуется полное "
                r"рекурсивное разложение всех чисел $p-1$."
                r"\BLOCK{else} Не все строки проходят проверку. Поэтому рекурсивная цепочка доказательства "
                r"разорвана и предъявленный набор не является сертификатом простоты $N$ (само $N$ при этом "
                r"может быть простым, но данный сертификат этого не устанавливает).\BLOCK{endif}")
    def sample(self, rng):
        n = rng.choice(self.cfg.primes)
        nodes = []
        _pratt_nodes(n, nodes)
        invalid = rng.random() < self.cfg.invalid_ratio
        if invalid:
            row = nodes[-1]
            g = 1
            checks = [{"q": q, "exp": (n - 1) // q, "value": 1} for q in sorted(factorize(n - 1))]
            row.update({"g": g, "full": 1, "checks": checks, "valid": False})
        valid = all(row["valid"] for row in nodes)
        return {"n": n, "nodes": nodes, "valid": valid, "answer": valid}

    def check(self, p):
        assert p["nodes"][-1]["p"] == p["n"] and is_prime(p["n"])
        seen = {2}
        valid = True
        for row in p["nodes"]:
            n, g = row["p"], row["g"]
            assert is_prime(n) and all(c["q"] in seen for c in row["checks"])
            assert row["full"] == pow(g, n - 1, n)
            row_valid = row["full"] == 1
            for c in row["checks"]:
                assert c["value"] == pow(g, (n - 1) // c["q"], n)
                row_valid &= c["value"] != 1
            assert row["valid"] == row_valid
            valid &= row_valid
            seen.add(n)
        assert p["valid"] == p["answer"] == valid


def _proth_primes() -> list[dict]:
    out = []
    for m in range(3, 10):
        for k in range(1, 2**m, 2):
            n = k * 2**m + 1
            if k < 2**m and is_prime(n):
                out.append({"n": n, "k": k, "m": m})
    return out


class ProthCertificate(Task):
    id = "number_theory.proth_certificate"
    title_ru = "Теорема Прота и простые числа специального вида"
    topics = ("number_theory.primality",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "Search in increasing a among Jacobi nonresidues; preset `bad_base` supplies a=1."
    presets = {"default": {"bad_ratio": 0.15}, "bad_base": {"bad_ratio": 1.0}}
    statement = (r"Число $n=\VAR{n}=\VAR{k}\cdot2^{\VAR{m}}+1$ имеет вид Прота, причём "
                 r"$\VAR{k}<2^{\VAR{m}}$ и $\VAR{k}$ нечётно."
                 r"\BLOCK{if bad_base} Проверить, даёт ли основание $a=1$ сертификат простоты по теореме "
                 r"Прота. \BLOCK{else} Начиная с $a=2$, подобрать основание $a$ с "
                 r"$\left(\frac an\right)=-1$ и проверить критерий Прота "
                 r"$a^{(n-1)/2}\equiv-1\pmod n$. \BLOCK{endif}Если критерий выполнен, обосновать простоту $n$; "
                 r"иначе объяснить, почему вывод сделать нельзя.")
    solution = (TX + r"Теорема Прота: если $n=k2^m+1$, $k<2^m$, $k$ нечётно, и для некоторого целого $a$ "
                r"выполнено $a^{(n-1)/2}\equiv-1\pmod n$, то $n$ простое. Здесь $(n-1)/2=\VAR{exp}$."
                r"\BLOCK{if not bad_base} Для простого нечётного $n$ подходящее $a$ обязано быть "
                r"квадратичным невычетом, поэтому сначала вычисляем символ Якоби; кандидатов с символом $+1$ "
                r"пропускаем.\BLOCK{endif}"
                r"\[\begin{array}{r|r|r|c}a & \left(\frac an\right) & a^{(n-1)/2}\bmod n & "
                r"\text{сертификат?} \\ \hline \BLOCK{for row in rows}\VAR{row.a} & \VAR{row.jacobi} & "
                r"\BLOCK{if row.value is none}\text{---}\BLOCK{else}\VAR{row.value}\BLOCK{endif} & "
                r"\BLOCK{if row.accepted}\text{да}\BLOCK{else}\text{нет}\BLOCK{endif} \\ "
                r"\BLOCK{endfor}\end{array}\]"
                r"\BLOCK{if valid} Для $a=\VAR{a}$ имеем $\VAR{tx.jacobi(j)}$, а главное "
                r"$\VAR{a}^{\VAR{exp}}\equiv\VAR{n - 1}\equiv-1\pmod{\VAR{n}}$. Все условия теоремы Прота "
                r"выполнены.\[\boxed{n=\VAR{n}\ \text{--- простое}}.\]"
                r"\BLOCK{else} Для $a=1$ получаем $1^{\VAR{exp}}\equiv1\not\equiv-1\pmod n$. Следовательно, "
                r"это основание не даёт сертификат Прота. Отсюда не следует, что $n$ составное: нужно "
                r"попробовать другие основания.\BLOCK{endif}")
    def sample(self, rng):
        item = rng.choice(_proth_primes())
        n, exp = item["n"], (item["n"] - 1) // 2
        bad = rng.random() < self.cfg.bad_ratio
        rows, accepted, j = [], None, None
        candidates = [1] if bad else range(2, n)
        for a in candidates:
            jac = steps.jacobi(a, n)
            if not bad and jac != -1:
                rows.append({"a": a, "jacobi": jac, "value": None, "accepted": False})
                continue
            value = pow(a, exp, n)
            ok = value == n - 1
            rows.append({"a": a, "jacobi": jac, "value": value, "accepted": ok})
            if ok:
                accepted, j = a, steps.jacobi_chain(a, n)
            break
        valid = accepted is not None
        return {**item, "exp": exp, "rows": rows, "a": accepted, "j": j, "valid": valid,
                "bad_base": bad, "answer": "простое" if valid else "сертификат неверен"}

    def check(self, p):
        n, k, m = p["n"], p["k"], p["m"]
        assert n == k * 2**m + 1 and k % 2 == 1 and k < 2**m and is_prime(n)
        valid = False
        for row in p["rows"]:
            a = row["a"]
            assert row["jacobi"] == steps.jacobi(a, n)
            if row["value"] is not None:
                assert row["value"] == pow(a, (n - 1) // 2, n)
            assert row["accepted"] == (row["value"] == n - 1)
            valid |= row["accepted"]
        assert p["valid"] == valid
        assert p["answer"] == ("простое" if valid else "сертификат неверен")
