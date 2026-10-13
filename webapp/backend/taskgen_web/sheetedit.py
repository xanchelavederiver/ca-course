"""Sheet specs (``sheets/**.yaml``): comment-preserving YAML round trip.

The form editor works on plain JSON data; ``merge`` applies that data onto
the existing YAML document with ``ruamel.yaml`` so comments, key order and
block scalars of unchanged parts survive a form edit. Validation is done by
the engine (``taskgen.service.check_sheet_text``) before anything is written.
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import LiteralScalarString

SHEETS_DIR = "sheets"


def _yaml() -> YAML:
    y = YAML()  # round-trip
    y.preserve_quotes = True
    y.width = 100
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def load(text: str) -> Any:
    return _yaml().load(text) if text.strip() else CommentedMap()


def dump(doc: Any) -> str:
    buf = io.StringIO()
    _yaml().dump(doc, buf)
    return buf.getvalue()


def to_plain(node: Any) -> Any:
    """ruamel nodes -> plain JSON data."""
    if isinstance(node, dict):
        return {str(k): to_plain(v) for k, v in node.items()}
    if isinstance(node, list):
        return [to_plain(v) for v in node]
    if isinstance(node, str):
        return str(node)
    return node


def _scalar(value: Any) -> Any:
    if isinstance(value, str) and "\n" in value:
        return LiteralScalarString(value if value.endswith("\n") else value + "\n")
    return value


def _new(value: Any) -> Any:
    if isinstance(value, dict):
        m = CommentedMap()
        for k, v in value.items():
            m[k] = _new(v)
        return m
    if isinstance(value, list):
        s = CommentedSeq(_new(v) for v in value)
        # short lists of scalars (task refs, topics, students) in flow style: [a, b]
        if value and all(isinstance(v, (str, int, float, bool)) for v in value):
            s.fa.set_flow_style()
        return s
    return _scalar(value)


def _same_scalar(old: Any, new: Any) -> bool:
    if isinstance(old, str) and isinstance(new, str):
        return str(old) == new or str(old).rstrip("\n") == new.rstrip("\n")
    return type(old) is type(new) and old == new


def _move_trailing_comment(parent: CommentedMap, key: Any, before: Any, after: Any) -> None:
    """Keep the comment/blank line that followed ``key``'s value when the value
    changes between a scalar and a mapping (ruamel would otherwise print it
    right after ``key:``)."""
    if isinstance(after, CommentedMap) and not isinstance(before, (dict, list)):
        c = parent.ca.items.pop(key, None)
        if c and len(c) > 2 and c[2] is not None and after:
            after.ca.items[list(after)[-1]] = [None, None, c[2], None]
    elif isinstance(before, CommentedMap) and not isinstance(after, (dict, list)) and before:
        c = before.ca.items.get(list(before)[-1])
        if c and len(c) > 2 and c[2] is not None:
            parent.ca.items[key] = [None, None, c[2], None]


def merge(old: Any, new: Any) -> Any:
    """Apply plain data ``new`` onto ruamel node ``old`` in place where possible."""
    if isinstance(old, CommentedMap) and isinstance(new, dict):
        for k in [k for k in old if k not in new]:
            del old[k]
        for k, v in new.items():
            if k in old:
                before = old[k]
                old[k] = merge(before, v)
                if old[k] is not before:
                    _move_trailing_comment(old, k, before, old[k])
            else:
                old[k] = _new(v)
        return old
    if isinstance(old, CommentedSeq) and isinstance(new, list):
        if all(not isinstance(v, (dict, list)) for v in new) and \
                all(not isinstance(v, (dict, list)) for v in old):
            if len(old) == len(new) and all(_same_scalar(a, b) for a, b in zip(old, new)):
                return old
            flow = old.fa.flow_style()
            seq = CommentedSeq(_scalar(v) for v in new)
            if flow or not old:
                seq.fa.set_flow_style()
            return seq
        for i, v in enumerate(new):
            if i < len(old):
                old[i] = merge(old[i], v)
            else:
                old.append(_new(v))
        del old[len(new):]
        return old
    if isinstance(old, (dict, list)) or isinstance(new, (dict, list)):
        return _new(new)
    return old if _same_scalar(old, new) else _scalar(new)


def merged_text(base: str, data: dict[str, Any]) -> str:
    """YAML text of ``data``, keeping the comments/formatting of ``base``.

    Unchanged data returns ``base`` itself; otherwise ruamel re-emits the
    document (comments, key order and block scalars are kept, but long flow
    lists may be re-wrapped).
    """
    doc = load(base)
    if not isinstance(doc, CommentedMap):
        doc = CommentedMap()
    elif to_plain(doc) == data:
        return base
    # ruamel leaves a trailing space where it wraps a flow sequence
    return re.sub(r"[ \t]+\n", "\n", dump(merge(doc, data)))


TEMPLATES = {
    "classroom": """\
# Classroom sheet: one sheet (+ solution manual) for a seminar.
id: {id}
kind: classroom
title: {title}
semester: {semester}
preset: null
document:
  toc: false
intro: ''
sections:
  - title: Задачи
    tasks: []
""",
    "individual": """\
# Individual sheet: one variant per student.
id: {id}
kind: individual
title: {title}
semester: {semester}
preset: null
intro: ''
groups:
  - {{name: '6411', count: 30}}
budget: null
slots:
  - title: Задание 1
    tasks: []
""",
}


def skeleton(kind: str, sheet_id: str, title: str, semester: int | None) -> str:
    return TEMPLATES[kind].format(id=sheet_id, title=title,
                                  semester="null" if semester is None else semester)


def list_sheets(repo: Path) -> list[Path]:
    root = repo / SHEETS_DIR
    return sorted(p for p in root.rglob("*.yaml") if p.is_file())
