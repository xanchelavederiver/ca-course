"""Sheet specs: list, read, validate, save (validated, comment-preserving), create."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from taskgen_web import sheetedit
from taskgen_web.context import Ctx, get_ctx

router = APIRouter(tags=["sheets"])


def _sheet_path(ctx: Ctx, rel: str, must_exist: bool = True) -> Path:
    p = PurePosixPath(rel)
    if p.is_absolute() or ".." in p.parts or not p.parts or p.parts[0] != "sheets" \
            or p.suffix != ".yaml":
        raise HTTPException(400, f"not a sheet path: {rel!r} (expected sheets/<dir>/<name>.yaml)")
    full = ctx.repo / p
    if must_exist and not full.is_file():
        raise HTTPException(404, f"no such sheet: {rel}")
    return full


def _plain(text: str) -> tuple[Any, str | None]:
    try:
        return sheetedit.to_plain(sheetedit.load(text)), None
    except Exception as e:  # YAML syntax error
        return None, f"YAML: {e}"


def _runs(ctx: Ctx, sheet_id: str) -> list[dict[str, Any]]:
    d = ctx.repo / "archive" / sheet_id
    if not d.is_dir():
        return []
    out = []
    for m in sorted(d.glob("*/manifest.json")):
        out.append({"run": m.parent.name, "created_at": _created(m)})
    return out


def _created(manifest: Path) -> str | None:
    try:
        return json.loads(manifest.read_text(encoding="utf-8")).get("created_at")
    except (OSError, ValueError):
        return None


def _draft(ctx: Ctx, sheet_id: str) -> dict[str, Any] | None:
    d = ctx.repo / "build" / "sheets" / sheet_id
    m = d / "manifest.json"
    if not m.is_file():
        return None
    data = json.loads(m.read_text(encoding="utf-8"))
    return {"out_dir": f"build/sheets/{sheet_id}", "created_at": data.get("created_at"),
            "master_seed": data.get("master_seed"), "files": list(data.get("files", {})),
            "pdfs": sorted(p.name for p in d.glob("*.pdf")),
            "variants": [{"key": v["key"], "group": v["group"], "number": v["number"],
                          "student": v["student"]} for v in data.get("variants", [])]}


@router.get("/sheets")
async def list_sheets(ctx: Ctx = Depends(get_ctx)) -> list[dict]:
    out = []
    for path in sheetedit.list_sheets(ctx.repo):
        rel = str(path.relative_to(ctx.repo))
        data, err = _plain(path.read_text(encoding="utf-8"))
        data = data if isinstance(data, dict) else {}
        sid = data.get("id")
        runs = _runs(ctx, sid) if isinstance(sid, str) else []
        draft = _draft(ctx, sid) if isinstance(sid, str) else None
        groups = data.get("groups") or []
        out.append({
            "path": rel, "dir": str(PurePosixPath(rel).parent.relative_to("sheets")),
            "id": sid, "kind": data.get("kind"), "title": data.get("title"),
            "semester": data.get("semester"), "error": err,
            "variants": sum((g.get("count") or len(g.get("students") or []))
                            for g in groups if isinstance(g, dict)) if groups else 1,
            "last_draft": draft["created_at"] if draft else None,
            "last_issue": runs[-1] if runs else None, "issued_runs": len(runs),
        })
    return out


@router.get("/sheets/{path:path}")
async def get_sheet(path: str, ctx: Ctx = Depends(get_ctx)) -> dict:
    full = _sheet_path(ctx, path)
    raw = full.read_text(encoding="utf-8")
    data, err = _plain(raw)
    problems = [err] if err else await ctx.worker.call("check_sheet", text=raw)
    sid = data.get("id") if isinstance(data, dict) else None
    return {"path": path, "raw": raw, "data": data, "problems": problems,
            "draft": _draft(ctx, sid) if isinstance(sid, str) else None,
            "runs": _runs(ctx, sid) if isinstance(sid, str) else []}


class SaveBody(BaseModel):
    raw: str


@router.put("/sheets/{path:path}")
async def put_sheet(path: str, body: SaveBody, ctx: Ctx = Depends(get_ctx)) -> Any:
    full = _sheet_path(ctx, path)
    problems = await ctx.worker.call("check_sheet", text=body.raw)
    if problems:
        return JSONResponse({"detail": "invalid sheet spec", "problems": problems}, status_code=422)
    full.write_text(body.raw, encoding="utf-8")
    data, _ = _plain(body.raw)
    return {"path": path, "raw": body.raw, "data": data, "problems": []}


class CreateBody(BaseModel):
    path: str
    kind: Literal["classroom", "individual"]
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    title: str
    semester: int | None = None
    raw: str | None = None


@router.post("/sheets", status_code=201)
async def create_sheet(body: CreateBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    full = _sheet_path(ctx, body.path, must_exist=False)
    if full.exists():
        raise HTTPException(409, f"{body.path} already exists")
    ids = {(_plain(p.read_text(encoding="utf-8"))[0] or {}).get("id")
           for p in sheetedit.list_sheets(ctx.repo)}
    if body.id in ids:
        raise HTTPException(409, f"sheet id {body.id!r} is already used")
    raw = body.raw or sheetedit.skeleton(body.kind, body.id, body.title, body.semester)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(raw, encoding="utf-8")  # a fresh skeleton may not validate yet (no tasks)
    return {"path": body.path, "raw": raw}


class YamlBody(BaseModel):
    yaml: str


@router.post("/sheets/validate")
async def validate_sheet(body: YamlBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    data, err = _plain(body.yaml)
    problems = [err] if err else await ctx.worker.call("check_sheet", text=body.yaml)
    return {"problems": problems, "data": data}


class MergeBody(BaseModel):
    base: str
    data: dict[str, Any]


@router.post("/sheets/merge")
async def merge_sheet(body: MergeBody) -> dict:
    """YAML text of form ``data``, keeping comments/formatting of ``base``."""
    try:
        return {"raw": sheetedit.merged_text(body.base, body.data)}
    except Exception as e:
        raise HTTPException(400, f"cannot merge: {e}") from None


class StatsBody(BaseModel):
    yaml: str
    seed: int = 0
    samples: int | None = Field(None, ge=1, le=20000)


@router.post("/sheets/stats")
async def sheet_stats(body: StatsBody, ctx: Ctx = Depends(get_ctx)) -> dict:
    return await ctx.worker.call("variant_stats", spec_text=body.yaml, seed=body.seed,
                                 samples=body.samples, timeout=120)


_schema_cache: dict[str, Any] = {}


@router.get("/schema/sheet")
async def sheet_schema(ctx: Ctx = Depends(get_ctx)) -> dict:
    key = str(ctx.worker.started_at)
    if key not in _schema_cache:
        _schema_cache.clear()
        _schema_cache[key] = await ctx.worker.call("sheet_schema")
    return _schema_cache[key]
