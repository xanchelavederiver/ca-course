"""Lenstra's elliptic curve factorization (lecture sem2/10).

Arithmetic on y^2 = x^3 + ax + b "over Z/NZ": the affine addition formulas with all
divisions done modulo N.  A division fails exactly when the denominator d has
gcd(d, N) > 1, and then gcd(d, N) is a divisor of N (Hoffstein–Pipher–Silverman §6.6).

* ``factoring.ec_mod_n_add`` — one pseudo-addition / pseudo-doubling modulo N = pq
  (warm-up); in ~2/5 of the instances the denominator is not invertible (P = -Q or
  a point of order 2 modulo one of the primes) and the answer is a divisor of N.
* ``factoring.lenstra`` — the algorithm itself: Q_k = k Q_{k-1} = k! P by double-and-add
  modulo N until an inverse fails; corner case (~1/5): the first curve gives
  gcd = N, the solution switches to the second curve given in the statement.
"""

from math import factorial, gcd

from taskgen.core import steps
from taskgen.core.nt import is_prime, is_square_mod
from taskgen.core.task import SolutionDetail, Task

ANSWER_PQ = r"\[N = \VAR{answer[0]} \cdot \VAR{answer[1]} = \VAR{n}.\]"
_PRIMES = [p for p in range(11, 60) if is_prime(p)]


def curve_tex(a: int, b: int) -> str:
    out = "x^3"
    if a:
        out += " + x" if a == 1 else f" + {a}x"
    if b:
        out += f" + {b}"
    return out


def euclid_remainders(a: int, b: int) -> list[int]:
    out = [a, b]
    while out[-1]:
        out.append(out[-2] % out[-1])
    return out


def pseudo_add(P, Q, a: int, N: int) -> dict:
    """P + Q (P == Q: doubling) on y^2 = x^3 + ax + b modulo N.

    Returns the denominator ``d`` and ``g = gcd(d, N)``; when g == 1 also the inverse,
    the slope and the result ``R``.  Equal x with P != Q gives d = 0, i.e. g = N.
    """
    (x1, y1), (x2, y2) = P, Q
    if list(P) == list(Q):
        op, d, num = "2R", 2 * y1 % N, 3 * x1 * x1 + a
    else:
        op, d, num = "R+Q", (x2 - x1) % N, y2 - y1
    g = gcd(d, N)
    row = {"op": op, "d": d, "num": num % N, "g": g}
    if g > 1:
        return row
    inv = pow(d, -1, N)
    lam = num * inv % N
    x3 = (lam * lam - x1 - x2) % N
    return {**row, "inv": inv, "lam": lam, "R": [x3, (lam * (x1 - x3) - y1) % N]}


def _mod_r_vanishes(P, Q, doubling: bool, a: int, r: int) -> bool:
    """Is the result of P + Q (or 2P) the point at infinity modulo the prime r?"""
    (x1, y1), (x2, y2) = P, Q
    if doubling:
        return y1 % r == 0
    return (x1 - x2) % r == 0 and (y1 + y2) % r == 0


def lenstra_trace(N: int, a: int, P, primes, kmax: int) -> dict | None:
    """Q_1 = P, Q_k = k Q_{k-1} by left-to-right double-and-add modulo N.

    Returns the trace up to the first non-invertible denominator, or None if there is
    none for k <= kmax or the instance is "unclean" (the denominator vanishes modulo a
    prime r but the true result modulo r is not the point at infinity: equal points
    modulo r added by the chord formula) — such instances do not illustrate the
    ord(P mod r) | m argument and are rejected by the sampler.
    """
    Q, groups = list(P), []
    for k in range(2, kmax + 1):
        R, j, ops = list(Q), 1, []
        bits = format(k, "b")
        for bit in bits[1:]:
            for kind in ("2R", "R+Q") if bit == "1" else ("2R",):
                other = R if kind == "2R" else Q
                st = pseudo_add(R, other, a, N)
                if kind == "R+Q" and st["op"] == "2R":  # R == Q mod N: never in a clean trace
                    return None
                j = 2 * j if kind == "2R" else j + 1
                st["m"] = j * factorial(k - 1)
                ops.append(st)
                for r in primes:
                    if st["d"] % r == 0 and not _mod_r_vanishes(R, other, kind == "2R", a, r):
                        return None
                if st["g"] > 1:
                    groups.append({"k": k, "bits": bits, "ops": ops, "Q": None})
                    return {"groups": groups, "k": k, "fail": st, "g": st["g"], "m": st["m"],
                            "euclid": euclid_remainders(N, st["d"])}
                R = st["R"]
        Q = R
        groups.append({"k": k, "bits": bits, "ops": ops, "Q": Q})
    return None


def _orders(p: int, q: int, a: int, b: int, P) -> list[dict]:
    from sage.all import GF, EllipticCurve

    out = []
    for r in (p, q):
        E = EllipticCurve(GF(r), [a % r, b % r])
        Pr = E(P[0] % r, P[1] % r)
        out.append({"r": r, "card": int(E.order()), "ord": int(Pr.order()),
                    "ord_f": steps.factor_tex(int(Pr.order())) if Pr.order() > 1 else "1"})
    return out


def _sample_curve(rng, p: int, q: int, kmin: int, kmax: int, want_N: bool) -> dict | None:
    N = p * q
    a, x0, y0 = rng.randrange(1, N), rng.randrange(N), rng.randrange(1, N)
    b = (y0 * y0 - x0**3 - a * x0) % N
    disc = (4 * a**3 + 27 * b * b) % N
    if gcd(disc, N) > 1:
        return None
    tr = lenstra_trace(N, a, [x0, y0], (p, q), kmax)
    if tr is None or tr["k"] < kmin or (tr["g"] == N) != want_N:
        return None
    return {"a": a, "b": b, "x": x0, "y": y0, "curve": curve_tex(a, b), "disc": disc,
            "orders": _orders(p, q, a, b, [x0, y0]), **tr}


_TRACE = (r"\[{\small\begin{array}{c|l|r|r|r|r|c}"
          r"k & \text{шаг} & m & d & d^{-1} & \lambda & R = mP \\ \hline "
          r"\BLOCK{for g in c.groups}\BLOCK{for o in g.ops}"
          r"\BLOCK{if loop.first}\VAR{g.k} = \VAR{g.bits}_2\BLOCK{endif} & \VAR{o.op} & \VAR{o.m} & \VAR{o.d} & "
          r"\BLOCK{if o.g > 1}\gcd = \VAR{o.g} & \text{---} & \text{---}\BLOCK{else}\VAR{o.inv} & \VAR{o.lam} & "
          r"(\VAR{o.R[0]}, \VAR{o.R[1]})\BLOCK{endif} \\ \BLOCK{endfor}"
          r"\BLOCK{if g.Q is not none}\hline \BLOCK{endif}\BLOCK{endfor}"
          r"\end{array}}\]")

_CURVE = (r"\BLOCK{macro curve_solution(c, n, name, pt)}"
          r"$b = y_0^2 - x_0^3 - a x_0 = \VAR{c.y}^2 - \VAR{c.x}^3 - \VAR{c.a} \cdot \VAR{c.x} \equiv \VAR{c.b}"
          r"\pmod{\VAR{n}}$, кривая $\VAR{name}\colon y^2 = \VAR{c.curve}$; "
          r"$4a^3 + 27b^2 \equiv \VAR{c.disc}$, $\gcd(\VAR{c.disc}, \VAR{n}) = 1$ "
          r"(кривая невырождена по модулю обоих простых делителей). "
          r"$Q_1 = \VAR{pt} = (\VAR{c.x}, \VAR{c.y})$; строки $k$ "
          r"вычисляют $Q_k = k\,Q_{k-1}$, $Q = Q_{k-1}$, $m$ --- кратность точки $R = mP$ "
          r"после шага, $d$ --- знаменатель:"
          + _TRACE.replace("mP", r"m\VAR{pt}") +
          r"\par Знаменатель $d = \VAR{c.fail.d}$ при $k = \VAR{c.k}$ необратим: "
          r"$\gcd(\VAR{c.fail.d}, \VAR{n}) = \VAR{c.g}$ (остатки алгоритма Евклида: "
          r"$\VAR{c.euclid|join(', ')}$). "
          r"Объяснение: $\#E(\mathbb{F}_{\VAR{c.orders[0].r}}) = \VAR{c.orders[0].card}$, "
          r"$\operatorname{ord}(\VAR{pt} \bmod \VAR{c.orders[0].r}) = \VAR{c.orders[0].ord_f}$; "
          r"$\#E(\mathbb{F}_{\VAR{c.orders[1].r}}) = \VAR{c.orders[1].card}$, "
          r"$\operatorname{ord}(\VAR{pt} \bmod \VAR{c.orders[1].r}) = \VAR{c.orders[1].ord_f}$; "
          r"на последнем шаге вычисляется точка $\VAR{c.m}\VAR{pt}$"
          r"\BLOCK{if c.m_f != c.m|string} ($\VAR{c.m} = \VAR{c.m_f}$)\BLOCK{endif}, и она равна $\mathcal{O}$ по модулю "
          r"\BLOCK{if c.g == n}обоих простых сразу.\BLOCK{else}$\VAR{c.g}$, но не по модулю "
          r"$\VAR{n // c.g}$.\BLOCK{endif}"
          r"\BLOCK{endmacro}")


class Lenstra(Task):
    id = "factoring.lenstra"
    title_ru = "Алгоритм Ленстры (факторизация с помощью эллиптических кривых)"
    topics = ("factoring.ecm",)
    complexity = 3
    solution_detail = SolutionDetail.FULL
    notes = ("N = pq < 2000 (11 <= p, q < 60); the factor appears at k = 3..5 (Q_k = k! P). "
             "Corner case (~1/5): the first curve gives gcd(d, N) = N (both primes at once); "
             "the solution switches to the second curve, which the statement always gives. "
             "Instances where a denominator vanishes mod r without the point vanishing mod r "
             "(equal points added by the chord rule) are rejected.")
    presets = {"default": {"primes": _PRIMES, "n_max": 2000, "kmin": 3, "kmax": 5,
                           "gcd_n_ratio": 0.2},
               # corner case only: the first curve always gives gcd = N
               "gcd_n": {"gcd_n_ratio": 1.0}}
    statement = (r"Найти нетривиальный делитель числа $N = \VAR{n}$ алгоритмом Ленстры. "
                 r"Кривая $E_1\colon y^2 = x^3 + \VAR{c1.a}x + b_1$ над $\mathbb{Z}/N\mathbb{Z}$, "
                 r"где $b_1$ выбрано так, что точка $P_1 = (\VAR{c1.x}, \VAR{c1.y})$ лежит на $E_1$. "
                 r"Вычислять $Q_k = k\,Q_{k-1}$ ($Q_1 = P_1$, т.\,е. $Q_k = k!\,P_1$), $k = 2, 3, \dots$, "
                 r"удвоением"
                 r"-сложением по модулю $N$, пока не встретится необратимый знаменатель. Если "
                 r"алгоритм на $E_1$ не даст нетривиального делителя, взять кривую "
                 r"$E_2\colon y^2 = x^3 + \VAR{c2.a}x + b_2$ с точкой $P_2 = (\VAR{c2.x}, \VAR{c2.y})$.")
    solution = (r"\BLOCK{import 'macros.tex.j2' as tx}" + _CURVE +
                r"Формулы над $\mathbb{Z}/N\mathbb{Z}$: $\lambda = (3x_1^2 + a)/(2y_1)$ (удвоение), "
                r"$\lambda = (y_2 - y_1)/(x_2 - x_1)$ (сложение), $x_3 = \lambda^2 - x_1 - x_2$, "
                r"$y_3 = \lambda(x_1 - x_3) - y_1$. Деление на $d$ --- умножение на $d^{-1} \bmod N$ "
                r"(расширенный алгоритм Евклида для $(N, d)$); если $\gcd(d, N) > 1$, обратного нет, "
                r"и $\gcd(d, N)$ --- делитель $N$. Умножение на $k$ --- слева направо по двоичной "
                r"записи $k$: $R \gets Q$, для каждого следующего бита $R \gets 2R$, при бите $1$ "
                r"ещё $R \gets R + Q$."
                r"\par\medskip\noindent\textbf{Кривая $E_1$.} \VAR{curve_solution(c1, n, 'E_1', 'P_1')}"
                r"\BLOCK{if switched}\par Делитель тривиален ($\gcd = N$): порядки $P_1$ по модулю "
                r"обоих простых делят $\VAR{c1.m}$. Неудача --- берём вторую кривую."
                r"\par\medskip\noindent\textbf{Кривая $E_2$.} \VAR{curve_solution(c2, n, 'E_2', 'P_2')}"
                r"\BLOCK{endif}"
                r"\par Делитель $\VAR{d}$, $N / \VAR{d} = \VAR{n // d}$." + ANSWER_PQ)

    def sample(self, rng):
        cfg = self.cfg
        while True:
            p, q = sorted(rng.sample(cfg.primes, 2))
            if p * q < cfg.n_max:
                break
        switched = rng.random() < cfg.gcd_n_ratio
        curves = []
        for want_N in ((True, False) if switched else (False, False)):
            for _ in range(5000):
                c = _sample_curve(rng, p, q, cfg.kmin if not want_N else 2, cfg.kmax, want_N)
                if c is not None:
                    break
            else:  # this N admits no gcd = N curve with small k: start over with other primes
                return self.sample(rng)
            c["m_f"] = steps.factor_tex(c["m"])
            curves.append(c)
        if not switched:  # the spare curve of the statement: any curve, not used
            curves[1] = {k: curves[1][k] for k in ("a", "x", "y")}
        good = curves[1] if switched else curves[0]
        return {"n": p * q, "c1": curves[0], "c2": curves[1], "switched": switched,
                "d": good["g"], "answer": [p, q]}

    def check(self, p):
        from sage.all import GF, EllipticCurve

        n, (pp, qq) = p["n"], p["answer"]
        assert pp * qq == n and is_prime(pp) and is_prime(qq) and pp != qq
        used = [p["c1"], p["c2"]] if p["switched"] else [p["c1"]]
        for i, c in enumerate(used):
            assert (c["y"] ** 2 - c["x"] ** 3 - c["a"] * c["x"] - c["b"]) % n == 0
            last = i == len(used) - 1
            assert (c["g"] in (pp, qq)) if last else c["g"] == n
            # independent route: Sage's group law over F_r, r = p, q
            for r in (pp, qq):
                E = EllipticCurve(GF(r), [c["a"] % r, c["b"] % r])
                Pr = E(c["x"] % r, c["y"] % r)
                for g in c["groups"]:
                    for o in g["ops"]:
                        mP = o["m"] * Pr
                        if o["g"] == 1:
                            assert not mP.is_zero() and [int(mP[0]), int(mP[1])] == \
                                [o["R"][0] % r, o["R"][1] % r]
                        else:
                            assert mP.is_zero() == (o["g"] % r == 0)
                            assert o["m"] % int(Pr.order()) == 0 or o["g"] % r
        assert p["d"] in (pp, qq) and n % p["d"] == 0



# --- a single pseudo-addition ------------------------------------------------------------


def _crt2(r1: int, m1: int, r2: int, m2: int) -> int:
    return (r1 + m1 * ((r2 - r1) * pow(m1, -1, m2) % m2)) % (m1 * m2)


def _point_mod(rng, r: int, a: int, b: int, avoid_x=()):
    """A random affine point with y != 0 on y^2 = x^3 + ax + b over F_r (rng only)."""
    from sage.all import GF

    for _ in range(1000):
        x = rng.randrange(r)
        if x in avoid_x:
            continue
        rhs = (x**3 + a * x + b) % r
        if rhs and is_square_mod(rhs, r):
            y = int(GF(r)(rhs).sqrt())
            return [x, y if rng.random() < 0.5 else r - y]
    return None


class EcModNAdd(Task):
    id = "factoring.ec_mod_n_add"
    title_ru = "Сложение точек эллиптической кривой по составному модулю"
    topics = ("factoring.ecm", "ecc.group_law")
    complexity = 1
    solution_detail = SolutionDetail.FULL
    notes = ("Modes: chord addition / doubling with an invertible denominator (the answer is a "
             "point), and corner cases (~2/5): Q = -P modulo one prime (the chord denominator "
             "vanishes) or P of order 2 modulo one prime (2y vanishes) — the answer is a divisor.")
    presets = {"default": {"primes": [p for p in range(7, 48) if is_prime(p)], "fail_ratio": 0.4,
                           "double_ratio": 0.5},
               # corner cases only: the denominator is never invertible
               "fail": {"fail_ratio": 1.0}}
    statement = (r"Кривая $y^2 = \VAR{curve}$ рассматривается над $\mathbb{Z}/\VAR{n}\mathbb{Z}$. "
                 r"\BLOCK{if double}Вычислить $2P$ для $P = (\VAR{P[0]}, \VAR{P[1]})$\BLOCK{else}"
                 r"Вычислить $P + Q$ для $P = (\VAR{P[0]}, \VAR{P[1]})$, $Q = (\VAR{Q[0]}, \VAR{Q[1]})$"
                 r"\BLOCK{endif} по обычным формулам с делением по модулю $\VAR{n}$. Если деление "
                 r"невозможно, найти нетривиальный делитель числа $\VAR{n}$.")
    solution = (r"\BLOCK{import 'macros.tex.j2' as tx}"
                r"\BLOCK{if double}Точка лежит\BLOCK{else}Точки лежат\BLOCK{endif} на кривой (проверка подстановкой). "
                r"\BLOCK{if double}Удвоение: $\lambda = \dfrac{3x_1^2 + a}{2y_1}$, знаменатель "
                r"$d = 2 \cdot \VAR{P[1]} \bmod \VAR{n} = \VAR{st.d}$, числитель "
                r"$3 \cdot \VAR{P[0]}^2 + \VAR{a} \equiv \VAR{st.num}$."
                r"\BLOCK{else}Сложение: $\lambda = \dfrac{y_2 - y_1}{x_2 - x_1}$, знаменатель "
                r"$d = \VAR{Q[0]} - \VAR{P[0]} \equiv \VAR{st.d}$, числитель "
                r"$\VAR{Q[1]} - \VAR{P[1]} \equiv \VAR{st.num}$.\BLOCK{endif}"
                r"\BLOCK{if st.g == 1} \VAR{tx.inverse(inv)}"
                r"$\lambda = \VAR{st.num} \cdot \VAR{st.inv} \equiv \VAR{st.lam}$, "
                r"$x_3 = \lambda^2 - x_1 - x_2 \equiv \VAR{st.R[0]}$, "
                r"$y_3 = \lambda(x_1 - x_3) - y_1 \equiv \VAR{st.R[1]}$."
                r"\[\BLOCK{if double}2P\BLOCK{else}P + Q\BLOCK{endif} = (\VAR{st.R[0]}, \VAR{st.R[1]}).\]"
                r"\par Проверка по модулю простых делителей ($\VAR{n} = \VAR{p} \cdot \VAR{q}$): "
                r"приведения ответа \BLOCK{for c in red}$\VAR{tx.pt(c.R)} \in E(\mathbb{F}_{\VAR{c.r}})$\BLOCK{if not loop.last} и "
                r"\BLOCK{endif}\BLOCK{endfor} --- это \BLOCK{if double}удвоенные приведения $P$\BLOCK{else}суммы приведений $P$ и $Q$\BLOCK{endif} (приведение по модулю простого "
                r"делителя сохраняет операцию)."
                r"\BLOCK{else} Алгоритм Евклида для $(\VAR{n}, \VAR{st.d})$: остатки "
                r"$\VAR{euclid|join(', ')}$, т.\,е. $\gcd(\VAR{st.d}, \VAR{n}) = \VAR{st.g} > 1$: "
                r"$\VAR{st.d}$ необратим по модулю $\VAR{n}$, и найден делитель "
                r"$\VAR{st.g}$, $\VAR{n} = \VAR{st.g} \cdot \VAR{n // st.g}$."
                r"\par Причина: по модулю $\VAR{st.g}$ имеем "
                r"\BLOCK{if double}$P \equiv (\VAR{P[0] % st.g}, 0)$ --- точка порядка $2$, и $2P = \mathcal{O}$"
                r"\BLOCK{else}$P \equiv (\VAR{P[0] % st.g}, \VAR{P[1] % st.g})$, $Q \equiv (\VAR{Q[0] % st.g}, "
                r"\VAR{Q[1] % st.g}) = -P$, и $P + Q = \mathcal{O}$\BLOCK{endif}; по модулю "
                r"$\VAR{n // st.g}$ результат --- обычная точка $\VAR{tx.pt(other)}$."
                r"\[\VAR{n} = \VAR{answer[0]} \cdot \VAR{answer[1]}.\]\BLOCK{endif}")

    def sample(self, rng):
        cfg = self.cfg
        p, q = sorted(rng.sample(cfg.primes, 2))
        n = p * q
        fail = rng.random() < cfg.fail_ratio
        double = rng.random() < cfg.double_ratio
        bad = rng.choice([p, q]) if fail else None
        a = rng.randrange(1, n)
        # build P, b (and Q) prime by prime, glue by CRT
        parts = {}
        for r in (p, q):
            while True:
                x, y = rng.randrange(r), rng.randrange(1, r)
                if r == bad and double:
                    y = 0
                br = (y * y - x**3 - a * x) % r
                if (4 * a**3 + 27 * br * br) % r:
                    break
            Pr = [x, y]
            if double:
                Qr = Pr
            elif r == bad:
                Qr = [x, (-y) % r]
            else:
                Qr = _point_mod(rng, r, a % r, br, avoid_x=(x,))
                if Qr is None:
                    return self.sample(rng)
            parts[r] = (Pr, Qr, br)
        P = [_crt2(parts[p][0][i], p, parts[q][0][i], q) for i in (0, 1)]
        Q = [_crt2(parts[p][1][i], p, parts[q][1][i], q) for i in (0, 1)]
        b = _crt2(parts[p][2], p, parts[q][2], q)
        st = pseudo_add(P, Q, a, n)
        assert (st["g"] > 1) == fail
        ctx = {"n": n, "p": p, "q": q, "a": a, "b": b, "curve": curve_tex(a, b), "P": P, "Q": Q,
               "double": double, "st": st, "inv": None, "euclid": [], "red": [], "other": None}
        if fail:
            o = q if st["g"] == p else p
            so = pseudo_add([P[0] % o, P[1] % o], [Q[0] % o, Q[1] % o], a % o, o)
            ctx.update(euclid=euclid_remainders(n, st["d"]), other=so["R"],
                       answer=sorted([st["g"], n // st["g"]]))
        else:
            ctx.update(inv=steps.inverse_rows(st["d"], n),
                       red=[{"r": r, "R": [st["R"][0] % r, st["R"][1] % r]} for r in (p, q)],
                       answer=st["R"])
        return ctx

    def check(self, p):
        from sage.all import GF, EllipticCurve

        n, a, b = p["n"], p["a"], p["b"]
        for X in (p["P"], p["Q"]):
            assert (X[1] ** 2 - X[0] ** 3 - a * X[0] - b) % n == 0
        res = []
        for r in (p["p"], p["q"]):
            assert (4 * a**3 + 27 * b * b) % r
            E = EllipticCurve(GF(r), [a % r, b % r])
            S = E(p["P"][0] % r, p["P"][1] % r) + E(p["Q"][0] % r, p["Q"][1] % r)
            res.append((r, S))
        if p["st"]["g"] == 1:
            for r, S in res:
                assert not S.is_zero() and [int(S[0]), int(S[1])] == [p["answer"][0] % r, p["answer"][1] % r]
        else:
            g = p["st"]["g"]
            assert g in (p["p"], p["q"]) and p["answer"][0] * p["answer"][1] == n
            for r, S in res:
                assert S.is_zero() == (r == g)
