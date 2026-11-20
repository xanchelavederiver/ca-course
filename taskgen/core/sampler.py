"""Task selection for individual variants.

Each slot gets exactly one task from its candidate pool such that

* the total complexity satisfies the sheet budget (if any), and
* no two chosen tasks share a family (if ``distinct_families``) — the
  generalisation of the ``taken[]`` category rule of the legacy scripts;
* conditional rules restrict a slot's candidates according to the family
  already selected in another slot.

Selection is a randomized depth-first search: slots are visited in a random
order, candidates are tried in a random order, and branches that can no
longer meet the budget are pruned. All randomness comes from ``rng``.
"""

from __future__ import annotations

import random
from typing import Sequence

from taskgen.core.sheet import Budget, SlotRule
from taskgen.core.task import Task


class SamplingError(Exception):
    pass


def select(pools: Sequence[Sequence[Task]], rng: random.Random,
           budget: Budget | None = None, distinct_families: bool = True,
           stats: dict[str, int] | None = None,
           rules: Sequence[SlotRule] = ()) -> list[Task]:
    """One task per pool. ``stats["family_skips"]`` (if given) counts candidates
    skipped because their family was already taken; it never affects the result."""
    n = len(pools)
    if any(not p for p in pools):
        raise SamplingError("empty candidate pool")
    order = list(range(n))
    rng.shuffle(order)
    lo = [min(t.complexity for t in pools[i]) for i in order]
    hi = [max(t.complexity for t in pools[i]) for i in order]
    # suffix sums of the min/max complexity of the not-yet-filled slots
    rest_lo = [sum(lo[k:]) for k in range(n + 1)]
    rest_hi = [sum(hi[k:]) for k in range(n + 1)]
    bmin = budget.min if budget and budget.min is not None else -10**9
    bmax = budget.max if budget and budget.max is not None else 10**9

    chosen: dict[int, Task] = {}
    families: set[str] = set()

    def rule_allows(slot: int, task: Task) -> bool:
        for rule in rules:
            if rule.require_slot != slot:
                continue
            source = chosen.get(rule.when_slot)
            if source is not None and source.family_name() in rule.when_families \
                    and task.ref not in {str(ref) for ref in rule.tasks}:
                return False
        return True

    def dfs(k: int, total: int) -> bool:
        if k == n:
            return bmin <= total <= bmax and all(rule_allows(i, t) for i, t in chosen.items())
        if total + rest_lo[k] > bmax or total + rest_hi[k] < bmin:
            return False
        slot = order[k]
        cands = list(pools[slot])
        rng.shuffle(cands)
        for t in cands:
            if not rule_allows(slot, t):
                continue
            fam = t.family_name()
            if distinct_families and fam in families:
                if stats is not None:
                    stats["family_skips"] = stats.get("family_skips", 0) + 1
                continue
            chosen[slot] = t
            families.add(fam)
            if dfs(k + 1, total + t.complexity):
                return True
            families.discard(fam)
            del chosen[slot]
        return False

    if not dfs(0, 0):
        raise SamplingError("no task combination satisfies the budget/family constraints")
    return [chosen[i] for i in range(n)]
