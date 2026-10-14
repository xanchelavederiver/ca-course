"""Addition and multiplication in the diminished-one code modulo a Fermat number 2^t + 1
(lecture sem1/05). Corner cases: a zero operand (flag bit), an operand -1 = 2^t (code of
all ones), a zero sum (a + b = 2^t + 1), a product -1.
"""

from taskgen.core.nt import inverse
from taskgen.core.task import SolutionDetail, Task
from taskgen.tasks.modular.fermat_mersenne import from_2f, integer_to_2f


def code_str(x: int, t: int) -> str:
    """Diminished-one code of x mod 2^t + 1 as a (t+1)-bit string, flag bit first."""
    return "".join(map(str, integer_to_2f(x, t)[::-1]))


def dim1_add(x: int, y: int, t: int) -> dict:
    """Code of x + y from the codes x' = x - 1, y' = y - 1 (x, y != 0): s = x' + y';
    with a carry out of t bits the code is s - 2^t, else s + 1 (s + 1 = 2^t means zero)."""
    xp, yp = x - 1, y - 1
    s = xp + yp
    carry = s >> t
    if carry:
        r, zero = s - 2**t, False
    else:
        r = s + 1
        zero = r == 2**t
    return {"xp": xp, "yp": yp, "s": s, "carry": carry, "r": r, "zero": zero,
            "value": 0 if zero else r + 1}


def dim1_mul(x: int, y: int, t: int) -> dict:
    """Code of x y: P = x'y' + x' + y' = xy - 1 = H 2^t + L, code = L - H (mod 2^t + 1)."""
    m = 2**t + 1
    xp, yp = x - 1, y - 1
    P = xp * yp + xp + yp
    H, L = P >> t, P & (2**t - 1)
    r = L - H
    r_red = r + m if r < 0 else r
    return {"xp": xp, "yp": yp, "prod": xp * yp, "P": P, "H": H, "L": L, "r": r, "r_red": r_red,
            "value": r_red + 1}


class FermatDiminishedOne(Task):
    id = "modular.fermat_dim1"
    title_ru = "Сложение и умножение в коде с уменьшением на единицу по модулю числа Ферма"
    topics = ("arithmetic.modular",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Modulus 2^8 + 1 = 257. With probability corner_ratio one of the corner cases: a zero "
             "operand, an operand -1 (code 0 11111111), a zero sum, a product -1.")
    presets = {"default": {"t": 8, "corner_ratio": 0.5}}
    statement = (r"В кольце $\mathbb{Z}/\VAR{m}\mathbb{Z}$, $\VAR{m} = 2^{\VAR{t}} + 1$, вычеты хранятся "
                 r"в коде с уменьшением на единицу ($\VAR{t + 1}$ бит: старший бит --- признак нуля, "
                 r"младшие $\VAR{t}$ бит --- $x - 1$ при $x \ne 0$). Даны коды "
                 r"\[a = \VAR{ca}_{2f}, \qquad b = \VAR{cb}_{2f}.\] "
                 r"Вычислить коды суммы $a + b$ и произведения $a \cdot b$, выполняя операции над "
                 r"кодами. Проверить ответ, перейдя к обычной записи.")
    solution = (r"Обозначим $x' = x - 1$ ($\VAR{t}$-битовую часть кода ненулевого $x$). Тогда "
                r"$(x + y)' \equiv x' + y' + 1$, $(xy)' \equiv xy - 1 = x'y' + x' + y'$ (по модулю "
                r"$\VAR{m}$), и $2^{\VAR{t}} \equiv -1$."
                r"\BLOCK{if zero_op}\par Код \BLOCK{if a == 0}$a$\BLOCK{else}$b$\BLOCK{endif} имеет "
                r"единичный старший бит: это нуль. Поэтому $a + b = \BLOCK{if a == 0}b\BLOCK{else}a"
                r"\BLOCK{endif}$ (код не меняется), $a \cdot b = 0$ (код $\VAR{zero_code}_{2f}$)."
                r"\BLOCK{else}"
                r"\par Сумма: $a' + b' = \VAR{add.xp|bin}_2 + \VAR{add.yp|bin}_2 = \VAR{add.s|bin}_2$ "
                r"($\VAR{add.xp} + \VAR{add.yp} = \VAR{add.s}$). "
                r"\BLOCK{if add.carry}Есть перенос из $\VAR{t}$-го разряда: $2^{\VAR{t}} \equiv -1$ "
                r"съедает прибавляемую единицу, код суммы $= a' + b' - 2^{\VAR{t}} = \VAR{add.r}$."
                r"\BLOCK{else}Переноса нет: код суммы $= a' + b' + 1 = \VAR{add.s + 1}"
                r"\BLOCK{if add.zero} = 2^{\VAR{t}}\BLOCK{endif}$\BLOCK{if add.zero}, т.\,е. $a + b = 2^{\VAR{t}} + 1 \equiv 0$: "
                r"результат --- нуль, взводим признак нуля\BLOCK{endif}.\BLOCK{endif}"
                r"\par Произведение: $P = a'b' + a' + b' = \VAR{mul.prod} + \VAR{mul.xp} + \VAR{mul.yp} = "
                r"\VAR{mul.P} = \VAR{mul.P|bin}_2$, $P = H \cdot 2^{\VAR{t}} + L$, $H = \VAR{mul.H}$, "
                r"$L = \VAR{mul.L}$; так как $2^{\VAR{t}} \equiv -1$, код произведения "
                r"$\equiv L - H = \VAR{mul.r}$\BLOCK{if mul.r < 0}, прибавляем $\VAR{m}$: "
                r"$\VAR{mul.r_red}$\BLOCK{endif}\BLOCK{if mul.r_red == 2**t - 1} "
                r"(все единицы: $ab \equiv 2^{\VAR{t}} \equiv -1$)\BLOCK{endif}."
                r"\BLOCK{endif}"
                r"\par Проверка: $a = \VAR{a}$, $b = \VAR{b}$, $a + b \equiv \VAR{s}$, "
                r"$a b = \VAR{a * b} \equiv \VAR{p} \pmod{\VAR{m}}$."
                r"\[a + b = \VAR{code_s}_{2f}, \qquad a \cdot b = \VAR{code_p}_{2f}.\]")

    def sample(self, rng):
        t = self.cfg.t
        m = 2**t + 1
        a, b = rng.randrange(1, m), rng.randrange(1, m)
        if rng.random() < self.cfg.corner_ratio:
            kind = rng.choice(["zero", "minus1", "sum_zero", "prod_minus1"])
            if kind == "zero":
                a = 0
            elif kind == "minus1":
                a = m - 1
            elif kind == "sum_zero":
                b = m - a
            else:
                b = (-inverse(a, m)) % m
            if rng.random() < 0.5:
                a, b = b, a
        s, p = (a + b) % m, a * b % m
        zero_op = a == 0 or b == 0
        add = mul = None
        if not zero_op:
            add, mul = dim1_add(a, b, t), dim1_mul(a, b, t)
        return {"t": t, "m": m, "a": a, "b": b, "ca": code_str(a, t), "cb": code_str(b, t),
                "zero_op": zero_op, "add": add, "mul": mul, "s": s, "p": p,
                "zero_code": code_str(0, t), "code_s": code_str(s, t), "code_p": code_str(p, t),
                "answer": [code_str(s, t), code_str(p, t)]}

    def check(self, p):
        t, m = p["t"], p["m"]
        dec = lambda c: from_2f([int(x) for x in c[::-1]])  # noqa: E731
        a, b = dec(p["ca"]), dec(p["cb"])
        assert (a, b) == (p["a"], p["b"])
        assert dec(p["answer"][0]) == (a + b) % m and dec(p["answer"][1]) == a * b % m
        if not p["zero_op"]:  # the code-level rules agree with the residues
            add, mul = p["add"], p["mul"]
            assert add["value"] % m == (a + b) % m
            assert mul["value"] % m == a * b % m and 0 <= mul["r_red"] < 2**t
