"""Fast exponentiation (ported from main-{1,2}sem.py).

Presets: "default" = 1st-semester ranges, "sem2" = 2nd-semester ranges.
"""

from taskgen.core import steps
from taskgen.core.task import SolutionDetail, Task

SEM1_EXP = {"p_lo": 42, "p_hi": 128}
SEM2_EXP = {"p_lo": 15, "p_hi": 65}
# Exponents 20..30 for the tasks without a modulus: a^p is computed in full by hand,
# so it must fit on paper (3^30 has 15 digits; the 42..127 range gave up to 61).
PLAIN_EXP = {"p_lo": 20, "p_hi": 31}
MOD = r"\ (\textrm{mod}\ \VAR{m})"
TX = r"\BLOCK{import 'macros.tex.j2' as tx}"

BINARY_RULE = (r"$\VAR{p} = \VAR{p|bin}_2$. Биты показателя обрабатываются слева направо: "
               r"$r \gets r^2$, при бите $1$ ещё $r \gets r \cdot a$ (в столбце $e$ --- текущий "
               r"показатель, $r = a^e$).")
QARY_RULE = (r"$\VAR{p} = (\VAR{q.digits|join(' ')})_4$. Предвычисление: "
             r"\BLOCK{for x in q.table}$a^{\VAR{loop.index0}} = \VAR{x}$\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}. "
             r"Цифры показателя обрабатываются слева направо: $r \gets r^4$ (два возведения в квадрат), "
             r"затем $r \gets r \cdot a^{d}$, где $d$ --- очередная цифра.")


class BinaryPow(Task):
    id = "powmod.binary"
    title_ru = "Бинарный алгоритм возведения в степень"
    topics = ("powmod",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"a_lo": 2, "a_hi": 4, **PLAIN_EXP}}
    statement = r"Возвести целое число в степень с помощью бинарного алгоритма: \[\VAR{a}^{\VAR{p}}.\]"
    solution = (BINARY_RULE +
                r"\BLOCK{for s in steps}\par\noindent бит \VAR{s.bit}: "
                r"\BLOCK{if loop.first}$r = a = \VAR{a}$\BLOCK{else}$r^2 = \VAR{s.sq|bignum}$"
                r"\BLOCK{if s.bit == '1'}, $r = r^2 \cdot \VAR{a} = \VAR{s.r|bignum}$\BLOCK{endif}\BLOCK{endif}"
                r" ($e = \VAR{s.e}$)\BLOCK{endfor}"
                r"\par\noindent Ответ: $\VAR{a}^{\VAR{p}} = \VAR{answer|bignum}$.")

    def sample(self, rng):
        a = rng.randrange(self.cfg.a_lo, self.cfg.a_hi)
        p = rng.randrange(self.cfg.p_lo, self.cfg.p_hi)
        return {"a": a, "p": p, "steps": steps.binary_pow_steps(a, p), "answer": a**p}

    def check(self, p):
        assert p["answer"] == p["a"] ** p["p"] == p["steps"][-1]["r"]


class BinaryPowMod(Task):
    id = "powmod.binary_mod"
    title_ru = "Бинарный алгоритм возведения в степень по модулю"
    topics = ("powmod",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    presets = {
        "default": {"a_lo": 2, "a_hi": 1000, "m_lo": 300, "m_hi": 500, **SEM1_EXP},
        "sem2": SEM2_EXP,
    }
    statement = (r"Возвести целое число в степень по модулю с помощью бинарного алгоритма: "
                 r"\[\VAR{a}^{\VAR{p}}" + MOD + r".\]")
    solution = (r"\BLOCK{if a != a_red}$a = \VAR{a} \equiv \VAR{a_red}" + MOD + r"$. \BLOCK{endif}" +
                BINARY_RULE +
                r"\[\begin{array}{c|r|r|r}"
                r"\text{бит} & r^2 & r & e \\ \hline "
                r"\BLOCK{for s in steps}\VAR{s.bit} & \VAR{s.sq} & \VAR{s.r} & \VAR{s.e} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"\[\VAR{a}^{\VAR{p}} \equiv \VAR{answer}" + MOD + r".\]")

    def sample(self, rng):
        a = rng.randrange(self.cfg.a_lo, self.cfg.a_hi)
        p = rng.randrange(self.cfg.p_lo, self.cfg.p_hi)
        m = rng.randrange(self.cfg.m_lo, self.cfg.m_hi)
        st = steps.binary_pow_steps(a % m, p, m)
        return {"a": a, "p": p, "m": m, "a_red": a % m, "steps": st, "answer": st[-1]["r"]}

    def check(self, p):
        assert p["answer"] == pow(p["a"], p["p"], p["m"])
        assert len(p["steps"]) == p["p"].bit_length()


class QaryPow(Task):
    id = "powmod.qary"
    title_ru = "4-арный алгоритм возведения в степень"
    topics = ("powmod",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"a_lo": 2, "a_hi": 4, **PLAIN_EXP}}
    statement = r"Возвести целое число в степень с помощью $4$-арного алгоритма: \[\VAR{a}^{\VAR{p}}.\]"
    solution = (QARY_RULE +
                r"\BLOCK{for s in q.steps}\par\noindent цифра \VAR{s.digit}: "
                r"\BLOCK{if s.first}$r = a^{\VAR{s.digit}} = \VAR{s.r|bignum}$"
                r"\BLOCK{else}$r^4 = \VAR{s.pow|bignum}$, $r = r^4 \cdot a^{\VAR{s.digit}} = \VAR{s.r|bignum}$"
                r"\BLOCK{endif} ($r = a^{\VAR{s.e}}$)\BLOCK{endfor}"
                r"\par\noindent Ответ: $\VAR{a}^{\VAR{p}} = \VAR{answer|bignum}$.")

    def sample(self, rng):
        a = rng.randrange(self.cfg.a_lo, self.cfg.a_hi)
        p = rng.randrange(self.cfg.p_lo, self.cfg.p_hi)
        q = steps.qary_pow_steps(a, p)
        return {"a": a, "p": p, "q": q, "answer": q["result"]}

    def check(self, p):
        assert p["answer"] == p["a"] ** p["p"]


class QaryPowMod(Task):
    id = "powmod.qary_mod"
    title_ru = "4-арный алгоритм возведения в степень по модулю"
    topics = ("powmod",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    presets = {
        "default": {"a_lo": 2, "a_hi": 1000, "m_lo": 300, "m_hi": 500, **SEM1_EXP},
        "sem2": SEM2_EXP,
    }
    statement = (r"Возвести целое число в степень по модулю с помощью $4$-арного алгоритма: "
                 r"\[\VAR{a}^{\VAR{p}}" + MOD + r".\]")
    solution = (r"Все вычисления по модулю $\VAR{m}$. " + QARY_RULE +
                r"\[\begin{array}{c|r|r|r}"
                r"d & r^4 & r & e \\ \hline "
                r"\BLOCK{for s in q.steps}\VAR{s.digit} & \BLOCK{if not s.first}\VAR{s.pow}\BLOCK{else}"
                r"\text{---}\BLOCK{endif} & \VAR{s.r} & \VAR{s.e} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"\[\VAR{a}^{\VAR{p}} \equiv \VAR{answer}" + MOD + r".\]")

    def sample(self, rng):
        a = rng.randrange(self.cfg.a_lo, self.cfg.a_hi)
        p = rng.randrange(self.cfg.p_lo, self.cfg.p_hi)
        m = rng.randrange(self.cfg.m_lo, self.cfg.m_hi)
        q = steps.qary_pow_steps(a % m, p, m)
        return {"a": a, "p": p, "m": m, "q": q, "answer": q["result"]}

    def check(self, p):
        assert p["answer"] == pow(p["a"], p["p"], p["m"])


MONT_POW = (r"\VAR{tx.montgomery_params(mo)} "
            r"Переводим $a$ в форму Монтгомери $\bar a = \mathrm{REDC}(a \cdot (R^2 \bmod m)) = aR \bmod m$; "
            r"далее для битов показателя $\VAR{mo.bits}_2$ после старшего: $\bar x \gets \mathrm{REDC}(\bar x^2)$, "
            r"при бите $1$ ещё $\bar x \gets \mathrm{REDC}(\bar x \bar a)$; в конце $x = \mathrm{REDC}(\bar x)$."
            r"\VAR{tx.redc_table(mo)}")


class MontgomeryPow(Task):
    id = "powmod.montgomery"
    title_ru = "Возведение в степень по модулю методом Монтгомери"
    topics = ("powmod", "arithmetic.montgomery")
    complexity = 2
    family = "montgomery"
    solution_detail = SolutionDetail.FULL
    notes = "Odd modulus; the even-modulus version is powmod.montgomery_even."
    presets = {
        "default": {"a_lo": 2, "a_hi": 59, "m_lo": 300, "m_hi": 500, **SEM1_EXP},
        "sem2": SEM2_EXP,
    }
    statement = (r"Возвести целое число в степень по модулю: \[\VAR{a}^{\VAR{p}}" + MOD + r"\] "
                 r"с помощью метода Монтгомери. Обосновать выбор параметра $R$.")
    solution = TX + MONT_POW + r"\[\VAR{a}^{\VAR{p}} \equiv \VAR{answer}" + MOD + r".\]"

    def sample(self, rng):
        a = rng.randrange(self.cfg.a_lo, self.cfg.a_hi)
        p = rng.randrange(self.cfg.p_lo, self.cfg.p_hi)
        m = rng.randrange(self.cfg.m_lo, self.cfg.m_hi) | 1
        mo = steps.montgomery_pow(a, p, m)
        return {"a": a, "p": p, "m": m, "mo": mo, "answer": mo["result"]}

    def check(self, p):
        assert p["m"] % 2 == 1, "Montgomery modulus must be odd"
        assert p["answer"] == pow(p["a"], p["p"], p["m"])


class MontgomeryPowEven(Task):
    id = "powmod.montgomery_even"
    title_ru = "Возведение в степень по модулю методом Монтгомери (чётный модуль)"
    topics = ("powmod", "arithmetic.montgomery")
    complexity = 3
    family = "montgomery"
    solution_detail = SolutionDetail.FULL
    notes = ("Harder version: m = 2^t s is even; mod 2^t by the binary method, mod s by "
             "Montgomery, combined by CRT. The legacy sem1 script always produced even moduli.")
    presets = MontgomeryPow.presets
    statement = MontgomeryPow.statement
    solution = (TX + r"Модуль чётный: $m = \VAR{m} = 2^{\VAR{t}} \cdot \VAR{s}$, и $R = 2^k$ не взаимно прост "
                r"с $m$. Решаем задачу по модулям $2^{\VAR{t}}$ и $s = \VAR{s}$ и объединяем по КТО."
                r"\par По модулю $2^{\VAR{t}} = \VAR{pt}$ бинарным алгоритмом "
                r"($a \equiv \VAR{a % pt}$, $\VAR{p} = \VAR{p|bin}_2$): "
                r"\BLOCK{for st in low}$\VAR{st.r}$\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}"
                r" --- значения $r$ после каждого бита; $a^{\VAR{p}} \equiv \VAR{r1}\VAR{tx.mod(pt)}$."
                r"\par По модулю $s$ методом Монтгомери ($a \equiv \VAR{mo.a_r}$ по модулю $s$): "
                + MONT_POW +
                r"Итак, $a^{\VAR{p}} \equiv \VAR{r2}\VAR{tx.mod(s)}$. КТО:"
                r"\VAR{tx.crt(c)}"
                r"\[\VAR{a}^{\VAR{p}} \equiv \VAR{answer}" + MOD + r".\]")

    def sample(self, rng):
        while True:
            a = rng.randrange(self.cfg.a_lo, self.cfg.a_hi)
            p = rng.randrange(self.cfg.p_lo, self.cfg.p_hi)
            m = rng.randrange(self.cfg.m_lo, self.cfg.m_hi) & ~1
            t, s = steps.split_even(m)
            if s > 1:
                break
        pt = 2**t
        low = steps.binary_pow_steps(a % pt, p, pt)
        mo = steps.montgomery_pow(a, p, s)
        c = steps.crt([low[-1]["r"], mo["result"]], [pt, s])
        return {"a": a, "p": p, "m": m, "t": t, "s": s, "pt": pt, "low": low, "r1": low[-1]["r"],
                "r2": mo["result"], "mo": mo, "c": c, "answer": c["x"]}

    def check(self, p):
        assert p["m"] % 2 == 0 and p["pt"] * p["s"] == p["m"]
        assert p["answer"] == pow(p["a"], p["p"], p["m"])
