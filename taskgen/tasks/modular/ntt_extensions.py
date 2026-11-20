"""NTT validity, parameter selection, exact CRT reconstruction and negacyclic convolution."""

from taskgen.core import steps
from taskgen.core.nt import inverse
from taskgen.core.task import SolutionDetail, Task
from taskgen.tasks.arithmetic.convolution import cyclic_conv
from taskgen.tasks.modular.ntt import ntt


def seq_tex(v: list[int]) -> str:
    return "(" + ", ".join(map(str, v)) + ")"


class NTTPrincipalRoot(Task):
    id = "modular.ntt_principal_root"
    title_ru = "Порядок корня и обратимость ТЧП в составном кольце"
    topics = ("arithmetic.ntt",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    presets = {"default": {}}
    statement = (r"В кольце $\mathbb Z/15\mathbb Z$ рассматривается преобразование длины $n=4$ "
                 r"с $\omega=2$: $A_k=\sum_{j=0}^3a_j2^{jk}\bmod15$. "
                 r"а)~Проверить, что $\omega$ имеет порядок $4$ и что $4$ обратимо по модулю $15$. "
                 r"б)~Вычислить геометрические суммы $\sum_{j=0}^3\omega^{jk}$ для $k=1,2,3$ "
                 r"и проверить условие главного корня. в)~Показать, что преобразование необратимо, "
                 r"найдя ненулевой вектор с нулевым преобразованием. Объяснить, почему в поле "
                 r"аналогичная проверка порядка была бы достаточной, а в кольце~--~нет.")
    solution = (r"Степени $2$ по модулю $15$ равны $2,4,8,1$, поэтому порядок действительно равен $4$. "
                 r"Кроме того, $4^{-1}\equiv4\pmod{15}$. Однако для $k=1,2,3$ геометрические суммы равны "
                 r"\[1+2+4+8=15\equiv0,\qquad1+4+1+4=10\not\equiv0,\qquad1+8+4+2=15\equiv0.\] "
                 r"Условие главного корня нарушено при $k=2$, поэтому стандартное доказательство формулы "
                 r"обращения не проходит. Более того, для $v=(0,5,0,10)$ имеем "
                 r"\[A_0=5+10=15,\quad A_1=2\cdot5+8\cdot10=90,\quad "
                 r"A_2=4\cdot5+4\cdot10=60,\quad A_3=8\cdot5+2\cdot10=60,\] "
                 r"и все четыре значения делятся на $15$. Следовательно, ненулевой вектор $v$ принадлежит ядру "
                 r"и преобразование необратимо. "
                 r"В поле ненулевой многочлен $1+x^k+\dots+x^{(n-1)k}$ степени меньше $n$ не может иметь "
                 r"корень $\omega$ при всех $k\not\equiv0\pmod n$, если порядок $\omega$ равен $n$; "
                 r"в кольце с делителями нуля это рассуждение неприменимо. "
                 r"\[\boxed{\ker\mathrm{NTT}\ne\{0\},\quad v=(0,5,0,10)}.\]")

    def sample(self, rng):
        return {"answer": {"kernel_vector": [0, 5, 0, 10], "bad_sum": 10, "n_inverse": 4}}

    def check(self, p):
        v = p["answer"]["kernel_vector"]
        assert pow(2, 4, 15) == 1 and all(pow(2, d, 15) != 1 for d in range(1, 4))
        assert ntt(v, 2, 15) == [0, 0, 0, 0]
        assert sum(pow(2, 2 * j, 15) for j in range(4)) % 15 == 10


class NTTParameters(Task):
    id = "modular.ntt_parameters"
    title_ru = "Выбор параметров точного ТЧП"
    topics = ("arithmetic.ntt",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"lengths": [4, 8], "vmax": 3}}
    statement = (r"Требуется вычислить циклическую свёртку длины $N=\VAR{N}$ для последовательностей "
                 r"с коэффициентами от $0$ до $\VAR{vmax}$ и восстановить её целые коэффициенты точно. "
                 r"Предложены модули:\[\begin{array}{c|c}\text{вариант} & p\\\hline "
                 r"\BLOCK{for c in candidates}\VAR{c.label} & \VAR{c.p}"
                 r"\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}\end{array}.\] "
                 r"Для каждого варианта проверить существование ТЧП и достаточность модуля. "
                 r"Для подходящего простого $p$ найти корень $\omega=g^{(p-1)/N}$ степени $N$, "
                 r"где $g$ --- первообразный корень, а также $\omega^{-1}$ и $N^{-1}$.")
    solution = (r"Коэффициент циклической свёртки не превосходит "
                 r"$N\cdot\VAR{vmax}^2=\VAR{bound}$. Нужны простое $p>\VAR{bound}$ и условие $N\mid p-1$. "
                 r"\[\begin{array}{c|c|c|l}p & N\mid p-1? & p>\VAR{bound}? & \text{вывод}\\\hline "
                 r"\BLOCK{for c in candidates}\VAR{c.p} & \VAR{c.div_yes} & \VAR{c.bound_yes} & \VAR{c.reason}"
                 r"\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}\end{array}.\] "
                 r"Подходит вариант $\VAR{valid_label}$: $p=\VAR{p}$. Первообразный корень $g=\VAR{g}$, "
                 r"поэтому $\omega=\VAR{g}^{(\VAR{p}-1)/\VAR{N}}=\VAR{g}^{\VAR{exponent}}\equiv\VAR{w}\pmod{\VAR{p}}$. "
                 r"Проверка: $\omega^N\equiv1$, а для каждого простого $q\mid N$ имеем $\omega^{N/q}\not\equiv1$. "
                 r"Обратные элементы: $\omega^{-1}\equiv\VAR{wi}$ и $N^{-1}\equiv\VAR{ni}\pmod{\VAR{p}}$. "
                 r"Так как $p>\VAR{bound}$, после обратного преобразования вычеты совпадают с целыми "
                 r"коэффициентами свёртки. \[\boxed{p=\VAR{p},\quad\omega=\VAR{w},\quad"
                 r"\omega^{-1}=\VAR{wi},\quad N^{-1}=\VAR{ni}}.\]")

    def sample(self, rng):
        N = rng.choice(self.cfg.lengths)
        bound = N * self.cfg.vmax**2
        if N == 4:
            valid, bad_root, bad_bound = 37, 19, 13
        else:
            valid, bad_root, bad_bound = 73, 19, 17
        candidates = [{"p": valid, "kind": "valid"}, {"p": bad_root, "kind": "bad_root"},
                      {"p": bad_bound, "kind": "bad_bound"}]
        rng.shuffle(candidates)
        for i, c in enumerate(candidates):
            p = c["p"]
            div = (p - 1) % N == 0
            large = p > bound
            c.update({"label": chr(ord("A") + i), "div": div, "large": large,
                      "div_yes": "да" if div else "нет", "bound_yes": "да" if large else "нет",
                      "reason": "подходит" if div and large else
                                ("не существует корня нужной степени" if not div else "возможно переполнение")})
        valid_label = next(c["label"] for c in candidates if c["kind"] == "valid")
        g = steps.primitive_root(valid)
        w = pow(g, (valid - 1) // N, valid)
        return {"N": N, "vmax": self.cfg.vmax, "bound": bound, "candidates": candidates,
                "valid_label": valid_label, "p": valid, "g": g, "exponent": (valid - 1) // N,
                "w": w, "wi": inverse(w, valid), "ni": inverse(N, valid),
                "answer": {"label": valid_label, "p": valid, "omega": w,
                           "omega_inverse": inverse(w, valid), "n_inverse": inverse(N, valid)}}

    def check(self, p):
        good = [c for c in p["candidates"] if c["div"] and c["large"]]
        assert len(good) == 1 and good[0]["p"] == p["p"]
        assert p["p"] > p["bound"] and (p["p"] - 1) % p["N"] == 0
        assert pow(p["w"], p["N"], p["p"]) == 1
        assert pow(p["w"], p["N"] // 2, p["p"]) != 1
        assert p["w"] * p["wi"] % p["p"] == 1 and p["N"] * p["ni"] % p["p"] == 1


def ntt_convolution(a: list[int], b: list[int], w: int, p: int) -> dict:
    n = len(a)
    A, B = ntt(a, w, p), ntt(b, w, p)
    C = [x * y % p for x, y in zip(A, B)]
    ni = inverse(n, p)
    c = [ni * x % p for x in ntt(C, inverse(w, p), p)]
    return {"A": A, "B": B, "C": C, "c": c, "ni": ni}


class NTTCRT(Task):
    id = "modular.ntt_crt"
    title_ru = "Точная свёртка по нескольким ТЧП-модулям"
    topics = ("arithmetic.ntt", "number_theory.crt")
    complexity = 3
    solution_detail = SolutionDetail.FULL
    notes = "Length 4, moduli 5, 13, 17; the first two moduli are deliberately insufficient."
    presets = {"default": {"lo": 4, "hi": 6}}
    statement = (r"Вычислить над $\mathbb Z$ циклическую свёртку последовательностей "
                 r"$a=\VAR{a_tex}$ и $b=\VAR{b_tex}$ длины $4$. Для этого выполнить ТЧП по модулям "
                 r"$5,13,17$, получить три набора вычетов и восстановить коэффициенты по китайской теореме "
                 r"об остатках. Доказать, почему произведения только первых двух модулей недостаточно, "
                 r"а произведения всех трёх достаточно. Проверить ответ прямым вычислением.")
    solution = (r"Для каждого $p$ выбран $\omega=g^{(p-1)/4}$; обратное преобразование умножается на $4^{-1}\bmod p$. "
                 r"Преобразования входов и результат $c^{(p)}=a*b\pmod p$:"
                 r"\[\begin{array}{c|c|c|l|l|l}p & \omega & 4^{-1} & \mathrm{NTT}(a) & \mathrm{NTT}(b) & c^{(p)}\\\hline "
                 r"\BLOCK{for r in transforms}\VAR{r.p} & \VAR{r.w} & \VAR{r.ni} & \VAR{r.A_tex} & "
                 r"\VAR{r.B_tex} & \VAR{r.c_tex}\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}\end{array}.\] "
                 r"Прямая свёртка имеет наибольший коэффициент $\VAR{maxc}$. Произведение $5\cdot13=\VAR{P2}<\VAR{maxc}$, "
                 r"поэтому по двум модулям целые коэффициенты не определяются однозначно. Но "
                 r"$P=5\cdot13\cdot17=\VAR{P}>\VAR{maxc}$, и все коэффициенты неотрицательны, значит, "
                 r"восстановление по трём модулям однозначно. Применяем КТО к соответствующим вычетам; "
                 r"например, для коэффициента $c_0$ получаем \VAR{tx.crt(c)} "
                 r"Остальные три коэффициента восстанавливаются по той же формуле из столбцов "
                 r"$\VAR{columns_tex}$. Полученные коэффициенты: $\VAR{answer_tex}$. Прямое вычисление "
                 r"$c_j=\sum_{i+l\equiv j\pmod4}a_ib_l$ подтверждает результат. "
                 r"\[\boxed{c=\VAR{answer_tex}}.\]")

    def sample(self, rng):
        while True:
            a = [rng.randint(self.cfg.lo, self.cfg.hi) for _ in range(4)]
            b = [rng.randint(self.cfg.lo, self.cfg.hi) for _ in range(4)]
            direct = cyclic_conv(a, b, 4)
            if max(direct) > 5 * 13:
                break
        transforms, residues = [], []
        for p in [5, 13, 17]:
            g = steps.primitive_root(p)
            w = pow(g, (p - 1) // 4, p)
            tr = ntt_convolution(a, b, w, p)
            tr.update({"p": p, "g": g, "w": w, "A_tex": seq_tex(tr["A"]),
                       "B_tex": seq_tex(tr["B"]), "c_tex": seq_tex(tr["c"])})
            transforms.append(tr)
            residues.append(tr["c"])
        columns = [[residues[j][i] for j in range(3)] for i in range(4)]
        reconstructed = [steps.crt(col, [5, 13, 17])["x"] for col in columns]
        first = steps.crt(columns[0], [5, 13, 17])
        return {"a": a, "b": b, "a_tex": seq_tex(a), "b_tex": seq_tex(b), "transforms": transforms,
                "residues": residues, "columns": columns, "columns_tex": "; ".join(map(seq_tex, columns)),
                "direct": direct, "maxc": max(direct),
                "P2": 65, "P": 1105, "c": first, "answer_tex": seq_tex(reconstructed), "answer": reconstructed}

    def check(self, p):
        assert p["answer"] == cyclic_conv(p["a"], p["b"], 4) == p["direct"]
        assert p["P2"] < max(p["answer"]) < p["P"]
        for tr in p["transforms"]:
            mod = tr["p"]
            assert tr["c"] == [x % mod for x in p["direct"]]
            assert tr["C"] == [x * y % mod for x, y in zip(tr["A"], tr["B"])]


class NTTNegacyclic(Task):
    id = "modular.ntt_negacyclic"
    title_ru = "Негациклическое ТЧП в кольце $\\mathbb Z_{17}[x]/(x^4+1)$"
    topics = ("arithmetic.ntt", "crypto.lattice")
    complexity = 3
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"vmax": 3}}
    statement = (r"Вычислить произведение многочленов с коэффициентами $a=\VAR{a_tex}$ и $b=\VAR{b_tex}$ "
                 r"в кольце $R=\mathbb Z_{17}[x]/(x^4+1)$, используемом в игрушечных примерах "
                 r"решётчатой криптографии. Применить негациклическое ТЧП с $\psi=2$ и $\omega=\psi^2=4$: "
                 r"выполнить скручивание коэффициентов степенями $\psi$, циклическое ТЧП длины $4$ "
                 r"и обратное скручивание. Проверить ответ прямым приведением по модулю $x^4+1$.")
    solution = (r"В $\mathbb F_{17}$ выполнено $\psi^4=2^4\equiv-1$, поэтому $\psi$ имеет порядок $8$, "
                 r"а $\omega=\psi^2=4$ --- порядок $4$; также $4^{-1}=13$ и $\psi^{-1}=9$. "
                 r"Скрученные входы $\tilde a_i=a_i\psi^i$, $\tilde b_i=b_i\psi^i$: "
                 r"$\tilde a=\VAR{ta_tex}$, $\tilde b=\VAR{tb_tex}$. Их преобразования: "
                 r"$A=\VAR{A_tex}$, $B=\VAR{B_tex}$. Поточечное произведение $C=A_iB_i\bmod17$ равно $\VAR{C_tex}$. "
                 r"Обратное циклическое преобразование даёт "
                 r"$\tilde c_j=13\sum_kC_k4^{-jk}\equiv\VAR{tc_tex}$. Наконец, $c_j=\tilde c_j\psi^{-j}$:"
                 r"\[\boxed{c=\VAR{answer_tex}\pmod{17}}.\] "
                 r"Прямое вычисление: при $i+l\geq4$ член $x^{i+l}$ заменяется на $-x^{i+l-4}$, "
                 r"поэтому $c_j=\sum_{i+l=j}a_ib_l-\sum_{i+l=j+4}a_ib_l$. Оно даёт тот же вектор. "
                 r"Скручивание заменяет вычисления в $\mathbb Z_{17}[x]/(x^4+1)$ циклической свёрткой, "
                 r"но не превращает игрушечные параметры в безопасную решётчатую криптосистему.")

    def sample(self, rng):
        a = [rng.randint(0, self.cfg.vmax) for _ in range(4)]
        b = [rng.randint(0, self.cfg.vmax) for _ in range(4)]
        ta = [x * pow(2, i, 17) % 17 for i, x in enumerate(a)]
        tb = [x * pow(2, i, 17) % 17 for i, x in enumerate(b)]
        tr = ntt_convolution(ta, tb, 4, 17)
        tc = tr["c"]
        c = [x * pow(9, i, 17) % 17 for i, x in enumerate(tc)]
        return {"a": a, "b": b, "a_tex": seq_tex(a), "b_tex": seq_tex(b), "ta": ta, "tb": tb,
                "ta_tex": seq_tex(ta), "tb_tex": seq_tex(tb), "A": tr["A"], "B": tr["B"], "C": tr["C"],
                "A_tex": seq_tex(tr["A"]), "B_tex": seq_tex(tr["B"]), "C_tex": seq_tex(tr["C"]),
                "tc": tc, "tc_tex": seq_tex(tc), "answer_tex": seq_tex(c), "answer": c}

    def check(self, p):
        direct = cyclic_conv(p["a"], p["b"], 4, -1)
        assert p["answer"] == [x % 17 for x in direct]
        assert p["ta"] == [x * pow(2, i, 17) % 17 for i, x in enumerate(p["a"])]
        assert p["tc"] == [x % 17 for x in cyclic_conv(p["ta"], p["tb"], 4)]


TX = r"\BLOCK{import 'macros.tex.j2' as tx}"
NTTCRT.solution = TX + NTTCRT.solution
