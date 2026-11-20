"""Additional LFSR representations, jump-ahead, finite-prefix ambiguity and a Geffe attack."""

from taskgen.core.task import SolutionDetail, Task
from taskgen.tasks.crypto.lfsr import (berlekamp_massey, bits_tex, companion, gauss_jordan_gf2,
                                       is_primitive, lfsr_bits, mat_tex, mat_vec, pmod, pmul,
                                       poly_from_taps, ptex, taps_from_poly)


def primitive_poly(rng, degree: int) -> int:
    candidates = [f for f in range(1 << degree, 1 << (degree + 1)) if f & 1 and is_primitive(f)]
    return rng.choice(candidates)


def state_tex(state: list[int]) -> str:
    return "(" + ", ".join(map(str, state)) + ")"


class LFSRGalois(Task):
    id = "crypto.lfsr_galois"
    title_ru = "Преобразование РСЛОС Фибоначчи в форму Галуа"
    topics = ("crypto.lfsr",)
    complexity = 3
    solution_detail = SolutionDetail.FULL
    notes = "The Galois update and observability equations are stated explicitly to avoid tap-convention ambiguity."
    presets = {"default": {"degrees": [3, 4]}}
    statement = (r"РСЛОС Фибоначчи имеет характеристический многочлен $f(x)=\VAR{f_tex}$ "
                 r"и рекуррентность $\VAR{rec}$. Начальное состояние "
                 r"$S_0=(s_0,\ldots,s_{\VAR{L}-1})=\VAR{S0_tex}$. Рассматривается регистр Галуа "
                 r"$G=(g_0,\ldots,g_{\VAR{L}-1})$ с выходом $g_0$ и обновлением "
                 r"\[g_i'=g_{i+1}+c_{i+1}g_0\quad(0\leq i<\VAR{L}-1),\qquad "
                 r"g_{\VAR{L}-1}'=c_{\VAR{L}}g_0\quad\text{в }\mathbb F_2.\] "
                 r"Записать матрицу $B$ этого обновления, проверить, что её характеристический многочлен равен $f$, "
                 r"и найти начальное состояние $G_0$, дающее ту же выходную последовательность, что и регистр Фибоначчи. "
                 r"Проверить совпадение первых $\VAR{check_len}$ выходных бит.")
    solution = (r"Коэффициенты $(c_1,\ldots,c_{\VAR{L}})=\VAR{cs_tex}$. Матрица обновления Галуа: "
                 r"\[B=\VAR{B_tex}.\] Её характеристический многочлен равен $\VAR{f_tex}$: ненулевые элементы "
                 r"над диагональю выполняют сдвиг, а коэффициенты $c_i$ образуют первый столбец. "
                 r"Поскольку $c_{\VAR{L}}=1$, матрица невырождена. Пусть $u=(1,0,\ldots,0)$. "
                 r"Первые $\VAR{L}$ выходов регистра Галуа равны $uB^kG_0$, $k=0,\ldots,\VAR{L}-1$. "
                 r"Приравнивая их к $s_0,\ldots,s_{\VAR{L}-1}$, получаем наблюдаемостную систему "
                 r"\[\VAR{O_tex}G_0=\VAR{rhs_tex}.\] Она невырождена; решение над $\mathbb F_2$: "
                 r"$G_0=\VAR{G0_tex}$. При таком выборе совпадают первые $\VAR{L}$ бит, а одинаковая "
                 r"рекуррентность продолжает совпадение на все следующие позиции. Проверка: "
                 r"Фибоначчи и Галуа выдают \[\VAR{out_tex}.\] "
                 r"\[\boxed{G_0=\VAR{G0_tex}}.\]")

    def sample(self, rng):
        L = rng.choice(self.cfg.degrees)
        f = primitive_poly(rng, L)
        cs = taps_from_poly(f)
        S0 = [rng.randrange(2) for _ in range(L)]
        while not any(S0):
            S0 = [rng.randrange(2) for _ in range(L)]
        fib = lfsr_bits(cs, S0, 3 * L)
        B = [[0] * L for _ in range(L)]
        for i in range(L - 1):
            B[i][0] = cs[i]
            B[i][i + 1] = 1
        B[L - 1][0] = cs[L - 1]
        O = []
        v = [1] + [0] * (L - 1)
        for _ in range(L):
            O.append(list(v))
            v = [sum(v[i] * B[i][j] for i in range(L)) % 2 for j in range(L)]
        augmented = [row + [fib[k]] for k, row in enumerate(O)]
        gj = gauss_jordan_gf2(augmented, L)
        assert gj["rank"] == L
        G0 = [gj["R"][i][L] for i in range(L)]
        gal, state = [], list(G0)
        for _ in range(3 * L):
            gal.append(state[0])
            feedback = state[0]
            state = [state[i + 1] ^ (cs[i] & feedback) for i in range(L - 1)] + [cs[L - 1] & feedback]
        assert gal == fib
        rec = f"s_{{n+{L}}} = " + " + ".join(
            f"s_{{n+{L-j}}}" for j in range(1, L + 1) if cs[j - 1])
        return {"L": L, "f": f, "f_tex": ptex(f), "cs": cs, "cs_tex": state_tex(cs),
                "rec": rec, "S0": S0, "S0_tex": state_tex(S0), "B": B,
                "B_tex": mat_tex(B, small=False), "O": O, "O_tex": mat_tex(O, small=False),
                "rhs_tex": state_tex(fib[:L]) + "^T", "G0": G0, "G0_tex": state_tex(G0),
                "check_len": 3 * L, "fib": fib, "gal": gal, "out_tex": bits_tex(fib),
                "answer": {"initial_state": G0, "output": gal}}

    def check(self, p):
        from sage.all import GF, PolynomialRing, matrix

        R = PolynomialRing(GF(2), "x")
        f = R([p["f"] >> i & 1 for i in range(p["L"] + 1)])
        assert matrix(GF(2), p["B"]).charpoly(R.gen()) == f
        assert p["answer"]["output"] == p["fib"] == p["gal"]
        assert p["fib"] == lfsr_bits(p["cs"], p["S0"], p["check_len"])
        state = p["G0"][:]
        out = []
        for _ in range(p["check_len"]):
            out.append(state[0])
            feedback = state[0]
            state = [state[i + 1] ^ (p["cs"][i] & feedback) for i in range(p["L"] - 1)] + \
                    [p["cs"][-1] & feedback]
        assert out == p["fib"]


class LFSRJump(Task):
    id = "crypto.lfsr_jump"
    title_ru = "Быстрый переход РСЛОС через степень многочлена"
    topics = ("crypto.lfsr",)
    complexity = 3
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"degrees": [4, 5], "n_lo": 35, "n_hi": 110}}
    statement = (r"РСЛОС имеет характеристический многочлен $f(x)=\VAR{f_tex}$ и начальное состояние "
                 r"$S_0=\VAR{S0_tex}$, где $S_n=(s_n,\ldots,s_{n+\VAR{L}-1})^T$. "
                 r"Вычислить $s_{\VAR{N}}$ без последовательного выполнения $\VAR{N}$ шагов и без возведения "
                 r"сопровождающей матрицы в степень. Для этого найти $r(x)=x^{\VAR{N}}\bmod f(x)$ "
                 r"бинарным возведением многочлена в степень и использовать $S_{\VAR{N}}=r(A)S_0$. "
                 r"Сравнить сложность с матричным методом.")
    solution = (r'По теореме Кэли"--~Гамильтона $f(A)=0$, поэтому при вычислении $A^{\VAR{N}}S_0$ '
                 r"достаточно знать остаток $r(x)=x^{\VAR{N}}\bmod f(x)$. Бинарное возведение "
                 r"в кольце $\mathbb F_2[x]/(f)$:"
                 r"\[\begin{array}{c|c|l|l}\text{шаг} & \text{бит} & \text{накопленный остаток} & "
                 r"\text{основание }x^{2^i}\bmod f\\\hline \BLOCK{for r in trace}\VAR{r.i} & \VAR{r.bit} & "
                 r"\VAR{r.acc_tex} & \VAR{r.base_tex}\BLOCK{if not loop.last}\\\BLOCK{endif}\BLOCK{endfor}"
                 r"\end{array}.\] Таким образом, $r(x)=\VAR{r_tex}$. Первые состояния "
                 r"$S_0,AS_0,\ldots,A^{\VAR{L}-1}S_0$:"
                 r"\[\VAR{states_tex}.\] Складывая те $S_i$, для которых коэффициент $r_i=1$, получаем "
                 r"$S_{\VAR{N}}=\VAR{SN_tex}$. Его первая координата равна $\VAR{answer.bit}$. "
                 r"Прямая проверка рекуррентностью подтверждает результат. Полиномиальный метод использует "
                 r"$O(\VAR{L}^2\log\VAR{N})$ битовых операций вместо $O(\VAR{L}^3\log\VAR{N})$ "
                 r"при наивном возведении матрицы в степень. \[\boxed{s_{\VAR{N}}=\VAR{answer.bit}}.\]")

    def sample(self, rng):
        L = rng.choice(self.cfg.degrees)
        f = primitive_poly(rng, L)
        cs = taps_from_poly(f)
        S0 = [rng.randrange(2) for _ in range(L)]
        while not any(S0):
            S0 = [rng.randrange(2) for _ in range(L)]
        N = rng.randint(self.cfg.n_lo, self.cfg.n_hi)
        acc, base, e, trace = 1, 2, N, []
        i = 0
        while e:
            bit = e & 1
            if bit:
                acc = pmod(pmul(acc, base), f)
            trace.append({"i": i, "bit": bit, "acc": acc, "acc_tex": ptex(acc), "base_tex": ptex(base)})
            base = pmod(pmul(base, base), f)
            e >>= 1
            i += 1
        A = companion(cs)
        states = [list(S0)]
        for _ in range(1, L):
            states.append(mat_vec(A, states[-1]))
        SN = [0] * L
        for j in range(L):
            if acc >> j & 1:
                SN = [SN[k] ^ states[j][k] for k in range(L)]
        bit = SN[0]
        return {"L": L, "f": f, "f_tex": ptex(f), "cs": cs, "S0": S0, "S0_tex": state_tex(S0),
                "N": N, "trace": trace, "r": acc, "r_tex": ptex(acc), "states": states,
                "states_tex": r",\; ".join(state_tex(s) + "^T" for s in states),
                "SN": SN, "SN_tex": state_tex(SN) + "^T", "answer": {"bit": bit, "state": SN}}

    def check(self, p):
        direct = lfsr_bits(p["cs"], p["S0"], p["N"] + 1)[p["N"]]
        assert p["answer"]["bit"] == direct == p["SN"][0]
        assert p["r"] == p["trace"][-1]["acc"]


class BerlekampMasseyShort(Task):
    id = "crypto.berlekamp_massey_short"
    title_ru = 'Неоднозначность РСЛОС на коротком префиксе и алгоритм Берлекэмпа"--~Месси'
    topics = ("crypto.lfsr",)
    complexity = 3
    solution_detail = SolutionDetail.FULL
    presets = {"default": {"degrees": [3, 4]}}
    statement = (r"Дана выходная последовательность РСЛОС линейной сложности $\VAR{L}$. "
                 r"а)~По короткому префиксу $\VAR{short_tex}$ доказать, что продолжение не определено однозначно: "
                 r"построить два различных РСЛОС длины $\VAR{L}$, согласованных с префиксом, но дающих разные "
                 r"следующие биты. б)~После раскрытия полного префикса из $2L=\VAR{full_len}$ бит "
                 r'$\VAR{full_tex}$ найти кратчайший РСЛОС алгоритмом Берлекэмпа"--~Месси '
                 r"и объяснить, почему теперь ответ единствен.")
    solution = (r"Короткий префикс имеет длину $\VAR{short_len}<2\VAR{L}$, поэтому он не задаёт "
                 r"$\VAR{L}$ независимых ограничений на все неизвестные параметры и продолжение. "
                 r"Два подходящих характеристических многочлена: "
                 r"\[f_1(x)=\VAR{f1_tex},\qquad f_2(x)=\VAR{f2_tex}.\] "
                 r"С начальными состояниями $\VAR{S1_tex}$ и $\VAR{S2_tex}$ оба регистра выдают "
                 r"префикс $\VAR{short_tex}$, но следующий бит соответственно равен $\VAR{next1}$ и $\VAR{next2}$. "
                 r"Следовательно, по короткой выборке предсказание невозможно обосновать однозначно. "
                 r'Для полного префикса алгоритм Берлекэмпа"--~Месси даёт линейную сложность '
                 r"$\lambda=\VAR{L}$ и многочлен связей $C(x)=\VAR{C_tex}$. Обращение коэффициентов "
                 r"даёт $f(x)=x^{\VAR{L}}C(1/x)=\VAR{f1_tex}$. Проверка рекуррентности подтверждает все "
                 r"$\VAR{full_len}$ бит. Так как теперь наблюдений $2\lambda$, кратчайший РСЛОС единствен. "
                 r"\[\boxed{L=\VAR{L},\quad f(x)=\VAR{f1_tex}}.\]")

    def sample(self, rng):
        L = rng.choice(self.cfg.degrees)
        f1 = primitive_poly(rng, L)
        cs1 = taps_from_poly(f1)
        S1 = [rng.randrange(2) for _ in range(L)]
        while not any(S1):
            S1 = [rng.randrange(2) for _ in range(L)]
        full = lfsr_bits(cs1, S1, 2 * L)
        short_len = L
        if full[:L] == [1] + [0] * (L - 1):
            return self.sample(rng)
        found = False
        for f2 in range((1 << L) | 1, 1 << (L + 1), 2):
            if f2 == f1:
                continue
            cs2 = taps_from_poly(f2)
            for mask in range(1, 1 << L):
                S2 = [(mask >> i) & 1 for i in range(L)]
                other = lfsr_bits(cs2, S2, 2 * L)
                if other[:short_len] == full[:short_len] and other[short_len] != full[short_len]:
                    found = True
                    break
            if found:
                break
        if not found:
            raise ValueError("no alternative LFSR")
        bm = berlekamp_massey(full)
        C = bm["C"]
        return {"L": L, "short_len": short_len, "full_len": 2 * L,
                "short_tex": bits_tex(full[:short_len]), "full_tex": bits_tex(full),
                "f1": f1, "f1_tex": ptex(f1), "f2": f2, "f2_tex": ptex(f2),
                "cs1": cs1, "cs2": cs2, "S1": S1, "S2": S2,
                "S1_tex": state_tex(S1), "S2_tex": state_tex(S2),
                "next1": full[short_len], "next2": other[short_len], "full": full, "other": other,
                "C": C, "C_tex": ptex(C), "answer": {"linear_complexity": L, "polynomial": f1,
                                                      "alternatives": [f1, f2]}}

    def check(self, p):
        k, L = p["short_len"], p["L"]
        assert k < 2 * L and p["full"][:k] == p["other"][:k]
        assert p["full"][k] != p["other"][k]
        assert p["full"] == lfsr_bits(p["cs1"], p["S1"], 2 * L)
        assert p["other"] == lfsr_bits(p["cs2"], p["S2"], 2 * L)
        assert berlekamp_massey(p["full"])["L"] == L


def geffe(x1: list[int], x2: list[int], x3: list[int]) -> list[int]:
    return [(a & b) ^ (b & c) ^ c for a, b, c in zip(x1, x2, x3)]


class GeffeAttack(Task):
    id = "crypto.geffe_attack"
    title_ru = "Корреляционная атака на генератор Джеффе"
    topics = ("crypto.lfsr", "crypto.prng")
    complexity = 3
    solution_detail = SolutionDetail.FULL
    notes = "Instances are accepted only when the true first/third states are unique correlation maxima."
    presets = {"default": {"length": 24}}
    statement = (r"Три РСЛОС длины $3$ имеют характеристические многочлены "
                 r"$f_1=\VAR{f1_tex}$, $f_2=\VAR{f2_tex}$, $f_3=\VAR{f3_tex}$ и неизвестные ненулевые "
                 r"начальные состояния. Их выходы объединяются функцией Джеффе "
                 r"$z=x_1x_2\oplus x_2x_3\oplus x_3$. Известна строка \[\VAR{z_tex}.\] "
                 r"Вычислить корреляции $z$ с $x_1$ и $x_3$, восстановить их состояния перебором "
                 r"по наибольшему числу совпадений, затем перебором состояний второго регистра найти "
                 r"единственную тройку, дающую всю строку. Определить следующий бит.")
    solution = (r"Если $x_2=0$, то $z=x_3$; если $x_2=1$, то $z=x_1x_2\oplus x_2\oplus x_3=x_1$. "
                 r"Для независимых равномерных битов поэтому "
                 r"\[\Pr[z=x_1]=\Pr[z=x_3]=\frac12\cdot1+\frac12\cdot\frac12=\frac34.\] "
                 r"Перебираем $2^3-1=7$ ненулевых состояний первого и третьего регистров. "
                 r"Максимальные числа совпадений дают:"
                 r"\[\begin{array}{c|c|c|c}\text{регистр} & \text{состояние} & \text{совпадения} & "
                 r"\text{лучший результат остальных}\\\hline 1 & \VAR{S1_tex} & \VAR{score1}/\VAR{n} & \VAR{other1}/\VAR{n}\\ "
                 r"3 & \VAR{S3_tex} & \VAR{score3}/\VAR{n} & \VAR{other3}/\VAR{n}\end{array}.\] "
                 r"Максимумы единственны. После восстановления $x_1,x_3$ перебор семи состояний второго "
                 r"регистра оставляет только $S_2=\VAR{S2_tex}$: именно эта тройка воспроизводит все "
                 r"$\VAR{n}$ бит. Следующий бит равен $\VAR{answer.next}$. "
                 r"Нелинейная функция усложнила непосредственное решение системы, но корреляции позволили "
                 r"разделить атаку на три малых перебора. \[\boxed{S_1=\VAR{S1_tex},\ S_2=\VAR{S2_tex},\ "
                 r"S_3=\VAR{S3_tex},\quad z_{\VAR{n}}=\VAR{answer.next}}.\]")

    def sample(self, rng):
        n = self.cfg.length
        for _ in range(10000):
            fs = [primitive_poly(rng, 3) for _ in range(3)]
            css = [taps_from_poly(f) for f in fs]
            states = [[rng.randrange(2) for _ in range(3)] for _ in range(3)]
            states = [s if any(s) else [1, 0, 0] for s in states]
            xs = [lfsr_bits(css[i], states[i], n + 1) for i in range(3)]
            z = geffe(xs[0], xs[1], xs[2])
            rankings = []
            for reg in [0, 2]:
                scored = []
                for mask in range(1, 8):
                    state = [(mask >> i) & 1 for i in range(3)]
                    bits = lfsr_bits(css[reg], state, n)
                    score = sum(a == b for a, b in zip(bits, z[:n]))
                    scored.append((score, mask, state))
                scored.sort(reverse=True)
                true_mask = sum(states[reg][i] << i for i in range(3))
                if scored[0][1] != true_mask or scored[0][0] == scored[1][0]:
                    break
                rankings.append({"score": scored[0][0], "other": scored[1][0]})
            if len(rankings) != 2:
                continue
            candidates = []
            for mask in range(1, 8):
                state = [(mask >> i) & 1 for i in range(3)]
                x2 = lfsr_bits(css[1], state, n)
                if geffe(xs[0][:n], x2, xs[2][:n]) == z[:n]:
                    candidates.append(state)
            if candidates != [states[1]]:
                continue
            return {"f1": fs[0], "f2": fs[1], "f3": fs[2], "f1_tex": ptex(fs[0]),
                    "f2_tex": ptex(fs[1]), "f3_tex": ptex(fs[2]), "css": css, "states": states,
                    "xs": xs, "z": z, "z_tex": bits_tex(z[:n]), "n": n,
                    "S1_tex": state_tex(states[0]), "S2_tex": state_tex(states[1]),
                    "S3_tex": state_tex(states[2]), "score1": rankings[0]["score"],
                    "score3": rankings[1]["score"], "other1": rankings[0]["other"],
                    "other3": rankings[1]["other"], "answer": {"states": states, "next": z[n]}}
        raise ValueError("failed to generate a uniquely solvable Geffe instance")

    def check(self, p):
        n = p["n"]
        assert p["z"] == geffe(*p["xs"])
        for i in range(3):
            assert p["xs"][i] == lfsr_bits(p["css"][i], p["states"][i], n + 1)
        assert p["answer"]["next"] == p["z"][n]
        assert p["score1"] > p["other1"] and p["score3"] > p["other3"]
