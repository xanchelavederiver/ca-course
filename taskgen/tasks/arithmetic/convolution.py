"""Convolutions and the discrete Fourier transform (lecture sem1/04): linear, cyclic and
negacyclic convolution of digit sequences, zero padding, the DFT over a small prime field
and the convolution theorem.
"""

from taskgen.core.nt import factorize, inverse
from taskgen.core.steps import primitive_root
from taskgen.core.task import SolutionDetail, Task


def digits10(a: int) -> list[int]:
    """Decimal digits of a > 0, least significant first."""
    return [int(c) for c in str(a)[::-1]]


def linear_conv(x: list[int], y: list[int]) -> list[int]:
    z = [0] * (len(x) + len(y) - 1)
    for i, xi in enumerate(x):
        for j, yj in enumerate(y):
            z[i + j] += xi * yj
    return z


def cyclic_conv(x: list[int], y: list[int], n: int, sign: int = 1) -> list[int]:
    """Cyclic (sign=+1) or negacyclic (sign=-1) convolution of length n, by the definition."""
    z = [0] * n
    for i, xi in enumerate(x):
        for j, yj in enumerate(y):
            k = i + j
            z[k % n] += xi * yj * (sign if k >= n else 1)
    return z


def carries(z: list[int], B: int = 10) -> list[dict]:
    """Carry propagation sum z_k B^k -> base-B digits (rows k, z_k, t = z_k + carry, digit, carry)."""
    rows, c, k = [], 0, 0
    while k < len(z) or c:
        zk = z[k] if k < len(z) else 0
        t = zk + c
        rows.append({"k": k, "z": zk, "t": t, "d": t % B, "c": t // B})
        c = t // B
        k += 1
    return rows


def _terms(x: list[int], y: list[int], k: int) -> list[tuple[int, int]]:
    return [(x[i], y[k - i]) for i in range(len(x)) if 0 <= k - i < len(y)]


class Convolution(Task):
    id = "arithmetic.convolution"
    title_ru = "Линейная, циклическая и негациклическая свёртки"
    topics = ("arithmetic.convolution",)
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("The cyclic length n is drawn from [max(M, N), M + N - 1]: n = M + N - 1 (no wrap-around, "
             "cyclic = linear) is kept as a valid case; preset 'wrap' forces n < M + N - 1.")
    presets = {"default": {"len_lo": 2, "len_hi": 4, "wrap_only": False},
               "wrap": {"wrap_only": True}}
    statement = (r"Пусть $x$ и $y$ "
                 r"--- последовательности десятичных цифр чисел $a = \VAR{a}$ и $b = \VAR{b}$ "
                 r"(младшие цифры первыми). Найти: а)~линейную свёртку $x * y$; б)~циклическую "
                 r"и негациклическую свёртки длины $n = \VAR{n}$ (дополнив $x$ и $y$ нулями до длины $n$); "
                 r"в)~все длины $L$, при которых циклическая свёртка длины $L$ дополненных нулями "
                 r"последовательностей совпадает с линейной, и наименьшую такую длину "
                 r"--- степень двойки; г)~произведение $ab$ по линейной свёртке с помощью переносов.")
    solution = (r"$x = (\VAR{x|join(', ')})$, $M = \VAR{M}$; $y = (\VAR{y|join(', ')})$, $N = \VAR{N}$."
                r"\par а) $z_k = \sum_{i + j = k} x_i y_j$, $k = 0, \dots, M + N - 2 = \VAR{M + N - 2}$:"
                r"\[\begin{array}{c|l|r}"
                r"k & \sum_{i+j=k} x_i y_j & z_k \\ \hline "
                r"\BLOCK{for r in lin_rows}\VAR{r.k} & \VAR{r.expr} & \VAR{r.z} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"$x * y = (\VAR{z|join(', ')})$."
                r"\par б) Циклическая свёртка длины $n$ "
                r"--- это линейная, «свёрнутая» по модулю $n$: $\tilde z_k = z_k + z_{k+n}$, "
                r"негациклическая: $\hat z_k = z_k - z_{k+n}$ "
                r"(умножение многочленов по модулю $t^n - 1$ и $t^n + 1$; $z_m = 0$ при $m > \VAR{M + N - 2}$):"
                r"\[\begin{array}{c|\BLOCK{for _ in range(n)}r\BLOCK{endfor}}"
                r"k\BLOCK{for k in range(n)} & \VAR{k}\BLOCK{endfor} \\ \hline "
                r"z_k\BLOCK{for v in z[:n]} & \VAR{v}\BLOCK{endfor} \\ "
                r"z_{k+n}\BLOCK{for v in zhi} & \VAR{v}\BLOCK{endfor} \\ \hline "
                r"\tilde z_k\BLOCK{for v in cyc} & \VAR{v}\BLOCK{endfor} \\ "
                r"\hat z_k\BLOCK{for v in nega} & \VAR{v}\BLOCK{endfor}"
                r"\end{array}\]"
                r"\BLOCK{if wraps}Так как $n = \VAR{n} < M + N - 1 = \VAR{M + N - 1}$, \BLOCK{if n == M + N - 2}старший коэффициент "
                r"$z_{\VAR{n}}$ «заворачивается»\BLOCK{else}старшие коэффициенты "
                r"$z_{\VAR{n}}, \dots, z_{\VAR{M + N - 2}}$ «заворачиваются»\BLOCK{endif} на младшие позиции, и "
                r"циклическая свёртка \emph{не} совпадает с линейной."
                r"\BLOCK{else}Так как $n = M + N - 1$, заворачивания нет: циклическая и негациклическая "
                r"свёртки совпадают с линейной.\BLOCK{endif}"
                r" Проверка по определению: $\tilde z_k = \sum_{i + j \equiv k\ (\mathrm{mod}\ n)} x_i y_j$"
                r"\BLOCK{if wraps}, например $\tilde z_{0} = \VAR{cyc_check}$\BLOCK{endif}."
                r"\par в) Линейная свёртка имеет $M + N - 1 = \VAR{M + N - 1}$ коэффициентов. При $L \ge M + N - 1$ "
                r"для дополненных нулями последовательностей $x_i y_j \ne 0$ только при $i + j \le M + N - 2 < L$, "
                r"поэтому сравнение $i + j \equiv k\ (\mathrm{mod}\ L)$ равносильно равенству $i + j = k$ "
                r"и циклическая свёртка совпадает с линейной; при $L < M + N - 1$ коэффициент "
                r"$z_{M+N-2} = x_{M-1} y_{N-1} \ne 0$ заворачивается на позицию $M + N - 2 - L$ и "
                r"последний коэффициент линейной свёртки теряется. Ответ: $L \ge \VAR{M + N - 1}$, "
                r"наименьшая степень двойки $L = \VAR{L}$."
                r"\par г) $ab = \sum_k z_k 10^k$; переносы ($t = z_k + c$, цифра $t \bmod 10$, "
                r"новый перенос $c = \lfloor t/10 \rfloor$):"
                r"\[\begin{array}{c|\BLOCK{for _ in carry_rows}r\BLOCK{endfor}}"
                r"k\BLOCK{for r in carry_rows} & \VAR{r.k}\BLOCK{endfor} \\ \hline "
                r"z_k\BLOCK{for r in carry_rows} & \VAR{r.z}\BLOCK{endfor} \\ "
                r"t\BLOCK{for r in carry_rows} & \VAR{r.t}\BLOCK{endfor} \\ "
                r"\text{цифра}\BLOCK{for r in carry_rows} & \VAR{r.d}\BLOCK{endfor} \\ "
                r"c\BLOCK{for r in carry_rows} & \VAR{r.c}\BLOCK{endfor}"
                r"\end{array}\]"
                r"\[\VAR{a} \cdot \VAR{b} = \VAR{product}.\]")

    def sample(self, rng):
        M = rng.randint(self.cfg.len_lo, self.cfg.len_hi)
        N = rng.randint(self.cfg.len_lo, self.cfg.len_hi)
        a = rng.randrange(10 ** (M - 1), 10**M)
        b = rng.randrange(10 ** (N - 1), 10**N)
        x, y = digits10(a), digits10(b)
        hi = M + N - 2 if self.cfg.wrap_only else M + N - 1
        n = rng.randint(max(M, N), hi)
        z = linear_conv(x, y)
        zz = z + [0] * (2 * n - len(z))
        zhi = zz[n:2 * n]
        cyc = [zz[k] + zz[k + n] for k in range(n)]
        nega = [zz[k] - zz[k + n] for k in range(n)]
        lin_rows = [{"k": k, "z": z[k],
                     "expr": " + ".join(rf"{u} \cdot {v}" for u, v in _terms(x, y, k))}
                    for k in range(len(z))]
        cyc_check = " + ".join(rf"x_{{{i}}} y_{{{j}}}" for i in range(M) for j in range(N)
                               if (i + j) % n == 0) + f" = {cyc[0]}"
        L = 1
        while L < M + N - 1:
            L *= 2
        rows = carries(z)
        return {"a": a, "b": b, "x": x, "y": y, "M": M, "N": N, "n": n, "z": z, "zhi": zhi,
                "cyc": cyc, "nega": nega, "wraps": n < M + N - 1, "lin_rows": lin_rows,
                "cyc_check": cyc_check, "L": L, "carry_rows": rows, "product": a * b,
                "answer": {"linear": z, "cyclic": cyc, "negacyclic": nega, "L": L, "product": a * b}}

    def check(self, p):
        x, y, n = p["x"], p["y"], p["n"]
        assert max(len(x), len(y)) <= n <= len(x) + len(y) - 1
        ans = p["answer"]
        # linear convolution = coefficients of the product polynomial: evaluate at 10 and at 1000
        assert sum(c * 10**k for k, c in enumerate(ans["linear"])) == p["a"] * p["b"] == ans["product"]
        X = sum(c * 1000**k for k, c in enumerate(x))
        Y = sum(c * 1000**k for k, c in enumerate(y))
        assert sum(c * 1000**k for k, c in enumerate(ans["linear"])) == X * Y
        assert ans["cyclic"] == cyclic_conv(x, y, n, 1)
        assert ans["negacyclic"] == cyclic_conv(x, y, n, -1)
        assert (ans["cyclic"] == ans["linear"] + [0] * (n - len(ans["linear"]))) == (not p["wraps"])
        L = ans["L"]
        assert L & (L - 1) == 0 and L >= len(x) + len(y) - 1 > L // 2
        assert cyclic_conv(x, y, L) == ans["linear"] + [0] * (L - len(ans["linear"]))
        digits = [r["d"] for r in p["carry_rows"]]
        assert sum(d * 10**k for k, d in enumerate(digits)) == ans["product"]


# --- DFT over a small prime field ------------------------------------------------------


def dft(v: list[int], w: int, p: int) -> list[int]:
    n = len(v)
    return [sum(v[j] * pow(w, j * k, p) for j in range(n)) % p for k in range(n)]


def _sum_lines(v: list[int], wp: list[int], n: int, sign: int, p: int, name: str) -> list[dict]:
    """Rows 'name_k = sum v_j w^{sign*jk} = raw = value (mod p)', skipping zero terms."""
    out = []
    for k in range(n):
        terms = [(v[j], wp[(sign * j * k) % n]) for j in range(n) if v[j]]
        raw = sum(a * b for a, b in terms)
        parts = [rf"{a} \cdot {b}" for a, b in terms]
        # at most 4 products per line (length 8 transforms): continue on the next line
        chunks = [" + ".join(parts[i:i + 4]) for i in range(0, len(parts), 4)]
        expr = r" \\ &\qquad + ".join(chunks) or "0"
        out.append({"k": k, "name": name, "expr": expr, "raw": raw, "val": raw % p})
    return out


class DFTSmall(Task):
    id = "arithmetic.dft_small"
    title_ru = "ДПФ над конечным полем и теорема о свёртке"
    topics = ("arithmetic.convolution",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Given candidate omega_0 always satisfies omega_0^n = 1; with probability bad_root_ratio "
             "its order is a proper divisor of n (not a principal root: the student must notice and "
             "take g^((p-1)/n)). Sequence lengths may exceed n/2 (wrap-around), coefficients may "
             "exceed p: the answer is the cyclic convolution mod p, and the solution says whether it "
             "equals the integer linear convolution. Preset 'bad_root' always gives a bad candidate, "
             "'n8' uses length 8.")
    presets = {"default": {"n": 4, "primes": [13, 17, 29, 37, 41], "bad_root_ratio": 0.3, "vmax": 9},
               "bad_root": {"bad_root_ratio": 1.0},
               "n8": {"n": 8, "primes": [17, 41, 73, 89, 97]}}
    statement = (r"В поле $\mathbb{F}_{\VAR{p}}$ дан элемент $\omega_0 = \VAR{cand}$. "
                 r"а)~Проверить, является ли $\omega_0$ главным корнем степени $n = \VAR{n}$ из единицы; "
                 r"если нет, найти такой корень $\omega$ в виде $g^{(p-1)/n}$, где $g$ "
                 r"--- первообразный корень. "
                 r"б)~Вычислить ДПФ $X = \mathrm{DFT}_\omega(x)$, $Y = \mathrm{DFT}_\omega(y)$ для "
                 r"$x = (\VAR{x|join(', ')})$, $y = (\VAR{y|join(', ')})$, поточечное произведение $Z = XY$ "
                 r"и обратное ДПФ $z = \mathrm{DFT}^{-1}_\omega(Z)$. "
                 r"в)~Проверить ответ по теореме о свёртке, вычислив циклическую свёртку $x \circledast y$ "
                 r"непосредственно. Совпадает ли $z$ с линейной свёрткой $x * y$ над $\mathbb{Z}$?")
    solution = (r"а) $p - 1 = \VAR{pm1}$ делится на $n = \VAR{n}$. Так как $n$ "
                r"--- степень двойки и $n$ обратимо в $\mathbb{F}_{\VAR{p}}$, $\omega$ "
                r"--- главный корень степени $n$ тогда и только тогда, когда $\omega^{n/2} = -1$ "
                r"(в поле это равносильно тому, что порядок $\omega$ равен ровно $n$). "
                r"Степени $\omega_0$: $\BLOCK{for v in cand_pows}\omega_0^{\VAR{loop.index}} \equiv \VAR{v}"
                r"\BLOCK{if not loop.last},\ \BLOCK{endif}\BLOCK{endfor}$. "
                r"\BLOCK{if cand_ok}$\omega_0^{\VAR{n // 2}} \equiv \VAR{p - 1} = -1$, значит $\omega = \omega_0$ "
                r"--- главный корень (порядок $\VAR{n}$)."
                r"\BLOCK{else}$\omega_0^{\VAR{n}} = 1$, но $\omega_0^{\VAR{n // 2}} \equiv \VAR{cand_half} \ne -1$: "
                r"порядок $\omega_0$ равен $\VAR{cand_order} < n$, и, например, "
                r"$\sum_{j=0}^{\VAR{n - 1}} \omega_0^{\VAR{cand_order} j} = \VAR{n} \not\equiv 0$, т.\,е. "
                r"$\omega_0$ \emph{не} является главным корнем (такое «ДПФ» необратимо). "
                r"Первообразный корень: $g = \VAR{g}$, так как "
                r"\BLOCK{for c in g_checks}$\VAR{g}^{\VAR{c.e}} \equiv \VAR{c.v} \ne 1$"
                r"\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor} (показатели $(p-1)/q$ для простых "
                r"$q \mid p - 1$). Тогда $\omega = g^{(p-1)/n} = \VAR{g}^{\VAR{(p - 1) // n}} \equiv \VAR{w}$, "
                r"$\omega^{\VAR{n // 2}} \equiv \VAR{p - 1} = -1$.\BLOCK{endif}"
                r"\par Нужные константы (по модулю $\VAR{p}$): $\omega^{-1} = \omega^{\VAR{n - 1}} \equiv \VAR{wi}$, "
                r"$n^{-1} \equiv \VAR{ni}$ ($\VAR{n} \cdot \VAR{ni} = \VAR{n * ni} \equiv 1$). Степени "
                r"$\omega^m$ (показатель $jk$ берётся по модулю $n$):"
                r"\[\begin{array}{c|\BLOCK{for _ in range(n)}r\BLOCK{endfor}}"
                r"m\BLOCK{for m in range(n)} & \VAR{m}\BLOCK{endfor} \\ \hline "
                r"\omega^m\BLOCK{for v in wpow} & \VAR{v}\BLOCK{endfor}"
                r"\end{array}\]"
                r"б) $X_k = \sum_j x_j \omega^{jk}$, $Y_k = \sum_j y_j \omega^{jk}$ (нулевые слагаемые опущены):"
                r"\[\begin{aligned}"
                r"\BLOCK{for r in X_lines}X_{\VAR{r.k}} &= \VAR{r.expr} = \VAR{r.raw}\BLOCK{if r.raw != r.val} \equiv \VAR{r.val}\BLOCK{endif}, \\ "
                r"\BLOCK{endfor}"
                r"\BLOCK{for r in Y_lines}Y_{\VAR{r.k}} &= \VAR{r.expr} = \VAR{r.raw}\BLOCK{if r.raw != r.val} \equiv \VAR{r.val}\BLOCK{endif}"
                r"\BLOCK{if not loop.last}, \\ \BLOCK{else}.\BLOCK{endif}\BLOCK{endfor}"
                r"\end{aligned}\]"
                r"Поточечное произведение $Z_k = X_k Y_k \bmod \VAR{p}$:"
                r"\[\begin{array}{c|\BLOCK{for _ in range(n)}r\BLOCK{endfor}}"
                r"k\BLOCK{for k in range(n)} & \VAR{k}\BLOCK{endfor} \\ \hline "
                r"X_k\BLOCK{for v in X} & \VAR{v}\BLOCK{endfor} \\ "
                r"Y_k\BLOCK{for v in Y} & \VAR{v}\BLOCK{endfor} \\ \hline "
                r"Z_k\BLOCK{for v in Z} & \VAR{v}\BLOCK{endfor}"
                r"\end{array}\]"
                r"Обратное ДПФ: $u_j = \sum_k Z_k \omega^{-jk}$, $\omega^{-jk} = \omega^{(-jk) \bmod n}$, "
                r"$z_j = n^{-1} u_j = \VAR{ni} \cdot u_j$:"
                r"\[\begin{aligned}"
                r"\BLOCK{for r in U_lines}u_{\VAR{r.k}} &= \VAR{r.expr} = \VAR{r.raw}\BLOCK{if r.raw != r.val} \equiv \VAR{r.val}\BLOCK{endif}"
                r"\BLOCK{if not loop.last}, \\ \BLOCK{else};\BLOCK{endif}\BLOCK{endfor}"
                r"\end{aligned}\]"
                r"\[\begin{array}{c|\BLOCK{for _ in range(n)}r\BLOCK{endfor}}"
                r"j\BLOCK{for k in range(n)} & \VAR{k}\BLOCK{endfor} \\ \hline "
                r"u_j\BLOCK{for r in U_lines} & \VAR{r.val}\BLOCK{endfor} \\ "
                r"z_j = \VAR{ni} u_j\BLOCK{for v in zres} & \VAR{v}\BLOCK{endfor}"
                r"\end{array}\]"
                r"Итак, $z = (\VAR{zres|join(', ')})$."
                r"\par в) Непосредственно: $(x \circledast y)_k = \sum_{i + j \equiv k\ (\mathrm{mod}\ \VAR{n})} x_i y_j$. "
                r"Линейная свёртка $\ell = x * y = (\VAR{lin|join(', ')})$\BLOCK{if wraps}; её коэффициенты с номерами "
                r"$\ge \VAR{n}$ заворачиваются: $(x \circledast y)_k = \ell_k + \ell_{k + \VAR{n}}$\BLOCK{endif}:"
                r"\[x \circledast y = (\VAR{cyc|join(', ')}) \equiv (\VAR{cyc_mod|join(', ')}) "
                r"\pmod{\VAR{p}},\]"
                r"что совпадает с $z$ (теорема о свёртке). "
                r"\BLOCK{if matches}Здесь $\VAR{la} + \VAR{lb} - 1 \le n$ и все коэффициенты меньше $p$, поэтому "
                r"$z$ \emph{совпадает} с линейной свёрткой над $\mathbb{Z}$."
                r"\BLOCK{else}Однако $z$ \emph{не совпадает} с линейной свёрткой над $\mathbb{Z}$: "
                r"\BLOCK{if wraps}длина линейной свёртки $\VAR{la} + \VAR{lb} - 1 = \VAR{la + lb - 1} > n$ "
                r"(заворачивание)\BLOCK{if overflow}; кроме того, \BLOCK{else}.\BLOCK{endif}\BLOCK{endif}"
                r"\BLOCK{if overflow}коэффициент $\VAR{maxc} \ge p$ известен лишь по модулю $p$.\BLOCK{endif}"
                r" Чтобы получить линейную свёртку, нужны $n \ge \VAR{la + lb - 1}$ и $p > \max_k (x * y)_k$."
                r"\BLOCK{endif}")

    def sample(self, rng):
        n, half = self.cfg.n, self.cfg.n // 2
        p = rng.choice(self.cfg.primes)
        assert (p - 1) % n == 0
        good = [w for w in range(2, p) if pow(w, half, p) == p - 1]
        bad = [w for w in range(2, p) if pow(w, n, p) == 1 and pow(w, half, p) == 1]
        cand_ok = rng.random() >= self.cfg.bad_root_ratio
        cand = rng.choice(good if cand_ok else bad)
        g = primitive_root(p)
        g_checks = [{"e": (p - 1) // q, "v": pow(g, (p - 1) // q, p)} for q in sorted(factorize(p - 1))]
        w = cand if cand_ok else pow(g, (p - 1) // n, p)
        cand_order = next(d for d in range(1, n + 1) if pow(cand, d, p) == 1)
        wpow = [pow(w, m, p) for m in range(n)]
        wi, ni = inverse(w, p), inverse(n, p)

        def seq(length):
            v = [rng.randint(0, self.cfg.vmax) for _ in range(length - 1)] + [rng.randint(1, self.cfg.vmax)]
            return v + [0] * (n - length)

        la, lb = rng.randint(2, half + 1), rng.randint(2, half + 1)
        x, y = seq(la), seq(lb)
        X_lines = _sum_lines(x, wpow, n, 1, p, "X")
        Y_lines = _sum_lines(y, wpow, n, 1, p, "Y")
        X = [r["val"] for r in X_lines]
        Y = [r["val"] for r in Y_lines]
        Z = [a * b % p for a, b in zip(X, Y)]
        U_lines = _sum_lines(Z, wpow, n, -1, p, "u")
        zres = [ni * r["val"] % p for r in U_lines]
        lin = linear_conv(x[:la], y[:lb])
        cyc = cyclic_conv(x[:la], y[:lb], n)
        wraps = la + lb - 1 > n
        overflow = max(lin) >= p
        return {"p": p, "pm1": p - 1, "n": n, "cand": cand, "cand_ok": cand_ok,
                "cand_pows": [pow(cand, m, p) for m in range(1, n + 1)],
                "cand_half": pow(cand, half, p), "cand_order": cand_order,
                "g": g, "g_checks": g_checks, "w": w, "wi": wi, "ni": ni, "wpow": wpow,
                "x": x, "y": y, "la": la, "lb": lb, "X_lines": X_lines, "Y_lines": Y_lines,
                "X": X, "Y": Y, "Z": Z, "U_lines": U_lines, "zres": zres, "lin": lin, "cyc": cyc,
                "cyc_mod": [c % p for c in cyc], "wraps": wraps, "overflow": overflow,
                "maxc": max(lin), "matches": not wraps and not overflow,
                "answer": {"omega": w, "X": X, "Y": Y, "Z": Z, "z": zres}}

    def check(self, p):
        P, n, w = p["p"], p["n"], p["w"]
        # principal root by the definition: w^n = 1 and all geometric sums vanish
        assert pow(w, n, P) == 1
        assert all(sum(pow(w, j * k, P) for j in range(n)) % P == 0 for k in range(1, n))
        cand = p["cand"]
        cand_principal = all(sum(pow(cand, j * k, P) for j in range(n)) % P == 0 for k in range(1, n))
        assert pow(cand, n, P) == 1 and cand_principal == p["cand_ok"]
        assert (w == cand) == p["cand_ok"]
        assert w * p["wi"] % P == 1 and n * p["ni"] % P == 1
        ans = p["answer"]
        assert ans["X"] == dft(p["x"], w, P) and ans["Y"] == dft(p["y"], w, P)
        # inverse transform really inverts, and the convolution theorem holds
        assert [p["ni"] * v % P for v in dft(ans["X"], p["wi"], P)] == p["x"]
        direct = [c % P for c in cyclic_conv(p["x"], p["y"], n)]
        assert ans["z"] == direct
        assert p["lin"] == linear_conv(p["x"][:p["la"]], p["y"][:p["lb"]])
        if p["matches"]:
            assert ans["z"] == p["lin"] + [0] * (n - len(p["lin"]))
        else:
            assert len(p["lin"]) > n or max(p["lin"]) >= P
