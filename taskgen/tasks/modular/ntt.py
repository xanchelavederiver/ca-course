"""Number-theoretic transforms (lecture sem1/05): cyclic convolution of two short
sequences via an NTT modulo a Fermat number (omega = a power of two, length 4) or a
Mersenne number 2^q - 1 (omega = 2, length q).

Presets: "default" = "fermat" (F_2 = 17 with omega = 4 or F_3 = 257 with omega = 16,
n = 4: all twiddle factors are +-2^e, i.e. shifts); "mersenne" (31 = 2^5 - 1, omega = 2,
n = 5: multiplications by 2^e are cyclic rotations of 5-bit words).
"""

from taskgen.core.nt import inverse
from taskgen.core.task import SolutionDetail, Task


def ntt(a: list[int], w: int, m: int) -> list[int]:
    """A_k = sum_j a_j w^{jk} mod m (definition, O(n^2))."""
    n = len(a)
    return [sum(a[j] * pow(w, j * k, m) for j in range(n)) % m for k in range(n)]


def cyclic_convolution(a: list[int], b: list[int]) -> list[int]:
    """c_j = sum_{i + l = j (mod n)} a_i b_l over Z."""
    n = len(a)
    return [sum(a[i] * b[(j - i) % n] for i in range(n)) for j in range(n)]


def _signed(v: int, m: int, fermat: bool) -> int:
    """Twiddle factor as printed: +-2^e for Fermat moduli, the residue for Mersenne ones."""
    return v - m if fermat and v > m // 2 else v


def _expr(coefs: list[int], xs: list[int]) -> str:
    """'x_0 + 16 \\cdot x_1 - x_2 - 16 \\cdot x_3' with the coefficients printed as given."""
    out = []
    for c, x in zip(coefs, xs):
        mag = abs(c)
        term = str(x) if mag == 1 else rf"{mag} \cdot {x}"
        sign = "-" if c < 0 else "+"
        out.append(("-" if c < 0 else "") + term if not out else f" {sign} {term}")
    return "".join(out)


def _transform_rows(xs: list[int], matrix: list[list[int]], m: int) -> list[dict]:
    rows = []
    for k, coefs in enumerate(matrix):
        s = sum(c * x for c, x in zip(coefs, xs))
        rows.append({"k": k, "expr": _expr(coefs, xs), "sum": s, "res": s % m})
    return rows


class NTTConvolution(Task):
    id = "modular.ntt"
    title_ru = "Циклическая свёртка с помощью теоретико-числового преобразования"
    topics = ("arithmetic.ntt",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Transforms by the definition (n = 4 or 5, all twiddles are +-2^e). Digits 0..9, so the "
             "convolution over Z often exceeds the modulus (corner case: the NTT then gives it only "
             "modulo m, the solution says so); the check recomputes the cyclic convolution directly.")
    presets = {
        "default": {"kind": "fermat", "rings": [[2, 4], [3, 4]], "hi": 9},
        "fermat": {"kind": "fermat", "rings": [[2, 4], [3, 4]], "hi": 9},
        "mersenne": {"kind": "mersenne", "rings": [[5, 5]], "hi": 9},
    }
    statement = (r"Вычислить циклическую свёртку последовательностей "
                 r"\[a = (\VAR{a|join(', ')}), \qquad b = (\VAR{b|join(', ')})\] "
                 r"длины $n = \VAR{n}$ в кольце $\mathbb{Z}/\VAR{m}\mathbb{Z}$, "
                 r"$\VAR{m} = \VAR{m_tex}$, с помощью теоретико-числового преобразования "
                 r"с корнем $\omega = \VAR{w}$ из единицы степени $\VAR{n}$. Проверить ответ прямым "
                 r"вычислением свёртки.")
    solution = (r"\BLOCK{if fermat}$\VAR{m} = \VAR{m_tex}$, поэтому $2^{\VAR{half}} \equiv -1$ и "
                r"$2^{\VAR{2 * half}} \equiv 1$: $\omega = \VAR{w} = 2^{\VAR{e}}$ имеет порядок "
                r"$\VAR{2 * half} / \VAR{e} = \VAR{n}$, $\omega^{\VAR{n // 2}} \equiv -1$."
                r"\BLOCK{else}$\VAR{m} = \VAR{m_tex}$, поэтому $2^{\VAR{q}} \equiv 1$, и $\omega = 2$ "
                r"имеет порядок $\VAR{q} = n$ (\VAR{q} "
                r"--- простое число); умножение на $2^e$ --- циклический сдвиг $\VAR{q}$-битового слова."
                r"\BLOCK{endif} "
                r"Прямое преобразование: $A_k = \sum_j a_j \omega^{jk}$, матрица $(\omega^{jk} \bmod m)$"
                r"\BLOCK{if fermat} (вычеты $\pm 2^e$)\BLOCK{endif}:"
                r"\[W = \begin{pmatrix}\BLOCK{for row in W}\VAR{row|join(' & ')}"
                r"\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}\end{pmatrix}.\]"
                r"\[\begin{array}{c|l|r|r}"
                r"k & A_k = \sum_j \omega^{jk} a_j & & A_k \bmod \VAR{m} \\ \hline "
                r"\BLOCK{for r in fa}\VAR{r.k} & \VAR{r.expr} & \VAR{r.sum} & \VAR{r.res} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"\[\begin{array}{c|l|r|r}"
                r"k & B_k = \sum_j \omega^{jk} b_j & & B_k \bmod \VAR{m} \\ \hline "
                r"\BLOCK{for r in fb}\VAR{r.k} & \VAR{r.expr} & \VAR{r.sum} & \VAR{r.res} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"Поточечное произведение $C_k = A_k B_k \bmod \VAR{m}$: "
                r"\BLOCK{for k in range(n)}$\VAR{fa[k].res} \cdot \VAR{fb[k].res} = \VAR{fa[k].res * fb[k].res}"
                r" \equiv \VAR{C[k]}$\BLOCK{if not loop.last}; \BLOCK{endif}\BLOCK{endfor}."
                r"\par Обратное преобразование: $c_j = n^{-1} \sum_k C_k \omega^{-jk}$, "
                r"$\omega^{-1} = \omega^{\VAR{n - 1}} \equiv \VAR{winv}$, "
                r"$n^{-1} = \VAR{n}^{-1} \equiv \VAR{ninv_tex} \pmod{\VAR{m}}$\VAR{ninv_note}, "
                r"матрица $(\omega^{-jk} \bmod m)$:"
                r"\[W^{-} = \begin{pmatrix}\BLOCK{for row in Wi}\VAR{row|join(' & ')}"
                r"\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}\end{pmatrix}.\]"
                r"\[\begin{array}{c|l|r|r|r}"
                r"j & \sum_k \omega^{-jk} C_k & & \bmod \VAR{m} & c_j = n^{-1} \cdot (\ldots) \\ \hline "
                r"\BLOCK{for r in inv}\VAR{r.k} & \VAR{r.expr} & \VAR{r.sum} & \VAR{r.res} & "
                r"\VAR{c[loop.index0]} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"Проверка: прямое вычисление циклической свёртки над $\mathbb{Z}$, "
                r"$c_j = \sum_i a_i b_{(j - i) \bmod n}$, даёт $(\VAR{direct|join(', ')})$"
                r"\BLOCK{if exact}; все $c_j < \VAR{m}$, "
                r"поэтому ТЧП дало \emph{точную} свёртку над $\mathbb{Z}$."
                r"\BLOCK{else}, по модулю $\VAR{m}$ это $(\VAR{answer|join(', ')})$ --- совпадает. "
                r"Здесь $\max c_j = \VAR{direct|max} \ge \VAR{m}$: ТЧП даёт свёртку лишь по модулю $m$; "
                r"для точной свёртки цифр $0, \ldots, \VAR{cfg.hi}$ заведомо достаточно модуля $m > n \cdot \VAR{cfg.hi}^2 = "
                r"\VAR{n * cfg.hi * cfg.hi}$.\BLOCK{endif}"
                r"\[c = a * b = (\VAR{answer|join(', ')}) \pmod{\VAR{m}}.\]")

    def sample(self, rng):
        fermat = self.cfg.kind == "fermat"
        p1, n = rng.choice(self.cfg.rings)
        if fermat:
            half = 2**p1                      # m = 2^half + 1, ord(2) = 2 half
            m = 2**half + 1
            e = 2 * half // n
            w = 2**e
            m_tex = rf"2^{{{half}}} + 1"
        else:
            half, q = 0, p1
            m = 2**q - 1
            e, w = 1, 2
            m_tex = rf"2^{{{q}}} - 1"
        a = [rng.randrange(0, self.cfg.hi + 1) for _ in range(n)]
        b = [rng.randrange(0, self.cfg.hi + 1) for _ in range(n)]
        while not any(a):
            a = [rng.randrange(0, self.cfg.hi + 1) for _ in range(n)]
        while not any(b):
            b = [rng.randrange(0, self.cfg.hi + 1) for _ in range(n)]
        winv = pow(w, n - 1, m)
        W = [[_signed(pow(w, j * k, m), m, fermat) for j in range(n)] for k in range(n)]
        Wi = [[_signed(pow(winv, j * k, m), m, fermat) for k in range(n)] for j in range(n)]
        fa = _transform_rows(a, W, m)
        fb = _transform_rows(b, W, m)
        C = [ra["res"] * rb["res"] % m for ra, rb in zip(fa, fb)]
        inv = _transform_rows(C, Wi, m)
        ninv = inverse(n, m)
        c = [r["res"] * ninv % m for r in inv]
        if fermat:  # n = 2^s, n^{-1} = 2^{2 half - s} = -2^{half - s}
            s = n.bit_length() - 1
            ninv_tex = rf"2^{{{2 * half - s}}} \equiv -2^{{{half - s}}} \equiv {ninv}"
            ninv_note = ""
        else:
            ninv_tex = str(ninv)
            ninv_note = rf" (${n} \cdot {ninv} = {n * ninv} = {n * ninv // m} \cdot {m} + 1$)"
        direct = cyclic_convolution(a, b)
        return {"fermat": fermat, "m": m, "m_tex": m_tex, "half": half, "q": n, "n": n, "e": e,
                "w": w, "winv": _signed(winv, m, fermat), "a": a, "b": b, "W": W, "Wi": Wi,
                "fa": fa, "fb": fb, "C": C, "inv": inv, "ninv": ninv, "ninv_tex": ninv_tex,
                "ninv_note": ninv_note, "c": c, "direct": direct,
                "exact": max(direct) < m, "answer": c}

    def check(self, p):
        m, n, w = p["m"], p["n"], p["w"]
        # omega is a principal n-th root of unity: order exactly n, n invertible
        assert pow(w, n, m) == 1 and all(pow(w, d, m) != 1 for d in range(1, n))
        assert n * p["ninv"] % m == 1
        if p["fermat"]:
            assert m == 2 ** p["half"] + 1 and pow(w, n // 2, m) == m - 1
        else:
            assert (m + 1) & m == 0 and n == m.bit_length()
        # independent route: direct cyclic convolution over Z, reduced mod m
        a, b = p["a"], p["b"]
        direct = [sum(a[i] * b[l] for i in range(n) for l in range(n) if (i + l) % n == j)
                  for j in range(n)]
        assert p["answer"] == [x % m for x in direct] and p["direct"] == direct
        assert p["exact"] == (max(direct) < m)
        # convolution theorem on the transforms
        assert all(p["C"][k] == p["fa"][k]["res"] * p["fb"][k]["res"] % m for k in range(n))
        assert [r["res"] for r in p["fa"]] == ntt(a, w, m)
