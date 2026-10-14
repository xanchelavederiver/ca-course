"""Division with remainder of big integers (lecture sem1/03): Knuth's Algorithm D in base 10."""

from taskgen.core.task import SolutionDetail, Task

BASE = 10


def digits_of(x: int, width: int) -> list[int]:
    """Base-10 digits of x, most significant first, padded with zeros to ``width``."""
    s = str(x).rjust(width, "0")
    assert len(s) == width
    return [int(c) for c in s]


def algorithm_d(u: int, v: int, b: int = BASE) -> dict:
    """Knuth's Algorithm D (TAOCP 4.3.1) with the full hand trace.

    n = len(v) >= 2, m + n = len(u). D1: d = floor(b / (v_{n-1} + 1)), u' = u d (m + n + 1 digits,
    the leading one may be 0), v' = v d (n digits, v'_{n-1} >= b/2). D3: for j = m, ..., 0 the
    estimate q^ = min(floor((u_{j+n} b + u_{j+n-1}) / v'_{n-1}), b - 1) is refined by the test
    q^ v'_{n-2} > b r^ + u_{j+n-2}; D4-D6: subtract q^ v' from the window, add back if negative.
    """
    assert b == BASE
    n = len(str(v))
    assert n >= 2 and u >= v
    m = len(str(u)) - n
    d = b // (v // b ** (n - 1) + 1)
    un, vn = u * d, v * d
    assert len(str(vn)) == n
    vd = digits_of(vn, n)
    v1, v2 = vd[0], vd[1]
    ud = digits_of(un, m + n + 1)        # ud[0] = u_{m+n}
    rows, qdigits = [], []
    rem = un // b ** (m + 1)             # leading n digits (u_{m+n} ... u_{m+1})
    for j in range(m, -1, -1):
        window = rem * b + ud[m - j + n]   # (u_{j+n} ... u_j)
        w = digits_of(window, n + 1)
        top = w[0] * b + w[1]
        raw = top // v1
        chain = [raw]
        qh = min(raw, b - 1)
        if qh != raw:
            chain.append(qh)
        rh = top - qh * v1
        test_steps = 0
        while rh < b and qh * v2 > b * rh + w[2]:
            qh -= 1
            rh += v1
            test_steps += 1
            chain.append(qh)
        prod = qh * vn
        addback = prod > window
        q = qh - 1 if addback else qh
        rem = window - q * vn
        assert 0 <= rem < vn and 0 <= q < b
        rows.append({"j": j, "window": str(window).rjust(n + 1, "0"), "top": top, "raw": raw,
                     "chain": chain, "qhat0": min(raw, b - 1), "qhat": qh, "tested": test_steps,
                     "prod": prod, "addback": addback, "q": q,
                     "rem": str(rem).rjust(n, "0")})
        qdigits.append(q)
    quotient = int("".join(map(str, qdigits)))
    return {"n": n, "m": m, "d": d, "un": un, "vn": vn, "v1": v1, "v2": v2,
            "un_digits": ud, "rows": rows, "q": quotient, "rn": rem, "r": rem // d}


class LongDivision(Task):
    id = "arithmetic.long_division"
    title_ru = "Деление с остатком: алгоритм D Кнута"
    topics = ("arithmetic.division",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Base 10, normalization, the two-digit estimate q^ capped at 9, Knuth's v_{n-2} test and "
             "the add-back step D6. `correction_ratio` of the instances have at least one corrected "
             "estimate and `addback_ratio` an add-back step (natural rates ~2/3 and ~1/9); "
             "`norm_ratio` of the instances need a normalization factor d > 1 (otherwise d = 1 is kept); "
             "preset `corrections` forces both kinds of correction (the test and add-back).")
    presets = {
        "default": {"u_digits": [7, 8], "v_digits": [3, 4], "correction_ratio": 0.5,
                    "addback_ratio": 0.25, "need_test": False, "norm_ratio": 0.7},
        "long": {"u_digits": [8, 9], "v_digits": [3, 4]},
        "corrections": {"correction_ratio": 1.0, "addback_ratio": 1.0, "need_test": True},
    }
    statement = (r"Разделить с остатком $u = \VAR{u}$ на $v = \VAR{v}$ по алгоритму D Кнута в десятичной "
                 r"системе: выполнить нормализацию, для каждой цифры частного найти оценку $\hat q$ по двум "
                 r"старшим цифрам текущего остатка и старшей цифре делителя, уточнить её по второй цифре "
                 r"делителя, выполнить вычитание (с возвратом, если нужно). Найти частное и остаток.")
    solution = (r"$n = \VAR{n}$ (длина делителя), $m = \VAR{m}$ (частное имеет $m + 1 = \VAR{m + 1}$ цифр). "
                r"\textbf{Нормализация:} $d = \lfloor 10/(v_{n-1} + 1) \rfloor = \lfloor 10/\VAR{v // 10 ** (n - 1) + 1} "
                r"\rfloor = \VAR{d}$\BLOCK{if d == 1} (старшая цифра делителя уже не меньше $5$)\BLOCK{endif}, "
                r"$u' = \VAR{d} u = \VAR{un_digits|join('')}$ ($m + n + 1$ цифр), $v' = \VAR{d} v = \VAR{vn}$; "
                r"$v'_{n-1} = \VAR{v1} \ge 5$, $v'_{n-2} = \VAR{v2}$."
                r"\par \textbf{Шаги} $j = \VAR{m}, \dots, 0$. Окно $U = (u'_{j+n} \dots u'_j)$; "
                r"$\hat q = \min(\lfloor (u'_{j+n} \cdot 10 + u'_{j+n-1}) / \VAR{v1} \rfloor, 9)$; пока "
                r"$\hat r = (u'_{j+n} \cdot 10 + u'_{j+n-1}) - \hat q \cdot \VAR{v1} < 10$ и "
                r"$\hat q \cdot \VAR{v2} > 10\hat r + u'_{j+n-2}$, уменьшаем $\hat q$ (стрелки в столбце "
                r"$\hat q$); затем $U - \hat q v'$, при отрицательной разности "
                r"--- возврат: $q_j = \hat q - 1$ (${}^{*}$)."
                r"\[\begin{array}{c|c|l|r|c|c}"
                r"j & U & \hat q & \hat q v' & q_j & U - q_j v' \\ \hline "
                r"\BLOCK{for r in rows}\VAR{r.j} & \VAR{r.window} & \VAR{r.chain|join(' \\to ')} & \VAR{r.prod} & "
                r"\VAR{r.q}\BLOCK{if r.addback}^{*}\BLOCK{endif} & \VAR{r.rem} \\ \BLOCK{endfor}"
                r"\end{array}\]"
                r"\BLOCK{if rows|selectattr('addback')|list}${}^{*}$ "
                r"--- $\hat q v' > U$: шаг D6, $\hat q$ уменьшено на $1$, к остатку прибавлено $v'$. \BLOCK{endif}"
                r"Частное $q = \VAR{q}$ (цифры $q_j$ сверху вниз), остаток $r = r'/d = \VAR{rn}/\VAR{d} = \VAR{r}$."
                r"\par Проверка: $\VAR{q} \cdot \VAR{v} + \VAR{r} = \VAR{u}$, $0 \le \VAR{r} < \VAR{v}$."
                r"\[q = \VAR{q}, \qquad r = \VAR{r}.\]")

    def sample(self, rng):
        cfg = self.cfg
        want_correction = rng.random() < cfg.correction_ratio
        want_addback = rng.random() < cfg.addback_ratio
        want_norm = rng.random() < cfg.norm_ratio
        while True:
            nv = rng.choice(cfg.v_digits)
            nu = rng.choice(cfg.u_digits)
            v = rng.randrange(10 ** (nv - 1), 10**nv)
            u = rng.randrange(10 ** (nu - 1), 10**nu)
            if nu - nv < 3:
                continue
            if want_norm and v // 10 ** (nv - 1) >= 5:
                continue
            tr = algorithm_d(u, v)
            corrected = [r for r in tr["rows"] if r["qhat0"] != r["q"]]
            if want_correction and not corrected:
                continue
            if cfg.need_test and not any(r["tested"] for r in tr["rows"]):
                continue
            if want_addback and not any(r["addback"] for r in tr["rows"]):
                continue
            break
        return {"u": u, "v": v, **tr, "answer": {"q": tr["q"], "r": tr["r"]}}

    def check(self, p):
        u, v = p["u"], p["v"]
        q, r = p["answer"]["q"], p["answer"]["r"]
        assert (q, r) == divmod(u, v)                 # independent route: built-in division
        assert p["vn"] * p["d"] // p["d"] == p["vn"] and p["v1"] >= 5
        assert p["rn"] == p["d"] * r
        for row in p["rows"]:
            # Knuth's theorem B: q^ - 2 <= q <= q^ for the two-digit estimate,
            # and after the v_{n-2} test the estimate is off by at most one.
            assert row["qhat0"] - 2 <= row["q"] <= row["qhat0"]
            assert row["q"] <= row["qhat"] <= row["q"] + 1
            assert row["addback"] == (row["qhat"] == row["q"] + 1)
        assert len(p["rows"]) == p["m"] + 1 and 3 <= p["m"] + 1 <= 7
