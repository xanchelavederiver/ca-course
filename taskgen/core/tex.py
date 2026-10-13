"""LaTeX helpers: a Jinja2 environment with LaTeX-safe delimiters, value
formatting and a cheap syntactic sanity check for generated snippets.

Template syntax (used by task statements/solutions and sheet templates)::

    \\VAR{expr}                 — expression
    \\BLOCK{for x in xs} ... \\BLOCK{endfor}
    \\#{ comment }
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import jinja2

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "render" / "templates"


def _make_env(loader: jinja2.BaseLoader | None = None) -> jinja2.Environment:
    env = jinja2.Environment(
        block_start_string=r"\BLOCK{",
        block_end_string="}",
        variable_start_string=r"\VAR{",
        variable_end_string="}",
        comment_start_string=r"\#{",
        comment_end_string="}",
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,
        undefined=jinja2.StrictUndefined,
        loader=loader,
    )
    env.filters["bin"] = lambda n: format(int(n), "b")
    env.filters["vec"] = vec
    env.filters["pmatrix_col"] = pmatrix_col
    env.filters["bignum"] = bignum
    env.filters["signed"] = signed
    return env


@lru_cache(maxsize=1)
def env() -> jinja2.Environment:
    return _make_env(jinja2.FileSystemLoader(str(TEMPLATES_DIR)))


@lru_cache(maxsize=512)
def _compile(source: str) -> jinja2.Template:
    return env().from_string(source)


def render(source: str, **ctx: object) -> str:
    """Render a template string with the LaTeX-safe syntax."""
    return _compile(source).render(**ctx).strip()


# --- formatting ------------------------------------------------------------------

def vec(v) -> str:
    """``(a, b)^T`` row notation of a column vector."""
    return "(" + ", ".join(str(x) for x in v) + ")^T"


def bignum(n) -> str:
    """Integer with line-break opportunities every 3 digits (for long values in inline math)."""
    s = str(int(n))
    sign, digits = ("-", s[1:]) if s.startswith("-") else ("", s)
    head = len(digits) % 3 or 3
    groups = [digits[:head]] + [digits[i:i + 3] for i in range(head, len(digits), 3)]
    return sign + r"\allowbreak ".join(groups)


def signed(n) -> str:
    """'+ 5' / '- 5' for writing sums."""
    n = int(n)
    return f"+ {n}" if n >= 0 else f"- {-n}"


def pmatrix_col(v) -> str:
    return r"\begin{pmatrix}" + r" \\ ".join(str(x) for x in v) + r"\end{pmatrix}"


# --- sanity checks ------------------------------------------------------------------

_ESCAPED = re.compile(r"\\[{}$%]")


def latex_problems(s: str) -> list[str]:
    """Return a list of obvious syntax problems in a LaTeX snippet."""
    problems = []
    if not s or not s.strip():
        return ["empty"]
    t = _ESCAPED.sub("", s)
    depth = 0
    for ch in t:
        depth += (ch == "{") - (ch == "}")
        if depth < 0:
            problems.append("unbalanced '}'")
            break
    if depth > 0:
        problems.append("unbalanced '{'")
    if t.count(r"\[") != t.count(r"\]"):
        problems.append(r"unbalanced \[ \]")
    if (t.count("$") - 2 * t.count("$$")) % 2:
        problems.append("odd number of '$'")
    if r"\VAR{" in s or r"\BLOCK{" in s:
        problems.append("unrendered template syntax")
    for env_name in set(re.findall(r"\\begin\{(\w+\*?)\}", t)):
        if t.count(r"\begin{%s}" % env_name) != t.count(r"\end{%s}" % env_name):
            problems.append(f"unbalanced environment {env_name}")
    return problems
