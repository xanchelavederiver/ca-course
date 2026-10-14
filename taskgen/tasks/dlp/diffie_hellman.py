"""Toy discrete-log cryptography and generic DLP algorithms (lecture sem2/01).

Tasks: trivial DLP by listing powers, BSGS in a subgroup of known order (with
h possibly outside the subgroup), toy Diffie-Hellman and ElGamal.
Corner cases are kept on purpose: g that is not a generator (small subgroups,
the key takes few values), exponents divisible by ord(g) (A = 1, K = 1),
h not in <g> (no solution).
"""

import math

from taskgen.core import steps
from taskgen.core.nt import factorize, first_primes, inverse
from taskgen.core.task import SolutionDetail, Task
from taskgen.tasks.number_theory.order import successive_reduction

PRIMES = first_primes(80)


def _divisors(n: int) -> list[int]:
    return [d for d in range(1, n + 1) if n % d == 0]


def _order_naive(g: int, p: int) -> int:
    """Order by iteration (independent of the factorisation-based routes)."""
    x, k = g % p, 1
    while x != 1:
        x, k = x * g % p, k + 1
    return k


def _element_of_order(rng, p: int, n: int) -> int:
    """A random element of order exactly n (n | p - 1) of (Z/pZ)^*."""
    while True:
        g = pow(rng.randrange(2, p - 1), (p - 1) // n, p)
        if all(pow(g, n // q, p) != 1 for q in factorize(n)) and (n > 1 or g == 1):
            return g


def _subgroup(g: int, p: int) -> list[int]:
    """[g^0, g^1, ..., g^{n-1}], n = ord(g)."""
    out = [1]
    while True:
        y = out[-1] * g % p
        if y == 1:
            return out
        out.append(y)


def _pow(a: int, e: int, p: int) -> list[dict]:
    return steps.binary_pow_steps(a % p, e, p)


# Horizontal binary-exponentiation trace: name = base^exp with the bits of exp, r^2 and r.
POWTRACE = (r"\BLOCK{macro powtrace(name, base, exp, st)}"
            r"\[\VAR{name} = \VAR{base}^{\VAR{exp}}:\quad"
            r"\begin{array}{c|\BLOCK{for s in st}r\BLOCK{endfor}}"
            r"\text{бит}\BLOCK{for s in st} & \VAR{s.bit}\BLOCK{endfor} \\ \hline "
            r"r^2\BLOCK{for s in st} & \BLOCK{if not loop.first}\VAR{s.sq}\BLOCK{endif}\BLOCK{endfor} \\ "
            r"r\BLOCK{for s in st} & \VAR{s.r}\BLOCK{endfor}"
            r"\end{array}\qquad \VAR{name} \equiv \VAR{st[-1].r}.\]"
            r"\BLOCK{endmacro}")
BINARY_RULE = (r"Степени вычисляем бинарным алгоритмом: биты показателя слева направо, $r \gets r^2$, "
               r"при бите $1$ ещё $r \gets r \cdot (\text{основание})$; все вычисления по модулю $p = \VAR{p}$.")
ORDER_TRACE = (r"Порядок $g$ (последовательное снижение): $\ord(g) \mid p - 1 = \VAR{p - 1} = \VAR{factor}$"
               r"\BLOCK{for t in tests}; $\VAR{g}^{\VAR{t.o}/\VAR{t.q}} = \VAR{g}^{\VAR{t.exp}} \equiv \VAR{t.val}$"
               r"\BLOCK{if t.val == 1} $\Rightarrow o = \VAR{t.exp}$\BLOCK{else} $\ne 1$\BLOCK{endif}\BLOCK{endfor}"
               r". Итак, $n = \ord(g) = \VAR{n}$.")


def _chunks(xs: list, size: int) -> list[list]:
    return [xs[i:i + size] for i in range(0, len(xs), size)]


# --- trivial DLP --------------------------------------------------------------------------


class BruteForce(Task):
    id = "dlp.brute_force"
    title_ru = "Дискретный логарифм перебором"
    topics = ("dlp.generic",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("g need not be a generator; with probability ~1/4 h is outside <g> (no solution). "
             "The whole cycle g^k is listed, so all solutions x = x0 + kn are found.")
    presets = {"default": {"primes": [p for p in PRIMES if 19 <= p <= 47], "out_ratio": 0.25}}
    statement = (r"Решить задачу дискретного логарифмирования перебором, вычисляя последовательно "
                 r"$g, g^2, g^3, \dots$: \[\VAR{g}^x \equiv \VAR{h}\ (\textrm{mod}\ \VAR{p}).\] "
                 r"Найти все решения или показать, что их нет. Сколько умножений потребовалось?")
    solution = (r"Каждая следующая степень --- одно умножение на $g = \VAR{g}$ по модулю $\VAR{p}$; "
                r"идём до возврата в $1$ (тогда $k = \ord(g)$ и степени начинают повторяться):"
                r"\BLOCK{for row in rows}\[\begin{array}{c|\BLOCK{for c in row}r\BLOCK{endfor}}"
                r"k\BLOCK{for c in row} & \VAR{c.k}\BLOCK{endfor} \\ \hline "
                r"g^k\BLOCK{for c in row} & \BLOCK{if c.v == h}\mathbf{\VAR{c.v}}\BLOCK{else}\VAR{c.v}\BLOCK{endif}"
                r"\BLOCK{endfor}\end{array}\]\BLOCK{endfor}"
                r"Итак, $n = \ord(\VAR{g}) = \VAR{n}$\BLOCK{if n == p - 1} ($g$ --- первообразный корень)"
                r"\BLOCK{else}, $\langle g \rangle$ --- подгруппа индекса $\VAR{(p - 1) // n}$ в "
                r"$(\mathbb{Z}/\VAR{p}\mathbb{Z})^*$\BLOCK{endif}. "
                r"\BLOCK{if x0 is not none}Значение $\VAR{h}$ впервые встретилось при $k = \VAR{x0}$ "
                r"(после $\VAR{x0 - 1}$ умножений, если остановиться сразу). Так как $g^x = g^y \iff "
                r"x \equiv y \pmod{n}$, все решения: \[x \equiv \VAR{x0}\ (\textrm{mod}\ \VAR{n}).\]"
                r"\BLOCK{else}Число $\VAR{h}$ в списке $\langle g \rangle$ не встретилось, а дальше степени "
                r"повторяются ($g^{k + \VAR{n}} = g^k$); значит, $h \notin \langle g \rangle$ "
                r"(понадобилось $\VAR{n - 1}$ умножений). Проверка: элементы $\langle g \rangle$ --- в точности "
                r"решения $y^{\VAR{n}} = 1$, а $\VAR{h}^{\VAR{n}} \equiv \VAR{hn} \ne 1$. "
                r"\[\text{Решений нет.}\]\BLOCK{endif}")

    def sample(self, rng):
        out = rng.random() < self.cfg.out_ratio
        while True:
            p = rng.choice(self.cfg.primes)
            g = rng.randrange(2, p - 1)
            sub = _subgroup(g, p)
            n = len(sub)
            if n < 4:
                continue
            if out:
                if n == p - 1:
                    continue
                h = rng.choice([y for y in range(2, p) if y not in sub])
                x0 = None
            else:
                x0 = rng.randrange(2, n)
                h = sub[x0]
            cells = [{"k": k, "v": sub[k % n]} for k in range(1, n + 1)]
            return {"g": g, "h": h, "p": p, "n": n, "rows": _chunks(cells, 12), "x0": x0,
                    "hn": pow(h, n, p), "answer": x0 if x0 is not None else "нет решений"}

    def check(self, p):
        n = _order_naive(p["g"], p["p"])
        assert n == p["n"]
        if p["x0"] is None:
            assert all(pow(p["g"], k, p["p"]) != p["h"] for k in range(p["p"] - 1))
            assert p["hn"] != 1
        else:
            assert pow(p["g"], p["x0"], p["p"]) == p["h"]
            assert all(pow(p["g"], k, p["p"]) != p["h"] for k in range(p["x0"]))


# --- BSGS in a subgroup of known order ------------------------------------------------------


def bsgs_order(g: int, h: int, p: int, n: int) -> dict:
    """Shanks with m = ceil(sqrt(n)), n = ord(g): baby steps g^j, giant steps h * g^{-im}."""
    m = math.isqrt(n - 1) + 1
    baby = [pow(g, j, p) for j in range(m)]
    g_inv = inverse(g, p)
    gm = pow(g_inv, m, p)
    giant, hit = [], None
    y = h % p
    for i in range(m):
        giant.append(y)
        if y in baby:
            hit = (i, baby.index(y))
            break
        y = y * gm % p
    res = {"m": m, "baby": baby, "g_inv": g_inv, "gm": gm, "giant": giant}
    if hit:
        res.update(i=hit[0], j=hit[1], x=hit[0] * m + hit[1])
    else:
        res.update(i=None, j=None, x=None)
    return res


class ShanksSubgroup(Task):
    id = "dlp.shanks_subgroup"
    title_ru = "Алгоритм Шенкса в подгруппе известного порядка"
    topics = ("dlp.generic",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("ord(g) = n is a proper divisor of p - 1 (lists of length ceil(sqrt n) instead of "
             "ceil(sqrt(p - 1))); n may be prime; with probability ~1/4 h is not in <g>.")
    presets = {"default": {"primes": [p for p in PRIMES if 100 <= p <= 400], "n_lo": 12, "n_hi": 110,
                           "out_ratio": 0.25}}
    statement = (r"Известно, что $\ord(\VAR{g}) = \VAR{n}$ в $(\mathbb{Z}/\VAR{p}\mathbb{Z})^*$. "
                 r"Решить методом Шенкса \[\VAR{g}^x \equiv \VAR{h}\ (\textrm{mod}\ \VAR{p})\] "
                 r"(или показать, что решений нет), выбрав длину списков по порядку $g$, а не по $p - 1$.")
    solution = (r"Решение ищем среди $0 \le x < n = \VAR{n}$; $m = \lceil\sqrt{\VAR{n}}\rceil = \VAR{s.m}$ "
                r"(вместо $\lceil\sqrt{\VAR{p - 1}}\rceil = \VAR{m_full}$), так как каждое $x < n \le m^2$ "
                r"записывается как $x = im + j$, $0 \le i, j < m$. Малые шаги $g^j$:"
                r"\[\begin{array}{c|\BLOCK{for _ in s.baby}r\BLOCK{endfor}}"
                r"j\BLOCK{for x in s.baby} & \VAR{loop.index0}\BLOCK{endfor} \\ \hline "
                r"g^j\BLOCK{for x in s.baby} & \VAR{x}\BLOCK{endfor}\end{array}\]"
                r"$g^{-1} \equiv \VAR{s.g_inv}$, $g^{-m} \equiv \VAR{s.g_inv}^{\VAR{s.m}} \equiv \VAR{s.gm}$. "
                r"Большие шаги $y_i = h \cdot g^{-im}$ ($y_{i+1} = y_i \cdot \VAR{s.gm}$)"
                r"\BLOCK{if s.x is not none} до совпадения\BLOCK{endif}:"
                r"\[\begin{array}{c|\BLOCK{for _ in s.giant}r\BLOCK{endfor}}"
                r"i\BLOCK{for x in s.giant} & \VAR{loop.index0}\BLOCK{endfor} \\ \hline "
                r"y_i\BLOCK{for x in s.giant} & \VAR{x}\BLOCK{endfor}\end{array}\]"
                r"\BLOCK{if s.x is not none}Совпадение $y_{\VAR{s.i}} = g^{\VAR{s.j}}$, откуда "
                r"$x = \VAR{s.i} \cdot \VAR{s.m} + \VAR{s.j} = \VAR{s.x}$. Проверка: "
                r"$\VAR{g}^{\VAR{s.x}} \equiv \VAR{h}$.\[x \equiv \VAR{answer}\ (\textrm{mod}\ \VAR{n}).\]"
                r"\BLOCK{else}Все $m$ больших шагов сделаны, совпадений нет. Если бы $h = g^x$, $0 \le x < n$, "
                r"то при $x = im + j$ было бы $y_i = g^j$; значит, $h \notin \langle g \rangle$. "
                r"Независимая проверка: $\langle g \rangle$ --- единственная подгруппа порядка $n$ "
                r"циклической группы $(\mathbb{Z}/\VAR{p}\mathbb{Z})^*$, она состоит из решений "
                r"$y^{n} = 1$, а $\VAR{h}^{\VAR{n}} \equiv \VAR{hn} \ne 1$.\[\text{Решений нет.}\]\BLOCK{endif}")

    def sample(self, rng):
        out = rng.random() < self.cfg.out_ratio
        while True:
            p = rng.choice(self.cfg.primes)
            ns = [d for d in _divisors(p - 1) if self.cfg.n_lo <= d <= min(self.cfg.n_hi, (p - 1) // 2)]
            if not ns:
                continue
            n = rng.choice(ns)
            g = _element_of_order(rng, p, n)
            if out:
                h = rng.randrange(2, p - 1)
                if pow(h, n, p) == 1:
                    continue
            else:
                m = math.isqrt(n - 1) + 1
                x = rng.randrange(m, n)  # at least one giant step
                h = pow(g, x, p)
            if h == g:
                continue
            s = bsgs_order(g, h, p, n)
            return {"g": g, "h": h, "p": p, "n": n, "m_full": math.isqrt(p - 2) + 1, "s": s,
                    "hn": pow(h, n, p), "answer": s["x"] if s["x"] is not None else "нет решений"}

    def check(self, p):
        g, h, P, n = p["g"], p["h"], p["p"], p["n"]
        assert _order_naive(g, P) == n < P - 1
        logs = [k for k in range(n) if pow(g, k, P) == h]
        if p["s"]["x"] is None:
            assert not logs and p["hn"] != 1
        else:
            assert logs == [p["s"]["x"]] and p["answer"] == logs[0]
        assert p["s"]["m"] ** 2 >= n > (p["s"]["m"] - 1) ** 2


# --- Diffie-Hellman -------------------------------------------------------------------------


def _sample_group(rng, primes, mode):
    """(p, g, n) for a DH/ElGamal instance of the given mode."""
    while True:
        p = rng.choice(primes)
        divs = _divisors(p - 1)
        if mode == "generator":
            n = p - 1
        elif mode == "prime_order":
            qs = [q for q in factorize(p - 1) if 11 <= q < p - 1]
            if not qs:
                continue
            n = rng.choice(qs)
        elif mode == "small":
            ns = [d for d in divs if 3 <= d <= 12 and d < (p - 1) // 2]
            if not ns:
                continue
            n = rng.choice(ns)
        else:  # degenerate: some exponent is a multiple of n
            ns = [d for d in divs if 3 <= d <= (p - 1) // 3]
            if not ns:
                continue
            n = rng.choice(ns)
        return p, _element_of_order(rng, p, n), n


def _pick_mode(rng, weights: dict) -> str:
    r, acc = rng.random() * sum(weights.values()), 0.0
    for mode, w in sorted(weights.items()):
        acc += w
        if r < acc:
            return mode
    return sorted(weights)[-1]


DH_MODES = {"generator": 0.35, "prime_order": 0.25, "small": 0.25, "degenerate": 0.15}
DH_PRIMES = [p for p in PRIMES if 53 <= p <= 251]


class DiffieHellman(Task):
    id = "dlp.diffie_hellman"
    title_ru = "Протокол Диффи--Хеллмана (игрушечный пример)"
    topics = ("dlp.generic",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Modes: g a primitive root; g of prime order q | p - 1; g of small order (<= 12, the key "
             "takes few values, Eve lists <g>); a or b divisible by ord(g) (A = 1 or B = 1, K = 1). "
             "Preset small_subgroup: only the last two (corner cases).")
    presets = {"default": {"primes": DH_PRIMES, "modes": DH_MODES},
               "small_subgroup": {"modes": {"small": 0.6, "degenerate": 0.4}}}
    statement = (r"Алиса и Боб согласуют ключ по протоколу Диффи--Хеллмана с открытыми параметрами "
                 r"$p = \VAR{p}$, $g = \VAR{g}$. Секретный показатель Алисы $a = \VAR{a}$, Боба "
                 r"$b = \VAR{b}$. \par (а) Бинарным алгоритмом вычислить открытые ключи $A$, $B$ и общий "
                 r"ключ $K$ --- отдельно на стороне Алисы и на стороне Боба. \par (б) Найти $\ord(g)$. "
                 r"Сколько различных значений может принимать общий ключ при этих $p$, $g$? Что знает Ева "
                 r"и как она может найти $K$?")
    solution = (POWTRACE + BINARY_RULE +
                r"\VAR{powtrace('A', g, a, sa)}\VAR{powtrace('B', g, b, sb)}"
                r"Алиса получает $B$ и вычисляет $K_A = B^a$, Боб получает $A$ и вычисляет $K_B = A^b$:"
                r"\VAR{powtrace('K_A', B, a, ka)}\VAR{powtrace('K_B', A, b, kb)}"
                r"$K_A = K_B = g^{ab} = \VAR{K}$."
                r"\par (б) " + ORDER_TRACE +
                r" Ключ $K = g^{ab}$ лежит в $\langle g \rangle$, поэтому он принимает не более "
                r"$\VAR{n}$ значений\BLOCK{if n <= 12}: $\langle g \rangle = \{\VAR{sub|join(', ')}\}$ "
                r"($g^0, g^1, \dots, g^{\VAR{n - 1}}$)\BLOCK{endif}. "
                r"\BLOCK{if mode == 'generator'}$g$ --- первообразный корень, $K$ может быть любым элементом "
                r"$(\mathbb{Z}/\VAR{p}\mathbb{Z})^*$."
                r"\BLOCK{elif mode == 'prime_order'}$\langle g \rangle$ --- подгруппа простого порядка "
                r"$q = \VAR{n}$; так и выбирают параметры на практике (но $q$ должно быть огромным, "
                r"$q \approx 2^{256}$), а $A, B$ проверяют условием $A^q = 1$."
                r"\BLOCK{elif mode == 'small'}Подгруппа мала: ключ принимает лишь $\VAR{n}$ значений "
                r"--- параметры никуда не годятся."
                r"\BLOCK{else}Вырожденный случай: $\VAR{zname} = \VAR{zval} = \VAR{zval // n} \cdot \VAR{n} "
                r"\equiv 0 \pmod{\ord g}$, поэтому $\VAR{zname|upper} = g^{\VAR{zname}} = 1$ и $K = 1$ "
                r"при любом показателе второй стороны: Ева видит $\VAR{zname|upper} = 1$ и сразу знает ключ. "
                r"Показатели нужно выбирать из $[1, \ord(g) - 1]$.\BLOCK{endif}"
                r"\par Ева видит $p, g, A = \VAR{A}, B = \VAR{B}$ (но не $a, b$). Ей достаточно найти "
                r"$a' = \log_g A$ (это $a \bmod n = \VAR{a % n}$): тогда $K = B^{a'}$. "
                r"\BLOCK{if n <= 12}Здесь это делается перебором списка $\langle g \rangle$ выше: "
                r"$A = \VAR{A} = g^{\VAR{a % n}}$, $K = \VAR{B}^{\VAR{a % n}} \equiv \VAR{K}$."
                r"\BLOCK{else}Перебором --- до $n - 1 = \VAR{n - 1}$ умножений, методом Шенкса --- около "
                r"$2\lceil\sqrt{n}\,\rceil = \VAR{2 * m}$ операций; для настоящих $n \approx 2^{256}$ "
                r"это недостижимо.\BLOCK{endif}"
                r"\[A = \VAR{A},\quad B = \VAR{B},\quad K = \VAR{K}.\]")

    def sample(self, rng):
        mode = _pick_mode(rng, self.cfg.modes)
        while True:
            p, g, n = _sample_group(rng, self.cfg.primes, mode)
            if mode == "degenerate":
                z = n * rng.randrange(1, (p - 2) // n + 1)
                other = rng.randrange(2, p - 1)
                if other % n == 0 or z > p - 2:
                    continue
                if rng.random() < 0.5:
                    a, b, zname = z, other, "a"
                else:
                    a, b, zname = other, z, "b"
            else:
                a, b = rng.randrange(2, p - 1), rng.randrange(2, p - 1)
                if a % n == 0 or b % n == 0 or a == b:
                    continue
                zname = None
            A, B = pow(g, a, p), pow(g, b, p)
            if mode != "degenerate" and A == B:
                continue  # keep the toy exchange non-trivial (a, b are nonzero mod n here)
            K = pow(B, a, p)
            return {"mode": mode, "p": p, "g": g, "a": a, "b": b, "A": A, "B": B, "K": K, "n": n,
                    "m": math.isqrt(n - 1) + 1, "sub": _subgroup(g, p) if n <= 12 else [],
                    "zname": zname, "zval": a if zname == "a" else b,
                    "sa": _pow(g, a, p), "sb": _pow(g, b, p), "ka": _pow(B, a, p), "kb": _pow(A, b, p),
                    "factor": steps.factor_tex(p - 1), "tests": successive_reduction(g, p),
                    "answer": {"A": A, "B": B, "K": K}}

    def check(self, p):
        P, g, a, b = p["p"], p["g"], p["a"], p["b"]
        assert p["A"] == pow(g, a, P) and p["B"] == pow(g, b, P)
        assert p["K"] == pow(g, a * b % (P - 1), P)
        assert p["ka"][-1]["r"] == p["kb"][-1]["r"] == p["K"]
        assert p["sa"][-1]["r"] == p["A"] and p["sb"][-1]["r"] == p["B"]
        assert _order_naive(g, P) == p["n"]
        assert pow(p["B"], a % p["n"], P) == p["K"]
        if p["mode"] == "degenerate":
            assert p["K"] == 1 and p["zval"] % p["n"] == 0
        else:
            assert a % p["n"] and b % p["n"]


# --- ElGamal --------------------------------------------------------------------------------


EG_MODES = {"generator": 0.6, "small": 0.2, "degenerate": 0.2}


class ElGamal(Task):
    id = "dlp.elgamal"
    title_ru = "Шифрование Эль-Гамаля (игрушечный пример)"
    topics = ("dlp.generic",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Modes: g a primitive root; g of small order (the mask A^k takes few values); "
             "degenerate: a or k divisible by ord(g), so the mask is 1 and c2 = m.")
    presets = {"default": {"primes": DH_PRIMES, "modes": EG_MODES}}
    statement = (r"Открытые параметры системы Эль-Гамаля: $p = \VAR{p}$, $g = \VAR{g}$; секретный ключ "
                 r"Алисы $a = \VAR{a}$. Боб шифрует для Алисы сообщение $m = \VAR{msg}$ со случайным "
                 r"(одноразовым) показателем $k = \VAR{k}$. \par (а) Найти открытый ключ Алисы $A$ и "
                 r"шифртекст $(c_1, c_2)$. \par (б) Расшифровать $(c_1, c_2)$ так, как это делает Алиса: "
                 r"обратный элемент найти расширенным алгоритмом Евклида и проверить по малой теореме Ферма.")
    solution = (r"\BLOCK{import 'macros.tex.j2' as tx}" + POWTRACE + BINARY_RULE +
                r"\par (а) $A = g^a$, $c_1 = g^k$, $c_2 = m \cdot A^k$:"
                r"\VAR{powtrace('A', g, a, sa)}\VAR{powtrace('c_1', g, k, sc1)}"
                r"\VAR{powtrace('s', A, k, ss)}"
                r"$c_2 = m s = \VAR{msg} \cdot \VAR{s} = \VAR{msg * s} \equiv \VAR{c2}$. "
                r"Шифртекст $(c_1, c_2) = (\VAR{c1}, \VAR{c2})$."
                r"\par (б) Алиса знает $a$ и вычисляет маску $s = c_1^a = g^{ka} = A^k$:"
                r"\VAR{powtrace('s', c1, a, sd)}"
                r"\BLOCK{if s == 1}Маска $s = 1$, поэтому $s^{-1} = 1$ и $m = c_2 = \VAR{c2}$: "
                r"\BLOCK{if zname == 'k'}показатель $k = \VAR{k}$ кратен $\ord(g) = \VAR{n}$, $c_1 = 1$"
                r"\BLOCK{else}секретный ключ $a = \VAR{a}$ кратен $\ord(g) = \VAR{n}$, $A = 1$\BLOCK{endif}, "
                r"и шифртекст содержит сообщение в открытом виде --- такие показатели выбирать нельзя."
                r"\BLOCK{else}\VAR{tx.inverse(inv)}"
                r"Проверка по малой теореме Ферма: $s^{-1} = c_1^{-a} = c_1^{p - 1 - a} = "
                r"\VAR{c1}^{\VAR{p - 1 - a}} \equiv \VAR{fermat}$. "
                r"Тогда $m = c_2 s^{-1} = \VAR{c2} \cdot \VAR{inv.inv} = \VAR{c2 * inv.inv} \equiv \VAR{msg}$."
                r"\BLOCK{endif}"
                r"\par $\ord(g) = \VAR{n}$\BLOCK{if n == p - 1} ($g$ --- первообразный корень): маска "
                r"$s = A^k$ пробегает всю группу $(\mathbb{Z}/\VAR{p}\mathbb{Z})^*$."
                r"\BLOCK{else}: маска $s \in \langle g \rangle$ принимает лишь $\VAR{n}$ значений"
                r"\BLOCK{if n <= 12} ($\langle g \rangle = \{\VAR{sub|join(', ')}\}$)\BLOCK{endif}, "
                r"и Ева, перебрав их, получит не более $\VAR{n}$ кандидатов $c_2 s^{-1}$ на роль $m$."
                r"\BLOCK{endif}"
                r"\[A = \VAR{A},\quad (c_1, c_2) = (\VAR{c1}, \VAR{c2}),\quad m = \VAR{msg}.\]")

    def sample(self, rng):
        mode = _pick_mode(rng, self.cfg.modes)
        while True:
            p, g, n = _sample_group(rng, self.cfg.primes, mode)
            msg = rng.randrange(2, p - 1)
            zname = None
            if mode == "degenerate":
                z = n * rng.randrange(1, (p - 2) // n + 1)
                other = rng.randrange(2, p - 1)
                if z > p - 2 or other % n == 0:
                    continue
                zname = rng.choice(["a", "k"])
                a, k = (z, other) if zname == "a" else (other, z)
            else:
                a, k = rng.randrange(2, p - 1), rng.randrange(2, p - 1)
                if a % n == 0 or k % n == 0:
                    continue
            A, c1 = pow(g, a, p), pow(g, k, p)
            s = pow(A, k, p)
            if mode != "degenerate" and s == 1:
                continue
            c2 = msg * s % p
            return {"mode": mode, "p": p, "g": g, "n": n, "a": a, "k": k, "msg": msg, "A": A,
                    "c1": c1, "c2": c2, "s": s, "zname": zname,
                    "sa": _pow(g, a, p), "sc1": _pow(g, k, p), "ss": _pow(A, k, p), "sd": _pow(c1, a, p),
                    "inv": steps.inverse_rows(s, p) if s != 1 else None,
                    "fermat": pow(c1, p - 1 - a, p), "sub": _subgroup(g, p) if n <= 12 else [],
                    "answer": {"A": A, "c1": c1, "c2": c2, "m": msg}}

    def check(self, p):
        P = p["p"]
        assert p["A"] == pow(p["g"], p["a"], P) and p["c1"] == pow(p["g"], p["k"], P)
        assert p["c2"] == p["msg"] * pow(p["A"], p["k"], P) % P
        # decryption by Fermat's little theorem, independent of the xgcd route
        assert p["c2"] * pow(p["c1"], P - 1 - p["a"], P) % P == p["msg"]
        assert p["sd"][-1]["r"] == p["s"] == p["ss"][-1]["r"]
        if p["inv"] is not None:
            assert p["inv"]["inv"] * p["s"] % P == 1 == p["fermat"] * p["s"] % P
        assert _order_naive(p["g"], P) == p["n"]
        assert (p["s"] == 1) == (p["mode"] == "degenerate")
