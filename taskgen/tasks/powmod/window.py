"""Sliding-window exponentiation and addition chains (lecture sem1/06).

powmod.sliding_window: left-to-right sliding-window method with window width k = 2 or 3
(precomputed odd powers a, a^3, ..., a^{2^k - 1}); presets "runs" (exponents made of long runs
of ones, where windows pay off most) and "pow2" (e = 2^j: the precomputation is wasted).
powmod.addition_chain: a chain shorter than the binary one for small e, used to compute a^e mod m.
"""

import math

from taskgen.core.task import SolutionDetail, Task

MOD = r"\ (\textrm{mod}\ \VAR{m})"


# --- helpers ------------------------------------------------------------------------------


def sliding_windows(e: int, k: int) -> list[str]:
    """Split the binary digits of e (most significant first) into windows: a single '0', or a
    string of length <= k that starts and ends with '1' (the longest such)."""
    bits, i, out = format(e, "b"), 0, []
    while i < len(bits):
        if bits[i] == "0":
            out.append("0")
            i += 1
            continue
        j = min(i + k, len(bits))
        while bits[j - 1] == "0":
            j -= 1
        out.append(bits[i:j])
        i = j
    return out


def sliding_window_pow(a: int, e: int, m: int, k: int) -> dict:
    """Trace of the sliding-window method a^e mod m (a already reduced)."""
    a2 = a * a % m
    table = {1: a}
    for d in range(3, 1 << k, 2):
        table[d] = table[d - 2] * a2 % m
    windows = sliding_windows(e, k)
    rows, r, ex = [], None, 0
    for i, w in enumerate(windows):
        d = int(w, 2)
        if i == 0:
            r, ex = table[d], d
            rows.append({"w": w, "sq": [], "d": d, "r": r, "e": ex})
            continue
        sq = []
        for _ in w:
            r = r * r % m
            sq.append(r)
        ex <<= len(w)
        if d:
            r = r * table[d] % m
            ex += d
        rows.append({"w": w, "sq": sq, "d": d if d else None, "r": r, "e": ex})
    n_bits = e.bit_length()
    pre_sq, pre_mul = 1, (1 << (k - 1)) - 1
    main_sq = n_bits - len(windows[0])
    main_mul = sum(1 for w in windows[1:] if w != "0")
    return {"a2": a2, "table": [{"d": d, "v": v} for d, v in table.items()], "windows": windows,
            "rows": rows, "result": r, "pre_sq": pre_sq, "pre_mul": pre_mul,
            "sq": pre_sq + main_sq, "mul": pre_mul + main_mul,
            "bin_sq": n_bits - 1, "bin_mul": bin(e).count("1") - 1}


def _runs_exponent(rng, n_lo: int, n_hi: int) -> int:
    """Random exponent of n_lo..n_hi-1 bits made of runs of ones (length 3..6) separated by
    short runs of zeros (length 1..2)."""
    target = rng.randrange(n_lo, n_hi)
    bits = ""
    while len(bits) < target:
        bits += "1" * rng.randint(3, 6)
        if len(bits) < target:
            bits += "0" * rng.randint(1, 2)
    return int(bits[:target], 2)


# --- sliding window -------------------------------------------------------------------------


class SlidingWindowPow(Task):
    id = "powmod.sliding_window"
    title_ru = "Возведение в степень методом скользящего окна"
    topics = ("powmod",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Window width k = 2 or 3. Presets: 'runs' — exponents made of long runs of ones "
             "(the windows pay off); 'pow2' — e = 2^j (corner case: only squarings, the "
             "precomputation is wasted and the binary method is better).")
    presets = {
        "default": {"m_lo": 300, "m_hi": 500, "ks": [2, 3], "shape": "random",
                    "e_lo": 300, "e_hi": 2048},
        "runs": {"shape": "runs", "n_lo": 9, "n_hi": 12},
        "pow2": {"shape": "pow2", "j_lo": 7, "j_hi": 11},
    }
    statement = (r"Вычислить \[\VAR{a}^{\VAR{e}}" + MOD + r"\] методом скользящего окна ширины "
                 r"$k = \VAR{k}$ (предвычисляются нечётные степени "
                 r"$\BLOCK{if k == 2}a, a^3\BLOCK{else}a, a^3, a^5, a^7\BLOCK{endif}$). "
                 r"Подсчитать число возведений в квадрат и умножений (вместе с предвычислением) и сравнить с бинарным алгоритмом.")
    solution = (r"$e = \VAR{e} = \VAR{e|bin}_2$. Предвычисление: $a^2 = \VAR{w.a2}$, "
                r"\BLOCK{for t in w.table[1:]}$a^{\VAR{t.d}} = \VAR{t.v}$\BLOCK{if not loop.last}, "
                r"\BLOCK{endif}\BLOCK{endfor} "
                r"(возведений в квадрат: $\VAR{w.pre_sq}$, умножений: $\VAR{w.pre_mul}$). "
                r"\par Биты просматриваются слева направо: нулевой бит "
                r"--- окно <<$0$>> (одно возведение в квадрат); единичный бит открывает окно длины "
                r"не больше $\VAR{k}$, оканчивающееся единицей; окно $w$ длины $s$: "
                r"$r \gets r^{2^s} \cdot a^{w}$ (первое окно: $r \gets a^{w}$). Окна: "
                r"\[\BLOCK{for x in w.windows}\VAR{x}\BLOCK{if not loop.last}\,|\,\BLOCK{endif}"
                r"\BLOCK{endfor}\]"
                r"\[\begin{array}{c|l|c|r|r}"
                r"\text{окно} & r^2, r^4, \dots & \text{множитель} & r & e \\ \hline "
                r"\BLOCK{for s in w.rows}\VAR{s.w} & "
                r"\BLOCK{if s.sq}\VAR{s.sq|join(',\\ ')}\BLOCK{else}\text{---}\BLOCK{endif} & "
                r"\BLOCK{if s.d is none}\text{---}\BLOCK{elif s.d == 1}a\BLOCK{else}a^{\VAR{s.d}}\BLOCK{endif} & "
                r"\VAR{s.r} & \VAR{s.e} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"Число операций (вместе с предвычислением):"
                r"\[\begin{array}{l|c|c|c} & \text{квадраты} & \text{умножения} & \text{всего} \\ \hline "
                r"\text{окно } k = \VAR{k} & \VAR{w.sq} & \VAR{w.mul} & \VAR{w.sq + w.mul} \\ "
                r"\text{бинарный} & \VAR{w.bin_sq} & \VAR{w.bin_mul} & \VAR{w.bin_sq + w.bin_mul} \\ "
                r"\end{array}\]"
                r"\BLOCK{if w.sq + w.mul < w.bin_sq + w.bin_mul}Экономия метода окна: "
                r"$\VAR{w.bin_sq + w.bin_mul - w.sq - w.mul}$."
                r"\BLOCK{elif w.sq + w.mul == w.bin_sq + w.bin_mul}Выигрыша нет: показатель "
                r"слишком мал (или содержит мало единиц), и предвычисление не окупается."
                r"\BLOCK{else}Бинарный алгоритм лучше: \BLOCK{if e == 2**(e.bit_length() - 1)}"
                r"при $e = 2^{\VAR{e.bit_length() - 1}}$ нужны только возведения в квадрат, "
                r"\BLOCK{else}в показателе мало единиц, \BLOCK{endif}"
                r"и предвычисление не окупается.\BLOCK{endif}"
                r"\[\VAR{a}^{\VAR{e}} \equiv \VAR{answer}" + MOD + r".\]")

    def sample(self, rng):
        cfg = self.cfg
        m = rng.randrange(cfg.m_lo, cfg.m_hi)
        a = rng.randrange(2, m - 1)
        k = rng.choice(cfg.ks)
        if cfg.shape == "runs":
            e = _runs_exponent(rng, cfg.n_lo, cfg.n_hi)
        elif cfg.shape == "pow2":
            e = 2 ** rng.randrange(cfg.j_lo, cfg.j_hi)
        else:
            e = rng.randrange(cfg.e_lo, cfg.e_hi)
        w = sliding_window_pow(a, e, m, k)
        return {"a": a, "e": e, "m": m, "k": k, "w": w, "answer": w["result"]}

    def check(self, p):
        a, e, m, k, w = p["a"], p["e"], p["m"], p["k"], p["w"]
        assert p["answer"] == pow(a, e, m)
        assert "".join(w["windows"]) == format(e, "b")
        for x in w["windows"]:
            assert x == "0" or (len(x) <= k and x[0] == x[-1] == "1"), x
        for row in w["rows"]:  # every intermediate value is a^{e_row} mod m
            assert row["r"] == pow(a, row["e"], m)
        assert w["rows"][-1]["e"] == e
        for t in w["table"]:
            assert t["v"] == pow(a, t["d"], m) and t["d"] % 2 == 1
        sq = 1 + sum(len(row["sq"]) for row in w["rows"])
        mul = len(w["table"]) - 1 + sum(1 for row in w["rows"][1:] if row["d"] is not None)
        assert (sq, mul) == (w["sq"], w["mul"])


# --- addition chains --------------------------------------------------------------------------


def shortest_chain(n: int) -> list[int]:
    """A shortest addition chain 1 = c_0 < c_1 < ... < c_L = n (iterative deepening DFS)."""
    if n == 1:
        return [1]
    chain = [1]

    def dfs(limit: int) -> bool:
        last = chain[-1]
        if last == n:
            return True
        steps_left = limit - (len(chain) - 1)
        if steps_left == 0 or last << steps_left < n:
            return False
        cands = sorted({x + y for i, x in enumerate(chain) for y in chain[i:]
                        if last < x + y <= n}, reverse=True)
        for c in cands:
            chain.append(c)
            if dfs(limit):
                return True
            chain.pop()
        return False

    limit = math.ceil(math.log2(n))
    while not dfs(limit):
        limit += 1
    return list(chain)


def binary_chain(n: int) -> list[int]:
    """The addition chain of the left-to-right binary method."""
    chain = [1]
    for bit in format(n, "b")[1:]:
        chain.append(2 * chain[-1])
        if bit == "1":
            chain.append(chain[-1] + 1)
    return chain


def chain_rows(chain: list[int], a: int, m: int) -> list[dict]:
    """For each element c_i = c_j + c_k (j >= k) the power a^{c_i} mod m."""
    vals, rows = {1: a % m}, []
    for i, c in enumerate(chain[1:], 1):
        j, k = next((x, c - x) for x in reversed(chain[:i]) if c - x in chain[:i])
        vals[c] = vals[j] * vals[k] % m
        rows.append({"i": i, "c": c, "j": j, "k": k, "v": vals[c], "sq": j == k})
    return rows


class AdditionChain(Task):
    id = "powmod.addition_chain"
    title_ru = "Аддитивные цепочки"
    topics = ("powmod",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Only exponents for which the binary chain is not optimal; the solution shows a "
             "shortest chain (found by exhaustive search) and the lower bound ceil(log2 e).")
    presets = {"default": {"e_lo": 15, "e_hi": 256, "m_lo": 300, "m_hi": 500}}
    statement = (r"Построить аддитивную цепочку для $e = \VAR{e}$, соответствующую бинарному "
                 r"алгоритму, и найти более короткую аддитивную цепочку. С её помощью вычислить "
                 r"\[\VAR{a}^{\VAR{e}}" + MOD + r".\]")
    solution = (r"$e = \VAR{e|bin}_2$. Бинарный алгоритм (слева направо: удвоение, при бите $1$ "
                r"ещё прибавление единицы) даёт цепочку "
                r"\[\VAR{binary|join(',\\ ')}\]"
                r"длины $\lambda(e) + \nu(e) - 1 = \VAR{lam} + \VAR{nu} - 1 = \VAR{binary|length - 1}$ "
                r"($\lambda(e) = \lfloor \log_2 e \rfloor$, $\nu(e)$ --- число единиц). "
                r"Более короткая цепочка длины $\VAR{chain|length - 1}$:"
                r"\[\VAR{chain|join(',\\ ')}.\]"
                r"Она кратчайшая: нижняя оценка $\ell(e) \ge \lceil \log_2 e \rceil = \VAR{lb}$"
                r"\BLOCK{if lb < chain|length - 1}, а полный перебор цепочек длины "
                r"$\VAR{chain|length - 2}$ показывает, что их не существует\BLOCK{endif}. "
                r"Вычисления по цепочке ($c_i = c_j + c_k$, $a^{c_i} = a^{c_j} a^{c_k}$):"
                r"\[\begin{array}{c|c|r}"
                r"i & c_i = c_j + c_k & a^{c_i} \bmod \VAR{m} \\ \hline "
                r"0 & 1 & \VAR{a} \\ "
                r"\BLOCK{for s in rows}\VAR{s.i} & \VAR{s.c} = \VAR{s.j} + \VAR{s.k}"
                r"\BLOCK{if s.sq}\ (\text{кв.})\BLOCK{endif} & \VAR{s.v} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"\[\VAR{a}^{\VAR{e}} \equiv \VAR{answer}" + MOD + r".\]")

    def sample(self, rng):
        cfg = self.cfg
        while True:
            e = rng.randrange(cfg.e_lo, cfg.e_hi)
            chain, binary = shortest_chain(e), binary_chain(e)
            if len(chain) < len(binary):
                break
        m = rng.randrange(cfg.m_lo, cfg.m_hi)
        a = rng.randrange(2, m - 1)
        rows = chain_rows(chain, a, m)
        return {"a": a, "e": e, "m": m, "chain": chain, "binary": binary, "rows": rows,
                "lam": e.bit_length() - 1, "nu": bin(e).count("1"),
                "lb": math.ceil(math.log2(e)), "answer": rows[-1]["v"]}

    def check(self, p):
        a, e, m, chain, binary = p["a"], p["e"], p["m"], p["chain"], p["binary"]
        for c in (chain, binary):
            assert c[0] == 1 and c[-1] == e
            for i in range(1, len(c)):
                assert any(c[i] - x in c[:i] for x in c[:i]), (c, i)
        assert len(binary) - 1 == (e.bit_length() - 1) + bin(e).count("1") - 1
        assert (e - 1).bit_length() <= len(chain) - 1 < len(binary) - 1
        for row in p["rows"]:
            assert row["v"] == pow(a, row["c"], m)
        assert p["answer"] == pow(a, e, m)
