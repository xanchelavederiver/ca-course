"""Cryptographic applications: LCG, RSA common modulus, congruential
cryptosystem (ported from main-{1,2}sem.py).

Presets: "default" = 1st-semester ranges, "sem2" = 2nd-semester ranges.
"""

from math import gcd, isqrt

from taskgen.core import steps
from taskgen.core.nt import first_primes, inverse, random_prime
from taskgen.core.task import SolutionDetail, Task

P100, P40 = list(first_primes(100)), list(first_primes(40))
TX = r"\BLOCK{import 'macros.tex.j2' as tx}"


class LCG(Task):
    id = "crypto.lcg"
    title_ru = "Взлом линейного конгруэнтного генератора"
    topics = ("crypto.prng",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("Instances where the standard attack (m = gcd of t_{i+2} t_i - t_{i+1}^2) does not "
             "recover m exactly are rejected (legacy did not check solvability).")
    presets = {"default": {"moduli": P100[20:]}, "sem2": {"moduli": P40[20:]}}
    statement = (r"Восстановить параметры $a$, $c$ и $m$ Линейного конгруэнтного генератора "
                 r"\[x_i \equiv a \cdot x_{i-1} + c\ (\textrm{mod}\ m)\] по последовательности "
                 r"подряд идущих выходных значений генератора: \[\VAR{xs|join(', ')}.\]")
    solution = (r"Разности $t_i = x_{i+1} - x_i$: $\VAR{ts|join(', ')}$. "
                r"Величины $u_i = t_{i+2} t_i - t_{i+1}^2$ делятся на $m$: $\VAR{us|join(', ')}$, "
                r"$m = \gcd(u_i) = \VAR{answer.m}$. "
                r"Далее $a \equiv t_1 t_0^{-1} \equiv \VAR{answer.a}\ (\textrm{mod}\ m)$, "
                r"$c \equiv x_1 - a x_0 \equiv \VAR{answer.c}\ (\textrm{mod}\ m)$."
                r"\[a = \VAR{answer.a},\ c = \VAR{answer.c},\ m = \VAR{answer.m}.\]")

    def sample(self, rng):
        while True:
            m = rng.choice(self.cfg.moduli)
            a, c = rng.randrange(1, m), rng.randrange(1, m)
            xs = [rng.randrange(1, m)]
            for _ in range(5):
                xs.append((xs[-1] * a + c) % m)
            ts = [xs[i + 1] - xs[i] for i in range(5)]
            us = [ts[i + 2] * ts[i] - ts[i + 1] ** 2 for i in range(3)]
            if gcd(*us) == m:
                return {"xs": xs, "ts": ts, "us": us, "answer": {"a": a, "c": c, "m": m}}

    def check(self, p):
        xs, ans = p["xs"], p["answer"]
        m = gcd(*p["us"])
        assert m == ans["m"], "attack does not recover m"
        a = p["ts"][1] * inverse(p["ts"][0] % m, m) % m
        c = (xs[1] - a * xs[0]) % m
        assert (a, c) == (ans["a"], ans["c"])
        assert all(xs[i + 1] == (a * xs[i] + c) % m for i in range(5))


class RSACommonModulus(Task):
    id = "crypto.rsa_common_modulus"
    title_ru = "Атака на RSA с общим модулем"
    topics = ("crypto.rsa",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = "Requires gcd(e1, e2) = 1, p != q, gcd(C_i, N) = 1 (legacy sem2 did not check)."
    presets = {
        "default": {"exps": P100[:10], "primes": P100[20:-10]},
        "sem2": {"exps": P40[:10], "primes": P40[20:-10]},
    }
    statement = (r"Открытый текст $M$ зашифрован криптосистемой RSA с помощью пары открытых ключей "
                 r"$(e_1, N)$ и $(e_2, N)$:  \[\begin{aligned} C_1 \equiv M^{e_1}\ (\textrm{mod}\ N), "
                 r"\\ C_2 \equiv M^{e_2}\ (\textrm{mod}\ N). \end{aligned}\] "
                 r"Зная пару шифротекстов и открытые ключи: "
                 r"\[C_1 = \VAR{c1}, C_2 = \VAR{c2}, e_1 = \VAR{e1}, e_2 = \VAR{e2}, N = \VAR{n},\] "
                 r"восстановить открытый текст $M$ без разложения модуля $N$ на множители.")
    solution = (TX + r"Так как $\gcd(e_1, e_2) = 1$, найдём $u e_1 + v e_2 = 1$ (расширенный алгоритм Евклида):"
                r"\VAR{tx.xgcd_table(eu, [e1, e2]|max, [e1, e2]|min)}"
                r"$u = \VAR{u}$, $v = \VAR{v}$: $\VAR{u} \cdot \VAR{e1} \VAR{v|signed} \cdot \VAR{e2} = 1$. Тогда "
                r"$C_1^u C_2^v \equiv M^{u e_1 + v e_2} = M$. Отрицательную степень вычисляем через обратный: "
                r"\VAR{tx.inverse(inv)}"
                r"\par $\VAR{neg_name}^{\VAR{neg_exp}} \equiv \VAR{inv.inv}^{\VAR{-neg_exp}} \equiv \VAR{neg_pow}$, "
                r"$\VAR{pos_name}^{\VAR{pos_exp}} \equiv \VAR{pos_pow}$ (бинарным алгоритмом), "
                r"$\VAR{neg_pow} \cdot \VAR{pos_pow} \equiv \VAR{answer}\VAR{tx.mod(n)}$."
                r"\[M = \VAR{answer}.\]")

    def sample(self, rng):
        while True:
            e1, e2 = rng.choice(self.cfg.exps), rng.choice(self.cfg.exps)
            p, q = rng.choice(self.cfg.primes), rng.choice(self.cfg.primes)
            n = p * q
            msg = rng.randrange(n // 2, n)
            c1, c2 = pow(msg, e1, n), pow(msg, e2, n)
            if gcd(e1, e2) == 1 and p != q and gcd(c1, n) == 1 and gcd(c2, n) == 1:
                break
        big, small = max(e1, e2), min(e1, e2)
        eu = steps.xgcd_rows(big, small)
        cb, cs = eu[-2]["u"], eu[-2]["v"]
        u, v = (cb, cs) if e1 == big else (cs, cb)
        if u < 0:
            neg, pos = ("C_1", u, c1), ("C_2", v, c2)
        else:
            neg, pos = ("C_2", v, c2), ("C_1", u, c1)
        inv = steps.inverse_rows(neg[2], n)
        neg_pow, pos_pow = pow(inv["inv"], -neg[1], n), pow(pos[2], pos[1], n)
        return {"e1": e1, "e2": e2, "n": n, "c1": c1, "c2": c2, "eu": eu, "u": u, "v": v,
                "inv": inv, "neg_name": neg[0], "neg_exp": neg[1], "pos_name": pos[0],
                "pos_exp": pos[1], "neg_pow": neg_pow, "pos_pow": pos_pow, "answer": msg}

    def check(self, p):
        n = p["n"]
        assert p["u"] * p["e1"] + p["v"] * p["e2"] == 1
        assert pow(p["c1"], p["u"], n) * pow(p["c2"], p["v"], n) % n == p["answer"]
        assert p["neg_pow"] * p["pos_pow"] % n == p["answer"]


def decrypt_with(vec: list[int], e: int, q: int):
    """Congruential-cryptosystem decryption with a candidate private key (f, g); None if it fails."""
    f, g = vec
    if f <= 0 or g == 0 or gcd(f, abs(g)) != 1:
        return None
    a = f * e % q
    return {"f": f, "g": g, "a": a, "finv": inverse(f, abs(g)), "b": a * inverse(f, abs(g)) % abs(g)}


class CongruentialCryptosystem(Task):
    id = "crypto.congruential"
    title_ru = "Взлом конгруэнтной криптосистемы"
    topics = ("crypto.lattice",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("The attack takes the shortest vector +-(f', g') of the lattice; it need not be the "
             "actual key, it only has to decrypt correctly (otherwise the instance is rejected).")
    presets = {"default": {"q_lo": 10**6, "q_hi": 10**8}}
    statement = (r"Открытый текст $m$ зашифрован конгруэнтной криптосистемой. Зная шифротекст "
                 r"$c = \VAR{e}$ и открытый ключ \[(q, h) = (\VAR{q}, \VAR{h}),\] восстановить $m$.")
    solution = (TX + r"Закрытый ключ $(f, g)$ удовлетворяет $fh \equiv g\ (\textrm{mod}\ q)$ и мал, т.е. "
                r"$(f, g)$ --- короткий вектор решётки с базисом $(1, h)^T = (1, \VAR{h})^T$, "
                r"$(0, q)^T = (0, \VAR{q})^T$. Ищем кратчайший вектор методом Гаусса:"
                r"\VAR{tx.gauss_table(gr, norms=False)}"
                r"Кратчайший вектор $\pm(\VAR{gr.v1[0]}, \VAR{gr.v1[1]})^T$; берём знак с $f' > 0$: "
                r"$(f', g') = (\VAR{dk.f}, \VAR{dk.g})$ (годится любой вектор, с которым расшифрование корректно). "
                r"Расшифрование: $a \equiv f' c \equiv \VAR{dk.f} \cdot \VAR{e} \equiv \VAR{dk.a}\ (\textrm{mod}\ q)$, "
                r"$f'^{-1} \equiv \VAR{dk.finv}\ (\textrm{mod}\ |g'|)$, "
                r"$b \equiv a f'^{-1} \equiv \VAR{dk.b}\ (\textrm{mod}\ |g'|)$."
                r"\[m = \VAR{answer}.\]")

    def sample(self, rng):
        while True:
            q = rng.randrange(self.cfg.q_lo, self.cfg.q_hi)
            # legacy: f in [q^(1/4), sqrt(q/2)], g in [sqrt(q/4), sqrt(q/2)]
            f = random_prime(rng, int(q ** 0.25), isqrt(q // 2))
            g = random_prime(rng, isqrt(q // 4), isqrt(q // 2))
            if gcd(f, q) != 1 or f == g:
                continue
            h = inverse(f, q) * g % q
            msg = rng.randrange(2, isqrt(q // 4))
            r = rng.randrange(2, isqrt(q // 2))
            e = (r * h + msg) % q
            gr = steps.gauss_reduce([1, h], [0, q])
            sv = gr["v1"] if gr["v1"][0] > 0 else [-gr["v1"][0], -gr["v1"][1]]
            dk = decrypt_with(sv, e, q)
            if dk is not None and dk["b"] == msg:
                return {"q": q, "h": h, "e": e, "gr": gr, "dk": dk, "key": [f, g], "answer": msg}

    def check(self, p):
        q, dk = p["q"], p["dk"]
        assert (p["h"] * dk["f"] - dk["g"]) % q == 0, "(f', g') not in the lattice"
        assert decrypt_with([dk["f"], dk["g"]], p["e"], q)["b"] == p["answer"]
