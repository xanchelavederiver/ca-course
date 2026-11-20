"""Pseudorandom generators (lecture sem1/09): LFSR sequences over GF(2) (period, companion
matrix, n-th term via A^n), recovering the feedback polynomial from 2L bits (Gauss over GF(2),
Berlekamp--Massey), and the full-period criterion for linear congruential sequences
(Knuth's Theorem A / Hull--Dobell).

Conventions (the same as in the notes and the handout):
  * s_{n+L} = c_1 s_{n+L-1} + c_2 s_{n+L-2} + ... + c_L s_n over GF(2);
  * characteristic (feedback) polynomial f(x) = x^L + c_1 x^{L-1} + ... + c_L;
  * connection polynomial C(x) = 1 + c_1 x + ... + c_L x^L = x^L f(1/x) (Berlekamp--Massey);
  * state S_n = (s_n, ..., s_{n+L-1})^T, S_{n+1} = A S_n with the companion matrix A whose last
    row is (c_L, ..., c_1) and whose other rows shift the state.

GF(2)[x] polynomials are ints: bit i is the coefficient of x^i.
"""

from __future__ import annotations

from math import gcd

from taskgen.core.nt import factorize
from taskgen.core.task import SolutionDetail, Task

# --- GF(2)[x] arithmetic (pure Python; Sage is used only in the self-checks) -------------


def pdeg(a: int) -> int:
    return a.bit_length() - 1


def pmul(a: int, b: int) -> int:
    r = 0
    while b:
        if b & 1:
            r ^= a
        a <<= 1
        b >>= 1
    return r


def pmod(a: int, b: int) -> int:
    db = pdeg(b)
    while a and pdeg(a) >= db:
        a ^= b << (pdeg(a) - db)
    return a


def pdiv(a: int, b: int) -> int:
    q, db = 0, pdeg(b)
    while a and pdeg(a) >= db:
        k = pdeg(a) - db
        q |= 1 << k
        a ^= b << k
    return q


def ptex(a: int, var: str = "x") -> str:
    """Polynomial in descending powers: x^4 + x + 1."""
    if a == 0:
        return "0"
    terms = []
    for i in range(pdeg(a), -1, -1):
        if a >> i & 1:
            terms.append("1" if i == 0 else var if i == 1 else f"{var}^{{{i}}}")
    return " + ".join(terms)


def ptex_asc(a: int, var: str = "x") -> str:
    """Polynomial in ascending powers: 1 + x + x^4 (connection polynomials)."""
    if a == 0:
        return "0"
    terms = [("1" if i == 0 else var if i == 1 else f"{var}^{{{i}}}")
             for i in range(pdeg(a) + 1) if a >> i & 1]
    return " + ".join(terms)


def _irreducibles(max_deg: int) -> list[int]:
    out = []
    for f in range(2, 1 << (max_deg + 1)):
        if all(pmod(f, g) for g in out if 2 * pdeg(g) <= pdeg(f)):
            out.append(f)
    return out


IRRED = _irreducibles(6)


def pfactor(f: int) -> list[tuple[int, int]]:
    """Factorisation of f (deg <= 12) into irreducibles: [(g, e)] by trial division."""
    out = []
    for g in IRRED:
        e = 0
        while pdeg(f) >= pdeg(g) and pmod(f, g) == 0:
            f, e = pdiv(f, g), e + 1
        if e:
            out.append((g, e))
        if f == 1:
            break
    if f != 1:
        out.append((f, 1))
    return out


def pfactor_tex(f: int) -> str:
    parts = []
    for g, e in pfactor(f):
        s = ptex(g)
        if "+" in s and (e > 1 or len(pfactor(f)) > 1):
            s = f"({s})"
        parts.append(s + (f"^{{{e}}}" if e > 1 else ""))
    return " ".join(parts)


def x_order(f: int) -> int:
    """Order of x modulo f (f(0) = 1)."""
    r, e = 2, 1
    while pmod(r, f) != 1:
        r, e = pmod(r << 1, f), e + 1
    return e


def is_primitive(f: int) -> bool:
    return f & 1 and x_order(f) == (1 << pdeg(f)) - 1


def poly_from_taps(cs: list[int]) -> int:
    """f(x) = x^L + c_1 x^{L-1} + ... + c_L from [c_1, ..., c_L]."""
    L = len(cs)
    return (1 << L) | sum(c << (L - j) for j, c in enumerate(cs, start=1))


def taps_from_poly(f: int) -> list[int]:
    L = pdeg(f)
    return [f >> (L - j) & 1 for j in range(1, L + 1)]


def lfsr_bits(cs: list[int], state: list[int], n: int) -> list[int]:
    s, L = list(state), len(cs)
    while len(s) < n:
        s.append(sum(cs[j - 1] * s[-j] for j in range(1, L + 1)) % 2)
    return s[:n]


def recurrence_tex(cs: list[int]) -> str:
    L = len(cs)
    terms = [("s_{n}" if L - j == 0 else f"s_{{n+{L - j}}}") for j in range(1, L + 1) if cs[j - 1]]
    return f"s_{{n+{L}}} = " + (" + ".join(terms) if terms else "0")


# --- GF(2) matrices: lists of rows of 0/1 ------------------------------------------------


def companion(cs: list[int]) -> list[list[int]]:
    L = len(cs)
    A = [[1 if j == i + 1 else 0 for j in range(L)] for i in range(L - 1)]
    A.append([cs[L - 1 - j] for j in range(L)])
    return A


def mat_mul(A, B):
    n, m, k = len(A), len(B[0]), len(B)
    return [[sum(A[i][t] & B[t][j] for t in range(k)) % 2 for j in range(m)] for i in range(n)]


def mat_vec(A, v):
    return [sum(a & b for a, b in zip(row, v)) % 2 for row in A]


def mat_tex(A, small: bool = True) -> str:
    rows = r" \\ ".join(" & ".join(str(x) for x in row) for row in A)
    if small:
        return r"\left(\begin{smallmatrix}" + rows + r"\end{smallmatrix}\right)"
    return r"\begin{pmatrix}" + rows + r"\end{pmatrix}"


def col_tex(v) -> str:
    return "(" + ", ".join(str(x) for x in v) + ")^T"


def bits_tex(bits: list[int], group: int = 5) -> str:
    """Bit string in groups (text mode, breakable): \\texttt{01101 10011 ...}."""
    s = "".join(str(b) for b in bits)
    return r"\texttt{" + " ".join(s[i:i + group] for i in range(0, len(s), group)) + "}"


# --- linear algebra over GF(2) with a trace ----------------------------------------------


def gauss_jordan_gf2(M: list[list[int]], nvars: int) -> dict:
    """Gauss--Jordan elimination of the augmented matrix M (nvars columns + rhs).

    Returns the steps (operations + matrix after each pivot), the pivot columns, the rank."""
    M = [row[:] for row in M]
    rank, pivots, trace = 0, [], []
    for col in range(nvars):
        piv = next((r for r in range(rank, len(M)) if M[r][col]), None)
        if piv is None:
            trace.append({"col": col, "ops": [], "free": True, "M": None})
            continue
        ops = []
        if piv != rank:
            M[piv], M[rank] = M[rank], M[piv]
            ops.append(rf"R_{{{rank + 1}}} \leftrightarrow R_{{{piv + 1}}}")
        adds = []
        for r in range(len(M)):
            if r != rank and M[r][col]:
                M[r] = [a ^ b for a, b in zip(M[r], M[rank])]
                adds.append(r + 1)
        if adds:
            ops.append(", ".join(f"R_{{{r}}}" for r in adds) + rf" \mathrel{{+}}= R_{{{rank + 1}}}")
        trace.append({"col": col, "ops": ops, "free": False, "M": [row[:] for row in M]})
        pivots.append(col)
        rank += 1
    return {"steps": trace, "pivots": pivots, "rank": rank, "R": M}


def berlekamp_massey(s: list[int]) -> dict:
    """Berlekamp--Massey over GF(2) (HAC Alg. 6.30) with a per-step trace.

    C, B are connection polynomials (bit i = coefficient of x^i)."""
    C, B, L, m = 1, 1, 0, -1
    rows = []
    for N in range(len(s)):
        d = s[N]
        for i in range(1, L + 1):
            d ^= (C >> i & 1) & s[N - i]
        row = {"N": N, "s": s[N], "d": d, "change": False, "lchange": False}
        if d:
            T = C
            C ^= B << (N - m)
            row["change"] = True
            row["shift"] = N - m
            if 2 * L <= N:
                L, m, B = N + 1 - L, N, T
                row["lchange"] = True
        row.update({"C": C, "L": L, "B": B, "m": m, "C_tex": ptex_asc(C), "B_tex": ptex_asc(B)})
        rows.append(row)
    return {"rows": rows, "C": C, "L": L}


def linear_complexity(s: list[int]) -> int:
    return berlekamp_massey(s)["L"]


def _sage_bm(bits: list[int]):
    from sage.all import GF
    from sage.matrix.berlekamp_massey import berlekamp_massey as sage_bm

    return sage_bm([GF(2)(b) for b in bits])


def _sage_poly(mask: int):
    from sage.all import GF, PolynomialRing

    R = PolynomialRing(GF(2), "x")
    return R([mask >> i & 1 for i in range(pdeg(mask) + 1)])


# --- tasks ------------------------------------------------------------------------------

KIND_TEX = {
    "primitive": "примитивный",
    "irreducible": "неприводимый, но не примитивный",
    "reducible": "приводимый",
}


class LFSRSequence(Task):
    id = "crypto.lfsr"
    title_ru = "Последовательность РСЛОС: период, матрица, $n$-й член"
    topics = ("crypto.lfsr",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("f(0) = 1 always (non-singular LFSR, purely periodic); non-zero initial state. "
             "Feedback polynomials: primitive / irreducible non-primitive / reducible (the period "
             "then depends on the state and may be tiny). s_N via right-to-left binary powering "
             "of the companion matrix applied to the state; N < 128.")
    presets = {
        "default": {"degrees": [4, 4, 5, 6], "mix": [0.4, 0.25, 0.35], "n_lo": 40, "n_hi": 127},
        "nonprimitive": {"degrees": [4, 6], "mix": [0.0, 0.5, 0.5]},
    }
    statement = (r"Последовательность $s_0, s_1, \dots$ над $\mathbb{F}_2$ порождается РСЛОС с "
                 r"характеристическим многочленом \[f(x) = \VAR{f_tex}\] и начальным состоянием "
                 r"$(s_0, \dots, s_{\VAR{L - 1}}) = (\VAR{state|join(', ')})$. "
                 r"(а)~Выписать рекуррентное соотношение и сопровождающую матрицу $A$ "
                 r"($S_{n+1} = A S_n$, $S_n = (s_n, \dots, s_{n+\VAR{L - 1}})^T$). "
                 r"(б)~Найти период последовательности. Является ли $f$ неприводимым, примитивным? "
                 r"(в)~Вычислить $s_{\VAR{N}}$ как первую координату вектора $A^{\VAR{N}} S_0$ "
                 r"(бинарный алгоритм возведения матрицы в степень).")
    solution = (r"(а) $\VAR{rec}$; \[A = \VAR{A_tex}.\] "
                r"(б) Члены последовательности, пока состояние не вернётся к $S_0$: "
                r"\VAR{seq_tex}, т.\,е. $S_{\VAR{T}} = S_0$, и период $T = \VAR{T}$. "
                r"Разложение: $f(x) = \VAR{fact}$"
                r"\BLOCK{if kind == 'reducible'} (проверка делимости на неприводимые многочлены "
                r"$x + 1$, $x^2 + x + 1$, $x^3 + x + 1$, $x^3 + x^2 + 1$), $f$ приводим. "
                r"Период последовательности зависит от начального состояния и делит "
                r"$\operatorname{ord}_f(x) = \VAR{ordx}$ (наименьшее $e$ с $x^e \equiv 1 \bmod f$)"
                r"\BLOCK{if T < ordx}; для данного $S_0$ он меньше\BLOCK{endif}. "
                r"\BLOCK{else} "
                r"неприводим (нет делителей степени $\le \VAR{L // 2}$). Для неприводимого $f$ период "
                r"любого ненулевого состояния равен $\operatorname{ord}_f(x)$ и делит "
                r"$2^{\VAR{L}} - 1 = \VAR{2 ** L - 1}$"
                r"\BLOCK{if kind == 'primitive'}; $T = 2^{\VAR{L}} - 1$, т.\,е. $x$ "
                r"порождает $\mathbb{F}_{2^{\VAR{L}}}^*$. "
                r"\BLOCK{else}; здесь $T = \VAR{T} < \VAR{2 ** L - 1}$ "
                r"($x^{\VAR{T}} \equiv 1 \bmod f$). \BLOCK{endif}\BLOCK{endif}"
                r"Многочлен $f$ \VAR{kind_tex}."
                r"\par (в) $\VAR{N} = (\VAR{N|bin})_2$. Справа налево: $v \gets S_0$; при $n_i = 1$ "
                r"$v \gets A^{2^i} v$; затем $A^{2^{i+1}} = (A^{2^i})^2$:"
                r"\[\begin{array}{c|c|c|c}"
                r"i & n_i & A^{2^i} & v \\ \hline "
                r"\BLOCK{for r in pw}\VAR{r.i} & \VAR{r.bit} & \VAR{r.P} & \VAR{r.v} \\ \noalign{\smallskip} \BLOCK{endfor}"
                r"\end{array}\]"
                r"$A^{\VAR{N}} S_0 = S_{\VAR{N}} = \VAR{SN}$. Проверка по периоду: "
                r"$\VAR{N} \equiv \VAR{N % T} \pmod{\VAR{T}}$, $s_{\VAR{N}} = s_{\VAR{N % T}}$."
                r"\[T = \VAR{T},\quad \text{$f$ \VAR{kind_tex}},\quad s_{\VAR{N}} = \VAR{answer.s_N}.\]")

    def _poly(self, rng, kind: str, L: int) -> int | None:
        cands = [f for f in range(1 << L, 1 << (L + 1)) if f & 1]
        if kind == "primitive":
            pool = [f for f in cands if is_primitive(f)]
        elif kind == "irreducible":
            pool = [f for f in cands if pfactor(f) == [(f, 1)] and not is_primitive(f)]
        else:
            pool = [f for f in cands if pfactor(f) != [(f, 1)]]
        return rng.choice(pool) if pool else None

    def sample(self, rng):
        while True:
            L = rng.choice(self.cfg.degrees)
            kind = rng.choices(["primitive", "irreducible", "reducible"], weights=self.cfg.mix)[0]
            f = self._poly(rng, kind, L)
            if f is not None:
                break
        cs = taps_from_poly(f)
        state = [0] * L
        while not any(state):
            state = [rng.randrange(2) for _ in range(L)]
        # period: run until the state returns
        T = 1
        while lfsr_bits(cs, state, T + L)[T:T + L] != state:
            T += 1
        seq = lfsr_bits(cs, state, T + L)
        N = rng.randint(self.cfg.n_lo, self.cfg.n_hi)
        A = companion(cs)
        pw, P, v = [], A, list(state)
        for i, bit in enumerate(reversed(format(N, "b"))):
            if bit == "1":
                v = mat_vec(P, v)
            pw.append({"i": i, "bit": int(bit), "P": mat_tex(P), "v": col_tex(v), "Pm": P})
            P = mat_mul(P, P)
        sN = v[0]
        return {"L": L, "f": f, "f_tex": ptex(f), "cs": cs, "state": state, "rec": recurrence_tex(cs),
                "A": A, "A_tex": mat_tex(A, small=False), "T": T, "seq": seq,
                "seq_tex": bits_tex(seq), "fact": pfactor_tex(f), "kind": kind, "kind_tex": KIND_TEX[kind],
                "ordx": x_order(f), "N": N, "pw": pw, "SN": col_tex(v), "SN_v": v,
                "answer": {"period": T, "kind": kind, "s_N": sN}}

    def check(self, p):
        from sage.all import GF, matrix, vector

        L, f, cs, T = p["L"], p["f"], p["cs"], p["answer"]["period"]
        F = GF(2)
        A = matrix(F, p["A"])
        x = _sage_poly(f).parent().gen()
        assert A.charpoly(x) == _sage_poly(f), "companion matrix"
        S0 = vector(F, p["state"])
        # period: A^T S0 = S0 and minimal
        assert A**T * S0 == S0 and all(A**d * S0 != S0 for d in range(1, T) if T % d == 0)
        # kind via Sage
        g = _sage_poly(f)
        kind = ("primitive" if g.is_primitive() else "irreducible" if g.is_irreducible()
                else "reducible")
        assert kind == p["answer"]["kind"]
        if kind != "reducible":
            assert T == p["ordx"] and ((1 << L) - 1) % T == 0
        else:
            assert p["ordx"] % T == 0
        # s_N by an independent route: periodicity and Sage's matrix power
        bits = lfsr_bits(cs, p["state"], T + L)
        assert p["answer"]["s_N"] == bits[p["N"] % T] == int((A ** p["N"] * S0)[0])
        assert 4 <= L <= 6 and any(p["state"])


class LFSRRecover(Task):
    id = "crypto.lfsr_recover"
    title_ru = "Восстановление РСЛОС по $2L$ битам (метод Гаусса)"
    topics = ("crypto.lfsr",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Unknowns ordered (c_L, ..., c_1), so the rows of the augmented matrix are windows "
             "of the sequence. Degenerate case (corner, ~1/5; preset 'degenerate'): the linear "
             "complexity is < L, the system has 2^{L - rank} solutions f = g h (g = minimal "
             "polynomial), all of them generate the same sequence (Massey's lemma).")
    presets = {
        "default": {"lengths": [3, 4, 4, 5], "degenerate_ratio": 0.2, "extra": 4},
        "degenerate": {"lengths": [4, 5], "degenerate_ratio": 1.0},
    }
    statement = (r"Известно, что последовательность $s_0, s_1, \dots$ над $\mathbb{F}_2$ "
                 r"порождается РСЛОС длины $L = \VAR{L}$, т.\,е. "
                 r"$s_{n+\VAR{L}} = c_1 s_{n+\VAR{L - 1}} + \dots + c_{\VAR{L}} s_n$. "
                 r"По первым $2L = \VAR{2 * L}$ битам \[\VAR{bits|join(',\\ ')}\] "
                 r"восстановить коэффициенты $c_1, \dots, c_{\VAR{L}}$ (составить и решить "
                 r"линейную систему над $\mathbb{F}_2$ методом Гаусса) и найти следующие "
                 r"\VAR{extra} бита.")
    solution = (r"Соотношения при $n = 0, \dots, \VAR{L - 1}$ дают систему из $\VAR{L}$ уравнений: "
                r"$c_{\VAR{L}} s_n + c_{\VAR{L - 1}} s_{n+1} + \dots + c_1 s_{n+\VAR{L - 1}} = s_{n+\VAR{L}}$. "
                r"Строки расширенной матрицы "
                r"(столбцы $c_{\VAR{L}}, \dots, c_1$ \textbar\ правая часть) "
                r"--- окна длины $\VAR{L + 1}$ последовательности:"
                r"\[\VAR{M0}\]"
                r"Метод Гаусса над $\mathbb{F}_2$ (сложение строк = XOR):"
                r"\BLOCK{for st in gj}\par\noindent столбец $c_{\VAR{st.c}}$: "
                r"\BLOCK{if st.free}ведущего элемента нет, $c_{\VAR{st.c}}$ --- свободная переменная;"
                r"\BLOCK{elif st.ops}$\VAR{st.ops|join(';\\ ')}$ $\Rightarrow$ $\VAR{st.M}$;"
                r"\BLOCK{else}преобразований не нужно;\BLOCK{endif}\BLOCK{endfor}"
                r"\par \BLOCK{if rank == L}Ранг равен $\VAR{L}$, решение единственно: "
                r"$(c_1, \dots, c_{\VAR{L}}) = (\VAR{sols[0].c|join(', ')})$, "
                r"$f(x) = \VAR{sols[0].f}$. "
                r"\BLOCK{else}Ранг равен $\VAR{rank} < \VAR{L}$: линейная сложность последовательности "
                r"$\VAR{rank}$, и система имеет $2^{\VAR{L - rank}} = \VAR{sols|length}$ решений "
                r"(свободные переменные пробегают $\{0, 1\}$):"
                r"\BLOCK{for s in sols}\par\noindent $(c_1, \dots, c_{\VAR{L}}) = (\VAR{s.c|join(', ')})$: "
                r"$f(x) = \VAR{s.f} = \VAR{s.fact}$;\BLOCK{endfor}"
                r"\par все они делятся на минимальный многочлен $g(x) = \VAR{g_tex}$ (РСЛОС длины "
                r"$\VAR{rank}$) и, по лемме Месси, порождают одну и ту же последовательность. "
                r"\BLOCK{endif}"
                r"Проверка: рекуррентность порождает данные $\VAR{2 * L}$ бит; продолжение: "
                r"\VAR{cont_tex}."
                r"\[\BLOCK{if rank == L}f(x) = \VAR{sols[0].f},\quad \BLOCK{endif}"
                r"s_{\VAR{2 * L}}, \dots, s_{\VAR{2 * L + extra - 1}} = \VAR{answer.next|join(',\\ ')}.\]")

    def sample(self, rng):
        L = rng.choice(self.cfg.lengths)
        degenerate = rng.random() < self.cfg.degenerate_ratio
        while True:
            if degenerate:
                lam = rng.randint(max(2, L - 2), L - 1)
                g = rng.choice([h for h in range(1 << lam, 1 << (lam + 1)) if h & 1])
                cs0 = taps_from_poly(g)
            else:
                lam = L
                g = rng.choice([h for h in range(1 << L, 1 << (L + 1)) if h & 1])
                cs0 = taps_from_poly(g)
            state = [rng.randrange(2) for _ in range(lam)]
            bits = lfsr_bits(cs0, state, 2 * L + self.cfg.extra)
            if linear_complexity(bits[:2 * L]) == lam:
                break
        M = [bits[n:n + L + 1] for n in range(L)]
        gj = gauss_jordan_gf2(M, L)
        rank = gj["rank"]
        assert rank == lam
        # all solutions: free variables over {0, 1}; unknown vector (c_L, ..., c_1)
        free = [c for c in range(L) if c not in gj["pivots"]]
        sols = []
        for mask in range(1 << len(free)):
            x = [0] * L
            for k, c in enumerate(free):
                x[c] = mask >> k & 1
            for r, c in enumerate(gj["pivots"]):
                x[c] = (gj["R"][r][L] + sum(gj["R"][r][j] * x[j] for j in free)) % 2
            cs = x[::-1]
            f = poly_from_taps(cs)
            sols.append({"c": cs, "f": ptex(f), "fmask": f, "fact": pfactor_tex(f) if f != 1 << L
                         else f"x^{{{L}}}"})
        steps = []
        for st in gj["steps"]:
            steps.append({"c": L - st["col"], "free": st["free"], "ops": st["ops"],
                          "M": _aug_tex(st["M"], L) if st["M"] else ""})
        nxt = bits[2 * L:2 * L + self.cfg.extra]
        return {"L": L, "bits": bits[:2 * L], "extra": self.cfg.extra, "M0": _aug_tex(M, L, small=False),
                "gj": steps, "rank": rank, "sols": sols, "g": g, "g_tex": ptex(g),
                "cont_tex": bits_tex(bits, group=L) + " (группы по $L$ бит)",
                "answer": {"c": sols[0]["c"] if rank == L else None, "next": nxt,
                           "n_solutions": len(sols)}}

    def check(self, p):
        L, bits, ext = p["L"], p["bits"], p["answer"]["next"]
        assert len(p["sols"]) == 2 ** (L - p["rank"])
        lam = int(_sage_bm(bits).degree())
        assert lam == p["rank"], "rank of the Hankel system = linear complexity"
        g = _sage_poly(p["g"])
        for s in p["sols"]:
            out = lfsr_bits(s["c"], bits[:L], 2 * L + len(ext))
            assert out[:2 * L] == bits, "solution does not generate the given bits"
            assert out[2 * L:] == ext, "continuation differs"
            assert _sage_poly(s["fmask"]) % g == 0
        if p["rank"] == L:
            assert p["answer"]["c"][-1] == 1 and len(p["sols"]) == 1


def _aug_tex(M, L, small=True) -> str:
    rows = r" \\ ".join(" & ".join(str(x) for x in row[:L]) + " & " + str(row[L]) for row in M)
    spec = "c" * L + "|c"
    if small:
        return r"\left(\begin{array}{@{}" + spec + r"@{}}" + rows + r"\end{array}\right)"
    return r"\left(\begin{array}{" + spec + "}" + rows + r"\end{array}\right)"


class BerlekampMassey(Task):
    id = "crypto.berlekamp_massey"
    title_ru = 'Алгоритм Берлекэмпа--~Месси'
    topics = ("crypto.lfsr",)
    complexity = 3
    solution_detail = SolutionDetail.FULL
    notes = ("2*Lmax bits of a random LFSR of length <= Lmax (f(0) = 1, random state); the linear "
             "complexity is >= max(2, Lmax - 1), so the answer (shortest LFSR) is unique (N >= 2 lambda).")
    presets = {
        "default": {"lmax": 4},
        "long": {"lmax": 5},
    }
    statement = (r'С помощью алгоритма Берлекэмпа--~Месси'
                 r" найти линейную сложность и кратчайший РСЛОС "
                 r"(многочлен связей $C(x)$ и характеристический многочлен $f(x)$), порождающий "
                 r"последовательность \[\VAR{bits|join(',\\ ')}.\]")
    solution = (r"Обозначения: $C(x) = 1 + c_1 x + \dots + c_\ell x^\ell$ --- текущий многочлен связей, "
                r"$\ell$ --- текущая длина, $B(x)$ --- многочлен связей до последнего увеличения длины "
                r"(на шаге $m$). На шаге $N$ невязка $d = s_N + \sum_{i=1}^{\ell} c_i s_{N-i}$; если $d = 1$, "
                r"то $C \gets C + x^{N-m} B$, и при $2\ell \le N$: $\ell \gets N + 1 - \ell$, $B \gets C_{\text{old}}$, "
                r"$m \gets N$. Начало: $C = B = 1$, $\ell = 0$, $m = -1$."
                r"\[\begin{array}{c|c|c|l|c|l|c}"
                r"N & s_N & d & C(x) & \ell & B(x) & m \\ \hline "
                r"\BLOCK{for r in rows}\VAR{r.N} & \VAR{r.s} & \VAR{r.d} & \VAR{r.C_tex}"
                r"\BLOCK{if r.change}\ (+x^{\VAR{r.shift}}B)\BLOCK{endif} & \VAR{r.L}\BLOCK{if r.lchange}^{*}"
                r"\BLOCK{endif} & \VAR{r.B_tex} & \VAR{r.m} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"{\small ${}^{*}$ --- длина увеличена.} "
                r"Линейная сложность $\ell = \VAR{lam}$; так как $\VAR{n} \ge 2\ell$, кратчайший РСЛОС "
                r"определён однозначно. Рекуррентность: $\VAR{rec}$. Проверка: при начальном состоянии "
                r"$(\VAR{bits[:lam]|join(', ')})$ она порождает все $\VAR{n}$ бит."
                r"\[C(x) = \VAR{C_tex},\quad f(x) = x^{\VAR{lam}} C(1/x) = \VAR{f_tex},\quad "
                r"\ell = \VAR{lam}.\]")

    def sample(self, rng):
        n = 2 * self.cfg.lmax
        while True:
            L = rng.randint(2, self.cfg.lmax)
            f = rng.choice([h for h in range(1 << L, 1 << (L + 1)) if h & 1])
            state = [rng.randrange(2) for _ in range(L)]
            bits = lfsr_bits(taps_from_poly(f), state, n)
            bm = berlekamp_massey(bits)
            if bm["L"] >= max(2, self.cfg.lmax - 1):
                break
        lam, C = bm["L"], bm["C"]
        # characteristic polynomial: reverse C as a degree-lam polynomial
        fmask = sum((C >> i & 1) << (lam - i) for i in range(lam + 1))
        cs = taps_from_poly(fmask)
        return {"bits": bits, "n": n, "rows": bm["rows"], "lam": lam, "C": C, "C_tex": ptex_asc(C),
                "f": fmask, "f_tex": ptex(fmask), "cs": cs, "rec": recurrence_tex(cs),
                "answer": {"L": lam, "C": ptex_asc(C)}}

    def check(self, p):
        bits, lam = p["bits"], p["lam"]
        conn = _sage_bm(bits)  # Sage returns the minimal (characteristic) polynomial
        assert int(conn.degree()) == lam
        assert conn == _sage_poly(p["f"]), "minimal polynomial differs from Sage's"
        assert lfsr_bits(p["cs"], bits[:lam], len(bits)) == bits
        assert 2 * lam <= len(bits)


# --- linear congruential sequences: full period (Theorem A) --------------------------------

FAMOUS = [
    (1103515245, 12345, 2**31, r"\texttt{rand()} из стандарта ANSI~C"),
    (1664525, 1013904223, 2**32, r"генератор из книги «Numerical Recipes»"),
    (22695477, 1, 2**32, r"генератор Borland~C/C++"),
    (134775813, 1, 2**32, r"генератор Borland Delphi"),
    (69069, 1, 2**32, r"генератор \texttt{MTH\$RANDOM} (VAX)"),
    (65539, 0, 2**31, r"RANDU (IBM, 1960-е)"),
]


def lcg_cycle_from_zero(a: int, c: int, m: int, limit: int = 1 << 13) -> int | None:
    """Length of the cycle through 0 (None if 0 is not on a cycle or the limit is hit)."""
    x, seen = 0, {}
    for n in range(limit):
        if x in seen:
            return n - seen[x] if seen[x] == 0 else None
        seen[x] = n
        x = (a * x + c) % m
    return None


def affine_pow(a: int, c: int, n: int, m: int) -> tuple[int, int]:
    """(A, C) with F^n(x) = A x + C for F(x) = a x + c mod m (binary powering of affine maps)."""
    ra, rc, ba, bc = 1, 0, a % m, c % m
    while n:
        if n & 1:
            ra, rc = ba * ra % m, (ba * rc + bc) % m
        ba, bc = ba * ba % m, (ba * bc + bc) % m
        n >>= 1
    return ra, rc


def full_period_affine(a: int, c: int, m: int) -> bool:
    """Independent criterion: x -> ax + c is a bijection and the orbit of 0 has length m."""
    if gcd(a, m) != 1:
        return False
    if affine_pow(a, c, m, m)[1] != 0:
        return False
    return all(affine_pow(a, c, m // q, m)[1] != 0 for q in factorize(m))


class LCGPeriod(Task):
    id = "crypto.lcg_period"
    title_ru = "Максимальный период линейной конгруэнтной последовательности"
    topics = ("crypto.prng",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("Outcomes: full period; gcd(c, m) > 1 (incl. c = 0, the multiplicative case); some "
             "p | m with p not dividing a - 1; 4 | m but a = 3 mod 4. Real-world generators with "
             "m = 2^31, 2^32 (prob. famous_ratio). For m <= small_m the orbit of 0 is listed.")
    presets = {
        "default": {"moduli": [16, 18, 20, 24, 27, 28, 30, 32, 36, 40, 44, 45, 48, 50, 54, 56, 60,
                               63, 64, 72, 75, 80, 81, 84, 90, 96, 98, 100, 108, 112, 120, 125, 126,
                               128, 144, 150, 162, 180, 196, 200, 216, 225, 240, 243, 250, 256,
                               300, 360, 375, 500, 1000, 1024],
                    "mix": {"full": 0.45, "coprime": 0.2, "prime": 0.15, "four": 0.2},
                    "famous_ratio": 0.12, "small_m": 40},
        "not_coprime": {"mix": {"coprime": 1.0}, "famous_ratio": 0.0},
        "mod4": {"mix": {"four": 1.0}, "famous_ratio": 0.0},
    }
    statement = (r"Имеет ли линейная конгруэнтная последовательность "
                 r"$x_{n+1} = (a x_n + c) \bmod m$ с параметрами \[a = \VAR{a},\quad c = \VAR{c},"
                 r"\quad m = \VAR{m_tex}\] максимальный период $m$ (при любом $x_0$)? "
                 r"Если нет, указать нарушенные условия теоремы о максимальном периоде."
                 r"\BLOCK{if orbit} Проверить ответ, выписав последовательность при $x_0 = 0$."
                 r"\BLOCK{endif}")
    solution = (r'Теорема (Халл"--~Добелл; Кнут, теорема~A): период равен $m$ тогда и только тогда, когда '
                r"1)~$\gcd(c, m) = 1$; 2)~$p \mid a - 1$ для каждого простого $p \mid m$; "
                r"3)~$4 \mid a - 1$, если $4 \mid m$.\par "
                r"Здесь $m = \VAR{m_fact}$, $a - 1 = \VAR{a1_fact}$."
                r"\par 1) $\gcd(\VAR{c}, \VAR{m_tex}) = \VAR{g}$"
                r"\BLOCK{if g == 1} --- выполнено.\BLOCK{else} --- \textbf{нарушено}"
                r"\BLOCK{if c == 0} (мультипликативный генератор, $c = 0$: значение $0$ неподвижно, "
                r"период не больше $\lambda(m) < m$)\BLOCK{endif}.\BLOCK{endif}"
                r"\par 2) \BLOCK{for q in primes}$\VAR{q} \BLOCK{if q in bad_primes}\nmid"
                r"\BLOCK{else}\mid\BLOCK{endif} \VAR{a - 1}$\BLOCK{if not loop.last}, \BLOCK{endif}"
                r"\BLOCK{endfor}\BLOCK{if bad_primes} --- \textbf{нарушено}"
                r"\BLOCK{else} --- выполнено\BLOCK{endif}."
                r"\par 3) \BLOCK{if four_divides}$4 \mid m$, $a - 1 \equiv \VAR{(a - 1) % 4} \pmod 4$"
                r"\BLOCK{if (a - 1) % 4} --- \textbf{нарушено}\BLOCK{else} --- выполнено\BLOCK{endif}."
                r"\BLOCK{else}$4 \nmid m$, условие не требуется.\BLOCK{endif}"
                r"\BLOCK{if name}\par Это \VAR{name}.\BLOCK{endif}"
                r"\BLOCK{if a == 1}\par При $a = 1$ получаем $x_n = (x_0 + nc) \bmod m$: даже при "
                r"максимальном периоде такая последовательность совсем не похожа на случайную.\BLOCK{endif}"
                r"\BLOCK{if orbit}\par Проверка, $x_0 = 0$: $\VAR{orbit|join(',\\allowbreak\\ ')}"
                r"\BLOCK{if cycle}, 0, \dots$ --- цикл длины $\VAR{cycle}$\BLOCK{else}, \dots$ "
                r"--- значение $0$ больше не встречается\BLOCK{endif}.\BLOCK{endif}"
                r"\[\text{\BLOCK{if answer.full}период максимален ($= \VAR{m_tex}$)"
                r"\BLOCK{else}период меньше $m$ (нарушены условия \VAR{answer.failed|join(', ')})"
                r"\BLOCK{endif}}.\]")

    def sample(self, rng):
        name = ""
        if rng.random() < self.cfg.famous_ratio:
            a, c, m, name = rng.choice(FAMOUS)
        else:
            kinds = list(self.cfg.mix)
            while True:
                kind = rng.choices(kinds, weights=[self.cfg.mix[k] for k in kinds])[0]
                m = rng.choice(self.cfg.moduli)
                ps = sorted(factorize(m))
                r = 1
                for q in ps:
                    r *= q
                if m % 4 == 0:
                    r = r * 2 if r % 4 else r
                if kind == "four" and m % 4:
                    continue
                coprimes = [x for x in range(1, m) if gcd(x, m) == 1]
                ks = range(1, m // r) if m // r > 1 else range(0, 1)
                if kind == "full":
                    a = 1 + r * rng.choice(ks)
                    c = rng.choice(coprimes)
                elif kind == "coprime":
                    a = 1 + r * rng.choice(ks)
                    c = rng.choice([x for x in range(0, m) if gcd(x, m) > 1 and (a, x) != (1, 0)])
                elif kind == "four":
                    # all p | a - 1, but a = 3 mod 4: a - 1 = 2 * odd multiple of rad(m)
                    r2 = r // 2  # rad(m) (contains a single factor 2)
                    cands = [a for a in range(2, m) if (a - 1) % r2 == 0 and (a - 1) % 4 == 2]
                    if not cands:
                        continue
                    a = rng.choice(cands)
                    c = rng.choice(coprimes)
                else:  # some prime p | m does not divide a - 1
                    a = rng.randrange(2, m)
                    if all((a - 1) % q == 0 for q in ps):
                        continue
                    c = rng.choice(coprimes)
                break
        ps = sorted(factorize(m))
        g = gcd(c, m)
        bad = [q for q in ps if (a - 1) % q]
        four = m % 4 == 0
        failed = ([1] if g != 1 else []) + ([2] if bad else []) + ([3] if four and (a - 1) % 4 else [])
        orbit, cycle = [], None
        if m <= self.cfg.small_m:
            x = 0
            for _ in range(m):
                orbit.append(x)
                x = (a * x + c) % m
                if x == 0 or x in orbit:
                    break
            cycle = len(orbit) if x == 0 else None
        m_tex = (rf"2^{{{m.bit_length() - 1}}}" if m > 10**6 and m & (m - 1) == 0 else str(m))
        return {"a": a, "c": c, "m": m, "m_tex": m_tex, "name": name, "primes": ps, "g": g,
                "bad_primes": bad, "four_divides": four,
                "m_fact": _fact_tex(m), "a1_fact": _fact_tex(a - 1),
                "orbit": orbit, "cycle": cycle,
                "answer": {"full": not failed, "failed": failed}}

    def check(self, p):
        a, c, m = p["a"], p["c"], p["m"]
        full = full_period_affine(a, c, m)
        assert full == p["answer"]["full"], "Theorem A disagrees with the direct check"
        if m <= 1 << 13:
            cyc = lcg_cycle_from_zero(a, c, m)
            assert (cyc == m) == full
        if p["orbit"]:
            assert (p["cycle"] == m) == full


def _fact_tex(n: int) -> str:
    if n == 0:
        return "0"
    if n == 1:
        return "1"
    return r" \cdot ".join(f"{q}^{{{e}}}" if e > 1 else str(q) for q, e in sorted(factorize(n).items()))
