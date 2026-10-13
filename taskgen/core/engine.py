"""Generation run: sheet spec + master seed -> task instances per variant.

Seed derivation (stable; recorded implicitly by the manifest's master seed):

* task selection of a variant:  ``derive_seed(master, sheet_id, variant_key, "select")``
* task in slot ``s`` of a variant: ``derive_seed(master, sheet_id, variant_key, s)``

so any variant (or a single task of it) can be regenerated alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from taskgen.core import sampler
from taskgen.core.rng import derive_seed, make_rng
from taskgen.core.sheet import (ClassroomSheet, IndividualSheet, VariantKey,
                                resolve_ref, slot_candidates, variants)
from taskgen.core.task import Task, TaskInstance


@dataclass
class Variant:
    vkey: VariantKey
    instances: list[TaskInstance]

    @property
    def key(self) -> str:
        return self.vkey.key


@dataclass
class SheetRun:
    spec: ClassroomSheet | IndividualSheet
    master_seed: int
    variants: list[Variant] = field(default_factory=list)


def _instantiate(task: Task, master_seed: int, sheet_id: str, vkey: str, slot: int) -> TaskInstance:
    seed = derive_seed(master_seed, sheet_id, vkey, slot)
    return task.generate(make_rng(seed), seed=seed)


def generate_variant(spec: ClassroomSheet | IndividualSheet, master_seed: int,
                     vkey: VariantKey) -> Variant:
    if isinstance(spec, ClassroomSheet):
        tasks = [resolve_ref(ref, spec.preset) for sec in spec.sections for ref in sec.tasks]
    else:
        pools = [slot_candidates(slot, spec.preset) for slot in spec.slots]
        rng = make_rng(master_seed, spec.id, vkey.key, "select")
        tasks = sampler.select(pools, rng, spec.budget, spec.distinct_families)
    return Variant(vkey, [_instantiate(t, master_seed, spec.id, vkey.key, i)
                          for i, t in enumerate(tasks)])


def generate(spec: ClassroomSheet | IndividualSheet, master_seed: int,
             only: set[str] | None = None) -> SheetRun:
    run = SheetRun(spec=spec, master_seed=master_seed)
    for vkey in variants(spec):
        if only is None or vkey.key in only:
            run.variants.append(generate_variant(spec, master_seed, vkey))
    if only is not None:
        missing = only - {v.key for v in run.variants}
        if missing:
            raise KeyError(f"unknown variant(s): {', '.join(sorted(missing))}")
    return run
