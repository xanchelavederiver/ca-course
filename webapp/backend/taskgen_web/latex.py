"""Client for the latex-worker service (scripts/latex-worker.py)."""

from __future__ import annotations

from typing import Any

import httpx


class LatexUnavailable(Exception):
    pass


class LatexClient:
    def __init__(self, url: str, timeout: float = 900.0) -> None:
        self.url = url.rstrip("/")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.url)

    async def build(self, tex: str, outdir: str | None = None) -> dict[str, Any]:
        """Compile a repo-relative ``.tex``; returns ``{ok, pdf}`` or ``{ok: False, log}``."""
        if not self.url:
            raise LatexUnavailable("PDF builds are unavailable (LATEX_WORKER_URL is not set)")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(f"{self.url}/build", json={"tex": tex, "outdir": outdir})
        except httpx.HTTPError as e:
            raise LatexUnavailable(f"latex-worker unreachable at {self.url}: {e}") from e
        data = r.json()
        if r.status_code != 200:
            return {"ok": False, "log": data.get("log", r.text)}
        return data

    async def health(self) -> bool:
        if not self.url:
            return False
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                return (await client.get(f"{self.url}/health")).status_code == 200
        except httpx.HTTPError:
            return False
