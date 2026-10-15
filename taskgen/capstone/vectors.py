"""Seeded test-vector generation: ``vectors/<size>.jsonl`` + ``vectors/manifest.json``.

Vector ``i`` of size class ``s`` is drawn from ``make_rng("capstone", slug, VERSION, seed,
s, i)``, so a single vector (or class) regenerates in isolation and the files are
byte-identical across runs (the same guarantee as task sheets). Classes with
``commit: false`` are listed in ``vectors/.gitignore`` and regenerated from the seed;
the manifest still records their hashes so a regeneration can be verified.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import taskgen
from taskgen.capstone.config import Capstone, Size
from taskgen.core.rng import make_rng

MANIFEST = "manifest.json"


def vector_line(vec: dict) -> str:
    return json.dumps(vec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def generate_size(cap: Capstone, size: Size) -> list[dict]:
    gen = cap.gen()
    out = []
    for i in range(size.count):
        rng = make_rng("capstone", cap.slug, gen.VERSION, cap.seed, size.name, i)
        v = gen.generate(dict(size.params), rng)
        out.append({"id": f"{size.name}-{i:03d}", "size": size.name,
                    "tags": sorted(v.get("tags") or []), "input": v["input"],
                    "expected": v.get("expected")})
    return out


def _text(vecs: list[dict]) -> str:
    return "".join(vector_line(v) + "\n" for v in vecs)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write(cap: Capstone, sizes: list[str] | None = None, check: bool = False,
          force: bool = False, log=print) -> bool:
    """Generate (or, with ``check``, regenerate and compare) vector files.

    Without ``force``, a class whose file matches the manifest (same hash, params, seed
    and generator version) is left alone. Returns False if a check found a mismatch
    with the manifest or the files on disk.
    """
    d = cap.vectors_dir
    d.mkdir(parents=True, exist_ok=True)
    mpath = d / MANIFEST
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    gen = cap.gen()
    ok = True
    entries = dict(manifest.get("sizes") or {})
    for size in cap.sizes:
        if sizes and size.name not in sizes:
            continue
        f = d / f"{size.name}.jsonl"
        e = entries.get(size.name) or {}
        if (not check and not force and f.exists() and e.get("params") == size.params
                and e.get("count") == size.count and manifest.get("seed") == cap.seed
                and manifest.get("generator_version") == gen.VERSION
                and sha256(f.read_text(encoding="utf-8")) == e.get("sha256")):
            log(f"ok      {cap.slug}/{size.name} (up to date)")
            continue
        text = _text(generate_size(cap, size))
        h = sha256(text)
        if check:
            want = (entries.get(size.name) or {}).get("sha256")
            disk = sha256(f.read_text(encoding="utf-8")) if f.exists() else None
            good = h == want and disk in (None, h) and (disk is not None or not size.commit)
            ok &= good
            log(f"{'ok      ' if good else 'MISMATCH'} {cap.slug}/{size.name} "
                f"({size.count} vectors{'' if disk else ', not on disk'})")
            continue
        f.write_text(text, encoding="utf-8")
        entries[size.name] = {"count": size.count, "sha256": h, "commit": size.commit,
                              "params": size.params}
        log(f"wrote   {cap.dir.name}/vectors/{f.name} ({size.count} vectors)")
    if check:
        return ok
    known = {s.name for s in cap.sizes}
    manifest = {"capstone": cap.slug, "generator": cap.generator, "generator_version": gen.VERSION,
                "seed": cap.seed, "taskgen_version": taskgen.__version__,
                "sizes": {k: v for k, v in sorted(entries.items(), key=lambda kv: _order(cap, kv[0]))
                          if k in known}}
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ignored = [f"{s.name}.jsonl" for s in cap.sizes if not s.commit]
    gi = d / ".gitignore"
    if ignored:
        gi.write_text("# regenerated from the seed (make vectors); see manifest.json\n"
                      + "".join(f"/{n}\n" for n in ignored), encoding="utf-8")
    elif gi.exists():
        gi.unlink()
    return ok


def _order(cap: Capstone, name: str) -> int:
    names = [s.name for s in cap.sizes]
    return names.index(name) if name in names else len(names)


def load(cap: Capstone, size: str) -> list[dict]:
    f = cap.vectors_dir / f"{size}.jsonl"
    if not f.exists():
        raise FileNotFoundError(f"{f} is missing: run `make vectors CAPSTONE={cap.slug}`")
    return [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
