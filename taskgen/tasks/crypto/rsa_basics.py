"""RSA basics (lecture sem2/05): toy key generation, encryption and CRT decryption;
factoring N from phi(N) and from a key pair (e, d).

Presets of crypto.rsa_toy: "default" (random corner cases), "plain" (no corner cases),
"bad_e" (the given e is not
coprime to phi(N): the next valid e must be chosen), "msg_not_coprime" (gcd(m, N) > 1).
"""

from math import gcd, isqrt

from taskgen.core import steps
from taskgen.core.nt import factorize, first_primes, inverse, is_prime
from taskgen.core.task import SolutionDetail, Task

TX = r"\BLOCK{import 'macros.tex.j2' as tx}"
SMALL_PRIMES = [p for p in first_primes(25) if p >= 11]  # 11 .. 97
EXPS = [3, 5, 7, 11, 13, 17]

# Binary exponentiation trace (rows of steps.binary_pow_steps), as a narrow array.
POWTAB = (r"\BLOCK{macro powtab(st)}\begin{array}{c|r|r|r}"
          r"\text{бит} & r^2 & r & e \\ \hline "
          r"\BLOCK{for s in st}\VAR{s.bit} & \VAR{s.sq} & \VAR{s.r} & \VAR{s.e} \\ \BLOCK{endfor}"
          r"\end{array}\BLOCK{endmacro}")


class RSAToy(Task):
    id = "crypto.rsa_toy"
    title_ru = "RSA: генерация ключей, шифрование и расшифрование"
    topics = ("crypto.rsa",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Corner cases: gcd(e, phi) > 1 (the next valid e is taken), gcd(m, N) > 1 "
             "(decryption still works, and gcd(c, N) reveals a factor). Presets force each case.")
    presets = {
        "default": {"primes": SMALL_PRIMES, "exps": EXPS, "bad_e_ratio": 0.3,
                    "shared_msg_ratio": 0.2},
        "plain": {"bad_e_ratio": 0.0, "shared_msg_ratio": 0.0},
        "bad_e": {"bad_e_ratio": 1.0, "shared_msg_ratio": 0.0},
        "msg_not_coprime": {"bad_e_ratio": 0.0, "shared_msg_ratio": 1.0},
    }
    statement = (r"Ключи RSA строятся по простым $p = \VAR{p}$, $q = \VAR{q}$ и открытой экспоненте "
                 r"$e = \VAR{e0}$ (если $\gcd(e, \varphi(N)) \ne 1$, вместо $e$ берётся наименьшее "
                 r"большее его число, взаимно простое с $\varphi(N)$). Найти $N$, $\varphi(N)$ и "
                 r"закрытый ключ $d$ (расширенным алгоритмом Евклида). Зашифровать сообщение "
                 r"$m = \VAR{m}$ бинарным алгоритмом возведения в степень и расшифровать полученный "
                 r"шифротекст с помощью китайской теоремы об остатках.")
    solution = (TX + POWTAB +
                r"$N = pq = \VAR{p} \cdot \VAR{q} = \VAR{n}$, "
                r"$\varphi(N) = (p - 1)(q - 1) = \VAR{p - 1} \cdot \VAR{q - 1} = \VAR{phi} = \VAR{phi_tex}$. "
                r"\BLOCK{if skipped}$\gcd(\VAR{e0}, \VAR{phi}) = \VAR{skipped[0].g} \ne 1$: такой показатель "
                r"недопустим (обратного к $e$ по модулю $\varphi(N)$ нет, и отображение $x \mapsto x^e$ "
                r"не биективно). Перебираем следующие числа: "
                r"\BLOCK{for s in skipped[1:]}$\gcd(\VAR{s.e}, \VAR{phi}) = \VAR{s.g}$, \BLOCK{endfor}"
                r"$\gcd(\VAR{e}, \VAR{phi}) = 1$, поэтому $e = \VAR{e}$."
                r"\BLOCK{else}$\gcd(\VAR{e}, \VAR{phi}) = 1$, показатель $e = \VAR{e}$ допустим.\BLOCK{endif}"
                r"\par Закрытый ключ $d \equiv e^{-1} \pmod{\varphi(N)}$. \VAR{tx.inverse(inv)} "
                r"Проверка: $ed = \VAR{e} \cdot \VAR{d} = \VAR{e * d} = \VAR{(e * d) // phi} \cdot \VAR{phi} + 1$."
                r"\par Шифрование: $c \equiv m^e \pmod{N}$, $e = \VAR{e} = \VAR{e|bin}_2$, все вычисления "
                r"по модулю $\VAR{n}$:"
                r"\[\VAR{powtab(enc)}\qquad c = \VAR{c}.\]"
                r"Расшифрование по КТО: $d_p = d \bmod (p - 1) = \VAR{dp}$, $d_q = d \bmod (q - 1) = \VAR{dq}$, "
                r"$c_p = c \bmod p = \VAR{cp}$, $c_q = c \bmod q = \VAR{cq}$; "
                r"$m_p = c_p^{d_p} \bmod p$, $m_q = c_q^{d_q} \bmod q$."
                r"\BLOCK{if cp == 0 or cq == 0} Если $c_p = 0$ (или $c_q = 0$), то и $m_p = 0$ ($m_q = 0$)."
                r"\BLOCK{endif}"
                r"\[\BLOCK{if cp}\VAR{powtab(dec_p)}\ \ m_p = \VAR{mp}\BLOCK{else} m_p = 0\BLOCK{endif}"
                r"\qquad \BLOCK{if cq}\VAR{powtab(dec_q)}\ \ m_q = \VAR{mq}\BLOCK{else} m_q = 0\BLOCK{endif}\]"
                r"\VAR{tx.crt(crt)}"
                r"\BLOCK{if shared}\par Здесь $\gcd(m, N) = \VAR{shared} > 1$, и всё же расшифрование "
                r"корректно: по модулю $\VAR{shared}$ обе части сравнения $c^d \equiv m$ равны нулю, а по "
                r"модулю другого простого работает теорема Ферма. Заметим, что тогда и "
                r"$\gcd(c, N) = \VAR{shared}$ раскрывает разложение $N$ (на практике вероятность "
                r"такого $m$ ничтожна).\BLOCK{endif}"
                r"\[N = \VAR{n},\ \varphi(N) = \VAR{phi},\ e = \VAR{e},\ d = \VAR{d},\ c = \VAR{c},\ "
                r"m = \VAR{m}.\]")

    def sample(self, rng):
        cfg = self.cfg
        while True:
            p, q = rng.sample(cfg.primes, 2)
            n, phi = p * q, (p - 1) * (q - 1)
            bad = rng.random() < cfg.bad_e_ratio
            cands = [e for e in cfg.exps if (gcd(e, phi) > 1) == bad]
            if cands:
                break
        e0 = rng.choice(cands)
        e, skipped = e0, []
        while gcd(e, phi) != 1:
            skipped.append({"e": e, "g": gcd(e, phi)})
            e += 1
        inv = steps.inverse_rows(e, phi)
        d = inv["inv"]
        if rng.random() < cfg.shared_msg_ratio:
            r, other = rng.choice([(p, q), (q, p)])
            m, shared = r * rng.randrange(1, other), r
        else:
            while True:
                m = rng.randrange(2, n - 1)
                if gcd(m, n) == 1:
                    break
            shared = 0
        enc = steps.binary_pow_steps(m, e, n)
        c = enc[-1]["r"]
        dp, dq, cp, cq = d % (p - 1), d % (q - 1), c % p, c % q
        dec_p = steps.binary_pow_steps(cp, dp, p) if cp else []
        dec_q = steps.binary_pow_steps(cq, dq, q) if cq else []
        mp, mq = pow(cp, dp, p), pow(cq, dq, q)
        crt = steps.crt([mp, mq], [p, q])
        return {"p": p, "q": q, "n": n, "phi": phi, "phi_tex": steps.factor_tex(phi), "e0": e0,
                "e": e, "skipped": skipped, "inv": inv, "d": d, "m": m, "shared": shared,
                "enc": enc, "c": c, "dp": dp, "dq": dq, "cp": cp, "cq": cq, "dec_p": dec_p,
                "dec_q": dec_q, "mp": mp, "mq": mq, "crt": crt,
                "answer": {"n": n, "phi": phi, "e": e, "d": d, "c": c, "m": m}}

    def check(self, p):
        a = p["answer"]
        n, phi, e, d = a["n"], a["phi"], a["e"], a["d"]
        assert p["p"] * p["q"] == n and (p["p"] - 1) * (p["q"] - 1) == phi
        # e: the least number >= e0 coprime to phi
        assert gcd(e, phi) == 1 and all(gcd(x, phi) > 1 for x in range(p["e0"], e))
        assert e * d % phi == 1 and 0 < d < phi
        assert a["c"] == pow(a["m"], e, n)
        assert pow(a["c"], d, n) == a["m"] == p["crt"]["x"]  # direct decryption, not via CRT
        assert (gcd(a["m"], n) > 1) == bool(p["shared"])


class RSAFactorFromPhi(Task):
    id = "crypto.rsa_factor_from_phi"
    title_ru = "Разложение модуля RSA по известному значению функции Эйлера"
    topics = ("crypto.rsa",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"p_lo": 100, "p_hi": 1000}}
    statement = (r"Известны модуль RSA $N = \VAR{n}$ (произведение двух различных простых) и значение "
                 r"$\varphi(N) = \VAR{phi}$. Разложить $N$ на множители.")
    solution = (r"Для $N = pq$ имеем $\varphi(N) = (p - 1)(q - 1) = N - (p + q) + 1$, поэтому "
                r"$p + q = N - \varphi(N) + 1 = \VAR{s}$, $pq = N$, т.\,е. $p$ и $q$ "
                r"--- корни квадратного уравнения \[x^2 - \VAR{s}\,x + \VAR{n} = 0.\] "
                r"Дискриминант $D = (p + q)^2 - 4pq = (q - p)^2 = \VAR{s}^2 - 4 \cdot \VAR{n} = \VAR{disc}$, "
                r"$\sqrt{D} = \VAR{root}$, "
                r"$p = \frac{\VAR{s} - \VAR{root}}{2} = \VAR{answer[0]}$, "
                r"$q = \frac{\VAR{s} + \VAR{root}}{2} = \VAR{answer[1]}$. Проверка: "
                r"$\VAR{answer[0]} \cdot \VAR{answer[1]} = \VAR{n}$."
                r"\[N = \VAR{answer[0]} \cdot \VAR{answer[1]}.\]")

    def sample(self, rng):
        primes = [x for x in range(self.cfg.p_lo, self.cfg.p_hi) if is_prime(x)]
        p, q = sorted(rng.sample(primes, 2))
        n, phi = p * q, (p - 1) * (q - 1)
        s = n - phi + 1
        disc = s * s - 4 * n
        return {"n": n, "phi": phi, "s": s, "disc": disc, "root": isqrt(disc), "answer": [p, q]}

    def check(self, p):
        a, b = p["answer"]
        assert p["root"] ** 2 == p["disc"] > 0
        assert sorted(factorize(p["n"])) == [a, b] and a < b  # trial division, independent
        assert (a - 1) * (b - 1) == p["phi"]


def factor_from_d(n: int, e: int, d: int, bases=(2, 3, 5, 7, 11, 13)) -> dict:
    """ed - 1 = 2^t r, r odd; for a = 2, 3, 5, ...: the chain a^r, a^{2r}, ... mod n up to 1;
    a nontrivial square root x of 1 (x != +-1, x^2 = 1) gives gcd(x - 1, n)."""
    k = e * d - 1
    t, r = steps.split_even(k)
    attempts = []
    for a in bases:
        g = gcd(a, n)
        if g > 1:
            attempts.append({"a": a, "chain": [], "kind": "gcd", "g": g})
            return {"k": k, "t": t, "r": r, "attempts": attempts, "factor": g}
        chain = [pow(a, r, n)]
        while chain[-1] != 1:
            chain.append(chain[-1] * chain[-1] % n)
        if len(chain) == 1:
            attempts.append({"a": a, "chain": chain, "kind": "one"})
        elif chain[-2] == n - 1:
            attempts.append({"a": a, "chain": chain, "kind": "minus"})
        else:
            g = gcd(chain[-2] - 1, n)
            attempts.append({"a": a, "chain": chain, "kind": "ok", "g": g})
            return {"k": k, "t": t, "r": r, "attempts": attempts, "factor": g}
    raise AssertionError("no base succeeded")


class RSAFactorFromD(Task):
    id = "crypto.rsa_factor_from_d"
    title_ru = "Разложение модуля RSA по открытому и закрытому ключам"
    topics = ("crypto.rsa",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "Bases a = 2, 3, 5, ... in order; failing bases (a^r = 1 or -1 in the chain) are kept."
    presets = {"default": {"primes": [p for p in first_primes(20) if p >= 11], "exps": EXPS}}
    statement = (r"Известны открытый ключ RSA $(N, e) = (\VAR{n}, \VAR{e})$ и соответствующий закрытый "
                 r"ключ $d = \VAR{d}$. Разложить $N$ на множители вероятностным алгоритмом: "
                 r"$ed - 1 = 2^t r$, $r$ нечётно; для оснований $a = 2, 3, 5, \ldots$ (по порядку) "
                 r"искать нетривиальный квадратный корень из единицы среди $a^{r}, a^{2r}, \ldots, "
                 r"a^{2^t r} \bmod N$.")
    solution = (r"$ed - 1 = \VAR{e} \cdot \VAR{d} - 1 = \VAR{fd.k} = 2^{\VAR{fd.t}} \cdot \VAR{fd.r}$, т.\,е. "
                r"$t = \VAR{fd.t}$, $r = \VAR{fd.r}$. Так как $\lambda(N) \mid ed - 1$, для $a$, взаимно "
                r"простого с $N$, $a^{2^t r} \equiv 1 \pmod{N}$. Вычисляем $x_0 = a^r \bmod N$ (бинарным "
                r"алгоритмом) и возводим в квадрат, пока не получим $1$. Если $x_0 = 1$ или перед единицей "
                r"стоит $-1 \equiv \VAR{n - 1}$, основание неудачно; иначе $x^2 \equiv 1$, $x \not\equiv "
                r"\pm 1$, т.\,е. $N \mid (x - 1)(x + 1)$, но $N$ не делит ни один множитель, и "
                r"$\gcd(x - 1, N)$ "
                r"--- нетривиальный делитель."
                r"\BLOCK{for at in fd.attempts}\par\noindent $a = \VAR{at.a}$: "
                r"\BLOCK{if at.kind == 'gcd'}$\gcd(\VAR{at.a}, N) = \VAR{at.g}$ --- делитель найден сразу."
                r"\BLOCK{else}\BLOCK{for x in at.chain}$x_{\VAR{loop.index0}} = \VAR{x}$"
                r"\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}. "
                r"\BLOCK{if at.kind == 'one'}$x_0 = 1$ --- неудача, берём следующее основание."
                r"\BLOCK{elif at.kind == 'minus'}Перед единицей стоит $-1$ --- неудача, берём следующее основание."
                r"\BLOCK{else}$x = \VAR{at.chain[-2]}$ --- нетривиальный корень из $1$: "
                r"$\gcd(\VAR{at.chain[-2]} - 1, \VAR{n}) = \VAR{at.g}$.\BLOCK{endif}\BLOCK{endif}"
                r"\BLOCK{endfor}"
                r"\par $N / \VAR{fd.factor} = \VAR{n // fd.factor}$."
                r"\[N = \VAR{answer[0]} \cdot \VAR{answer[1]} = \VAR{n}.\]")

    def sample(self, rng):
        while True:
            p, q = rng.sample(self.cfg.primes, 2)
            phi = (p - 1) * (q - 1)
            exps = [e for e in self.cfg.exps if gcd(e, phi) == 1]
            if exps:
                break
        n, e = p * q, rng.choice(exps)
        d = inverse(e, phi)
        fd = factor_from_d(n, e, d)
        return {"n": n, "e": e, "d": d, "fd": fd, "answer": sorted([p, q])}

    def check(self, p):
        a, b = p["answer"]
        n, fd = p["n"], p["fd"]
        assert a * b == n and fd["factor"] in (a, b)
        lam = (a - 1) * (b - 1) // gcd(a - 1, b - 1)
        assert (p["e"] * p["d"] - 1) % lam == 0
        assert fd["k"] == 2 ** fd["t"] * fd["r"] and fd["r"] % 2 == 1
        last = fd["attempts"][-1]
        if last["kind"] == "ok":
            x = last["chain"][-2]
            assert x * x % n == 1 and x not in (1, n - 1)
