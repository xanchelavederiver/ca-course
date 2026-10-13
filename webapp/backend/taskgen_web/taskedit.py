"""Read and edit task class metadata in the module source.

Tasks stay Python classes. The UI edits *literal* class attributes (id,
title, topics, complexity, family, solution detail, presets, notes, and the
statement/solution templates) in forms. Reading uses ``ast``; writing uses
``libcst``, so everything else in the module — comments, formatting, other
classes, helper code — is preserved byte for byte.

An attribute whose value is not a literal (e.g. ``statement = HEAD + r"..."``
or ``presets = {"default": {"primes": list(PRIMES[15:30])}}``) is reported as
non-editable; the UI then shows its evaluated value read-only and points to
the Code tab.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import libcst as cst

# Editable metadata attributes, in the order they are written for new tasks.
FIELDS = ("id", "title_ru", "topics", "complexity", "family", "solution_detail",
          "presets", "notes", "statement", "solution")
TEMPLATE_FIELDS = ("statement", "solution")
SOLUTION_DETAILS = {"answer_only": "ANSWER_ONLY", "full": "FULL"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]*(\.[a-z0-9][a-z0-9_]*)+$")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MODULE_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


class TaskEditError(ValueError):
    pass


# --- index ------------------------------------------------------------------------

@dataclass
class TaskLoc:
    id: str
    file: str  # repo-relative
    class_name: str
    line: int


def _class_attrs(cls: ast.ClassDef) -> dict[str, ast.AST]:
    out: dict[str, ast.AST] = {}
    for st in cls.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
            out[st.targets[0].id] = st.value
        elif isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name) and st.value is not None:
            out[st.target.id] = st.value
    return out


def _class_id(cls: ast.ClassDef) -> str | None:
    v = _class_attrs(cls).get("id")
    if isinstance(v, ast.Constant) and isinstance(v.value, str):
        return v.value
    return None


class TaskIndex:
    """Static index ``task id -> location`` built with ``ast`` (no imports).

    It finds tasks even when their module does not import. A module with a
    syntax error keeps its last known entries, so its tasks stay reachable
    in the editor while the error is being fixed.
    """

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.root = repo / "taskgen" / "tasks"
        self._by_file: dict[str, list[TaskLoc]] = {}
        self.syntax_errors: dict[str, str] = {}

    def scan(self) -> dict[str, TaskLoc]:
        seen = set()
        self.syntax_errors = {}
        for path in sorted(self.root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = str(path.relative_to(self.repo))
            seen.add(rel)
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError as e:
                self.syntax_errors[rel] = f"{e.msg} (line {e.lineno})"
                continue
            self._by_file[rel] = [TaskLoc(tid, rel, n.name, n.lineno)
                                  for n in tree.body if isinstance(n, ast.ClassDef)
                                  and (tid := _class_id(n))]
        for rel in set(self._by_file) - seen:
            del self._by_file[rel]
        return self.tasks()

    def tasks(self) -> dict[str, TaskLoc]:
        return {loc.id: loc for locs in self._by_file.values() for loc in locs}

    def find(self, task_id: str) -> TaskLoc:
        loc = self.scan().get(task_id)
        if loc is None:
            raise KeyError(f"unknown task id {task_id!r}")
        return loc

    def modules(self) -> list[str]:
        self.scan()
        return sorted(set(self._by_file) | set(self.syntax_errors))


# --- reading ----------------------------------------------------------------------

def _find_class(tree: ast.Module, task_id: str) -> ast.ClassDef:
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and _class_id(n) == task_id:
            return n
    raise TaskEditError(f"class with id = {task_id!r} not found in module")


_BINOPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
           ast.FloorDiv: lambda a, b: a // b, ast.Mod: lambda a, b: a % b,
           ast.Pow: lambda a, b: a ** b, ast.LShift: lambda a, b: a << b}


def const_eval(node: ast.AST) -> Any:
    """``ast.literal_eval`` plus integer arithmetic (``10**6 + 1``, ``2**31 - 1``)."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        items = [const_eval(e) for e in node.elts]
        return items if isinstance(node, ast.List) else tuple(items)
    if isinstance(node, ast.Dict):
        if any(k is None for k in node.keys):
            raise ValueError("dict unpacking")
        return {const_eval(k): const_eval(v) for k, v in zip(node.keys, node.values)}  # type: ignore[arg-type]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = const_eval(node.operand)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        a, b = const_eval(node.left), const_eval(node.right)
        if all(isinstance(x, int) and not isinstance(x, bool) for x in (a, b)):
            if isinstance(node.op, (ast.Pow, ast.LShift)) and not 0 <= b <= 4096:
                raise ValueError("exponent out of range")
            return _BINOPS[type(node.op)](a, b)
        if isinstance(node.op, ast.Add) and all(isinstance(x, str) for x in (a, b)):
            return a + b
    raise ValueError(f"not a constant: {ast.dump(node)[:60]}")


def py(v: Any) -> str:
    """Python literal in the codebase's style (double-quoted strings)."""
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool) or v is None or isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, (list, tuple)):
        inner = ", ".join(py(x) for x in v)
        return f"({inner}{',' if len(v) == 1 else ''})" if isinstance(v, tuple) else f"[{inner}]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{py(k)}: {py(x)}" for k, x in v.items()) + "}"
    raise TaskEditError(f"unsupported value {v!r}")


def _literal(node: ast.AST, name: str) -> tuple[bool, Any]:
    if name == "solution_detail":
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and node.value.id == "SolutionDetail" and node.attr in SOLUTION_DETAILS.values():
            return True, {v: k for k, v in SOLUTION_DETAILS.items()}[node.attr]
        if isinstance(node, ast.Constant) and node.value in SOLUTION_DETAILS:
            return True, node.value
        return False, None
    try:
        value = const_eval(node)
    except (ValueError, TypeError, ZeroDivisionError, RecursionError):
        return False, None
    if isinstance(value, tuple):
        value = list(value)
    return True, value


def read_meta(source: str, task_id: str) -> dict[str, Any]:
    """``{field: {defined, editable, value, expr}}`` for every metadata field.

    ``defined`` is False when the class inherits the attribute (from a base
    task class or ``Task`` itself); such a field is editable — saving it adds
    an assignment to the class.
    """
    tree = ast.parse(source)
    cls = _find_class(tree, task_id)
    attrs = _class_attrs(cls)
    out: dict[str, Any] = {"class_name": cls.name, "line": cls.lineno,
                           "bases": [ast.unparse(b) for b in cls.bases], "fields": {}}
    for name in FIELDS:
        node = attrs.get(name)
        if node is None:
            out["fields"][name] = {"defined": False, "editable": True, "value": None, "expr": None}
            continue
        ok, value = _literal(node, name)
        out["fields"][name] = {"defined": True, "editable": ok, "value": value if ok else None,
                               "expr": ast.get_source_segment(source, node)}
    return out


# --- writing ----------------------------------------------------------------------

def _raw_ok(s: str, quote: str) -> bool:
    if quote in s or s.endswith(quote[0]):
        return False
    trailing = len(s) - len(s.rstrip("\\"))
    return trailing % 2 == 0 and "\r" not in s


def _str_literal(s: str, indent: str = "", wrap: int = 80) -> str:
    """Readable Python literal for a (LaTeX) string: raw strings where possible,
    long one-line values as an implicitly concatenated parenthesized block."""
    if "\n" in s:
        if _raw_ok(s, '"""') and not s.endswith("\\"):
            return 'r"""' + s + '"""'
        return repr(s)
    if not _raw_ok(s, '"'):
        return repr(s)
    if len(s) <= wrap:
        return 'r"' + s + '"'
    chunks, cur = [], ""
    for word in re.split(r"(?<= )", s):
        if cur and len(cur) + len(word) > wrap and not cur.endswith("\\") \
                and _raw_ok(cur, '"'):
            chunks.append(cur)
            cur = ""
        cur += word
    chunks.append(cur)
    if any(not _raw_ok(c, '"') for c in chunks):
        return 'r"' + s + '"'
    inner = indent + "    "
    return "(\n" + "".join(f'{inner}r"{c}"\n' for c in chunks) + indent + ")"


def _leaf_sources(node: ast.AST | None, source: str | None) -> dict[tuple, tuple[Any, str]]:
    """``{key path: (value, source text)}`` of the non-dict leaves of a dict literal."""
    out: dict[tuple, tuple[Any, str]] = {}

    def walk(n: ast.AST, path: tuple) -> None:
        if isinstance(n, ast.Dict) and all(isinstance(k, ast.Constant) for k in n.keys):
            for k, v in zip(n.keys, n.values):
                walk(v, path + (k.value,))  # type: ignore[union-attr]
        elif path:
            try:
                out[path] = (const_eval(n), ast.get_source_segment(source or "", n) or "")
            except (ValueError, TypeError, ZeroDivisionError):
                pass

    if node is not None and source:
        walk(node, ())
    return out


def _wrap_list(xs: list, indent: str, width: int) -> str:
    """``[a, b, ...]`` wrapped over several lines (continuation lines at ``indent``)."""
    lines, cur = [], ""
    for item in (py(x) for x in xs):
        piece = item + ", "
        if cur and len(indent) + len(cur) + len(piece.rstrip()) > width:
            lines.append(cur.rstrip())
            cur = ""
        cur += piece
    lines.append(cur.rstrip().rstrip(","))
    return "[\n" + "".join(f"{indent}{line}\n" for line in lines) + indent[:-4] + "]"


# Generated multi-line values are indented relative to the class body: libcst
# re-indents continuation lines by the block's indentation (4 spaces) itself.
BLOCK = 4


def presets_source(value: dict, indent: str = "", old_node: ast.AST | None = None,
                   old_source: str | None = None, width: int = 99 - BLOCK) -> str:
    """Source of a presets dict; unchanged leaves keep their original expression
    (``10**6 + 1`` stays as written)."""
    leaves = _leaf_sources(old_node, old_source)

    def leaf(v: Any, path: tuple) -> str:
        old = leaves.get(path)
        if old is not None and old[0] == v and type(old[0]) is type(v) and old[1]:
            return old[1]
        return py(v)

    def inline(v: Any, path: tuple) -> str:
        if isinstance(v, dict):
            return "{" + ", ".join(f"{py(k)}: {inline(x, path + (k,))}" for k, x in v.items()) + "}"
        return leaf(v, path)

    one = inline(value, ())
    head = len(indent) + len("presets = ")
    if head + len(one) <= width:
        return one
    lines = ["{"]
    inner = indent + "    "
    for name, cfg in value.items():
        row = f"{inner}{py(name)}: {inline(cfg, (name,))},"
        if len(row) <= width or not isinstance(cfg, dict):
            lines.append(row)
            continue
        lines.append(f"{inner}{py(name)}: {{")
        for k, x in cfg.items():
            row = f"{inner}    {py(k)}: {inline(x, (name, k))},"
            if len(row) > width and isinstance(x, list) and x:
                row = f"{inner}    {py(k)}: " + _wrap_list(x, inner + "        ", width) + ","
            lines.append(row)
        lines.append(f"{inner}}},")
    lines.append(indent + "}")
    return "\n".join(lines)


def value_source(name: str, value: Any, indent: str = "", old_node: ast.AST | None = None,
                 old_source: str | None = None) -> str:
    """Python source of a metadata value."""
    if name == "solution_detail":
        if value not in SOLUTION_DETAILS:
            raise TaskEditError(f"solution_detail must be one of {sorted(SOLUTION_DETAILS)}")
        return f"SolutionDetail.{SOLUTION_DETAILS[value]}"
    if name == "id":
        if not isinstance(value, str) or not ID_RE.match(value):
            raise TaskEditError(f"bad task id {value!r} (expected e.g. 'dlp.shanks')")
        return py(value)
    if name in ("title_ru", "notes", "statement", "solution"):
        if not isinstance(value, str):
            raise TaskEditError(f"{name} must be a string")
        if name in TEMPLATE_FIELDS and not value.strip():
            raise TaskEditError(f"{name} must not be empty")
        return _str_literal(value, indent)
    if name == "topics":
        if not isinstance(value, list) or not all(isinstance(t, str) and t for t in value):
            raise TaskEditError("topics must be a list of topic slugs")
        if not value:
            raise TaskEditError("a task needs at least one topic")
        return py(tuple(value))
    if name == "complexity":
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 10:
            raise TaskEditError("complexity must be an integer 1..10")
        return repr(value)
    if name == "family":
        if value is not None and (not isinstance(value, str) or not value):
            raise TaskEditError("family must be a non-empty string or null")
        return py(value)
    if name == "presets":
        if not isinstance(value, dict) or "default" not in value \
                or not all(isinstance(v, dict) for v in value.values()):
            raise TaskEditError("presets must map preset names to dicts and include 'default'")
        return presets_source(value, indent, old_node, old_source)
    raise TaskEditError(f"unknown field {name!r}")


class _MetaTransformer(cst.CSTTransformer):
    def __init__(self, task_id: str, updates: dict[str, str]) -> None:
        self.task_id = task_id
        self.updates = updates
        self.found = False
        self._depth = 0

    @staticmethod
    def _assign_name(stmt: cst.BaseStatement) -> str | None:
        if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1:
            s = stmt.body[0]
            if isinstance(s, cst.Assign) and len(s.targets) == 1 \
                    and isinstance(s.targets[0].target, cst.Name):
                return s.targets[0].target.value
            if isinstance(s, cst.AnnAssign) and isinstance(s.target, cst.Name) and s.value is not None:
                return s.target.value
        return None

    def _is_target(self, node: cst.ClassDef) -> bool:
        if not isinstance(node.body, cst.IndentedBlock):
            return False
        for stmt in node.body.body:
            if self._assign_name(stmt) == "id":
                value = stmt.body[0].value  # type: ignore[union-attr]
                if isinstance(value, cst.SimpleString) and value.evaluated_value == self.task_id:
                    return True
        return False

    def leave_ClassDef(self, original: cst.ClassDef, updated: cst.ClassDef) -> cst.ClassDef:
        if self.found or not self._is_target(original):
            return updated
        self.found = True
        body = list(updated.body.body)  # type: ignore[union-attr]
        pending = dict(self.updates)
        last_meta = 0
        for i, stmt in enumerate(body):
            name = self._assign_name(stmt)
            if name in FIELDS:
                last_meta = i
            if name in pending:
                expr = cst.parse_expression(pending.pop(name))
                line = stmt  # type: ignore[assignment]
                small = line.body[0]  # type: ignore[union-attr]
                body[i] = line.with_changes(body=[small.with_changes(value=expr)])  # type: ignore[union-attr]
        # attributes the class did not define yet: insert after the last metadata line
        new = [cst.parse_statement(f"{name} = {src}\n") for name, src in
               sorted(pending.items(), key=lambda kv: FIELDS.index(kv[0]))]
        body[last_meta + 1:last_meta + 1] = new
        return updated.with_changes(body=updated.body.with_changes(body=body))  # type: ignore[union-attr]


def apply_meta(source: str, task_id: str, values: dict[str, Any]) -> str:
    """Return ``source`` with the given metadata fields of task ``task_id`` replaced.

    Only literal attributes can be written: replacing a computed expression
    would silently drop code, so it is refused.
    """
    meta = read_meta(source, task_id)
    nodes = _class_attrs(_find_class(ast.parse(source), task_id))
    updates = {}
    for name, value in values.items():
        if name not in FIELDS:
            raise TaskEditError(f"unknown field {name!r}")
        f = meta["fields"][name]
        if f["defined"] and not f["editable"]:
            raise TaskEditError(f"{name} is computed in code ({f['expr'][:60]}...); "
                                "edit it in the Code tab")
        if f["defined"] and f["value"] == value:
            continue
        updates[name] = value_source(name, value, old_node=nodes.get(name), old_source=source)
    if not updates:
        return source
    module = cst.parse_module(source)
    tr = _MetaTransformer(task_id, updates)
    out = module.visit(tr).code
    if not tr.found:
        raise TaskEditError(f"class with id = {task_id!r} not found in module")
    ast.parse(out)  # never write a module we broke
    return out


# --- scaffolding ------------------------------------------------------------------

SCAFFOLD_CLASS = '''

class {class_name}(Task):
    id = {id}
    title_ru = {title}
    topics = ({topic},)
    complexity = {complexity}
    solution_detail = SolutionDetail.FULL
    presets = {{"default": {{"lo": 10, "hi": 100}}}}
    statement = r"Вычислить $\\VAR{{a}} + \\VAR{{b}}$."
    solution = r"$\\VAR{{a}} + \\VAR{{b}} = \\VAR{{answer}}$."

    def sample(self, rng):
        # all randomness from rng; value ranges from self.cfg (presets)
        a = rng.randrange(self.cfg.lo, self.cfg.hi)
        b = rng.randrange(self.cfg.lo, self.cfg.hi)
        return {{"a": a, "b": b, "answer": a + b}}

    def check(self, p):
        # independent self-check of the answer
        assert p["answer"] == p["a"] + p["b"]
'''

IMPORT_LINE = "from taskgen.core.task import SolutionDetail, Task\n"


def scaffold(existing: str | None, *, task_id: str, class_name: str, title: str,
             topic: str, complexity: int = 1) -> str:
    """Module source with a new task class appended (or a new module)."""
    if not ID_RE.match(task_id):
        raise TaskEditError(f"bad task id {task_id!r} (expected e.g. 'dlp.shanks')")
    if not IDENT_RE.match(class_name):
        raise TaskEditError(f"bad class name {class_name!r}")
    cls = SCAFFOLD_CLASS.format(class_name=class_name, id=py(task_id), topic=py(topic),
                                title=_str_literal(title, "    "), complexity=int(complexity))
    if existing is None:
        out = f'"""{title}."""\n\n' + IMPORT_LINE + cls
    else:
        tree = ast.parse(existing)
        if any(isinstance(n, ast.ClassDef) and n.name == class_name for n in tree.body):
            raise TaskEditError(f"class {class_name} already exists in this module")
        out = existing.rstrip("\n") + "\n" + cls
        if not re.search(r"^from taskgen\.core\.task import .*\bTask\b", existing, re.M) \
                or "SolutionDetail" not in existing:
            lines = out.splitlines(keepends=True)
            pos = tree.body[0].end_lineno if tree.body and isinstance(tree.body[0], ast.Expr) \
                and isinstance(getattr(tree.body[0], "value", None), ast.Constant) else 0
            lines.insert(pos, ("\n" if pos else "") + IMPORT_LINE)
            out = "".join(lines)
    ast.parse(out)
    return out
