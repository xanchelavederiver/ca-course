"""Bellcore fault attack on RSA signatures recombined with CRT (lecture sem2/05)."""

from math import gcd

from taskgen.core import steps
from taskgen.core.nt import first_primes, inverse
from taskgen.core.task import SolutionDetail, Task
from taskgen.tasks.crypto.rsa_basics import EXPS


class RSACRTFault(Task):
    id = "crypto.rsa_crt_fault"
    title_ru = "Атака на RSA с помощью ошибки при CRT-пересборке подписи"
    topics = ("crypto.rsa", "number_theory.crt")
    complexity = 2
    solution_detail = SolutionDetail.FULL
    notes = ("The faulty signature is correct modulo one prime factor and wrong modulo the other. "
             "Preset `no_fault` gives identical correct signatures, so both gcds equal N.")
    presets = {"default": {"primes": list(first_primes(25)[4:]), "no_fault_ratio": 0.15},
               "no_fault": {"no_fault_ratio": 1.0}}
    statement = (r"Для RSA с модулем $N=\VAR{n}$ и открытой экспонентой $e=\VAR{e}$ сообщение "
                 r"$m=\VAR{m}$ подписано дважды. Первая подпись $s=\VAR{s}$ верна. При второй подписи "
                 r"вычисления по одному из простых модулей верны, а по другому искажены ошибкой; после "
                 r"CRT-пересборки получено $s'=\VAR{sf}$. Разложить $N$, используя сначала обе подписи, "
                 r"а затем только $s'$ и открытые данные. Объяснить результат и указать способ предотвратить атаку.")
    solution = (r"Правильная подпись удовлетворяет $s^e\equiv m\pmod N$: здесь "
                r"$\VAR{s}^{\VAR{e}}\bmod\VAR{n}=\VAR{check_s}$."
                r"\BLOCK{if fault} Пусть $N=pq$ и $s'$ верна по модулю $p$, но неверна по модулю $q$. "
                r"Тогда $p\mid s-s'$, а $q\nmid s-s'$, поэтому"
                r"\[\gcd(s-s',N)=\gcd(\VAR{diff},\VAR{n})=\VAR{g1}.\]"
                r"Тот же множитель получается без правильной подписи: $(s')^e-m$ делится на $p$, но не на $q$:"
                r"\[(s')^e\bmod N=\VAR{sf_pow},\qquad \gcd(\VAR{sf_pow}-\VAR{m},\VAR{n})=\VAR{g2}.\]"
                r"Следовательно $N=\VAR{g1}\cdot\VAR{cofactor}$. Проверка: "
                r"$\VAR{g1}\cdot\VAR{cofactor}=\VAR{n}$."
                r"\BLOCK{else} Здесь $s'=s$: ошибки на самом деле нет. Поэтому $\gcd(s-s',N)=N$ и "
                r"$\gcd((s')^e-m,N)=N$; нетривиального делителя метод не даёт. Это контрольный случай, "
                r"а не свидетельство простоты $N$.\BLOCK{endif}"
                r"\par На практике перед выдачей CRT-подписи нужно проверить $s^e\equiv m\pmod N$ "
                r"(или эквивалентное условие). Тогда повреждённая подпись не покидает устройство, и "
                r"описанный метод получает только корректные подписи.")
    def sample(self, rng):
        cfg = self.cfg
        while True:
            p, q = rng.sample(cfg.primes, 2)
            n, phi = p * q, (p - 1) * (q - 1)
            valid_e = [e for e in EXPS if gcd(e, phi) == 1]
            if valid_e:
                break
        e = rng.choice(valid_e)
        d = inverse(e, phi)
        while True:
            m = rng.randrange(2, n)
            if gcd(m, n) == 1:
                break
        s = pow(m, d, n)
        fault = rng.random() >= cfg.no_fault_ratio
        if fault:
            correct, wrong = (p, q) if rng.random() < 0.5 else (q, p)
            residues = list(range((s % wrong + 1) % wrong, wrong)) + list(range(0, s % wrong))
            sf = steps.crt([s % correct, rng.choice(residues)], [correct, wrong])["x"]
        else:
            correct, wrong, sf = None, None, s
        diff = (sf - s) % n
        sf_pow = pow(sf, e, n)
        g1, g2 = gcd(diff, n), gcd((sf_pow - m) % n, n)
        factor = g1 if fault else None
        return {"n": n, "e": e, "m": m, "s": s, "sf": sf, "p": p, "q": q,
                "correct": correct, "wrong": wrong, "fault": fault, "check_s": pow(s, e, n),
                "diff": diff, "sf_pow": sf_pow, "g1": g1, "g2": g2,
                "cofactor": n // g1 if fault else None,
                "answer": {"factor": factor, "cofactor": n // g1 if fault else None}}

    def check(self, p):
        n, e, m = p["n"], p["e"], p["m"]
        assert p["p"] * p["q"] == n and pow(p["s"], e, n) == m
        if p["fault"]:
            c, w = p["correct"], p["wrong"]
            assert c * w == n and p["sf"] != p["s"]
            assert pow(p["sf"], e, c) == m % c and pow(p["sf"], e, w) != m % w
            g = p["answer"]["factor"]
            assert g == c == p["g1"] == p["g2"] and 1 < g < n
            assert p["answer"]["cofactor"] == w == n // g
        else:
            assert p["sf"] == p["s"] and p["g1"] == p["g2"] == n
            assert p["answer"] == {"factor": None, "cofactor": None}
