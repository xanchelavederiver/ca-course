"""ECDLP and its applications (lecture sem2/09): NAF of the scalar, toy ECDH, Pollard rho
for the ECDLP on a tiny curve.

All curves are over F_p with small p (hand-computable); points are enumerated with Sage's
``E.points()`` (deterministic order) and chosen with ``rng``.
"""

import math

from taskgen.core import steps
from taskgen.core.nt import first_primes, inverse
from taskgen.core.task import SolutionDetail, Task
from taskgen.tasks.ecc.scalar_mult import _curve_tex

PRIMES_50 = [q for q in first_primes(20) if 11 <= q <= 50]  # 11, 13, ..., 47

EC_FORMULAS = (r"Формулы: $\lambda = \frac{3x_1^2 + a}{2y_1}$ (удвоение), "
               r"$\lambda = \frac{y_2 - y_1}{x_2 - x_1}$ (сложение), $x_3 = \lambda^2 - x_1 - x_2$, "
               r"$y_3 = \lambda(x_1 - x_3) - y_1$; если $x_1 = x_2$, $y_1 = -y_2$, то сумма равна "
               r'$\mathcal{O}$; $\mathcal{O}$ "--- нейтральный элемент.')


def _curve(p: int, a: int, b: int):
    from sage.all import GF, EllipticCurve

    return EllipticCurve(GF(p), [a, b])


def _random_curve(rng, primes):
    while True:
        p = rng.choice(primes)
        a, b = rng.randrange(0, p), rng.randrange(0, p)
        if (4 * a**3 + 27 * b**2) % p:
            return p, a, b, _curve(p, a, b)


def _pt(P):
    """Sage point -> [x, y] or None (point at infinity)."""
    return None if P.is_zero() else [int(P[0]), int(P[1])]


def _points_by_order(E) -> list[tuple[list[int], int]]:
    return [(_pt(P), int(P.order())) for P in E.points() if not P.is_zero()]


def mult_trace(k: int, P, a: int, p: int, name: str) -> list[dict]:
    """Left-to-right double-and-add for k*P (k >= 1), P affine or None; handles O on the way."""
    R, m, rows = P, 1, []
    for bit in format(k, "b")[1:]:
        st = steps.ec_add_step(R, R, a, p)
        R, m = st["R"], 2 * m
        rows.append({"op": "2R", "k": m, "lam": st["lam"], "R": R})
        if bit == "1":
            st = steps.ec_add_step(R, P, a, p)
            R, m = st["R"], m + 1
            rows.append({"op": f"R + {name}", "k": m, "lam": st["lam"], "R": R})
    assert m == k
    return rows


def _mult(k: int, P, a: int, p: int, name: str) -> dict:
    rows = mult_trace(k, P, a, p, name) if P is not None else []
    R = P if P is None else (rows[-1]["R"] if rows else P)
    return {"k": k, "bits": format(k, "b"), "name": name, "P": P, "rows": rows, "R": R,
            "zeros": [r["k"] for r in rows if r["R"] is None]}


# --- NAF ------------------------------------------------------------------------------------


def naf_rows(n: int) -> list[dict]:
    """Right-to-left NAF trace: n_i, n_i mod 4, digit z_i, n_{i+1} = (n_i - z_i)/2."""
    rows = []
    while n:
        z = (2 - n % 4) if n % 2 else 0
        rows.append({"n": n, "mod4": n % 4, "z": z, "next": (n - z) // 2})
        n = (n - z) // 2
    return rows


def _digits_tex(digits: list[int]) -> str:
    return "".join(r"\bar 1" if d < 0 else str(d) for d in digits)


def _has_adjacent_ones(n: int) -> bool:
    return bool(n & (n >> 1))


class NAF(Task):
    id = "ecc.naf"
    title_ru = "Несмежная форма (NAF) показателя и число групповых операций"
    topics = ("ecc.scalar_mult",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("Corner cases (~1/3): n = 2^k - 1 or long runs of ones (NAF is one digit longer "
             "than the binary expansion), n without adjacent ones (NAF = binary, no gain).")
    presets = {"default": {"lo": 40, "hi": 1024, "corner_ratio": 1 / 3},
               "sem2": {"lo": 100, "hi": 4096},
               "corner": {"lo": 100, "hi": 4096, "corner_ratio": 1.0}}
    statement = (r"Найти несмежную форму (NAF, тернарное разложение с цифрами $-1, 0, 1$) числа "
                 r"$n = \VAR{n}$. Сколько удвоений и сложений (вычитаний) точек требуется для "
                 r"вычисления $nP$ на эллиптической кривой по бинарному разложению и по NAF?")
    solution = (r"Двоичная запись: $n = \VAR{n|bin}_2$ (длина $\VAR{len_bin}$, единиц $\VAR{w_bin}$). "
                r"Цифры NAF справа налево: если $n_i$ чётно, $z_i = 0$; иначе $z_i = 2 - (n_i \bmod 4) "
                r"\in \{1, -1\}$; $n_{i+1} = (n_i - z_i)/2$."
                r"\[\begin{array}{c|r|c|r|r}"
                r"i & n_i & n_i \bmod 4 & z_i & n_{i+1} \\ \hline "
                r"\BLOCK{for r in rows}\VAR{loop.index0} & \VAR{r.n} & \VAR{r.mod4} & \VAR{r.z} & "
                r"\VAR{r.next} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"$\mathrm{NAF}(\VAR{n}) = (\VAR{naf_tex})$, т.\,е. $\VAR{n} = \VAR{naf_sum}$ "
                r"(длина $\VAR{len_naf}$, ненулевых цифр $\VAR{w_naf}$; соседних ненулевых цифр нет)."
                r"\BLOCK{if same} Двоичная запись уже не содержит соседних единиц, поэтому NAF "
                r"совпадает с ней (единственность NAF).\BLOCK{endif}"
                r"\BLOCK{if longer} NAF на одну цифру длиннее двоичной записи "
                r"(старшая цифра $1$ стоит в разряде $2^{\VAR{len_naf - 1}} > n$).\BLOCK{endif}"
                r"\par Начиная с $R = P$, на каждую следующую цифру "
                r"выполняется одно удвоение и, если цифра ненулевая, одно сложение ($+P$) или "
                r"вычитание ($-P$; $-P$ вычисляется бесплатно):"
                r"\[\begin{array}{l|c|c|c}"
                r" & \text{удвоений} & \text{сложений} & \text{всего} \\ \hline "
                r"\text{бинарное} & \VAR{len_bin - 1} & \VAR{w_bin - 1} & \VAR{ops_bin} \\ "
                r"\text{NAF} & \VAR{len_naf - 1} & \VAR{w_naf - 1} & \VAR{ops_naf} \\ "
                r"\end{array}\]"
                r"\BLOCK{if ops_naf < ops_bin}NAF экономит $\VAR{ops_bin - ops_naf}$ "
                r"\BLOCK{if ops_bin - ops_naf == 1}операцию\BLOCK{elif ops_bin - ops_naf < 5}операции"
                r"\BLOCK{else}операций\BLOCK{endif}.\BLOCK{elif ops_naf == ops_bin}Выигрыша нет.\BLOCK{else}"
                r"NAF проигрывает на $\VAR{ops_naf - ops_bin}$ (лишнее удвоение).\BLOCK{endif} "
                r"Для сравнения: $\log_2 n \approx \VAR{log2n}$, оценки в среднем "
                r"$1{,}5\log_2 n \approx \VAR{avg_bin}$ (бинарное) и "
                r"$\tfrac43\log_2 n \approx \VAR{avg_naf}$ (NAF)."
                r"\[\mathrm{NAF}(\VAR{n}) = (\VAR{naf_tex});\quad \VAR{ops_bin} \text{ и } \VAR{ops_naf} "
                r"\text{ операций}.\]")

    def sample(self, rng):
        lo, hi = self.cfg.lo, self.cfg.hi
        if rng.random() < self.cfg.corner_ratio:
            kind = rng.choice(["ones", "runs", "no_adjacent"])
            if kind == "ones":
                n = 2 ** rng.randrange(max(4, lo.bit_length() - 1), hi.bit_length()) - 1
            elif kind == "runs":
                while True:
                    n = rng.randrange(lo, hi)
                    n |= n >> 1  # runs of ones
                    n |= n >> 1
                    if lo <= n < hi and len(steps.naf(n)) > n.bit_length():
                        break
            else:
                while True:
                    n = rng.randrange(lo, hi)
                    n &= ~(n >> 1)
                    if lo <= n < hi and n & (n - 1):
                        break
        else:
            n = rng.randrange(lo, hi)
        rows = naf_rows(n)
        digits = [r["z"] for r in reversed(rows)]
        L = len(digits)
        len_bin, w_bin = n.bit_length(), bin(n).count("1")
        w_naf = sum(1 for d in digits if d)
        ops_bin, ops_naf = len_bin - 1 + w_bin - 1, L - 1 + w_naf - 1
        log2n = math.log2(n)
        return {"n": n, "rows": rows, "digits": digits, "naf_tex": _digits_tex(digits),
                "naf_sum": " ".join(f"{'-' if d < 0 else '+'} 2^{{{L - 1 - i}}}"
                                    for i, d in enumerate(digits) if d).lstrip("+ "),
                "len_bin": len_bin, "w_bin": w_bin, "len_naf": L, "w_naf": w_naf,
                "ops_bin": ops_bin, "ops_naf": ops_naf,
                "same": not _has_adjacent_ones(n), "longer": L > len_bin,
                "log2n": f"{log2n:.2f}".replace(".", "{,}"),
                "avg_bin": f"{1.5 * log2n:.1f}".replace(".", "{,}"),
                "avg_naf": f"{4 / 3 * log2n:.1f}".replace(".", "{,}"),
                "answer": {"naf": digits, "ops_binary": ops_bin, "ops_naf": ops_naf}}

    def check(self, p):
        d, n = p["digits"], p["n"]
        assert d[0] == 1 and set(d) <= {-1, 0, 1}
        assert sum(z * 2**i for i, z in enumerate(reversed(d))) == n
        assert all(d[i] == 0 or d[i + 1] == 0 for i in range(len(d) - 1)), "adjacent nonzero"
        assert len(d) <= n.bit_length() + 1
        # NAF weight is minimal among signed binary expansions: never above the binary weight
        assert p["w_naf"] <= p["w_bin"]
        assert p["same"] == (d == [int(c) for c in format(n, "b")])


# --- ECDH -----------------------------------------------------------------------------------

MULT_TABLE = (r"\BLOCK{macro mtable(m)}"
              r"\BLOCK{if m.P is none}$\VAR{m.k} \cdot \mathcal{O} = \mathcal{O}$.\BLOCK{else}"
              r"$\VAR{m.k} = \VAR{m.bits}_2$, $\VAR{m.name} = \VAR{tx.pt(m.P)}$:"
              r"\BLOCK{if m.rows}"
              r"\[\begin{array}{l|r|r|c}"
              r"\text{операция} & k & \lambda & R = k\VAR{m.name} \\ \hline "
              r"\BLOCK{for r in m.rows}\VAR{r.op} & \VAR{r.k} & \BLOCK{if r.lam is none}\text{---}"
              r"\BLOCK{else}\VAR{r.lam}\BLOCK{endif} & \VAR{tx.pt(r.R)} \\ \BLOCK{endfor}"
              r"\end{array}\]\BLOCK{else} $1 \cdot \VAR{m.name} = \VAR{m.name}$.\par \BLOCK{endif}"
              r"\BLOCK{if m.zeros}Встретилась точка $\VAR{m.zeros[0]}\VAR{m.name} = \mathcal{O}$, т.\,е. "
              r"$\operatorname{ord} \VAR{m.name} \mid \VAR{m.zeros[0]}$.\par \BLOCK{endif}"
              r"\BLOCK{endif}\BLOCK{endmacro}")


class ECDH(Task):
    id = "ecc.ecdh"
    title_ru = "Протокол Диффи-Хеллмана на эллиптической кривой (ECDH)"
    topics = ("ecc.ecdlp", "ecc.scalar_mult")
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Corner cases: P of small order 2..6 (the trace passes through O; secret keys "
             "are determined mod ord P only), and a secret key that is a multiple of ord P "
             "(public key O, shared key O).")
    presets = {"default": {"primes": PRIMES_50, "min_order": 11, "hi": 24,
                           "small_ratio": 0.15, "zero_ratio": 0.15},
               "small": {"small_ratio": 1.0, "zero_ratio": 0.0},
               "zero": {"small_ratio": 0.0, "zero_ratio": 1.0}}
    statement = (r"\BLOCK{import 'macros.tex.j2' as tx}Алиса и Боб используют ECDH на кривой $E\colon y^2 = \VAR{curve}$ над "
                 r"$\mathbb{F}_{\VAR{p}}$ с базовой точкой $P = \VAR{tx.pt(P)}$. Секретные ключи: "
                 r"$a = \VAR{ka}$ у Алисы, $b = \VAR{kb}$ у Боба. Вычислить открытые ключи "
                 r"$A = aP$, $B = bP$ и общий ключ $K$ двумя способами ($aB$ и $bA$) методом "
                 r'«удвоение"--~сложение». Что видит Ева?')
    solution = (r"\BLOCK{import 'macros.tex.j2' as tx}" + MULT_TABLE +
                r"Двоичная запись множителя читается слева направо: $R \gets 2R$, при единичном "
                r"бите $R \gets R + X$. " + EC_FORMULAS + r" Всё по модулю $\VAR{p}$, $a_E = \VAR{a}$."
                r"\par\noindent\textbf{Алиса}, $A = aP$. \VAR{mtable(mA)}"
                r"\par\noindent\textbf{Боб}, $B = bP$. \VAR{mtable(mB)}"
                r"\par\noindent\textbf{Алиса}, $K = aB$. \VAR{mtable(mKA)}"
                r"\par\noindent\textbf{Боб}, $K = bA$. \VAR{mtable(mKB)}"
                r"\par Результаты совпадают: $aB = bA = abP = \VAR{tx.pt(K)}$"
                r"\BLOCK{if K is not none} (на практике ключом служит $x$-координата "
                r"$\VAR{K[0]}$)\BLOCK{endif}. "
                r"Порядок $P$ равен $\VAR{N}$\BLOCK{if N <= 6} "
                r"(очень мал: $P, 2P, \dots$ повторяются с периодом $\VAR{N}$)\BLOCK{endif}\BLOCK{if ka >= N or kb >= N}"
                r", поэтому важны лишь $a \bmod \VAR{N} = \VAR{ka % N}$ и $b \bmod \VAR{N} = "
                r"\VAR{kb % N}$\BLOCK{endif}. "
                r"Ева видит $E$, $P$, $A = \VAR{tx.pt(A)}$, $B = \VAR{tx.pt(B)}$; чтобы найти $K$, ей "
                r"достаточно решить ECDLP $A = xP$\BLOCK{if N <= 12} "
                r'"--- при $\operatorname{ord} P = \VAR{N}$ это перебор из $\VAR{N}$ вариантов'
                r"\BLOCK{endif}."
                r"\BLOCK{if A is none or B is none} Здесь открытый ключ "
                r"\BLOCK{if A is none}Алисы\BLOCK{else}Боба\BLOCK{endif} равен $\mathcal{O}$ "
                r"(секретный ключ кратен $\operatorname{ord} P$), и общий ключ $\mathcal{O}$ "
                r"известен всем: такие ключи надо отбрасывать ($a, b \not\equiv 0 \pmod "
                r"{\operatorname{ord} P}$).\BLOCK{endif}"
                r"\[A = \VAR{tx.pt(A)},\quad B = \VAR{tx.pt(B)},\quad K = \VAR{tx.pt(K)}.\]")

    def sample(self, rng):
        r = rng.random()
        mode = ("small" if r < self.cfg.small_ratio else
                "zero" if r < self.cfg.small_ratio + self.cfg.zero_ratio else "normal")
        hi = self.cfg.hi
        while True:
            p, a, b, E = _random_curve(rng, self.cfg.primes)
            pts = _points_by_order(E)
            if mode == "small":
                cands = [(P, o) for P, o in pts if 2 <= o <= 6]
            elif mode == "zero":
                cands = [(P, o) for P, o in pts if 5 <= o <= hi // 2]
            else:
                cands = [(P, o) for P, o in pts if o >= self.cfg.min_order]
            if not cands:
                continue
            P, N = rng.choice(cands)
            if mode == "small":
                ka, kb = rng.randrange(3, 14), rng.randrange(3, 14)
            elif mode == "zero":
                ka, kb = N * rng.randrange(1, hi // N + 1), rng.randrange(3, hi)
                if kb % N == 0:
                    continue
                if rng.random() < 0.5:
                    ka, kb = kb, ka
            else:
                ka, kb = rng.randrange(3, min(N, hi)), rng.randrange(3, min(N, hi))
                if ka == kb:
                    continue
            mA, mB = _mult(ka, P, a, p, "P"), _mult(kb, P, a, p, "P")
            mKA, mKB = _mult(ka, mB["R"], a, p, "B"), _mult(kb, mA["R"], a, p, "A")
            zeros = mA["zeros"] + mB["zeros"] + mKA["zeros"] + mKB["zeros"]
            A, B, K = mA["R"], mB["R"], mKA["R"]
            return {"p": p, "a": a, "b": b, "curve": _curve_tex(a, b), "P": P, "N": N,
                    "ka": ka, "kb": kb, "mA": mA, "mB": mB, "mKA": mKA, "mKB": mKB,
                    "A": A, "B": B, "K": K, "zeros": zeros, "mode": mode,
                    "answer": {"A": A, "B": B, "K": K}}

    def check(self, p):
        E = _curve(p["p"], p["a"], p["b"])
        P = E(*p["P"])
        assert int(P.order()) == p["N"]
        ka, kb = p["ka"], p["kb"]
        assert _pt(ka * P) == p["A"] and _pt(kb * P) == p["B"]
        assert _pt((ka * kb % p["N"]) * P) == p["K"] == p["mKB"]["R"], "aB != bA"
        for m in ("mA", "mB", "mKA", "mKB"):
            for r in p[m]["rows"]:
                assert r["R"] is None or E.is_on_curve(*r["R"])


# --- Pollard rho for the ECDLP --------------------------------------------------------------


def _rho_walk(P, Q, N: int, a_E: int, p: int, a0: int, b0: int, max_i: int) -> dict:
    """Sequence R_j = a_j P + b_j Q with the x mod 3 partition; Floyd: first i with R_i = R_2i.

    Sets: x(R) = 0 (mod 3) or R = O -> R + P; 1 -> 2R; 2 -> R + Q.
    """
    def lin(u, v):
        R = None
        for _ in range(u):
            R = steps.ec_add_step(R, P, a_E, p)["R"]
        for _ in range(v):
            R = steps.ec_add_step(R, Q, a_E, p)["R"]
        return R

    R, a, b = lin(a0, b0), a0 % N, b0 % N
    seq = []
    for j in range(2 * max_i + 1):
        s = 0 if R is None else R[0] % 3
        seq.append({"j": j, "R": R, "a": a, "b": b, "s": s})
        if j >= 2 and j % 2 == 0 and seq[j // 2]["R"] == R:
            return {"seq": seq, "i": j // 2, "a0": a0, "b0": b0}
        if s == 0:
            R, a = steps.ec_add_step(R, P, a_E, p)["R"], (a + 1) % N
        elif s == 1:
            R, a, b = steps.ec_add_step(R, R, a_E, p)["R"], 2 * a % N, 2 * b % N
        else:
            R, b = steps.ec_add_step(R, Q, a_E, p)["R"], (b + 1) % N
    return {"seq": seq, "i": None, "a0": a0, "b0": b0}


class ECRho(Task):
    id = "ecc.rho"
    title_ru = "Решение ECDLP rho-методом Полларда"
    topics = ("ecc.ecdlp",)
    complexity = 3
    solution_detail = SolutionDetail.FULL
    notes = ("ord P is prime in [11, 41]; with probability ~1/4 it is composite (corner case: "
             "b_i - b_2i is not invertible mod ord P, several candidates are checked). A useless "
             "collision (b_i = b_2i) restarts the walk from R_0 = P + Q. At most 20 walk steps.")
    presets = {"default": {"primes": [q for q in PRIMES_50 if q >= 13], "min_order": 11,
                           "max_order": 41, "composite_ratio": 0.25, "max_i": 10,
                           "force_noninvertible": False},
               "composite": {"composite_ratio": 1.0, "force_noninvertible": True}}
    statement = (r"\BLOCK{import 'macros.tex.j2' as tx}На кривой $E\colon y^2 = \VAR{curve}$ над $\mathbb{F}_{\VAR{p}}$ точка "
                 r"$P = \VAR{tx.pt(P)}$ имеет порядок $N = \VAR{N}$. Решить ECDLP $Q = nP$, "
                 r"$Q = \VAR{tx.pt(Q)}$, $\rho$-методом Полларда: $R_{j+1} = R_j + P$, $2R_j$ или "
                 r"$R_j + Q$, если $x(R_j) \bmod 3$ равно $0$, $1$ или $2$ соответственно "
                 r"(точку $\mathcal{O}$ относим к первому множеству); $R_0 = P$; коллизию искать "
                 r"методом Флойда ($R_i = R_{2i}$).")
    solution = (r"\BLOCK{import 'macros.tex.j2' as tx}"
                r"Храним $R_j = a_j P + b_j Q$; при $R \gets R + P$: $a \gets a + 1$; при $R \gets 2R$: "
                r"$(a, b) \gets (2a, 2b)$; при $R \gets R + Q$: $b \gets b + 1$ (всё по модулю $N = "
                r"\VAR{N}$). " + EC_FORMULAS + r" Координаты по модулю $\VAR{p}$, $a_E = \VAR{a}$."
                r"\BLOCK{for w in walks}"
                r"\par \BLOCK{if not loop.first}\textbf{Повторный запуск} с $R_0 = "
                r"\VAR{w.a0}P + \VAR{w.b0}Q$. \BLOCK{endif}"
                r"Последовательность $R_j$ ($s = x(R_j) \bmod 3$) до $j = 2i = \VAR{2 * w.i}$:"
                r"\[\begin{array}{r|c|c|r|r}"
                r"j & R_j & s & a_j & b_j \\ \hline "
                r"\BLOCK{for r in w.seq}\VAR{r.j} & \VAR{tx.pt(r.R)} & \VAR{r.s} & \VAR{r.a} & \VAR{r.b} \\ "
                r"\BLOCK{endfor}\end{array}\]"
                r"Флойд: \BLOCK{for k in range(1, w.i)}$R_{\VAR{k}} \ne R_{\VAR{2 * k}}$, \BLOCK{endfor}"
                r"$R_{\VAR{w.i}} = R_{\VAR{2 * w.i}} = \VAR{tx.pt(w.seq[w.i].R)}$. Отсюда "
                r"$\VAR{w.ai} P + \VAR{w.bi} Q = \VAR{w.a2i} P + \VAR{w.b2i} Q$, т.\,е. "
                r"$(b_i - b_{2i})\, n \equiv a_{2i} - a_i$: "
                r"\[\VAR{w.db}\, n \equiv \VAR{w.da} \pmod{\VAR{N}}.\]"
                r"\BLOCK{if w.useless}Коэффициент при $n$ равен $0$: коллизия бесполезна "
                r"(сравнение $0 \cdot n \equiv 0$ верно при любом $n$), нужен новый запуск."
                r"\BLOCK{endif}\BLOCK{endfor}"
                r"\par \BLOCK{if d == 1}$\gcd(\VAR{db}, \VAR{N}) = 1$, "
                r"$\VAR{db}^{-1} \equiv \VAR{db_inv} \pmod{\VAR{N}}$ ($\VAR{db} \cdot \VAR{db_inv} = "
                r"\VAR{db * db_inv} \equiv 1$), $n \equiv \VAR{da} \cdot \VAR{db_inv} \equiv \VAR{answer}$."
                r"\BLOCK{else}$d = \gcd(\VAR{db}, \VAR{N}) = \VAR{d}$ "
                r"(коэффициент необратим, $N$ составное); $d \mid \VAR{da}$, делим на $d$: "
                r"$\VAR{db // d}\, n \equiv \VAR{da // d} \pmod{\VAR{N // d}}$, "
                r"$n \equiv \VAR{n0} \pmod{\VAR{N // d}}$. Кандидаты $n = \VAR{n0} + k \cdot \VAR{N // d}$, "
                r"$0 \le k < \VAR{d}$; проверяем: "
                r"\BLOCK{for c in cands}$\VAR{c.n}P = \VAR{tx.pt(c.R)}$\BLOCK{if c.n == answer}"
                r" $= Q$\BLOCK{endif}\BLOCK{if not loop.last}; \BLOCK{endif}\BLOCK{endfor}."
                r"\BLOCK{endif}"
                r" Проверка: $\VAR{answer}P = Q$."
                r"\[n = \VAR{answer}\ (\textrm{mod}\ \VAR{N}).\]")

    def sample(self, rng):
        from sage.all import is_prime

        composite = rng.random() < self.cfg.composite_ratio
        max_i = self.cfg.max_i
        while True:
            p, a, b, E = _random_curve(rng, self.cfg.primes)
            cands = [(P, o) for P, o in _points_by_order(E)
                     if self.cfg.min_order <= o <= self.cfg.max_order and bool(is_prime(o)) != composite
                     and (not composite or o >= 9)]
            if not cands:
                continue
            P, N = rng.choice(cands)
            n = rng.randrange(2, N)
            Q = _pt(n * E(*P))
            walks, total = [], 0
            for a0, b0 in ((1, 0), (1, 1)):
                w = _rho_walk(P, Q, N, a, p, a0, b0, max_i)
                if w["i"] is None:
                    break
                i = w["i"]
                si, s2i = w["seq"][i], w["seq"][2 * i]
                w.update({"ai": si["a"], "bi": si["b"], "a2i": s2i["a"], "b2i": s2i["b"],
                          "db": (si["b"] - s2i["b"]) % N, "da": (s2i["a"] - si["a"]) % N})
                w["useless"] = w["db"] == 0
                walks.append(w)
                total += 2 * i
                if not w["useless"]:
                    break
            if not walks or walks[-1]["i"] is None or walks[-1]["useless"] or total > 2 * max_i + 2:
                continue
            db, da = walks[-1]["db"], walks[-1]["da"]
            d = math.gcd(db, N)
            if composite and d == 1 and (self.cfg.force_noninvertible or rng.random() < 0.75):
                continue  # composite order: prefer instances where the corner case shows up
            if da % d:
                raise AssertionError("inconsistent collision")
            ctx = {"db_inv": None, "n0": None, "cands": []}
            if d == 1:
                ctx["db_inv"] = inverse(db, N)
                ans = da * ctx["db_inv"] % N
            else:
                M = N // d
                n0 = (da // d) * inverse((db // d) % M, M) % M if M > 1 else 0
                cs = [{"n": n0 + k * M, "R": _pt((n0 + k * M) * E(*P))} for k in range(d)]
                ans = next(c["n"] for c in cs if c["R"] == Q)
                ctx.update({"n0": n0, "cands": cs})
            if d > 4:
                continue
            return {"p": p, "a": a, "b": b, "curve": _curve_tex(a, b), "P": P, "Q": Q, "N": N,
                    "walks": walks, "db": db, "da": da, "d": d, **ctx, "steps": total,
                    "answer": ans}

    def check(self, p):
        E = _curve(p["p"], p["a"], p["b"])
        P, Q, N, n = E(*p["P"]), E(*p["Q"]), p["N"], p["answer"]
        assert int(P.order()) == N and 0 <= n < N
        assert _pt(n * P) == p["Q"]
        assert sum(1 for k in range(N) if k * P == Q) == 1  # brute force: unique log
        for w in p["walks"]:
            for r in w["seq"]:
                R = r["a"] * P + r["b"] * Q
                assert _pt(R) == r["R"], "R_j != a_j P + b_j Q"
            assert w["seq"][w["i"]]["R"] == w["seq"][2 * w["i"]]["R"]
            assert all(w["seq"][k]["R"] != w["seq"][2 * k]["R"] for k in range(1, w["i"]))
        assert p["steps"] <= 22
