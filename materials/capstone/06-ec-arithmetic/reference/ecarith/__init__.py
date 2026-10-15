"""Elliptic-curve arithmetic over F_p, written from scratch on top of gmpy2 bigints.

Modules: ``field`` (F_p, Tonelli--Shanks), ``curve`` (the group law, Jacobian
coordinates, point generation), ``scalar`` (binary and ternary scalar multiplication,
the ternary expansion), ``order`` (naive count, Shanks--Mestre), ``poly`` and
``schoof`` (Schoof's algorithm).
"""

from .curve import Curve, CurveError
from .order import order_naive, order_shanks_mestre
from .scalar import mul, mul_binary, mul_ternary, ternary_expansion
from .schoof import order_schoof

__all__ = ["Curve", "CurveError", "mul", "mul_binary", "mul_ternary", "ternary_expansion",
           "order_naive", "order_shanks_mestre", "order_schoof"]
