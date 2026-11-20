"""Special-modulus arithmetic, IDEA encoding, Lucas--Lehmer and residue-ring structure."""

from math import gcd

from taskgen.core.nt import factorize, is_prime
from taskgen.core.task import SolutionDetail, Task


def product_tex(factors: dict[int, int]) -> str:
    return r" \cdot ".join(str(q) if e == 1 else rf"{q}^{{{e}}}" for q, e in sorted(factors.items()))


class SpecialReduction(Task):
    id = "modular.special_reduction"
    title_ru = "Приведение по модулю $2^q\\pm1$ без деления"
    topics = ("arithmetic.modular",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"kind": "random", "q_lo": 5, "q_hi": 8, "force_full": False},
               "mersenne_full": {"kind": "mersenne", "q_lo": 5, "q_hi": 5, "force_full": True}}
    statement = (r"\BLOCK{if mersenne}Привести $x=\VAR{x}$ по модулю числа Мерсенна $M=2^{\VAR{q}}-1=\VAR{m}$, "
                 r"используя только разбиение на $\VAR{q}$-битовые части, сложение и циклический перенос. "
                 r"Показать все промежуточные приведения и отдельно рассмотреть представление $M\equiv0$."
                 r"\BLOCK{else}Привести $x=\VAR{x}$ по модулю $m=2^{\VAR{q}}+1=\VAR{m}$ без деления на $m$. "
                 r"Разбить $x$ на $\VAR{q}$-битовые части, использовать $2^{\VAR{q}}\equiv-1\pmod m$ "
                 r"и получить канонический вычет $0\leq r<m$.\BLOCK{endif}")
    solution = (r"\BLOCK{if mersenne}Из $2^{\VAR{q}}\equiv1\pmod M$ следует "
                 r"$H2^{\VAR{q}}+L\equiv H+L\pmod M$:"
                 r"\[\begin{array}{c|c|c|c|c}x & H & L & H+L & \text{действие}\\\hline "
                 r"\BLOCK{for r in folds}\VAR{r.x} & \VAR{r.h} & \VAR{r.l} & \VAR{r.s} & "
                 r"\BLOCK{if r.s > m}повторить\BLOCK{elif r.s == m}заменить на $0$\BLOCK{else}готово\BLOCK{endif}"
                 r"\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}\end{array}.\] "
                 r"\BLOCK{if full}Последнее значение равно $M=\VAR{m}$, но это неканоническое представление нуля. "
                 r"\BLOCK{endif}\[\boxed{x\equiv\VAR{answer}\pmod{\VAR{m}}}.\] "
                 r"Умножение на $2^j$ в этом кольце соответствует циклическому сдвигу $\VAR{q}$-битового слова."
                 r"\BLOCK{else}Запишем $x=L_0+L_12^{\VAR{q}}+L_22^{2\VAR{q}}+L_32^{3\VAR{q}}$, "
                 r"где $(L_0,L_1,L_2,L_3)=\VAR{limbs_tex}$. Тогда "
                 r"\[x\equiv L_0-L_1+L_2-L_3=\VAR{alt}\pmod{\VAR{m}}.\] "
                 r"Нормализация только добавлением или вычитанием модуля: "
                 r"\BLOCK{for r in normalization}$\VAR{r.before}\VAR{r.op}\VAR{m}=\VAR{r.after}$; "
                 r"\BLOCK{endfor}после этого $0\leq r<\VAR{m}$. "
                 r"\[\boxed{x\equiv\VAR{answer}\pmod{\VAR{m}}}.\]\BLOCK{endif}")

    def sample(self, rng):
        kind = self.cfg.kind if self.cfg.kind != "random" else rng.choice(["mersenne", "fermat"])
        q = rng.randint(self.cfg.q_lo, self.cfg.q_hi)
        mersenne = kind == "mersenne"
        m = (1 << q) - 1 if mersenne else (1 << q) + 1
        if self.cfg.force_full:
            x = (1 << (2 * q)) - 1
        else:
            x = rng.randrange(1 << (3 * q), 1 << (4 * q))
        data = {"x": x, "q": q, "m": m, "mersenne": mersenne}
        if mersenne:
            y, folds = x, []
            while y > m:
                h, l = y >> q, y & ((1 << q) - 1)
                s = h + l
                folds.append({"x": y, "h": h, "l": l, "s": s})
                y = s
            full = y == m
            answer = 0 if full else y
            data.update({"folds": folds, "full": full, "answer": answer})
        else:
            limbs = [(x >> (q * i)) & ((1 << q) - 1) for i in range(4)]
            alt = sum((-1)**i * v for i, v in enumerate(limbs))
            y, normalization = alt, []
            while y < 0 or y >= m:
                before = y
                op = "+" if y < 0 else "-"
                y = y + m if y < 0 else y - m
                normalization.append({"before": before, "after": y, "op": op})
            data.update({"limbs": limbs, "limbs_tex": "(" + ", ".join(map(str, limbs)) + ")",
                         "alt": alt, "normalization": normalization, "answer": y})
        return data

    def check(self, p):
        assert p["answer"] == p["x"] % p["m"]
        assert 0 <= p["answer"] < p["m"]
        if p["mersenne"]:
            assert p["m"] == (1 << p["q"]) - 1
            if p["full"]:
                assert p["answer"] == 0
        else:
            assert p["m"] == (1 << p["q"]) + 1
            assert p["alt"] % p["m"] == p["answer"]


def idea_decode(word: int) -> int:
    return 1 << 16 if word == 0 else word


def idea_encode(residue: int) -> int:
    return 0 if residue == 1 << 16 else residue


class IDEAMultiplication(Task):
    id = "modular.idea_mul"
    title_ru = "Умножение IDEA по модулю $2^{16}+1$"
    topics = ("arithmetic.modular",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "IDEA's 16-bit words: zero encodes 65536, all other words encode themselves."
    presets = {"default": {"zero_ratio": 0.25}}
    statement = (r"В шифре IDEA умножение выполняется по модулю $65537=2^{16}+1$, причём 16-битовые слова "
                 r"и \emph{ненулевые} вычеты связаны взаимно однозначным отображением "
                 r"\[D(w)=\begin{cases}w,&1\leq w\leq65535,\\65536,&w=0.\end{cases}\] "
                 r"Таким образом, разные слова никогда не обозначают один и тот же вычет. Нулевой вычет "
                 r"в этой операции не используется: произведение двух ненулевых вычетов по простому модулю "
                 r"не может быть нулевым. Умножить слова $a=\VAR{a}$ и $b=\VAR{b}$. Выполнить декодирование "
                 r"$A=D(a)$, $B=D(b)$, приведение произведения без деления на $65537$ и указать 16-битовое "
                 r"слово $D^{-1}(r)$, представляющее полученный ненулевой вычет $r$.")
    solution = (r"Декодирование даёт $A=\VAR{A}$ и $B=\VAR{B}$. Их произведение "
                 r"\[C=AB=\VAR{C}=\VAR{H}\cdot2^{16}+\VAR{L}.\] "
                 r"Поскольку $2^{16}\equiv-1\pmod{65537}$, получаем "
                 r"$C\equiv L-H=\VAR{L}-\VAR{H}=\VAR{raw}\pmod{65537}$. "
                 r"\BLOCK{if raw < 0}Добавляем модуль: $\VAR{raw}+65537=\VAR{residue}$. "
                 r"\BLOCK{elif raw >= 65537}Вычитаем модуль и получаем $\VAR{residue}$. "
                 r"\BLOCK{else}Дополнительной нормализации не требуется, поэтому вычет равен $\VAR{residue}$.\BLOCK{endif} "
                 r"\BLOCK{if answer == 0}Вычет $65536$ кодируется нулевым словом.\BLOCK{else}"
                 r"Вычет отличен от $65536$, поэтому его 16-битовый код совпадает с числом $\VAR{residue}$.\BLOCK{endif} "
                 r"\[\boxed{a\otimes b=\VAR{answer}}.\] Нулевое входное слово здесь не является нулём кольца: "
                 r"оно обозначает $65536\equiv-1\pmod{65537}$.")

    def sample(self, rng):
        def word():
            return 0 if rng.random() < self.cfg.zero_ratio else rng.randrange(1, 1 << 16)
        a, b = word(), word()
        A, B = idea_decode(a), idea_decode(b)
        C = A * B
        H, L = C >> 16, C & 0xffff
        raw = L - H
        residue = raw % 65537
        answer = idea_encode(residue)
        return {"a": a, "b": b, "A": A, "B": B, "C": C, "H": H, "L": L,
                "raw": raw, "residue": residue, "answer": answer}

    def check(self, p):
        assert p["residue"] == idea_decode(p["a"]) * idea_decode(p["b"]) % 65537
        assert p["answer"] == idea_encode(p["residue"])
        assert 0 <= p["answer"] < 1 << 16


class LucasLehmer(Task):
    id = "modular.lucas_lehmer"
    title_ru = "Тест Люка~--~Лемера с быстрым приведением"
    topics = ("arithmetic.modular", "number_theory.primality")
    complexity = 2
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"exponents": [5, 7, 11, 13]}}
    statement = (r"Проверить простоту числа Мерсенна $M_{\VAR{p}}=2^{\VAR{p}}-1=\VAR{m}$ "
                 r'тестом Люка~--~Лемера: $s_0=4$, $s_{i+1}=s_i^2-2\bmod M_{\VAR{p}}$; '
                 r"число простое тогда и только тогда, когда $s_{\VAR{p}-2}=0$. "
                 r"Все приведения выполнить по правилу $H2^{\VAR{p}}+L\equiv H+L$, без деления на $M_{\VAR{p}}$. "
                 r"Если число составное, дополнительно разложить его на множители.")
    solution = (r"На каждом шаге вычисляем $u=s_i^2-2$, затем заменяем $u=H2^{\VAR{p}}+L$ на $H+L$ "
                 r"(при необходимости повторяя и заменяя $M_{\VAR{p}}$ на ноль):"
                 r"\[\begin{array}{c|c|c|c|c|c}i & s_{i-1} & u=s_{i-1}^2-2 & H & L & s_i\\\hline "
                 r"\BLOCK{for r in rows}\VAR{r.i} & \VAR{r.prev} & \VAR{r.u} & \VAR{r.h} & \VAR{r.l} & \VAR{r.value}"
                 r"\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}\end{array}.\] "
                 r"Здесь показаны последнее разбиение на каждом шаге; промежуточные циклические переносы "
                 r"выполняются тем же правилом. Получено $s_{\VAR{p}-2}=\VAR{last}$. "
                 r"\BLOCK{if answer}Оно равно нулю, следовательно, $M_{\VAR{p}}=\VAR{m}$ --- простое."
                 r"\BLOCK{else}Оно отлично от нуля, следовательно, $M_{\VAR{p}}$ --- составное. "
                 r"Проверка: $\VAR{m}=\VAR{factor_tex}$.\BLOCK{endif} "
                 r"\[\boxed{M_{\VAR{p}}\text{ \BLOCK{if answer}простое\BLOCK{else}составное\BLOCK{endif}}}.\]")

    def sample(self, rng):
        p = rng.choice(self.cfg.exponents)
        m = (1 << p) - 1
        s, rows = 4, []
        for i in range(1, p - 1):
            prev = s
            u = s * s - 2
            y = u
            h, l = u >> p, u & m
            while y > m:
                h, l = y >> p, y & m
                y = h + l
            if y == m:
                y = 0
            s = y
            rows.append({"i": i, "prev": prev, "u": u, "h": h, "l": l, "value": s})
        prime = s == 0
        return {"p": p, "m": m, "rows": rows, "last": s,
                "factor_tex": product_tex(factorize(m)), "answer": prime}

    def check(self, p):
        assert p["m"] == (1 << p["p"]) - 1
        assert p["answer"] == is_prime(p["m"])
        s = 4
        for _ in range(p["p"] - 2):
            s = (s * s - 2) % p["m"]
        assert s == p["last"]


class ResidueRingUnits(Task):
    id = "modular.residue_ring_units"
    title_ru = "Единицы и делители нуля в кольцах Ферма и Мерсенна"
    topics = ("arithmetic.modular", "arithmetic.ntt")
    complexity = 2
    solution_detail = SolutionDetail.FULL
    presets = {"default": {}}
    statement = (r"Рассматривается кольцо $\mathbb Z/\VAR{m}\mathbb Z$, где $\VAR{name}=\VAR{m}=\VAR{q}\cdot\VAR{r}$. "
                 r"а)~Является ли это кольцо полем? Привести пару ненулевых делителей нуля. "
                 r"б)~Определить, является ли элемент $a=\VAR{a}$ обратимым. Если да, найти $a^{-1}\bmod\VAR{m}$; "
                 r"если нет, указать ненулевой элемент $b$, для которого $ab=0$ в кольце. "
                 r"в)~Почему нельзя автоматически переносить в это кольцо рассуждения о корнях из единицы "
                 r"в конечном поле?")
    solution = (r"Так как $\VAR{m}=\VAR{q}\cdot\VAR{r}$ и оба множителя больше единицы, кольцо не является "
                 r"полем: $\VAR{q}\ne0$, $\VAR{r}\ne0$, но $\VAR{q}\cdot\VAR{r}\equiv0\pmod{\VAR{m}}$. "
                 r"Элемент обратим тогда и только тогда, когда он взаимно прост с модулем. Здесь "
                 r"$\gcd(\VAR{a},\VAR{m})=\VAR{g}$. "
                 r"\BLOCK{if unit}Значит, $a$ --- единица кольца. Расширенный алгоритм Евклида даёт "
                 r"$a^{-1}\equiv\VAR{inverse}\pmod{\VAR{m}}$; проверка: "
                 r"$\VAR{a}\cdot\VAR{inverse}=\VAR{product}=\VAR{quotient}\cdot\VAR{m}+1$. "
                 r"\BLOCK{else}Значит, $a$ --- делитель нуля. Возьмём $b=\VAR{zero_partner}$: "
                 r"$ab=\VAR{zero_product}$ делится на $\VAR{m}$, хотя $a,b\not\equiv0$.\BLOCK{endif} "
                 r"В поле из $\omega^n=1$ и условий на простые делители $n$ можно доказывать точный порядок "
                 r"и обратимость матрицы ДПФ. В кольце с делителями нуля дополнительно требуются условия "
                 r"главного корня (включая исчезающие геометрические суммы); одного порядка недостаточно. "
                 r"\[\boxed{\BLOCK{if unit}a^{-1}=\VAR{inverse}\BLOCK{else}a\text{ --- делитель нуля},\ b=\VAR{zero_partner}\BLOCK{endif}}.\]")

    def sample(self, rng):
        name, m, q, r = rng.choice([("M_{11}", 2047, 23, 89),
                                     ("F_5", 4294967297, 641, 6700417)])
        unit = rng.random() < 0.5
        if unit:
            a = rng.randrange(2, 10000)
            while gcd(a, m) != 1:
                a = rng.randrange(2, 10000)
        else:
            a = q if rng.random() < 0.5 else r
        g = gcd(a, m)
        inv = pow(a, -1, m) if unit else None
        zero_partner = m // g if not unit else None
        return {"name": name, "m": m, "q": q, "r": r, "a": a, "g": g, "unit": unit,
                "inverse": inv, "product": a * inv if unit else None,
                "quotient": (a * inv - 1) // m if unit else None,
                "zero_partner": zero_partner, "zero_product": a * zero_partner if not unit else None,
                "answer": {"status": "unit" if unit else "zero_divisor", "inverse": inv}}

    def check(self, p):
        assert p["q"] * p["r"] == p["m"]
        assert p["g"] == gcd(p["a"], p["m"])
        if p["unit"]:
            assert p["g"] == 1 and p["a"] * p["inverse"] % p["m"] == 1
        else:
            assert p["g"] > 1 and p["a"] * p["zero_partner"] % p["m"] == 0
            assert p["zero_partner"] % p["m"] != 0
