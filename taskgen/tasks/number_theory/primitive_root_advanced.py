"""Primitive-root constructions, Schnorr subgroups, and Galbraith's Algorithm 5."""

from math import gcd

from taskgen.core import steps
from taskgen.core.nt import factorize, first_primes, is_order, is_prime
from taskgen.core.task import SolutionDetail, Task
from taskgen.tasks.number_theory.order import product_tree_order
from taskgen.tasks.number_theory.order_advanced import order_naive
from taskgen.tasks.number_theory.primitive_root import (carmichael, has_primitive_root, lambda_parts,
                                                       phi, root_search)

TX = r"\BLOCK{import 'macros.tex.j2' as tx}"


class PrimitiveRootLift(Task):
    id = "number_theory.primitive_root_lift"
    title_ru = "Подъём первообразного корня с модуля p на p²"
    topics = ("number_theory.primitive_root",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "Both branches of the lifting criterion; preset `replace` forces g^{p-1}=1 mod p^2."
    presets = {"default": {"primes": list(first_primes(30)[2:]), "mode": "mixed"},
               "direct": {"mode": "direct"}, "replace": {"mode": "replace"}}
    statement = (r"Дано нечётное простое $p=\VAR{p}$ и первообразный корень $g=\VAR{g}$ по модулю $p$. "
                 r"Не перебирая элементы по модулю $p^2$, получить первообразный корень по модулю "
                 r"$p^2=\VAR{p2}$: проверить критерий подъёма для $g$ и, если нужно, заменить его на $g+p$. "
                 r"Доказать, что найденный элемент является первообразным корнем и по всем модулям $p^k$, $k\ge2$.")
    solution = (r"Если $h$ --- первообразный корень по модулю $p$, то его порядок по модулю $p^2$ делит "
                r"$\varphi(p^2)=p(p-1)$ и кратен $p-1$, поэтому равен либо $p-1$, либо $p(p-1)$. Следовательно, "
                r"$h$ --- первообразный корень по модулю $p^2$ тогда и только тогда, когда "
                r"$h^{p-1}\not\equiv1\pmod{p^2}$."
                r"\par Здесь $g^{\VAR{p - 1}}\bmod\VAR{p2}=\VAR{lift}$."
                r"\BLOCK{if replace} Получили $1$, поэтому само $g$ не подходит. Положим $h=g+p=\VAR{answer}$. "
                r"По биному Ньютона"
                r"\[(g+p)^{p-1}\equiv g^{p-1}+(p-1)pg^{p-2}\equiv1-pg^{p-2}\pmod{p^2}.\]"
                r"Это значение не равно $1$ по модулю $p^2$, поскольку $p\nmid g$. Кроме того, $h\equiv g\pmod p$, "
                r"так что $h$ остаётся первообразным корнем по модулю $p$."
                r"\BLOCK{else} Получили значение, отличное от $1$, поэтому подходит $h=g=\VAR{answer}$."
                r"\BLOCK{endif} Проверка порядка по модулю $p^2$: $h^{\varphi(p^2)}\equiv1$, а для каждого "
                r"простого $q\mid\varphi(p^2)$ достаточно условия $h^{\varphi(p^2)/q}\not\equiv1$; здесь оно "
                r"следует из критерия подъёма и первообразности по модулю $p$."
                r"\[\boxed{h=\VAR{answer}\ \text{--- первообразный корень по модулю }\VAR{p2}}.\]"
                r"\par Далее индукция по $k$: если $h$ --- первообразный корень по модулю $p^2$, то "
                r"$h^{p-1}=1+Ap$ с $p\nmid A$. При переходе к следующей степени соответствующий коэффициент "
                r"остаётся неделимым на $p$, поэтому порядок каждый раз умножается на $p$ и равен "
                r"$\varphi(p^k)=p^{k-1}(p-1)$.")
    def sample(self, rng):
        cfg = self.cfg
        wanted = cfg.mode
        while True:
            p = rng.choice(cfg.primes)
            base = root_search(p)["g"]
            k = rng.choice([k for k in range(1, p - 1) if gcd(k, p - 1) == 1])
            g = pow(base, k, p)
            lift = pow(g, p - 1, p * p)
            kind = "replace" if lift == 1 else "direct"
            if wanted == "mixed" or wanted == kind:
                break
        answer = g + p if kind == "replace" else g
        return {"p": p, "p2": p * p, "g": g, "lift": lift, "replace": kind == "replace",
                "answer": answer}

    def check(self, p):
        P, g, h = p["p"], p["g"], p["answer"]
        assert is_prime(P) and is_order(g, P - 1, P)
        assert p["lift"] == pow(g, P - 1, P * P)
        assert p["replace"] == (p["lift"] == 1)
        assert h == (g + P if p["replace"] else g)
        assert is_order(h, P * (P - 1), P * P)
        assert pow(h, P - 1, P * P) != 1


class SchnorrGenerator(Task):
    id = "number_theory.schnorr_generator"
    title_ru = "Первообразные корни и образующие подгруппы Шнорра"
    topics = ("number_theory.primitive_root",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "Safe prime p=2q+1; candidates of orders 1, 2, q, 2q and two distinct order-q generators."
    presets = {"default": {"pairs": [[5, 11], [11, 23], [23, 47], [41, 83], [53, 107], [83, 167],
                                             [89, 179], [113, 227], [131, 263], [173, 347], [179, 359], [191, 383]]}}
    statement = (r"Пусть $p=\VAR{p}=2q+1$, где $q=\VAR{q}$ тоже простое. Для каждого "
                 r"$h\in\{\VAR{values|join(', ')}\}$ найти $\operatorname{ord}_p(h)$. Указать все "
                 r"первообразные корни по модулю $p$, все образующие подгруппы Шнорра порядка $q$ и все "
                 r"значения, допустимые как открытый ключ Диффи--Хеллмана в этой подгруппе: "
                 r"$1<h<p-1$ и $h^q=1$. Объяснить, почему для протокола обычно выбирают образующую "
                 r"порядка $q$, а не обязательно первообразный корень.")
    solution = (r"По теореме Лагранжа порядок делит $p-1=2q$, поэтому возможны только $1,2,q,2q$. "
                r"Для $h\ne\pm1$ достаточно вычислить $h^q$: если $h^q=1$, порядок равен $q$; иначе $2q$:"
                r"\[\begin{array}{r|r|r|r|c|c|c}h & h^2\bmod p & h^q\bmod p & \operatorname{ord}(h) & "
                r"\text{первообр.} & \text{обр. }q & \text{DH} \\ \hline "
                r"\BLOCK{for r in rows}\VAR{r.h} & \VAR{r.h2} & \VAR{r.hq} & \VAR{r.order} & "
                r"\BLOCK{if r.order == 2 * q}+\BLOCK{else}---\BLOCK{endif} & "
                r"\BLOCK{if r.order == q}+\BLOCK{else}---\BLOCK{endif} & "
                r"\BLOCK{if r.order == q}+\BLOCK{else}---\BLOCK{endif} \\ \BLOCK{endfor}\end{array}\]"
                r"Первообразные корни: $\VAR{roots|join(', ')}$; образующие подгруппы порядка $q$: "
                r"$\VAR{subgroup|join(', ')}$. Именно последние проходят проверку открытого ключа. "
                r"Подгруппа простого порядка $q$ не содержит малых собственных подгрупп, а её размер можно "
                r"выбрать независимо от размера всего поля. Поэтому для Диффи--Хеллмана она обычно удобнее "
                r"и безопаснее, чем вся группа порядка $2q$; первообразный корень по модулю $p$ сам по себе "
                r"такой проверки не проходит.")
    def sample(self, rng):
        q, p = rng.choice(self.cfg.pairs)
        g = root_search(p)["g"]
        u = rng.randrange(2, q)
        values = [1, p - 1, pow(g, 2, p), pow(g, 2 * u, p), g]
        rng.shuffle(values)
        rows = []
        for h in values:
            order = 1 if h == 1 else 2 if h == p - 1 else q if pow(h, q, p) == 1 else 2 * q
            rows.append({"h": h, "h2": pow(h, 2, p), "hq": pow(h, q, p), "order": order})
        roots = [r["h"] for r in rows if r["order"] == 2 * q]
        subgroup = [r["h"] for r in rows if r["order"] == q]
        return {"p": p, "q": q, "values": values, "rows": rows, "roots": roots, "subgroup": subgroup,
                "answer": {"primitive": roots, "schnorr": subgroup}}

    def check(self, p):
        P, q = p["p"], p["q"]
        assert P == 2 * q + 1 and is_prime(P) and is_prime(q)
        assert len({r["order"] for r in p["rows"]}) == 4
        for r in p["rows"]:
            assert order_naive(r["h"], P) == r["order"]
            assert r["h2"] == pow(r["h"], 2, P) and r["hq"] == pow(r["h"], q, P)
        assert p["answer"]["primitive"] == [r["h"] for r in p["rows"] if r["order"] == 2 * q]
        assert p["answer"]["schnorr"] == [r["h"] for r in p["rows"] if r["order"] == q]


class MaximalOrderElement(Task):
    id = "number_theory.maximal_order_element"
    title_ru = "Элемент максимального порядка, когда первообразного корня нет"
    topics = ("number_theory.primitive_root", "number_theory.order")
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = "Constructs an element of order lambda(n) componentwise and recombines it with CRT."
    presets = {"default": {"moduli": [24, 36, 40, 48, 56, 60, 63, 72, 80, 84, 90, 96, 100,
                                                108, 120, 128, 144]}}
    statement = (r"По модулю $n=\VAR{n}$ первообразных корней нет. Вычислить $\lambda(n)$ и "
                 r"$\varphi(n)$, построить элемент $g$ порядка $\lambda(n)$ и доказать, что большего "
                 r"порядка не бывает. Элемент по модулю $n$ собрать по КТО из элементов максимального "
                 r"порядка по примарным модулям $p^e\parallel n$.")
    solution = (TX + r"Для нечётного $p$ группа по модулю $p^e$ циклическая, поэтому берём первообразный "
                r"корень. Для $2^e$, $e\ge3$, максимальный порядок равен $2^{e-2}$; его имеет, например, "
                r"элемент $3$. Для $2$ и $4$ выбор очевиден:"
                r"\[\begin{array}{r|r|r}p^e & g_{p^e} & \lambda(p^e)=\operatorname{ord}(g_{p^e}) \\ \hline "
                r"\BLOCK{for c in parts}\VAR{c.pe} & \VAR{c.g} & \VAR{c.lam} \\ \BLOCK{endfor}\end{array}\]"
                r"Собираем $g\equiv g_{p^e}\pmod{p^e}$ по всем компонентам: \VAR{tx.crt(crt)}"
                r"По КТО порядок $g$ равен НОК порядков компонент:"
                r"\[\operatorname{ord}_n(g)=\operatorname{lcm}(\VAR{lams|join(', ')})=\VAR{lam}.\]"
                r"Для любого $x\in(\mathbb Z/n\mathbb Z)^*$ аналогично "
                r"$\operatorname{ord}_n(x)=\operatorname{lcm}_i\operatorname{ord}_{p_i^{e_i}}(x)$, а каждый "
                r"порядок компоненты делит $\lambda(p_i^{e_i})$. Следовательно, порядок любого $x$ делит "
                r"$\lambda(n)=\VAR{lam}$, так что найденный $g$ действительно имеет максимальный порядок. "
                r"Наконец $\varphi(n)=\VAR{phi}>\VAR{lam}$, поэтому первообразных корней нет."
                r"\[g=\VAR{answer.g},\qquad \operatorname{ord}_{\VAR{n}}(g)=\VAR{answer.order}.\]")
    def sample(self, rng):
        n = rng.choice(self.cfg.moduli)
        parts, residues, moduli = [], [], []
        for q, e in sorted(factorize(n).items()):
            pe = q**e
            lam = 2 ** (e - 2) if q == 2 and e >= 3 else q ** (e - 1) * (q - 1)
            if q == 2:
                g = 1 if e == 1 else 3
            else:
                g = root_search(pe)["g"]
            parts.append({"pe": pe, "g": g, "lam": lam})
            residues.append(g)
            moduli.append(pe)
        crt = steps.crt(residues, moduli)
        g, lam, ph = crt["x"], carmichael(n), phi(n)
        return {"n": n, "parts": parts, "crt": crt, "lams": [c["lam"] for c in parts],
                "lam": lam, "phi": ph, "answer": {"g": g, "order": lam}}

    def check(self, p):
        n, g = p["n"], p["answer"]["g"]
        assert not has_primitive_root(n) and gcd(g, n) == 1
        orders = [order_naive(x, n) for x in range(1, n) if gcd(x, n) == 1]
        assert p["lam"] == carmichael(n) == max(orders) < p["phi"] == phi(n)
        assert order_naive(g, n) == p["answer"]["order"] == p["lam"]
        for c in p["parts"]:
            assert g % c["pe"] == c["g"] % c["pe"]
            assert is_order(c["g"], c["lam"], c["pe"])


def _set_tex(values: list[int]) -> str:
    return r"\varnothing" if not values else r"\{" + ", ".join(map(str, values)) + r"\}"


class PrimitiveRootGalbraith(Task):
    id = "number_theory.primitive_root_galbraith"
    title_ru = "Поиск первообразного корня в Z/pZ"
    topics = ("number_theory.primitive_root",)
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("Galbraith, Mathematics of Public Key Cryptography v2.0, Algorithm 5, p. 72. "
             "Algorithm 4 supplies all prime-power components through a product tree; candidate bases "
             "are printed in the statement to make the randomized trace reproducible.")
    presets = {"default": {"primes": [421, 571, 619, 643, 659, 823, 853, 883, 991], "max_rounds": 4}}
    statement = (r"Простое $p=\VAR{p}$ имеет $p-1=\VAR{factor}$. Найти первообразный корень в "
                 r"$(\mathbb Z/p\mathbb Z)^*$ алгоритмом поиска первообразного корня в Z/pZ. Считать, что случайный выбор "
                 r"последовательно даёт основания $g=\VAR{bases|join(', ')}$ (лишние не использовать). "
                 r"Для каждого основания вычислить все $g_i=g^{(p-1)/\ell_i^{e_i}}$ деревом произведений "
                 r"(алгоритм~4), отобрать компоненты максимального порядка $\ell_i^{e_i}$ и собрать ответ $t$.")
    solution = (r"Обозначим $N=p-1$. Если $h_i=g^{N/\ell_i^{e_i}}$ и "
                r"$h_i^{\ell_i^{e_i-1}}\ne1$, то $\operatorname{ord}(h_i)=\ell_i^{e_i}$. Произведение "
                r"таких компонент по всем $i$ имеет порядок $N$, поскольку числа $\ell_i^{e_i}$ попарно "
                r"взаимно просты. Поэтому в алгоритме~5 множество $S$ содержит ещё не найденные индексы, "
                r"а $t$ --- произведение уже отобранных компонент."
                r"\par Одно и то же дерево произведений используется во всех раундах (от корня к листьям): "
                r"\BLOCK{for lv in tree_levels}\VAR{lv|join(',\\ ')}\BLOCK{if not loop.last}; \BLOCK{endif}"
                r"\BLOCK{endfor}. При спуске узлу с $h$ левый потомок получает $h^{P_R}$, правый --- $h^{P_L}$."
                r"\BLOCK{for r in rounds}\par\noindent\textbf{Раунд \VAR{r.i}.} $g=\VAR{r.g}$, "
                r"$S=\VAR{r.S_before}$, $t=\VAR{r.t_before}$. Спуск алгоритма~4:"
                r"\[\begin{array}{l|r|r|r|r}\text{листья узла} & h & P_L & P_R & (h^{P_R},h^{P_L}) \\ \hline "
                r"\BLOCK{for d in r.down}\{\VAR{d.node|join(', ')}\} & \VAR{d.h} & \VAR{d.pl} & \VAR{d.pr} & "
                r"(\VAR{d.hl},\VAR{d.hr}) \\ \BLOCK{endfor}\end{array}\]"
                r"В листьях возводим $h_i$ в степень $\ell_i$ до получения $1$; число шагов $k_i$ даёт "
                r"порядок $\ell_i^{k_i}$:"
                r"\[\begin{array}{r|r|r|r|r|r}\ell_i^{e_i} & h_i & k_i & \text{максимален?} & i\in S? & "
                r"\text{новое }t \\ \hline \BLOCK{for c in r.leaves}\VAR{c.qe} & \VAR{c.h} & \VAR{c.k} & "
                r"\BLOCK{if c.maximal}\text{да}\BLOCK{else}\text{нет}\BLOCK{endif} & "
                r"\BLOCK{if c.pending}\text{да}\BLOCK{else}\text{нет}\BLOCK{endif} & "
                r"\BLOCK{if c.accepted}\VAR{c.t_after}\BLOCK{else}\VAR{c.t_before}\BLOCK{endif} \\ "
                r"\BLOCK{endfor}\end{array}\]"
                r"После раунда $S=\VAR{r.S_after}$, $t=\VAR{r.t_after}$.\BLOCK{endfor}"
                r"\par Все индексы удалены из $S$. Проверка: $t^{p-1}\equiv1\pmod p$, а для каждого простого "
                r"$\ell\mid p-1$ имеем $t^{(p-1)/\ell}\not\equiv1\pmod p$."
                r"\[\boxed{t=\VAR{answer}\ \text{--- первообразный корень по модулю }\VAR{p}}.\]")
    def sample(self, rng):
        cfg = self.cfg
        while True:
            p = rng.choice(cfg.primes)
            fac = sorted(factorize(p - 1).items())
            S = list(range(1, len(fac) + 1))
            t, rounds, bases = 1, [], []
            while S and len(rounds) < cfg.max_rounds:
                g = rng.randrange(1, p)
                bases.append(g)
                tree = product_tree_order(g, p)
                before, t_before = list(S), t
                leaves = []
                for i, ((q, e), leaf) in enumerate(zip(fac, tree["leaves"]), 1):
                    maximal = leaf["k"] == e
                    pending = i in S
                    accepted = maximal and pending
                    old_t = t
                    if accepted:
                        t = t * leaf["h"] % p
                        S.remove(i)
                    leaves.append({"q": q, "e": e, "qe": q**e, "h": leaf["h"], "k": leaf["k"],
                                   "maximal": maximal, "pending": pending, "accepted": accepted,
                                   "t_before": old_t, "t_after": t})
                rounds.append({"i": len(rounds) + 1, "g": g, "S_before": _set_tex(before),
                               "S_after": _set_tex(S), "t_before": t_before, "t_after": t,
                               "down": tree["down"], "leaves": leaves})
            if not S:
                break
        return {"p": p, "factor": steps.factor_tex(p - 1), "bases": bases, "rounds": rounds,
                "tree_levels": product_tree_order(bases[0], p)["levels"], "answer": t}

    def check(self, p):
        P = p["p"]
        assert is_prime(P) and is_order(p["answer"], P - 1, P)
        fac = sorted(factorize(P - 1).items())
        pending = set(range(1, len(fac) + 1))
        t = 1
        for r in p["rounds"]:
            assert r["g"] == p["bases"][r["i"] - 1] and r["t_before"] == t
            for idx, (c, (q, e)) in enumerate(zip(r["leaves"], fac), 1):
                assert c["h"] == pow(r["g"], (P - 1) // q**e, P)
                assert c["maximal"] == is_order(c["h"], q**e, P)
                assert c["pending"] == (idx in pending)
                if c["accepted"]:
                    assert c["k"] == e and c["pending"]
                    t = t * c["h"] % P
                    pending.remove(idx)
            assert r["t_after"] == t
        assert not pending and t == p["answer"]
