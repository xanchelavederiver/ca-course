"""LCG and LFSR synthesis followed by stream-cipher decryption."""

from math import gcd

from taskgen.core.nt import inverse
from taskgen.core.task import SolutionDetail, Task
from taskgen.tasks.crypto.lfsr import (_aug_tex, berlekamp_massey, bits_tex, gauss_jordan_gf2,
                                       lfsr_bits, poly_from_taps, ptex, recurrence_tex,
                                       taps_from_poly)
from taskgen.tasks.crypto.lfsr_extensions import primitive_poly

MESSAGES = [
    "ALGEBRA",
    "KARATSUBA",
    "TOOM COOK",
    "MONTGOMERY",
    "EUCLID",
    "FERMAT",
    "MILLER",
    "SOLOVAY",
]


def bytes_to_bits(data: bytes) -> list[int]:
    return [(byte >> i) & 1 for byte in data for i in range(7, -1, -1)]


def bits_to_bytes(bits: list[int]) -> list[int]:
    assert len(bits) % 8 == 0
    return [sum(bits[i + j] << (7 - j) for j in range(8)) for i in range(0, len(bits), 8)]


def numbers_tex(values: list[int]) -> str:
    return r",\allowbreak\ ".join(map(str, values))


def bytes_block_tex(bits: list[int], columns: int = 4) -> str:
    s = "".join(map(str, bits))
    octets = [s[i:i + 8] for i in range(0, len(s), 8)]
    lines = [r"\texttt{" + " ".join(octets[i:i + columns]) + "}"
             for i in range(0, len(octets), columns)]
    return r"\begin{gathered}" + r"\\".join(lines) + r"\end{gathered}"


class LCGDecrypt(Task):
    id = "crypto.lcg_decrypt"
    title_ru = "Синтез ЛКГ и расшифровка данных"
    topics = ("crypto.prng",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"moduli": [61, 67, 71, 73, 79, 83, 89, 97, 101, 127, 131, 191, 251],
                           "messages": MESSAGES}}
    statement = (r"Последовательность целых чисел зашифрована по формуле "
                 r"$c_i \equiv m_i + k_i \pmod{256}$, где $m_i$ --- число открытого текста, "
                 r"а $k_i$ --- выход линейного конгруэнтного генератора "
                 r"$k_{i+1} \equiv a k_i + c \pmod m$. Модуль $m$ --- простое число, $m < 256$. "
                 r"Зашифрованные данные: \[\VAR{cipher_tex}.\] "
                 r"Известны первые шесть чисел открытого текста: \[\VAR{known_plain|join(', ')}.\] "
                 r"Найти $k_0,k_1,\ldots,k_5$, восстановить параметры $a,c,m$ генератора "
                 r"и расшифровать всю последовательность. Расшифрованные числа --- коды ASCII.")
    solution = (r"Из первых шести пар находим $k_i \equiv c_i-m_i\pmod{256}$: "
                r"$\VAR{known_keys|join(', ')}$. Разности $t_i=k_{i+1}-k_i$: "
                r"$\VAR{ts|join(', ')}$. Тогда $u_i=t_{i+2}t_i-t_{i+1}^2$ делятся на $m$: "
                r"$\VAR{us|join(', ')}$, и $\gcd(u_0,u_1,u_2)=\VAR{modulus}$. Поскольку это число "
                r"простое и больше всех наблюдаемых выходов, $m=\VAR{modulus}$. "
                r"Обратный элемент: $t_0^{-1}\equiv\VAR{t0_inv}\pmod m$. Следовательно, "
                r"\[a\equiv t_1t_0^{-1}\equiv\VAR{a}\pmod m,\qquad "
                r"c\equiv k_1-ak_0\equiv\VAR{increment}\pmod m.\] "
                r"Проверка рекуррентности на всех шести известных выходах выполнена. "
                r"Продолжая генератор, получаем ключевую последовательность "
                r"\[\VAR{keys_tex}.\] Вычитая её из шифротекста по модулю $256$, получаем "
                r"\[\VAR{plain_tex}.\] Это коды ASCII сообщения "
                r"\[\boxed{\texttt{\VAR{message}}}.\] "
                r"Итого: $a=\VAR{a}$, $c=\VAR{increment}$, $m=\VAR{modulus}$.")

    def sample(self, rng):
        while True:
            m = rng.choice(self.cfg.moduli)
            a, increment = rng.randrange(1, m), rng.randrange(m)
            keys = [rng.randrange(m)]
            for _ in range(5):
                keys.append((a * keys[-1] + increment) % m)
            ts = [keys[i + 1] - keys[i] for i in range(5)]
            us = [ts[i + 2] * ts[i] - ts[i + 1] ** 2 for i in range(3)]
            if gcd(*us) == m and gcd(ts[0], m) == 1:
                break
        message = rng.choice(self.cfg.messages)
        plain = list(message.encode("ascii"))
        for _ in range(len(keys), len(plain)):
            keys.append((a * keys[-1] + increment) % m)
        cipher = [(x + k) % 256 for x, k in zip(plain, keys)]
        t0_inv = inverse(ts[0] % m, m)
        return {"a": a, "increment": increment, "modulus": m, "keys": keys,
                "known_keys": keys[:6], "ts": ts, "us": us, "t0_inv": t0_inv,
                "plain": plain, "known_plain": plain[:6], "cipher": cipher,
                "message": message, "cipher_tex": numbers_tex(cipher),
                "keys_tex": numbers_tex(keys), "plain_tex": numbers_tex(plain),
                "answer": {"a": a, "c": increment, "m": m, "known_keys": keys[:6],
                           "plaintext": plain, "message": message}}

    def check(self, p):
        m, a, increment = p["answer"]["m"], p["answer"]["a"], p["answer"]["c"]
        plain, keys, cipher = p["plain"], p["keys"], p["cipher"]
        assert p["known_keys"] == [(c - x) % 256 for c, x in zip(cipher[:6], plain[:6])]
        assert gcd(*p["us"]) == m and gcd(p["ts"][0], m) == 1
        assert p["t0_inv"] * p["ts"][0] % m == 1
        assert a == p["ts"][1] * p["t0_inv"] % m
        assert increment == (keys[1] - a * keys[0]) % m
        assert keys[1:] == [(a * keys[i] + increment) % m for i in range(len(keys) - 1)]
        assert cipher == [(x + k) % 256 for x, k in zip(plain, keys)]
        assert plain == [(c - k) % 256 for c, k in zip(cipher, keys)]
        assert bytes(plain).decode("ascii") == p["answer"]["message"] == p["message"]


class LFSRDecrypt(Task):
    id = "crypto.lfsr_decrypt"
    title_ru = "Синтез РСЛОС и расшифровка данных"
    topics = ("crypto.lfsr",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"degrees": [4, 5], "messages": MESSAGES}}
    statement = (r"Биты сообщения зашифрованы по формуле $c_i=m_i\oplus k_i$, где $k_i$ --- "
                 r"выход РСЛОС длины $L=\VAR{L}$ с неизвестной рекуррентностью "
                 r"$k_{n+\VAR{L}}=c_1k_{n+\VAR{L - 1}}+\cdots+c_{\VAR{L}}k_n$ над $\mathbb F_2$. "
                 r"Зашифрованная битовая строка (группы по $8$ бит): \[\VAR{cipher_tex}.\] "
                 r"Известны первые $2L=\VAR{2 * L}$ бит открытого текста: "
                 r"\[\VAR{known_plain_tex}.\] Найти соответствующие биты ключевой последовательности, "
                 r"восстановить коэффициенты $c_1,\ldots,c_{\VAR{L}}$ и характеристический многочлен "
                 r"РСЛОС, затем расшифровать всё сообщение. Каждая группа из $8$ бит --- код ASCII, "
                 r"старший бит записан первым.")
    solution = (r"Складывая известные биты открытого текста с первыми битами шифротекста по модулю $2$, "
                r"получаем $\VAR{known_keys_tex}$. Для $n=0,\ldots,\VAR{L - 1}$ записываем систему "
                r"относительно $(c_{\VAR{L}},\ldots,c_1)$: \[\VAR{M0}.\] "
                r"Метод Гаусса над $\mathbb F_2$:"
                r"\BLOCK{for st in gj}\par\noindent столбец $c_{\VAR{st.c}}$: "
                r"\BLOCK{if st.ops}$\VAR{st.ops|join(';\\ ')}$ $\Rightarrow$ $\VAR{st.M}$"
                r"\BLOCK{else}преобразований не нужно\BLOCK{endif};\BLOCK{endfor}"
                r"\par Ранг равен $\VAR{L}$, поэтому решение единственно: "
                r"$(c_1,\ldots,c_{\VAR{L}})=(\VAR{cs|join(', ')})$, "
                r"\[f(x)=\VAR{f_tex},\qquad \VAR{rec}.\] "
                r"Все $\VAR{known_len}$ уравнений выполняются. Продолжая рекуррентность, получаем ключ: "
                r"\[\VAR{keys_tex}.\] Сложение с шифротекстом даёт открытый текст "
                r"\[\VAR{plain_tex}.\] В десятичной записи байты: $\VAR{plain_bytes|join(', ')}$; "
                r"сообщение: \[\boxed{\texttt{\VAR{message}}}.\]")

    def sample(self, rng):
        L = rng.choice(self.cfg.degrees)
        f = primitive_poly(rng, L)
        cs = taps_from_poly(f)
        state = [rng.randrange(2) for _ in range(L)]
        while not any(state):
            state = [rng.randrange(2) for _ in range(L)]
        message = rng.choice(self.cfg.messages)
        plain = bytes_to_bits(message.encode("ascii"))
        keys = lfsr_bits(cs, state, len(plain))
        cipher = [m ^ k for m, k in zip(plain, keys)]
        known_keys = keys[:2 * L]
        M = [known_keys[n:n + L + 1] for n in range(L)]
        gj = gauss_jordan_gf2(M, L)
        assert gj["rank"] == L
        recovered = [gj["R"][i][L] for i in range(L)][::-1]
        assert recovered == cs
        steps = [{"c": L - st["col"], "ops": st["ops"], "M": _aug_tex(st["M"], L) if st["M"] else ""}
                 for st in gj["steps"]]
        return {"L": L, "f": f, "f_tex": ptex(f), "cs": cs, "state": state,
                "rec": recurrence_tex(cs).replace("s_", "k_"), "known_len": L, "known_keys": known_keys,
                "known_keys_tex": bits_tex(known_keys), "known_plain": plain[:2 * L],
                "known_plain_tex": bits_tex(plain[:2 * L]), "M0": _aug_tex(M, L, small=False),
                "gj": steps, "keys": keys, "cipher": cipher, "plain": plain,
                "cipher_tex": bytes_block_tex(cipher), "keys_tex": bytes_block_tex(keys),
                "plain_tex": bytes_block_tex(plain), "plain_bytes": bits_to_bytes(plain),
                "message": message,
                "answer": {"c": cs, "f": f, "known_keys": known_keys,
                           "plaintext": bits_to_bytes(plain), "message": message}}

    def check(self, p):
        L, cs = p["L"], p["answer"]["c"]
        known, cipher, plain, keys = p["known_keys"], p["cipher"], p["plain"], p["keys"]
        assert poly_from_taps(cs) == p["answer"]["f"] == p["f"]
        assert known == [c ^ m for c, m in zip(cipher[:2 * L], p["known_plain"])]
        assert berlekamp_massey(known)["L"] == L
        assert lfsr_bits(cs, known[:L], 2 * L) == known
        assert keys == lfsr_bits(cs, p["state"], len(plain))
        assert plain == [c ^ k for c, k in zip(cipher, keys)]
        assert cipher == [m ^ k for m, k in zip(plain, keys)]
        assert bits_to_bytes(plain) == p["plain_bytes"] == p["answer"]["plaintext"]
        assert bytes(p["plain_bytes"]).decode("ascii") == p["answer"]["message"] == p["message"]
