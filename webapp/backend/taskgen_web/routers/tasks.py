"""Tasks: list, inspect, edit (source / metadata), scaffold, preview, validate."""

from __future__ import annotations

import ast
import re
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from taskgen_web import taskedit
from taskgen_web.context import Ctx, get_ctx
from taskgen_web.latex import LatexUnavailable
from taskgen_web.worker import EngineError

router = APIRouter(tags=["tasks"])


def _module_name(file: str) -> str:
    return file.removesuffix(".py").replace("/", ".")


def _import_error_for(ctx: Ctx, file: str) -> str | None:
    errors = ctx.worker.info.get("import_errors") or {}
    return errors.get(_module_name(file))


def _write_module(ctx: Ctx, path: Path, source: str) -> str | None:
    """Write a task module as-is (work in progress is never lost); returns a syntax error."""
    path.write_text(source, encoding="utf-8")
    ctx.worker.mark_stale()
    try:
        ast.parse(source)
    except SyntaxError as e:
        return f"{e.msg} (line {e.lineno})"
    return None


def _module_path(ctx: Ctx, rel: str) -> Path:
    p = PurePosixPath(rel)
    if p.is_absolute() or ".." in p.parts or p.parts[:2] != ("taskgen", "tasks") or p.suffix != ".py":
        raise HTTPException(400, f"not a task module path: {rel!r}")
    return ctx.repo / p


@router.get("/tasks")
async def list_tasks(topic: str | None = None, complexity: str | None = None,
                     family: str | None = None, text: str | None = None,
                     ctx: Ctx = Depends(get_ctx)) -> dict:
    comp = [int(c) for c in complexity.split(",")] if complexity else None
    tasks = await ctx.worker.call("list_tasks", topics=topic.split(",") if topic else None,
                                  complexity=comp, family=family, text=text)
    registered = {t["id"] for t in tasks}
    for t in tasks:
        t["validation"] = {k: v for k, v in ctx.validation.get(t["id"], {}).items() if k != "results"} \
            or None
        t["broken"] = False
    # tasks whose module does not import: still listed (from the static index) so they can be fixed
    unfiltered = not (topic or complexity or family or text)
    broken = []
    if unfiltered:
        for tid, loc in sorted(ctx.index.scan().items()):
            if tid not in registered:
                broken.append({"id": tid, "title": "", "topics": [], "complexity": None,
                               "family": None, "family_name": None, "solution_detail": None,
                               "presets": [], "notes": "", "module": _module_name(loc.file),
                               "class_name": loc.class_name, "file": loc.file,
                               "line_start": loc.line, "line_end": None, "validation": None,
                               "broken": True})
    return {"tasks": tasks + broken,
            "import_errors": ctx.worker.info.get("import_errors") or {},
            "syntax_errors": ctx.index.syntax_errors}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, ctx: Ctx = Depends(get_ctx)) -> dict:
    try:
        loc = ctx.index.find(task_id)
    except KeyError:
        raise HTTPException(404, f"unknown task id {task_id!r}") from None
    path = ctx.repo / loc.file
    source = path.read_text(encoding="utf-8")
    try:
        meta = taskedit.read_meta(source, task_id)
        meta_error = None
    except (SyntaxError, taskedit.TaskEditError) as e:
        meta, meta_error = None, str(e)
    try:
        info = await ctx.worker.call("task_info", task_id=task_id)
        info_error = None
    except EngineError as e:
        info, info_error = None, str(e)
    return {"id": task_id, "file": loc.file, "class_name": loc.class_name, "source": source,
            "meta": meta, "meta_error": meta_error, "info": info, "info_error": info_error,
            "import_error": _import_error_for(ctx, loc.file),
            "validation": ctx.validation.get(task_id)}


class SourceBody(BaseModel):
    source: str


@router.put("/tasks/{task_id}/source")
async def put_task_source(task_id: str, body: SourceBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    try:
        loc = ctx.index.find(task_id)
    except KeyError:
        raise HTTPException(404, f"unknown task id {task_id!r}") from None
    err = _write_module(ctx, ctx.repo / loc.file, body.source)
    return {"ok": err is None, "syntax_error": err, "file": loc.file}


class MetaBody(BaseModel):
    values: dict[str, Any]


@router.patch("/tasks/{task_id}/meta")
async def patch_task_meta(task_id: str, body: MetaBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    try:
        loc = ctx.index.find(task_id)
    except KeyError:
        raise HTTPException(404, f"unknown task id {task_id!r}") from None
    path = ctx.repo / loc.file
    source = path.read_text(encoding="utf-8")
    new_id = body.values.get("id", task_id)
    if new_id != task_id and new_id in ctx.index.scan():
        raise HTTPException(409, f"task id {new_id!r} already exists")
    try:
        out = taskedit.apply_meta(source, task_id, body.values)
    except (SyntaxError, taskedit.TaskEditError) as e:
        raise HTTPException(400, str(e)) from None
    if out != source:
        _write_module(ctx, path, out)
    return {"id": new_id, "file": loc.file, "source": out, "meta": taskedit.read_meta(out, new_id)}


class ScaffoldBody(BaseModel):
    task_id: str
    class_name: str
    title: str
    topic: str
    complexity: int = Field(1, ge=1, le=10)
    # module path relative to taskgen/tasks, e.g. "dlp/dlp_mod_p.py" (created if missing)
    module: str


@router.post("/tasks", status_code=201)
async def scaffold_task(body: ScaffoldBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    parts = PurePosixPath(body.module).parts
    if not parts or not body.module.endswith(".py") or \
            not all(re.match(taskedit.MODULE_RE, p.removesuffix(".py")) for p in parts):
        raise HTTPException(400, f"bad module path {body.module!r} (e.g. 'dlp/my_tasks.py')")
    if body.task_id in ctx.index.scan():
        raise HTTPException(409, f"task id {body.task_id!r} already exists")
    path = ctx.repo / "taskgen" / "tasks" / PurePosixPath(body.module)
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    try:
        source = taskedit.scaffold(existing, task_id=body.task_id, class_name=body.class_name,
                                   title=body.title, topic=body.topic, complexity=body.complexity)
    except (SyntaxError, taskedit.TaskEditError) as e:
        raise HTTPException(400, str(e)) from None
    # make sure every directory on the way is a package (discovery walks packages)
    d = path.parent
    while d != ctx.repo / "taskgen" / "tasks":
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").touch(exist_ok=True)
        d = d.parent
    _write_module(ctx, path, source)
    rel = str(path.relative_to(ctx.repo))
    return {"id": body.task_id, "file": rel, "created_module": existing is None}


@router.get("/modules")
async def get_module(path: str, ctx: Ctx = Depends(get_ctx)) -> dict:
    full = _module_path(ctx, path)
    if not full.is_file():
        raise HTTPException(404, f"no such module: {path}")
    ctx.index.scan()
    return {"path": path, "source": full.read_text(encoding="utf-8"),
            "import_error": _import_error_for(ctx, path),
            "syntax_error": ctx.index.syntax_errors.get(path),
            "tasks": [loc.id for loc in ctx.index.tasks().values() if loc.file == path]}


class ModuleBody(BaseModel):
    path: str
    source: str


@router.put("/modules")
async def put_module(body: ModuleBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    full = _module_path(ctx, body.path)
    if not full.is_file():
        raise HTTPException(404, f"no such module: {body.path}")
    err = _write_module(ctx, full, body.source)
    return {"ok": err is None, "syntax_error": err}


class PreviewBody(BaseModel):
    seed: int | None = None
    count: int = Field(3, ge=1, le=20)
    statement: str | None = None
    solution: str | None = None
    pdf: bool = False


@router.post("/tasks/{ref}/preview")
async def preview(ref: str, body: PreviewBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    import secrets

    seed = body.seed if body.seed is not None else secrets.randbits(31)
    tex = None
    if body.pdf:
        tex = f"build/web/preview/{re.sub(r'[^A-Za-z0-9._-]', '_', ref)}.tex"
    res = await ctx.worker.call("preview", ref=ref, seed=seed, count=body.count,
                                statement=body.statement, solution=body.solution, tex_path=tex,
                                timeout=60)
    out: dict[str, Any] = {"seed": seed, "instances": res["instances"], "pdf": None, "log": None}
    if tex:
        try:
            built = await ctx.latex.build(tex, str(PurePosixPath(tex).parent))
        except LatexUnavailable as e:
            out["log"] = str(e)
        else:
            out["pdf"] = built.get("pdf")
            out["log"] = built.get("log")
    return out


class ValidateBody(BaseModel):
    count: int = Field(50, ge=1, le=1000)
    seed: int = 0


@router.post("/tasks/{ref}/validate")
async def validate_task(ref: str, body: ValidateBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    res = await ctx.worker.call("validate", target=ref, count=body.count, seed=body.seed)
    ctx.record_validation(res["results"], body.count)
    return res


@router.post("/validate")
async def validate_all(body: ValidateBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    async def run(job):
        def progress(p):
            job.log(f"{'ok  ' if p['ok'] else 'FAIL'} {p['ref']}", **p)
        res = await ctx.worker.call("validate", target="all", count=body.count, seed=body.seed,
                                    on_progress=progress, timeout=3600)
        ctx.record_validation(res["results"], body.count)
        return res

    job = ctx.jobs.submit("validate", f"Validate all tasks ({body.count} instances)", run)
    return {"job": job.id}
