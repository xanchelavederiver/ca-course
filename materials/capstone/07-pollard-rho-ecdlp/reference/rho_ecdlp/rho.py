"""Pollard's rho for the ECDLP: find x with [x]P = Q, where n = ord(P).

Two variants, both keeping every point of the walk as X = [alpha]P + [beta]Q with
known (alpha, beta) mod n:

* ``floyd`` — Pollard's original walk (HPS, sec. 4.5 and 6.4.3) with Floyd's cycle
  detection. The group is split into three classes by x mod 3:

      S0: X -> X + P   (alpha + 1, beta)
      S1: X -> 2X      (2 alpha,   2 beta)
      S2: X -> X + Q   (alpha,     beta + 1)

  The tortoise X_i = [alpha_i]P + [beta_i]Q and the hare Y_i = X_{2i} =
  [gamma_i]P + [delta_i]Q move until X_i = Y_i (the alpha, beta, gamma, delta of the
  spec). That costs 3 group operations per iteration and O(1) memory.

* ``dp`` — distinguished points (van Oorschot-Wiener) with Teske's r-adding walk:
  X -> X + M_j with j = j(X) in [0, r) and fixed random M_j = [a_j]P + [b_j]Q. Each
  trail starts at a random [a]P + [b]Q and runs until it hits a distinguished point
  (x = 0 mod 2^theta); the distinguished points are stored. Two trails that ever
  meet end in the same distinguished point, which is the collision. 1 group operation
  per step; the memory is ~ sqrt(n) / 2^theta points.

A collision [a]P + [b]Q = [a']P + [b']Q gives the congruence
(b - b') x = a' - a (mod n). With d = gcd(b - b', n) it has no or exactly d solutions
(:func:`ntheory.solve_linear_congruence`); each is checked by [x]P = Q. A degenerate
collision (d too large to enumerate, e.g. b = b' mod n, or no candidate verifies) is
recorded, and the search restarts from a fresh random point.

All randomness comes from the ``rng`` argument, which the CLI seeds per request, so a
request always gives the same answer and the same intermediate data.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .ec import Curve, Point, to_json
from .ntheory import solve_linear_congruence

ENUM_LIMIT = 1 << 16        # enumerate at most this many solutions of a congruence
LIST_LIMIT = 64             # ... and record at most this many of them in `extra`


class RhoFailure(RuntimeError):
    """No solution within the iteration and retry budget."""


@dataclass
class Rho:
    """The search parameters (item 1 of the spec) and the record of a run."""
    E: Curve
    P: Point
    Q: Point
    n: int
    rng: random.Random
    start: tuple[int, int] | None = None     # (alpha_0, beta_0) of the first attempt
    max_iter: int | None = None              # per attempt (floyd) / per search (dp)
    max_attempts: int = 10
    attempts: list[dict] = field(default_factory=list)

    # --- helpers ----------------------------------------------------------------------

    def _start(self) -> tuple[int, int]:
        """(alpha_0, beta_0): the given start for the first attempt, then random."""
        if self.start is not None and not self.attempts:
            return self.start[0] % self.n, self.start[1] % self.n
        return self.rng.randrange(self.n), self.rng.randrange(self.n)

    def _solve(self, u: int, v: int, rec: dict) -> int | None:
        """Solve u x = v (mod n), check the candidates, fill ``rec``; x or None."""
        E, P, Q, n = self.E, self.P, self.Q, self.n
        d, xs = solve_linear_congruence(u, v, n, ENUM_LIMIT)
        rec["congruence"] = {"u": u % n, "v": v % n, "mod": n, "gcd": d}
        if xs is None:
            rec.update(result="degenerate", solutions_count=d)
            return None
        rec["solutions_count"] = len(xs)
        rec["solutions"] = xs[:LIST_LIMIT]
        # The candidates form x0 + t n/d: check them with one addition each.
        if xs:
            R, step = E.mul(xs[0], P), E.mul(n // d, P)
            for x in xs:
                if R == Q:
                    rec.update(result="solved", x=x)
                    return x
                R = E.add(R, step)
        rec["result"] = "no-valid-solution"
        return None

    # --- Pollard's walk + Floyd -------------------------------------------------------

    def floyd(self) -> int:
        E, P, Q, n = self.E, self.P, self.Q, self.n
        add = E.add
        limit = self.max_iter or 20 * math.isqrt(n) + 100

        def f(X, al, be):
            """One step of Pollard's walk; O is put into class S0."""
            s = 0 if X is None else X[0] % 3
            if s == 0:
                return add(X, P), al + 1 if al + 1 < n else 0, be
            if s == 1:
                return add(X, X), 2 * al % n, 2 * be % n
            return add(X, Q), al, be + 1 if be + 1 < n else 0

        while len(self.attempts) < self.max_attempts:
            al, be = self._start()
            X = E.lin(al, P, be, Q)
            rec = {"start": [al, be], "start_point": to_json(X)}
            self.attempts.append(rec)
            ga, de, Y = al, be, X
            for i in range(1, limit + 1):
                X, al, be = f(X, al, be)
                Y, ga, de = f(*f(Y, ga, de))
                if X == Y:
                    break
            else:
                rec.update(iterations=limit, result="max_iter")
                continue
            rec.update(iterations=i, alpha=al, beta=be, gamma=ga, delta=de, collision=to_json(X))
            # [al]P + [be]Q = [ga]P + [de]Q  =>  (be - de) x = ga - al (mod n)
            x = self._solve(be - de, ga - al, rec)
            if x is not None:
                return x
        raise RhoFailure(self._why())

    # --- r-adding walk + distinguished points -----------------------------------------

    def distinguished(self, r: int = 20, theta: int | None = None) -> int:
        E, P, Q, n = self.E, self.P, self.Q, self.n
        add = E.add
        if theta is None:   # trails of ~ sqrt(n) / 32 steps: ~ 40 trails per solution
            theta = max(0, n.bit_length() // 2 - 5)
        mask = (1 << theta) - 1
        max_trail = 20 << theta
        limit = self.max_iter or 20 * math.isqrt(n) + 20 * max_trail + 100
        # The r-adding walk: M_j = [a_j]P + [b_j]Q; j(X) = (x >> theta) mod r, so the
        # class does not depend on the bits that make X distinguished.
        coef = [(self.rng.randrange(n), self.rng.randrange(n)) for _ in range(r)]
        M = [E.lin(a, P, b, Q) for a, b in coef]
        rec: dict = {"r": r, "theta": theta, "walk": [list(c) for c in coef]}
        self.attempts.append(rec)
        seen: dict = {}                     # distinguished point -> (a, b)
        steps = trails = abandoned = 0
        degenerate: list[dict] = []
        while steps < limit:
            a, b = self._start() if trails == 0 else (self.rng.randrange(n), self.rng.randrange(n))
            if trails == 0:
                rec["start"] = [a, b]
            trails += 1
            X = E.lin(a, P, b, Q)
            for _ in range(max_trail):
                if X is not None and X[0] & mask == 0:
                    break
                j = 0 if X is None else (X[0] >> theta) % r
                X = add(X, M[j])
                a += coef[j][0]
                b += coef[j][1]
                steps += 1
            else:                           # a cycle without distinguished points
                abandoned += 1
                continue
            a, b = a % n, b % n
            old = seen.get(X)
            if old is None:
                seen[X] = (a, b)
                continue
            if old == (a, b):               # the same trail twice: no information
                continue
            col = {"point": to_json(X), "a": old[0], "b": old[1], "a2": a, "b2": b}
            # [a']P + [b']Q = [a]P + [b]Q  =>  (b' - b) x = a - a' (mod n)
            x = self._solve(old[1] - b, a - old[0], col)
            if x is not None:
                rec.update(iterations=steps, trails=trails, abandoned=abandoned,
                           stored=len(seen), collision=col, degenerate=degenerate,
                           result="solved")
                return x
            degenerate.append(col)
            seen[X] = (a, b)                # keep the newer pair, walk on
        rec.update(iterations=steps, trails=trails, abandoned=abandoned, stored=len(seen),
                   degenerate=degenerate, result="max_iter")
        raise RhoFailure(self._why())

    def _why(self) -> str:
        last = self.attempts[-1] if self.attempts else {}
        if last.get("result") == "max_iter":
            return (f"no collision within max_iter = {last.get('iterations')} "
                    f"({len(self.attempts)} attempt(s))")
        return (f"no valid solution after {len(self.attempts)} attempt(s): "
                "is Q in <P> and n = ord(P)?")
