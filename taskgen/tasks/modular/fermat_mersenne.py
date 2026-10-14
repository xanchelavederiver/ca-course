"""Arithmetic modulo Fermat and Mersenne numbers (ported from main-{1,2}sem.py).

Presets: "default" = 1st semester (decimal inputs; Fermat answer also in the
diminished-one code; Mersenne modulus 255), "sem2" = binary inputs, Mersenne
modulus 127.
"""

from taskgen.core.task import SolutionDetail, Task


def integer_to_2f(b: int, t: int) -> list[int]:
    """Diminished-one code of ``b`` modulo ``2^t + 1`` as little-endian bits (t + 1 of them).

    b in [1, 2^t] is stored as ``b - 1`` in the t low bits with the top (zero
    flag) bit 0; b = 0 is stored as the flag bit 1 and t zero bits.

    The legacy version produced 9- or 10-bit garbage for t = 8 (e.g. 2 and 4
    collided with 0-ish patterns); only its b = 0 branch matched this code.
    """
    if not 0 <= b <= 2**t:
        raise ValueError(f"{b} is not a residue modulo 2^{t} + 1")
    if b == 0:
        return [0] * t + [1]
    return [(b - 1) >> i & 1 for i in range(t)] + [0]


def from_2f(bits: list[int]) -> int:
    t = len(bits) - 1
    if bits[t]:
        return 0
    return sum(x << i for i, x in enumerate(bits[:t])) + 1


def _num(x: int, base: int) -> str:
    return f"{x:b}_2" if base == 2 else str(x)


class FermatMul(Task):
    id = "modular.fermat_mul"
    title_ru = "Арифметика в кольце вычетов по модулю чисел Ферма"
    topics = ("arithmetic.modular",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    presets = {
        "default": {"lo": 7, "hi": 257, "base": 10, "show_2f": True},
        "sem2": {"base": 2, "show_2f": False},
    }
    statement = r"Вычислить произведение в кольце вычетов по модулю числа Ферма: \[\VAR{a_tex} \cdot \VAR{b_tex}\ (\textrm{mod}\ 257).\]"
    solution = (r"$257 = 2^8 + 1$, поэтому $2^8 \equiv -1$ и для $c = H \cdot 2^8 + L$, $0 \le L < 2^8$: "
                r"$c \equiv L - H\ (\textrm{mod}\ 257)$. "
                r"\BLOCK{if cfg.base == 10}В двоичной записи $\VAR{a} = \VAR{a|bin}_2$, $\VAR{b} = \VAR{b|bin}_2$. \BLOCK{endif}"
                r"$c = \VAR{a|bin}_2 \cdot \VAR{b|bin}_2 = \VAR{c|bin}_2$ ($= \VAR{c}$), "
                r"$H = \VAR{h|bin}_2$, $L = \VAR{l|bin}_2$; "
                r"$L - H = \VAR{l} - \VAR{h} = \VAR{l - h}$\BLOCK{if l < h}, прибавляем $257$: "
                r"$\VAR{l - h + 257}$\BLOCK{endif}."
                r"\BLOCK{if cfg.show_2f} В коде с уменьшением на единицу (старший бит --- признак нуля, "
                r"младшие $8$ бит --- $c - 1$): $\VAR{answer}\ \mapsto\ \VAR{answer_2f}_{2f}$.\BLOCK{endif}"
                r"\[\VAR{answer|bin}_2\BLOCK{if cfg.show_2f}\ = \VAR{answer_2f}_{2f}\BLOCK{endif}"
                r"\ (\textrm{mod}\ 257).\]")

    def sample(self, rng):
        a = rng.randrange(self.cfg.lo, self.cfg.hi)
        b = rng.randrange(self.cfg.lo, self.cfg.hi)
        c = a * b
        h, low = c >> 8, c & 255
        return {"a": a, "b": b, "a_tex": _num(a, self.cfg.base), "b_tex": _num(b, self.cfg.base),
                "c": c, "h": h, "l": low,
                "answer_2f": "".join(map(str, integer_to_2f(c % 257, 8)[::-1])), "answer": c % 257}

    def check(self, p):
        assert p["answer"] == p["a"] * p["b"] % 257 == (p["l"] - p["h"]) % 257
        bits = [int(x) for x in p["answer_2f"][::-1]]
        assert len(bits) == 9 and from_2f(bits) == p["answer"]


class MersenneMul(Task):
    id = "modular.mersenne_mul"
    title_ru = "Арифметика в кольце вычетов по модулю чисел Мерсенна"
    topics = ("arithmetic.modular",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = "sem1 used modulus 255 = 2^8 - 1, sem2 uses 127 = 2^7 - 1 (legacy answer said 257: fixed)."
    presets = {
        "default": {"modulus": 255, "lo": 7, "base": 10},
        "sem2": {"modulus": 127, "base": 2},
    }
    statement = (r"Вычислить произведение в кольце вычетов по модулю числа Мерсенна: "
                 r"\[\VAR{a_tex} \cdot \VAR{b_tex}\ (\textrm{mod}\ \VAR{m}).\]")
    solution = (r"$\VAR{m} = 2^{\VAR{k}} - 1$, поэтому $2^{\VAR{k}} \equiv 1$ и для $c = H \cdot 2^{\VAR{k}} + L$: "
                r"$c \equiv H + L\ (\textrm{mod}\ \VAR{m})$ (циклический перенос). "
                r"\BLOCK{if cfg.base == 10}В двоичной записи $\VAR{a} = \VAR{a|bin}_2$, $\VAR{b} = \VAR{b|bin}_2$. \BLOCK{endif}"
                r"$c = \VAR{a|bin}_2 \cdot \VAR{b|bin}_2 = \VAR{c|bin}_2$, "
                r"\BLOCK{for f in folds}$H = \VAR{f.h|bin}_2$, $L = \VAR{f.l|bin}_2$, $H + L = \VAR{f.s|bin}_2$"
                r"\BLOCK{if not loop.last}; снова больше $\VAR{m}$: \BLOCK{endif}\BLOCK{endfor}"
                r"\BLOCK{if not folds}$c < \VAR{m}$, приведение не нужно\BLOCK{endif}"
                r"\BLOCK{if full}; $\VAR{m|bin}_2 \equiv 0$\BLOCK{endif}."
                r"\[\VAR{answer|bin}_2\BLOCK{if cfg.base == 10}\ = \VAR{answer}\BLOCK{endif}"
                r"\ (\textrm{mod}\ \VAR{m}).\]")

    def sample(self, rng):
        m = self.cfg.modulus
        k = m.bit_length()
        a = rng.randrange(self.cfg.lo, m)
        b = rng.randrange(self.cfg.lo, m)
        c, folds = a * b, []
        x = c
        while x > m:
            h, low = x >> k, x & m
            x = h + low
            folds.append({"h": h, "l": low, "s": x})
        full = x == m
        return {"a": a, "b": b, "m": m, "k": k, "a_tex": _num(a, self.cfg.base),
                "b_tex": _num(b, self.cfg.base), "c": c, "folds": folds, "full": full,
                "answer": 0 if full else x}

    def check(self, p):
        assert (p["m"] + 1) & p["m"] == 0, "modulus must be 2^k - 1"
        assert p["answer"] == p["a"] * p["b"] % p["m"]
