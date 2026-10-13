"""Topic taxonomy (``taskgen/tasks/taxonomy.yaml``)."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ruamel.yaml.comments import CommentedMap

from taskgen_web import sheetedit
from taskgen_web.context import Ctx, get_ctx

router = APIRouter(tags=["topics"])
TOPIC_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")


@router.get("/topics")
async def topics(ctx: Ctx = Depends(get_ctx)) -> list[dict]:
    return await ctx.worker.call("topics")


class Topic(BaseModel):
    slug: str
    title: str


class TopicsBody(BaseModel):
    items: list[Topic]


@router.put("/topics")
async def put_topics(body: TopicsBody, ctx: Ctx = Depends(get_ctx)) -> list[dict]:
    slugs = [t.slug for t in body.items]
    problems = [f"bad slug {s!r}" for s in slugs if not TOPIC_RE.match(s)]
    problems += [f"duplicate {s!r}" for s in sorted({s for s in slugs if slugs.count(s) > 1})]
    known = set(slugs)
    for s in slugs:
        parts = s.split(".")
        problems += [f"{s!r}: parent {'.'.join(parts[:i])!r} missing"
                     for i in range(1, len(parts)) if ".".join(parts[:i]) not in known]
    problems += [f"{t.slug!r}: empty title" for t in body.items if not t.title.strip()]
    used = {}
    for task in await ctx.worker.call("list_tasks"):
        for t in task["topics"]:
            used.setdefault(t, []).append(task["id"])
    problems += [f"topic {t!r} is used by {', '.join(ids)}" for t, ids in sorted(used.items())
                 if t not in known]
    if problems:
        raise HTTPException(422, {"problems": problems})

    path = ctx.repo / "taskgen" / "tasks" / "taxonomy.yaml"
    old = sheetedit.load(path.read_text(encoding="utf-8"))
    new = CommentedMap()
    for t in body.items:
        new[t.slug] = t.title
    if isinstance(old, CommentedMap):
        # keep the comments attached to surviving keys and the header comment
        new.ca.comment = old.ca.comment
        for k, c in old.ca.items.items():
            if k in new:
                new.ca.items[k] = c
    path.write_text(sheetedit.dump(new), encoding="utf-8")
    ctx.worker.mark_stale()
    return await ctx.worker.call("topics")
