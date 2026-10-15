"""``python -m taskgen.capstone`` — capstone vectors, benchmarks, reports, checks.

    list                                   capstones with a bench/config.yaml
    image <slug>                           compose service the capstone's reference runs in
    vectors <slug|all> [--size S] [--check] [--force]   (taskgen image: needs Sage)
    bench <slug> [--size S] [--limit N] [--out raw.json]   run the reference (its image)
    report <slug> [--raw raw.json] [--slack X]             results + requirements.tex (taskgen image)
    check <slug> --cmd CMD [--cwd DIR] [--size S] [--limit N]   run a submission (instructor)
    verify-reference <slug> [--size S] [--limit N]         run the reference, fail unless all ok

Through make: ``make vectors|bench|check-capstone CAPSTONE=<slug>`` (see the Makefile).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from taskgen.capstone import config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m taskgen.capstone")
    sub = ap.add_subparsers(dest="action", required=True)
    sub.add_parser("list")
    p = sub.add_parser("image")
    p.add_argument("slug")
    p = sub.add_parser("vectors")
    p.add_argument("slug")
    p.add_argument("--size", action="append")
    p.add_argument("--check", action="store_true", help="regenerate in memory and compare")
    p.add_argument("--force", action="store_true", help="regenerate even if up to date")
    for name in ("bench", "check", "verify-reference"):
        p = sub.add_parser(name)
        p.add_argument("slug")
        p.add_argument("--size", action="append")
        p.add_argument("--limit", type=int, default=None, help="vectors per size class")
        if name == "bench":
            p.add_argument("--out", type=Path, default=None)
        if name == "check":
            p.add_argument("--cmd", dest="solver", required=True, help="the submission's solver command")
            p.add_argument("--cwd", type=Path, default=Path.cwd())
    p = sub.add_parser("report")
    p.add_argument("slug")
    p.add_argument("--raw", type=Path, default=None)
    p.add_argument("--slack", type=float, default=None)
    a = ap.parse_args(argv)

    if a.action == "list":
        for s in config.slugs():
            c = config.load(s)
            print(f"{c.n:02d}  {c.slug:<20} {c.image:<11} {c.title}")
        return 0
    if a.action == "image":
        print(config.load(a.slug).image)
        return 0
    if a.action == "vectors":
        from taskgen.capstone import vectors

        ok = True
        for s in (config.slugs() if a.slug == "all" else [a.slug]):
            ok &= vectors.write(config.load(s), a.size, check=a.check, force=a.force)
        return 0 if ok else 1

    cap = config.load(a.slug, slack=getattr(a, "slack", None))
    if a.action == "bench":
        from taskgen.capstone import runner

        runner.bench(cap, a.size, a.limit, a.out)
        return 0
    if a.action == "report":
        from taskgen.capstone import report

        raw = a.raw or config.REPO / "build" / "capstone" / cap.slug / "raw.json"
        report.report(cap, raw)
        return 0
    if a.action == "verify-reference":
        from taskgen.capstone import runner

        runner.build(cap)
        recs = runner.run(cap, cap.command, cap.dir, a.size, a.limit)
        bad = [r for r in recs if r.status != "ok"]
        print(f"{len(recs) - len(bad)}/{len(recs)} ok")
        return 1 if bad else 0
    if a.action == "check":
        from taskgen.capstone import runner

        return 0 if runner.check(cap, a.solver, a.cwd.resolve(), a.size, a.limit) else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
