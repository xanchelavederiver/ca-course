"""Building blocks of the index calculus (lecture sem2/04): collecting relations, solving the
linear system modulo p - 1 (prime powers + CRT, non-invertible pivots, systems that are
singular modulo a prime factor of p - 1) and the individual logarithm (phase 2).

The full algorithm is ``dlp.index_calculus`` (dlp_mod_p.py). Here g is always a primitive
root modulo p. Presets ``signed`` use absolute least residues |r| < p/2 and the factor base
{-1, 2, 3, ...}: log_g(-1) = (p - 1)/2 (corner case of the factor base).
"""

import math

from taskgen.core.nt import factorize, first_primes, inverse, is_order
from taskgen.core.task import SolutionDetail, Task

PRIMES = first_primes(70)
SMALL = list(PRIMES[18:32])  # 67 .. 131, as dlp.index_calculus (73 .. 113) plus a margin
MEDIUM = list(PRIMES[25:67])  # 101 .. 331


# --- helpers -------------------------------------------------------------------------------


def primitive_roots(p: int) -> list[int]:
    return [g for g in range(2, p - 1) if is_order(g, p - 1, p)]


def lift(v: int, p: int, signed: bool) -> int:
    """v mod p as an absolute least residue (|r| < p/2) when signed."""
    v %= p
    return v - p if signed and v > p // 2 else v


def fb_exponents(v: int, fb: list[int]) -> list[int] | None:
    """Exponent vector of v over the factor base fb (fb may start with -1), None if v is
    not fb-smooth."""
    ex = []
    for q in fb:
        if q == -1:
            ex.append(1 if v < 0 else 0)
            v = abs(v)
            continue
        e = 0
        while v % q == 0:
            v //= q
            e += 1
        ex.append(e)
    return ex if v == 1 else None


def mono_tex(ex: list[int], fb: list[int]) -> str:
    """'-2^{3} \\cdot 5' for the exponent vector ex over fb."""
    neg = any(q == -1 and e % 2 for q, e in zip(fb, ex))
    body = r" \cdot ".join(f"{q}^{{{e}}}" if e > 1 else str(q) for e, q in zip(ex, fb) if e and q != -1)
    if neg:
        return "-" + (body or "1")
    return body or "1"


def lin_tex(ex: list[int], fb: list[int]) -> str:
    """'L_{-1} + 3L_{5}' for the exponent vector ex over fb."""
    terms = [f"{e if e > 1 else ''}L_{{{q}}}" for e, q in zip(ex, fb) if e]
    return " + ".join(terms) or "0"


def factor_signed_tex(v: int) -> str:
    """Full factorisation of a nonzero integer (sign included), e.g. '-2 \\cdot 31'."""
    if abs(v) == 1:
        return str(v)
    body = r" \cdot ".join(f"{q}^{{{e}}}" if e > 1 else str(q) for q, e in sorted(factorize(abs(v)).items()))
    return ("-" if v < 0 else "") + body


def factor_base(B: int, signed: bool) -> list[int]:
    return ([-1] if signed else []) + [q for q in PRIMES if q <= B]


def dlog(g: int, h: int, p: int) -> int:
    """Brute-force discrete logarithm (independent route for checks)."""
    x, y = 0, 1
    while y != h % p:
        y = y * g % p
        x += 1
        assert x < p, "no logarithm"
    return x


def int_det(A: list[list[int]]) -> int:
    """Determinant over Z by Laplace expansion (the matrices here are at most 4 x 4)."""
    if len(A) == 1:
        return A[0][0]
    return sum((-1) ** j * A[0][j] * int_det([row[:j] + row[j + 1:] for row in A[1:]])
               for j in range(len(A)) if A[0][j])


def rank_mod_prime(A: list[list[int]], q: int) -> int:
    M = [[x % q for x in row] for row in A]
    r = 0
    for col in range(len(M[0]) if M else 0):
        piv = next((i for i in range(r, len(M)) if M[i][col]), None)
        if piv is None:
            continue
        M[r], M[piv] = M[piv], M[r]
        inv = pow(M[r][col], -1, q)
        M[r] = [x * inv % q for x in M[r]]
        for i in range(len(M)):
            if i != r and M[i][col]:
                f = M[i][col]
                M[i] = [(x - f * y) % q for x, y in zip(M[i], M[r])]
        r += 1
    return r


def eliminate(rows: list[list[int]], n_vars: int, q: int, mod: int) -> dict | None:
    """Gauss-Jordan elimination of the augmented matrix ``rows`` modulo mod = q^e with unit
    pivots (coefficient not divisible by q, preferring +-1, then small ones). Returns the snapshots after each
    pivot step and the solution, or None if some column has no unit pivot."""
    A = [[x % mod for x in row] for row in rows]
    snaps = [{"col": None, "M": [r[:] for r in A]}]
    r = 0
    for col in range(n_vars):
        cand = [i for i in range(r, len(A)) if A[i][col] % q]
        if not cand:
            return None
        piv = min(cand, key=lambda i: (min(A[i][col], mod - A[i][col]), A[i][col] != 1, i))
        c = A[piv][col]
        A[r], A[piv] = A[piv], A[r]
        inv = inverse(c, mod) if mod > 1 else 0
        A[r] = [x * inv % mod for x in A[r]]
        for i in range(len(A)):
            if i != r and A[i][col]:
                f = A[i][col]
                A[i] = [(x - f * y) % mod for x, y in zip(A[i], A[r])]
        snaps.append({"col": col, "c": c, "inv": inv, "row": piv + 1, "M": [x[:] for x in A]})
        r += 1
    return {"snaps": snaps, "sol": [A[i][n_vars] for i in range(n_vars)]}


def crt_pair_list(residues: list[int], moduli: list[int]) -> int:
    M = math.prod(moduli)
    return sum(r * (M // m) * pow(M // m, -1, m) for r, m in zip(residues, moduli) if m > 1) % M


def chunks(xs: list, k: int) -> list[list]:
    return [xs[i:i + k] for i in range(0, len(xs), k)]


MATRIX = (r"\left(\begin{array}{\BLOCK{for _ in fb}r\BLOCK{endfor}|r}"
          r"\BLOCK{for row in s.M}\VAR{row[:-1]|join(' & ')} & \VAR{row[-1]} \\ \BLOCK{endfor}"
          r"\end{array}\right)")

# --- tasks ---------------------------------------------------------------------------------


class IcRelations(Task):
    id = "dlp.ic_relations"
    title_ru = "Исчисление индексов: сбор соотношений"
    topics = ("dlp.index_calculus",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("Warm-up: g^k mod p for k = 1..count, B-smoothness, relations for L_l = log_g l. "
             "Preset `signed`: absolute least residues, factor base {-1, 2, 3, ...}, L_{-1} = (p-1)/2.")
    presets = {"default": {"primes": SMALL, "bounds": [5, 7], "count": 8, "min_smooth": 3, "signed": False},
               "signed": {"signed": True, "bounds": [5]}}
    statement = (r"Пусть $p = \VAR{p}$, $g = \VAR{g}$ "
                 r"--- первообразный корень по модулю $p$, $B = \VAR{B}$, факторная база "
                 r"$F = \{\VAR{fb|join(', ')}\}$. Вычислить $g^k \bmod p$ для $k = 1, \dots, \VAR{count}$"
                 r"\BLOCK{if signed} (в абсолютно наименьших вычетах $r$, $|r| < p/2$)\BLOCK{endif}, "
                 r"определить, какие из полученных чисел раскладываются над $F$, и выписать соответствующие "
                 r"соотношения для $L_\ell = \log_g \ell$ по модулю $p - 1$."
                 r"\BLOCK{if signed} Чему равен $L_{-1}$?\BLOCK{endif}")
    solution = (r"Число $B$-гладкое, если все его простые делители не превосходят $B = \VAR{B}$. "
                r"Каждое следующее значение получаем умножением предыдущего на $g = \VAR{g}$ по модулю $\VAR{p}$:"
                r"\[\begin{array}{r|r\BLOCK{if signed}|r\BLOCK{endif}|l|c}"
                r"k & g^k \bmod p\BLOCK{if signed} & r\BLOCK{endif} & \text{разложение} & \text{гладкое?} \\ \hline "
                r"\BLOCK{for t in rows}\VAR{t.k} & \VAR{t.v}\BLOCK{if signed} & \VAR{t.r}\BLOCK{endif} & "
                r"\VAR{t.fact} & \BLOCK{if t.ex}+\BLOCK{else}-\BLOCK{endif} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"\BLOCK{if signed}Логарифм $-1$ известен заранее: $g^{(p-1)/2} \equiv -1$ (единственный "
                r"элемент порядка $2$ в циклической группе $\mathbb{Z}_p^*$, а $g$ --- первообразный корень), "
                r"поэтому $L_{-1} = (p - 1)/2 = \VAR{half}$. \BLOCK{endif}"
                r"Из гладких значений $g^k \equiv \prod_\ell \ell^{e_\ell}$ получаем $k \equiv \sum_\ell e_\ell L_\ell "
                r"\pmod{p - 1}$:"
                r"\[\begin{array}{rcl}"
                r"\BLOCK{for t in rows if t.ex}g^{\VAR{t.k}} \equiv \VAR{t.mono} & \Rightarrow & "
                r"\VAR{t.lin} \equiv \VAR{t.k} \\ \BLOCK{endfor}"
                r"\end{array}\pmod{\VAR{n}}\]"
                r"Соотношений \VAR{answer|length}, неизвестных \VAR{unknowns}\BLOCK{if signed} "
                r"(кроме известного $L_{-1}$)\BLOCK{endif}."
                r"\BLOCK{if answer|length < unknowns} Соотношений меньше, чем неизвестных: нужно продолжить "
                r"перебор $k$.\BLOCK{else} Однозначно ли они определяют $L_\ell$, выясняется при решении системы "
                r"по модулю каждого примарного делителя $p - 1 = \VAR{n_factor}$.\BLOCK{endif}"
                r"\[k \in \{\VAR{answer|join(', ')}\}.\]")

    def sample(self, rng):
        signed = self.cfg.signed
        while True:
            p = rng.choice(self.cfg.primes)
            g = rng.choice(primitive_roots(p))
            B = rng.choice(self.cfg.bounds)
            fb = factor_base(B, signed)
            rows = []
            for k in range(1, self.cfg.count + 1):
                v = pow(g, k, p)
                r = lift(v, p, signed)
                ex = fb_exponents(r, fb)
                rows.append({"k": k, "v": v, "r": r, "fact": factor_signed_tex(r), "ex": ex,
                             "mono": mono_tex(ex, fb) if ex else "", "lin": lin_tex(ex, fb) if ex else ""})
            smooth = [t["k"] for t in rows if t["ex"]]
            if len(smooth) >= self.cfg.min_smooth and (not signed or any(t["ex"] and t["r"] < 0 for t in rows)):
                n = p - 1
                return {"p": p, "g": g, "B": B, "fb": fb, "signed": signed, "count": self.cfg.count,
                        "rows": rows, "n": n, "n_factor": " \\cdot ".join(
                            f"{q}^{{{e}}}" if e > 1 else str(q) for q, e in sorted(factorize(n).items())),
                        "half": n // 2, "unknowns": len([q for q in fb if q != -1]), "answer": smooth}

    def check(self, p):
        P, g, B = p["p"], p["g"], p["B"]
        assert is_order(g, P - 1, P)
        expect = []
        for t in p["rows"]:
            assert pow(g, t["k"], P) == t["v"]
            r = t["r"]
            assert r % P == t["v"] and (abs(r) < P / 2 if p["signed"] else r == t["v"])
            is_smooth = abs(r) == 1 or max(factorize(abs(r))) <= B  # independent: largest prime factor
            assert bool(t["ex"]) == is_smooth
            if t["ex"]:
                expect.append(t["k"])
                assert math.prod(q ** e for q, e in zip(p["fb"], t["ex"])) == r
                # the relation holds for the true logarithms
                logs = [(P - 1) // 2 if q == -1 else dlog(g, q, P) for q in p["fb"]]
                assert sum(e * lg for e, lg in zip(t["ex"], logs)) % (P - 1) == t["k"] % (P - 1)
        assert expect == p["answer"]
        if p["signed"]:
            assert pow(g, (P - 1) // 2, P) == P - 1


class IcIndividualLog(Task):
    id = "dlp.ic_individual_log"
    title_ru = "Исчисление индексов: логарифм элемента (второй этап)"
    topics = ("dlp.index_calculus",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("Phase 2 only: the logs of the factor base are given; find s with h*g^s smooth. "
             "s = 0 (h itself smooth) is kept with probability `trivial_ratio`. Preset `signed`: "
             "factor base {-1, 2, 3, 5, ...}, L_{-1} = (p-1)/2 is NOT given, and the smooth value "
             "found is negative.")
    presets = {"default": {"primes": MEDIUM, "bounds": [7, 11], "signed": False, "trivial_ratio": 0.15},
               "signed": {"signed": True, "bounds": [5, 7]}}
    statement = (r"Пусть $p = \VAR{p}$, $g = \VAR{g}$ --- первообразный корень по модулю $p$, факторная база "
                 r"$F = \{\VAR{fb|join(', ')}\}$\BLOCK{if signed} (вычеты берутся абсолютно наименьшими, "
                 r"$|r| < p/2$)\BLOCK{endif}, и первый этап метода исчисления индексов уже дал логарифмы "
                 r"\BLOCK{for l in given}$L_{\VAR{l.q}} = \log_g \VAR{l.q} = \VAR{l.L}$\BLOCK{if not loop.last}, "
                 r"\BLOCK{endif}\BLOCK{endfor}. Найти $x = \log_g \VAR{h}$, т.\,е. решить "
                 r"\[\VAR{g}^x \equiv \VAR{h}\ (\textrm{mod}\ \VAR{p}).\]")
    solution = (r"Перебираем $s = 0, 1, 2, \dots$, пока $h g^{s} \bmod p$ не разложится над $F$ "
                r"(каждое следующее значение --- предыдущее, умноженное на $g = \VAR{g}$):"
                r"\[\begin{array}{r|r\BLOCK{if signed}|r\BLOCK{endif}|l}"
                r"s & h g^s \bmod p\BLOCK{if signed} & r\BLOCK{endif} & \text{разложение} \\ \hline "
                r"\BLOCK{for t in trace}\VAR{t.s} & \VAR{t.v}\BLOCK{if signed} & \VAR{t.r}\BLOCK{endif} & "
                r"\VAR{t.fact} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"\BLOCK{if s == 0}Само $h$ раскладывается над $F$ ($s = 0$). \BLOCK{endif}"
                r"\BLOCK{if signed}Логарифм $-1$: $g^{(p-1)/2} \equiv -1$, так как $-1$ --- единственный элемент "
                r"порядка $2$ в $\mathbb{Z}_p^*$, а $g^{(p-1)/2}$ имеет порядок $2$; значит, "
                r"$L_{-1} = \VAR{half}$. \BLOCK{endif}"
                r"Итак, $h g^{\VAR{s}} \equiv \VAR{mono}$, откуда "
                r"$x + \VAR{s} \equiv \VAR{lin}\pmod{\VAR{n}}$:"
                r"\[x \equiv \VAR{terms}\BLOCK{if s} - \VAR{s}\BLOCK{endif}\BLOCK{if show_raw} = \VAR{raw}\BLOCK{endif}"
                r"\BLOCK{if raw != answer} \equiv \VAR{answer}\BLOCK{endif}\ (\textrm{mod}\ \VAR{n}).\]"
                r"Проверка: $\VAR{g}^{\VAR{answer}} \equiv \VAR{h}\ (\textrm{mod}\ \VAR{p})$."
                r"\[x = \VAR{answer}.\]")

    def sample(self, rng):
        signed = self.cfg.signed
        while True:
            p = rng.choice(self.cfg.primes)
            g = rng.choice(primitive_roots(p))
            B = rng.choice(self.cfg.bounds)
            fb = factor_base(B, signed)
            n = p - 1
            x = rng.randrange(2, n)
            h = pow(g, x, p)
            if h in fb or h == g:
                continue
            trace = []
            for s in range(n):
                v = h * pow(g, s, p) % p
                r = lift(v, p, signed)
                ex = fb_exponents(r, fb)
                trace.append({"s": s, "v": v, "r": r, "fact": factor_signed_tex(r)})
                if ex:
                    break
            if s == 0 and rng.random() >= self.cfg.trivial_ratio:
                continue
            if signed and r > 0:
                continue
            if len(trace) > 12:
                continue
            logs = {q: (n // 2 if q == -1 else dlog(g, q, p)) for q in fb}
            used = [(q, e) for q, e in zip(fb, ex) if e]
            terms = " + ".join(f"{e} \\cdot {logs[q]}" if e > 1 else str(logs[q]) for q, e in used)
            raw = sum(e * logs[q] for q, e in used) - s
            return {"p": p, "g": g, "h": h, "fb": fb, "signed": signed, "n": n, "half": n // 2,
                    "given": [{"q": q, "L": logs[q]} for q in fb if q != -1],
                    "trace": trace, "s": s, "ex": ex, "mono": mono_tex(ex, fb), "lin": lin_tex(ex, fb),
                    "terms": terms, "raw": raw, "answer": raw % n,
                    "show_raw": bool(s) or len(used) > 1 or used[0][1] > 1}

    def check(self, p):
        P, g, h, n = p["p"], p["g"], p["h"], p["n"]
        assert is_order(g, n, P)
        for l in p["given"]:
            assert pow(g, l["L"], P) == l["q"]
        assert pow(g, p["answer"], P) == h
        assert dlog(g, h, P) == p["answer"]  # independent route: brute force
        last = p["trace"][-1]
        assert last["s"] == p["s"] and math.prod(q ** e for q, e in zip(p["fb"], p["ex"])) == last["r"]
        if p["signed"]:
            assert last["r"] < 0 and pow(g, n // 2, P) == P - 1


class IcLinearSystem(Task):
    id = "dlp.ic_linear_system"
    title_ru = "Исчисление индексов: решение системы по модулю p - 1"
    topics = ("dlp.index_calculus",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Relations g^k = prod l^e for random k; |F| + extra of them determine the logs uniquely "
             "modulo every prime power of p - 1. The first |F| relations may be singular modulo some "
             "q | p - 1 (preset `singular` forces it, typically q = 2). Solution: det, elimination "
             "modulo each q^e with unit pivots, CRT.")
    presets = {"default": {"primes": SMALL, "fb_size": 3, "extra": 1, "singular": False},
               "singular": {"singular": True}}
    statement = (r"Пусть $p = \VAR{p}$, $g = \VAR{g}$ --- первообразный корень по модулю $p$, факторная база "
                 r"$F = \{\VAR{fb|join(', ')}\}$. Найдены соотношения"
                 r"\[\BLOCK{for r in rels}g^{\VAR{r.k}} \equiv \VAR{r.mono}\BLOCK{if not loop.last},\quad "
                 r"\BLOCK{endif}\BLOCK{endfor}\pmod{\VAR{p}}.\]"
                 r"Определяют ли первые \VAR{fb|length} из них логарифмы $L_\ell = \log_g \ell$ однозначно? "
                 r"Найти $L_\ell$, $\ell \in F$, используя все соотношения (систему решать по модулю примарных "
                 r"делителей $p - 1$ и собирать по КТО).")
    solution = (r"Неизвестные $L_\ell$ определены по модулю $p - 1 = \VAR{n} = \VAR{n_factor}$. Система:"
                r"\[\begin{array}{rcl}"
                r"\BLOCK{for r in rels}(\VAR{loop.index})\colon\ \VAR{r.lin} & \equiv & \VAR{r.k} \\ \BLOCK{endfor}"
                r"\end{array}\pmod{\VAR{n}}\]"
                r"Определитель первых \VAR{fb|length} строк: $D = \VAR{det}$\BLOCK{if det == 0} (строки линейно "
                r"зависимы)\BLOCK{else}, $\gcd(D, \VAR{n}) = \VAR{det_gcd}$\BLOCK{endif}. "
                r"\BLOCK{if bad}По модулю \BLOCK{for q in bad}$\VAR{q}$\BLOCK{if not loop.last}, \BLOCK{endif}"
                r"\BLOCK{endfor} матрица первых \VAR{fb|length} соотношений вырождена: они \emph{не} определяют "
                r"$L_\ell$ однозначно (решений по модулю $q^e$ несколько), нужно соотношение "
                r"(\VAR{rels|length}).\BLOCK{else}Матрица обратима по модулю каждого простого делителя "
                r"$p - 1$: первые \VAR{fb|length} соотношения уже определяют $L_\ell$, последнее --- проверочное."
                r"\BLOCK{endif}"
                r"\par Метод Гаусса по модулю каждого $q^e$; ведущий элемент должен быть обратим, т.\,е. "
                r"не делиться на $q$ (столбцы --- коэффициенты при \BLOCK{for l in fb}$L_{\VAR{l}}$"
                r"\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor} и правая часть; над стрелкой --- "
                r"исключаемая переменная, номер ведущей строки в текущей матрице и обратный к ведущему коэффициенту)."
                r"\BLOCK{for pt in parts}\par\noindent По модулю $\VAR{pt.mod}$:"
                r"\BLOCK{for line in pt.lines}\[\BLOCK{for s in line}\BLOCK{if s.col is not none}"
                r"\xrightarrow{L_{\VAR{fb[s.col]}}:\ (\VAR{s.row}),\ \VAR{s.c}^{-1} = \VAR{s.inv}}\BLOCK{endif}"
                + MATRIX + r"\BLOCK{endfor}\]\BLOCK{endfor}"
                r"$\Rightarrow$ \BLOCK{for l in fb}$L_{\VAR{l}} \equiv \VAR{pt.sol[loop.index0]}$"
                r"\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor} $(\textrm{mod}\ \VAR{pt.mod})$."
                r"\BLOCK{endfor}"
                r"\par\noindent Собираем по КТО (модули \BLOCK{for pt in parts}$\VAR{pt.mod}$\BLOCK{if not loop.last}, "
                r"\BLOCK{endif}\BLOCK{endfor}):"
                r"\BLOCK{for l in fb} $L_{\VAR{l}} = \VAR{answer[loop.index0]}$\BLOCK{if not loop.last};\BLOCK{endif}"
                r"\BLOCK{endfor}. Проверка: \BLOCK{for l in fb}$\VAR{g}^{\VAR{answer[loop.index0]}} \equiv \VAR{l}$"
                r"\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor} $(\textrm{mod}\ \VAR{p})$."
                r"\[\BLOCK{for l in fb}L_{\VAR{l}} = \VAR{answer[loop.index0]}\BLOCK{if not loop.last},\ "
                r"\BLOCK{endif}\BLOCK{endfor}.\]")

    def sample(self, rng):
        t = self.cfg.fb_size
        fb = list(PRIMES[:t])
        m = t + self.cfg.extra
        while True:
            p = rng.choice(self.cfg.primes)
            n = p - 1
            g = rng.choice(primitive_roots(p))
            smooth = []
            for k in range(1, n):
                ex = fb_exponents(pow(g, k, p), fb)
                if ex and pow(g, k, p) not in fb:  # g^k = l gives L_l directly: too easy
                    smooth.append((k, ex))
            if len(smooth) < m:
                continue
            ks = sorted(rng.sample(smooth, m))
            A = [ex + [k] for k, ex in ks]
            qs = sorted(factorize(n))
            if any(rank_mod_prime([r[:t] for r in A], q) < t for q in qs):
                continue
            det = int_det([r[:t] for r in A[:t]])
            bad = [q for q in qs if det % q == 0]
            if self.cfg.singular and not bad:
                continue
            parts = []
            for q, e in sorted(factorize(n).items()):
                res = eliminate(A, t, q, q**e)
                assert res is not None
                parts.append({"q": q, "mod": q**e, "lines": chunks(res["snaps"], 2), "sol": res["sol"]})
            logs = [crt_pair_list([pt["sol"][i] for pt in parts], [pt["mod"] for pt in parts]) for i in range(t)]
            nf = " \\cdot ".join(f"{q}^{{{e}}}" if e > 1 else str(q) for q, e in sorted(factorize(n).items()))
            rels = [{"k": k, "mono": mono_tex(ex, fb), "lin": lin_tex(ex, fb), "ex": ex} for k, ex in ks]
            return {"p": p, "g": g, "fb": fb, "n": n, "n_factor": nf, "rels": rels, "det": det,
                    "det_gcd": math.gcd(det, n), "bad": bad, "parts": parts, "answer": logs}

    def check(self, p):
        P, g, n, fb = p["p"], p["g"], p["n"], p["fb"]
        assert is_order(g, n, P)
        for q, L in zip(fb, p["answer"]):
            assert dlog(g, q, P) == L  # independent route: brute force
        for r in p["rels"]:
            assert pow(g, r["k"], P) == math.prod(q ** e for q, e in zip(fb, r["ex"]))
        assert len(p["rels"]) > len(fb)
        t = len(fb)
        det = int_det([r["ex"] for r in p["rels"][:t]])
        assert det == p["det"] and p["bad"] == [q for q in sorted(factorize(n)) if det % q == 0]
        # the whole system determines the logs uniquely modulo every prime factor of p - 1
        assert all(rank_mod_prime([r["ex"] for r in p["rels"]], q) == t for q in factorize(n))
