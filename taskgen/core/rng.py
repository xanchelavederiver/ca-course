"""Deterministic randomness.

Every random choice in a generation run comes from a ``random.Random``
seeded by :func:`derive_seed` from the run's master seed plus a path
(sheet id, variant key, slot number, ...). A single variant or task can
therefore be regenerated in isolation, and results never depend on the
order in which other variants were generated.

Tasks must draw randomness *only* from the ``rng`` they are given — never
from the ``random`` module globals or Sage's global generator.
"""

from __future__ import annotations

import hashlib
import random
import secrets

SEED_BITS = 63


def derive_seed(*parts: object) -> int:
    """Stable 63-bit seed derived from ``parts`` (SHA-256 of their ``str``)."""
    data = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(data).digest()[:8], "big") >> (64 - SEED_BITS)


def make_rng(*parts: object) -> random.Random:
    return random.Random(derive_seed(*parts))


def new_master_seed() -> int:
    return secrets.randbits(SEED_BITS)
