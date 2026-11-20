"""Additional convolution and FFT tasks: quotient rings, radix-2 traces, exactness and cost models."""

from math import log2

from taskgen.core.task import SolutionDetail, Task
from taskgen.tasks.arithmetic.convolution import carries, cyclic_conv, linear_conv


def poly_tex(cs: list[int]) -> str:
    out = ""
    for i, c in enumerate(cs):
        if not c:
            continue
        x = "1" if i == 0 else "x" if i == 1 else rf"x^{{{i}}}"
        term = str(abs(c)) if i == 0 else (x if abs(c) == 1 else rf"{abs(c)}{x}")
        if not out:
            out = ("-" if c < 0 else "") + term
        else:
            out += (" - " if c < 0 else " + ") + term
    return out or "0"


def seq_tex(v: list[int]) -> str:
    return "(" + ", ".join(map(str, v)) + ")"


class ConvolutionQuotient(Task):
    id = "arithmetic.convolution_quotient"
    title_ru = "Свёртки и умножение в кольцах $R[x]/(x^n\\pm1)$"
    topics = ("arithmetic.convolution",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"lo": 2, "hi": 3, "vmax": 4}}
    statement = (r"Даны многочлены $A(x)=\VAR{A_tex}$ и $B(x)=\VAR{B_tex}$ с целыми коэффициентами. "
                 r"Вычислить: а)~обычное произведение $A(x)B(x)$; б)~остатки этого произведения по модулям "
                 r"$x^{\VAR{n}}-1$ и $x^{\VAR{n}}+1$. Объяснить, почему полученные коэффициенты являются "
                 r"соответственно циклической и негациклической свёртками коэффициентов $A$ и $B$. "
                 r"Какова наименьшая длина циклической свёртки, позволяющая восстановить обычное произведение "
                 r"без заворачивания коэффициентов?")
    solution = (r"Обычное произведение имеет коэффициенты $z_k=\sum_{i+j=k}a_ib_j$:"
                 r"\[A(x)B(x)=\VAR{prod_tex},\qquad z=\VAR{lin_tex}.\] "
                 r"В кольце $\mathbb Z[x]/(x^{\VAR{n}}-1)$ справедливо $x^{k+\VAR{n}}=x^k$, "
                 r"а в кольце $\mathbb Z[x]/(x^{\VAR{n}}+1)$ --- $x^{k+\VAR{n}}=-x^k$. Поэтому коэффициенты "
                 r"с номерами $k$ и $k+\VAR{n}$ складываются в первом случае и вычитаются во втором:"
                 r"\[\begin{array}{c|c|c}"
                 r"k & z_k+z_{k+\VAR{n}} & z_k-z_{k+\VAR{n}}\\\hline "
                 r"\BLOCK{for r in folds}\VAR{r.k} & \VAR{r.plus} & \VAR{r.minus}"
                 r"\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}\end{array}.\] "
                 r"Таким образом, остатки равны $\VAR{prod_cyc_tex}$ и $\VAR{prod_nega_tex}$, "
                 r"а их коэффициентные последовательности --- $\VAR{cyc_tex}$ и $\VAR{nega_tex}$. "
                 r"Обычная свёртка имеет $\VAR{need}$ коэффициентов. При длине $L\geq\VAR{need}$ заворачивания "
                 r"нет; при $L=\VAR{need}-1$ ненулевой старший коэффициент заворачивается. "
                 r"\[\boxed{L_{\min}=\VAR{need}}.\]")

    def sample(self, rng):
        la, lb = rng.randint(self.cfg.lo, self.cfg.hi), rng.randint(self.cfg.lo, self.cfg.hi)
        a = [rng.randint(1, self.cfg.vmax) for _ in range(la)]
        b = [rng.randint(1, self.cfg.vmax) for _ in range(lb)]
        n = max(la, lb)
        lin = linear_conv(a, b)
        cyc = cyclic_conv(a, b, n, 1)
        nega = cyclic_conv(a, b, n, -1)
        zz = lin + [0] * (2 * n - len(lin))
        folds = [{"k": k, "plus": zz[k] + zz[k + n], "minus": zz[k] - zz[k + n]} for k in range(n)]
        return {"A_tex": poly_tex(a), "B_tex": poly_tex(b), "n": n, "lin": lin,
                "prod_tex": poly_tex(lin), "lin_tex": seq_tex(lin), "folds": folds,
                "prod_cyc_tex": poly_tex(cyc), "prod_nega_tex": poly_tex(nega),
                "cyc_tex": seq_tex(cyc), "nega_tex": seq_tex(nega), "need": la + lb - 1,
                "answer": {"linear": lin, "cyclic": cyc, "negacyclic": nega, "min_length": la + lb - 1}}

    def check(self, p):
        n = p["n"]
        assert len(p["answer"]["linear"]) == p["need"]
        assert p["answer"]["cyclic"] == [r["plus"] for r in p["folds"]]
        assert p["answer"]["negacyclic"] == [r["minus"] for r in p["folds"]]
        assert p["answer"]["min_length"] > n


def bit_reverse(v: list[int]) -> list[int]:
    n = len(v)
    bits = n.bit_length() - 1
    return [v[int(f"{i:0{bits}b}"[::-1], 2)] for i in range(n)]


def fft_stages(v: list[int], w: int, p: int) -> tuple[list[int], list[dict]]:
    a = bit_reverse(v)
    n = len(a)
    stages = []
    size = 2
    while size <= n:
        half = size // 2
        wlen = pow(w, n // size, p)
        for start in range(0, n, size):
            for j in range(half):
                u = a[start + j]
                z = a[start + j + half] * pow(wlen, j, p) % p
                a[start + j] = (u + z) % p
                a[start + j + half] = (u - z) % p
        stages.append({"size": size, "values": list(a)})
        size *= 2
    return a, stages


def dft(v: list[int], w: int, p: int) -> list[int]:
    return [sum(v[j] * pow(w, j * k, p) for j in range(len(v))) % p for k in range(len(v))]


class FFTRadix2(Task):
    id = "arithmetic.fft_radix2"
    title_ru = "Быстрое преобразование Фурье по основанию два"
    topics = ("arithmetic.convolution",)
    complexity = 3
    solution_detail = SolutionDetail.FULL
    notes = "Fixed field F_17, length 8 and omega=2; complete butterfly traces for both inputs."
    presets = {"default": {"vmax": 4}}
    statement = (r"В поле $\mathbb F_{17}$ заданы дополненные нулями последовательности "
                 r"$x=\VAR{x_tex}$ и $y=\VAR{y_tex}$. Вычислить их циклическую свёртку длины $8$ "
                 r"с помощью БПФ по основанию два с $\omega=2$. Показать перестановку битовой инверсии "
                 r"и все три ступени бабочек для каждого входа, поточечное произведение и обратное преобразование. "
                 r"Проверить результат прямым вычислением.")
    solution = (r"Так как $2^8\equiv1$ и $2^4\equiv-1\pmod{17}$, элемент $2$ имеет порядок $8$. "
                 r"После битовой инверсии получаем $x^{(0)}=\VAR{xbr_tex}$ и $y^{(0)}=\VAR{ybr_tex}$. "
                 r"На ступени длины $2s$ используются пары $(u,v)\mapsto(u+\omega^{8j/(2s)}v,"
                 r"u-\omega^{8j/(2s)}v)\pmod{17}$:"
                 r"\[\begin{array}{c|l|l}"
                 r"\text{длина} & \text{преобразование }x & \text{преобразование }y\\\hline "
                 r"\BLOCK{for s in stages}\VAR{s.size} & \VAR{s.A_tex} & \VAR{s.B_tex}"
                 r"\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}\end{array}.\] "
                 r"Поточечно $C_k=A_kB_k\bmod17$: $C=\VAR{C_tex}$. Для обратного преобразования "
                 r"$\omega^{-1}=9$, $8^{-1}=15\pmod{17}$ и "
                 r"$c_j=15\sum_{k=0}^7C_k9^{jk}\bmod17$. Получаем $c=\VAR{answer_tex}$. "
                 r"Прямое вычисление $c_j=\sum_{i+l\equiv j\pmod8}x_iy_l$ даёт тот же вектор. "
                 r"БПФ использует $(8/2)\log_28=12$ бабочек (24 сложения) вместо $8^2=64$ "
                 r"произведений прямого матричного преобразования. \[\boxed{c=\VAR{answer_tex}}.\]")

    def sample(self, rng):
        x = [rng.randint(0, self.cfg.vmax) for _ in range(4)] + [0] * 4
        y = [rng.randint(0, self.cfg.vmax) for _ in range(4)] + [0] * 4
        A, sa = fft_stages(x, 2, 17)
        B, sb = fft_stages(y, 2, 17)
        stages = [{"size": a["size"], "A": a["values"], "B": b["values"],
                   "A_tex": seq_tex(a["values"]), "B_tex": seq_tex(b["values"])}
                  for a, b in zip(sa, sb)]
        C = [a * b % 17 for a, b in zip(A, B)]
        c = [15 * v % 17 for v in dft(C, 9, 17)]
        return {"x": x, "y": y, "x_tex": seq_tex(x), "y_tex": seq_tex(y),
                "xbr": bit_reverse(x), "ybr": bit_reverse(y),
                "xbr_tex": seq_tex(bit_reverse(x)), "ybr_tex": seq_tex(bit_reverse(y)),
                "stages": stages, "A": A, "B": B, "C": C, "C_tex": seq_tex(C),
                "answer_tex": seq_tex(c), "answer": c}

    def check(self, p):
        assert pow(2, 8, 17) == 1 and pow(2, 4, 17) == 16
        assert p["A"] == dft(p["x"], 2, 17) and p["B"] == dft(p["y"], 2, 17)
        assert p["answer"] == [x % 17 for x in cyclic_conv(p["x"], p["y"], 8)]


class FFTExactRounding(Task):
    id = "arithmetic.fft_exact_rounding"
    title_ru = "Точное умножение с помощью БПФ и ошибка округления"
    topics = ("arithmetic.convolution", "arithmetic.multiplication")
    complexity = 3
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"lo": 12, "hi": 900}}
    statement = (r"Целые числа $\VAR{a}$ и $\VAR{b}$ умножаются через свёртку их десятичных цифр "
                 r"с помощью БПФ над $\mathbb C$. После обратного преобразования и округления получены "
                 r"коэффициенты $\VAR{conv_tex}$; до округления абсолютная ошибка каждого коэффициента "
                 r"была меньше $\VAR{eps}$. Выбрать длину преобразования, доказать корректность округления "
                 r"и вычислить произведение, выполнив переносы. Затем рассмотреть альтернативную попытку "
                 r"с длиной $N'=\VAR{Nbad}$ и гарантированной ошибкой менее $\VAR{epsbad}$: "
                 r"достаточны ли эти параметры для безусловно точного восстановления?")
    solution = (r"Длина линейной свёртки равна $\VAR{la}+\VAR{lb}-1=\VAR{need}$, поэтому наименьшая "
                 r"допустимая степень двойки --- $N=\VAR{N}$. Для десятичных цифр "
                 r"$0\leq c_k\leq N\cdot9^2=\VAR{bound}$; вычисление над $\mathbb C$ не ограничено модулем. "
                 r"Так как ошибка меньше $\VAR{eps}<1/2$, ближайшее целое к каждому коэффициенту "
                 r"восстанавливается однозначно. \[\VAR{conv_tex}.\] "
                 r"Переносы выполняются по правилу $t_k=c_k+r_k$, цифра $d_k=t_k\bmod10$, "
                 r"$r_{k+1}=\lfloor t_k/10\rfloor$:"
                 r"\[\begin{array}{c|\BLOCK{for _ in carry_rows}r\BLOCK{endfor}}"
                 r"k\BLOCK{for r in carry_rows} & \VAR{r.k}\BLOCK{endfor}\\\hline "
                 r"t_k\BLOCK{for r in carry_rows} & \VAR{r.t}\BLOCK{endfor}\\ "
                 r"d_k\BLOCK{for r in carry_rows} & \VAR{r.d}\BLOCK{endfor}\\ "
                 r"r_{k+1}\BLOCK{for r in carry_rows} & \VAR{r.c}\BLOCK{endfor}"
                 r"\end{array}.\] \[\boxed{\VAR{a}\cdot\VAR{b}=\VAR{answer.product}}.\] "
                 r"В альтернативной попытке $N'=\VAR{Nbad}<\VAR{need}$: старшие коэффициенты "
                 r"заворачиваются. Кроме того, ошибка, ограниченная лишь числом $\VAR{epsbad}>1/2$, "
                 r"может перенести вещественное значение через середину между двумя целыми. "
                 r"Следовательно, ни отсутствие заворачивания, ни однозначное округление не гарантированы.")

    def sample(self, rng):
        a, b = rng.randint(self.cfg.lo, self.cfg.hi), rng.randint(self.cfg.lo, self.cfg.hi)
        da = [int(c) for c in str(a)[::-1]]
        db = [int(c) for c in str(b)[::-1]]
        need = len(da) + len(db) - 1
        N = 1
        while N < need:
            N *= 2
        conv = linear_conv(da, db)
        rows = carries(conv)
        eps, epsbad = rng.choice(["0.12", "0.23", "0.37"]), rng.choice(["0.55", "0.72", "0.90"])
        return {"a": a, "b": b, "la": len(da), "lb": len(db), "need": need, "N": N,
                "Nbad": N // 2, "bound": N * 81, "conv": conv, "conv_tex": seq_tex(conv),
                "eps": eps, "epsbad": epsbad, "carry_rows": rows,
                "answer": {"product": a * b, "alternative_exact": False}}

    def check(self, p):
        assert p["N"] >= p["need"] > p["N"] // 2
        assert p["Nbad"] < p["need"] and float(p["eps"]) < 0.5 < float(p["epsbad"])
        digits = [r["d"] for r in p["carry_rows"]]
        assert sum(d * 10**k for k, d in enumerate(digits)) == p["a"] * p["b"] == p["answer"]["product"]


class FFTModexpCost(Task):
    id = "arithmetic.fft_modexp_cost"
    title_ru = "Выбор алгоритма умножения для модульного возведения в степень"
    topics = ("arithmetic.convolution", "arithmetic.multiplication")
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "Simplified operation-count model; the solution explicitly distinguishes it from benchmarking."
    presets = {"default": {"limbs": [8, 16, 32], "e_lo": 12, "e_hi": 30}}
    statement = (r"В игрушечной RSA-операции вычисляется $a^{\VAR{e}}\bmod m$ бинарным методом слева направо. "
                 r"Операнды содержат $n=\VAR{n}$ машинных слов. Сравнить три реализации одного умножения "
                 r"в упрощённой модели стоимости: школьное --- $n^2$ единиц, Карацуба --- "
                 r"$n^{\log_2 3}$ единиц, БПФ --- $n\log_2n$ единиц. Найти число модульных произведений "
                 r"(возведений в квадрат и умножений на $a$), суммарную стоимость для каждого алгоритма "
                 r"и выбрать наименьшую. Объяснить, почему эта модель не заменяет измерения и не учитывает "
                 r"стоимость модульной редукции.")
    solution = (r"Показатель $\VAR{e}=(\VAR{ebin})_2$ имеет длину $\VAR{h}$ и вес $\VAR{weight}$. "
                 r"После обработки первого бита выполняется $\VAR{h}-1=\VAR{squares}$ возведений в квадрат "
                 r"и $\VAR{weight}-1=\VAR{mults}$ умножений на $a$, всего $\VAR{count}$ произведений. "
                 r"Стоимость одного произведения и общая оценка:"
                 r"\[\begin{array}{c|c|c|c}"
                 r"\text{алгоритм} & \text{одно произведение} & \text{всего} & \text{итог}\\\hline "
                 r"\BLOCK{for r in costs}\VAR{r.name} & \VAR{r.formula} & "
                 r"\VAR{count}\cdot\VAR{r.one} & \VAR{r.total}"
                 r"\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}\end{array}.\] "
                 r"В этой модели выгоднее всего \VAR{best}. На практике константы, память, редукция "
                 r"и размер операндов сдвигают точки перехода, поэтому нужны измерения. Для секретного "
                 r"показателя нельзя допускать зависимости времени и обращений к памяти от его битов. "
                 r"\[\boxed{\text{число произведений: }\VAR{count};\quad\text{выбор модели: \VAR{best}}}.\]")

    def sample(self, rng):
        n = rng.choice(self.cfg.limbs)
        e = rng.randrange(1 << (self.cfg.e_lo - 1), 1 << self.cfg.e_hi)
        h, weight = e.bit_length(), e.bit_count()
        squares, mults = h - 1, weight - 1
        count = squares + mults
        one_fft = n * int(log2(n))
        vals = [("школьное", n * n, rf"{n}^2={n*n}"),
                ("Карацуба", 3**int(log2(n)), rf"{n}^{{\log_2 3}}={3**int(log2(n))}"),
                ("БПФ", one_fft, rf"{n}\cdot{int(log2(n))}={one_fft}")]
        costs = [{"name": name, "one": one, "formula": formula, "total": one * count}
                 for name, one, formula in vals]
        best = min(costs, key=lambda r: r["total"])["name"]
        return {"e": e, "ebin": format(e, "b"), "n": n, "h": h, "weight": weight,
                "squares": squares, "mults": mults, "count": count, "costs": costs, "best": best,
                "answer": {"products": count, "best": best,
                           "totals": {r["name"]: r["total"] for r in costs}}}

    def check(self, p):
        assert p["count"] == p["e"].bit_length() + p["e"].bit_count() - 2
        assert p["answer"]["products"] == p["count"]
        assert min(p["answer"]["totals"].values()) == p["answer"]["totals"][p["best"]]
