"""taskgen command line interface (a thin wrapper over ``taskgen.service``).

    taskgen list [--topic T] [-v]
    taskgen topics
    taskgen preview <task-id[@preset]> [--seed N] [--count K]
    taskgen validate [<task-id[@preset]>|all] [--count N] [--seed S]
    taskgen gen <sheet.yaml> [--seed N] [--draft] [--variant KEY ...]
    taskgen regen <manifest.json|run-dir> [--variant KEY ...] [--out DIR]
    taskgen seal <run-dir>
    taskgen schema
    taskgen catalog [--check]
    taskgen course check|scaffold|examples|docs|book
    taskgen exam render [--sem N] [--check]
    taskgen exam coverage [--sem N]
"""

from __future__ import annotations

import json
from pathlib import Path

import click

import taskgen
from taskgen import service


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(p)


@click.group()
@click.version_option(taskgen.__version__, prog_name="taskgen")
def main() -> None:
    """Task database and deterministic task-sheet generator."""


@main.command("list")
@click.option("--topic", "topics", multiple=True, help="Filter by topic (prefix match).")
@click.option("-v", "--verbose", is_flag=True, help="Show presets, family and notes.")
def list_cmd(topics: tuple[str, ...], verbose: bool) -> None:
    """List registered tasks."""
    tasks = service.list_tasks(list(topics) or None)
    w = max((len(t["id"]) for t in tasks), default=10)
    for t in tasks:
        click.echo(f"{t['id']:<{w}}  c={t['complexity']}  {t['solution_detail']:<11}  "
                   f"{','.join(t['topics']):<34}  {t['title']}")
        if verbose:
            click.echo(f"{'':<{w}}  family={t['family_name']}  presets={','.join(t['presets'])}")
            if t["notes"]:
                click.echo(f"{'':<{w}}  notes: {t['notes']}")
    click.echo(f"\n{len(tasks)} task(s)", err=True)


@main.command()
def topics() -> None:
    """Show the topic taxonomy with task counts."""
    for t in service.topics():
        indent = "  " * t["depth"]
        click.echo(f"{indent}{t['slug']:<{34 - len(indent)}} {t['count']:>3}  {t['title']}")


@main.command()
@click.argument("ref")
@click.option("--seed", type=int, default=None, help="Instance seed (default: random).")
@click.option("--count", type=int, default=1, show_default=True)
@click.option("--json", "as_json", is_flag=True, help="Print full instances as JSON.")
def preview(ref: str, seed: int | None, count: int, as_json: bool) -> None:
    """Generate and print instance(s) of a task."""
    for inst in service.preview(ref, seed, count):
        if as_json:
            click.echo(json.dumps(inst.to_dict(), ensure_ascii=False, indent=2))
            continue
        click.secho(f"--- {inst.ref}  seed={inst.seed}", fg="cyan")
        click.echo(inst.statement)
        click.secho("solution:", fg="green")
        click.echo(inst.solution)
        click.secho(f"answer: {json.dumps(inst.answer, ensure_ascii=False)}", fg="green")


@main.command()
@click.argument("target", default="all")
@click.option("--count", type=int, default=50, show_default=True, help="Instances per task/preset.")
@click.option("--seed", type=int, default=0, show_default=True)
@click.option("--traceback", "show_tb", is_flag=True, help="Print tracebacks of failures.")
def validate(target: str, count: int, seed: int, show_tb: bool) -> None:
    """Generate and self-check many instances of task(s) (all presets)."""
    report = service.validate(target, count, seed)
    for p in report.taxonomy:
        click.secho(f"TAXONOMY  {p}", fg="red")
    for r in report.results:
        if r.ok:
            click.echo(f"ok    {r.ref}")
        else:
            click.secho(f"FAIL  {r.ref}: {r.error}", fg="red")
            if show_tb:
                click.echo(r.traceback, err=True)
    if not report.ok:
        raise SystemExit(1)


@main.command()
@click.argument("sheet", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--seed", type=int, default=None, help="Master seed (default: random, recorded).")
@click.option("--draft", is_flag=True,
              help="Write to build/sheets/<id>/ instead of issuing into archive/.")
@click.option("--variant", "variants", multiple=True, help="Only these variant keys (implies --draft).")
@click.option("--quiet", is_flag=True, help="Print only the output directory.")
def gen(sheet: Path, seed: int | None, draft: bool, variants: tuple[str, ...], quiet: bool) -> None:
    """Generate a sheet (+ solutions) from a YAML spec."""
    res = service.generate(sheet.read_text(encoding="utf-8"), seed, draft=draft,
                           only=set(variants) or None, spec_path=_rel(sheet))
    if res.git and res.git["dirty"]:
        click.secho("warning: working tree has uncommitted changes; the manifest's git "
                    "commit does not fully describe the generator", fg="yellow", err=True)
    if quiet:
        click.echo(_rel(res.out_dir))
        return
    n_tasks = sum(len(v.instances) for v in res.run.variants)
    click.echo(f"{res.run.spec.id}: {len(res.run.variants)} variant(s), {n_tasks} task(s), "
               f"master seed {res.run.master_seed}")
    click.echo(f"{'draft' if res.draft else 'issued'}: {_rel(res.manifest_path)}")
    click.echo(_rel(res.out_dir))


@main.command()
@click.argument("manifest", type=click.Path(exists=True, path_type=Path))
@click.option("--variant", "variants", multiple=True, help="Only regenerate these variant keys.")
@click.option("--out", type=click.Path(file_okay=False, path_type=Path), default=None,
              help="Output directory (default: build/regen/<sheet-id>/<run>).")
def regen(manifest: Path, variants: tuple[str, ...], out: Path | None) -> None:
    """Reproduce an archived run and verify it is identical."""
    report, out = service.regen(manifest, set(variants) or None, out)
    for w in report.warnings:
        click.secho(f"warning: {w}", fg="yellow", err=True)
    click.echo(f"regenerated {len(report.checked)} variant(s) into {_rel(out)}")
    if report.identical:
        click.secho("IDENTICAL", fg="green")
    else:
        click.secho("DIFFERENT: " + ", ".join(report.mismatches), fg="red")
        raise SystemExit(1)


@main.command()
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def seal(run_dir: Path) -> None:
    """Record the hashes of built PDFs in a run's manifest."""
    added = service.seal(run_dir)
    if not added:
        click.secho("no PDFs found", fg="yellow", err=True)
        raise SystemExit(1)
    click.echo(f"sealed {', '.join(added)} in {_rel(run_dir / 'manifest.json')}")


@main.command()
@click.option("--check", "check_only", is_flag=True, help="Fail if the catalog is out of date.")
def catalog(check_only: bool) -> None:
    """Regenerate sheets/catalog/all-tasks.yaml (one instance of every task and preset)."""
    text = service.catalog_yaml()
    current = service.CATALOG.read_text(encoding="utf-8") if service.CATALOG.exists() else ""
    if check_only:
        if current != text:
            click.secho("catalog is out of date: run `taskgen catalog`", fg="red")
            raise SystemExit(1)
        return
    service.CATALOG.write_text(text, encoding="utf-8")
    click.echo(_rel(service.CATALOG))


@main.group()
def course() -> None:
    """Course map (course.yaml): checks, scaffolding, worked examples, books."""


def _course():
    from taskgen.core import course as c

    return c, c.load_course()


@course.command("check")
@click.option("--no-examples", is_flag=True, help="Skip the worked-example staleness check.")
@click.option("--strict", is_flag=True, help="Fail on warnings too.")
def course_check(no_examples: bool, strict: bool) -> None:
    """Report gaps: missing notes/slides/handouts/sheets, uncovered topics and questions."""
    c, crs = _course()
    probs = c.check(crs, examples_stale=not no_examples)
    for p in probs:
        click.secho(str(p), fg="red" if p.level == "error" else "yellow")
    errors = sum(p.level == "error" for p in probs)
    click.echo(f"{errors} error(s), {len(probs) - errors} warning(s)", err=True)
    if errors or (strict and probs):
        raise SystemExit(1)


@course.command("scaffold")
@click.option("--sem", type=int, default=None)
def course_scaffold(sem: int | None) -> None:
    """Create missing lecture/seminar directories and seminar sheets from the templates."""
    c, crs = _course()
    for path in c.scaffold(crs, sem=sem):
        click.echo(f"created {path}")


@course.command("examples")
@click.option("--sem", type=int, default=None)
@click.option("--only", default=None, help="Only lecture directories containing this text.")
@click.option("--check", "check_only", is_flag=True, help="Only report stale examples.")
def course_examples(sem: int | None, only: str | None, check_only: bool) -> None:
    """Render taskgen worked examples of the lecture notes (examples.yaml -> examples/*.tex)."""
    c, crs = _course()
    bad = False
    for path, status in c.examples(crs, write=not check_only, sem=sem, only=only):
        if status != "ok":
            click.secho(f"{status:<8} {path}", fg="red" if status.startswith(("error", "stale")) else None)
        bad |= status.startswith(("error", "stale"))
    if bad:
        raise SystemExit(1)


@course.command("docs")
@click.option("--sem", type=int, default=None)
@click.option("--sheets", is_flag=True, help="List the seminar sheet specs instead.")
def course_docs(sem: int | None, sheets: bool) -> None:
    """List the LaTeX documents (or seminar sheets) of the course map."""
    c, crs = _course()
    for path in (c.sheets(crs, sem) if sheets else c.documents(crs, sem)):
        click.echo(path)


@course.command("book")
@click.argument("sem", type=int)
def course_book(sem: int) -> None:
    """Write the semester book of lecture notes (build/materials/semN/notes-book.tex)."""
    c, crs = _course()
    click.echo(_rel(c.write_book(crs, sem)))


@main.group()
def exam() -> None:
    """Exam question lists (materials/semN/exam/questions.yaml)."""


@exam.command("render")
@click.option("--sem", type=int, default=None)
@click.option("--check", "check_only", is_flag=True, help="Fail if questions-body.tex is stale.")
def exam_render(sem: int | None, check_only: bool) -> None:
    """Render questions.yaml -> questions-body.tex (shared by questions{,-refs}.tex)."""
    from taskgen.core import exam as ex

    _, crs = _course()
    bad = False
    for r in ex.render_all(crs, sem=sem, write=not check_only):
        bad |= r.status in ("stale", "missing")
        click.secho(f"{r.status:<8} {r.path}", fg="red" if r.status in ("stale", "missing") else None)
    if bad:
        if check_only:
            click.echo("run `taskgen exam render`", err=True)
        raise SystemExit(1)


@exam.command("coverage")
@click.option("--sem", type=int, default=None)
def exam_coverage(sem: int | None) -> None:
    """Which questions the exam task sheet (questions.yaml `sheet:`) covers, by topics."""
    from taskgen.core import exam as ex

    _, crs = _course()
    for s in crs.semesters:
        if sem is not None and s.n != sem:
            continue
        e = ex.load_sem(s.n)
        if e is None:
            continue
        cov = ex.coverage(e, s)
        n = sum(qc.covered for qc in cov)
        click.secho(f"semester {s.n}: {e.sheet or '(no sheet)'} covers {n}/{len(cov)} questions",
                    bold=True)
        for qc in cov:
            mark = "ok  " if qc.covered else "--  "
            what = "; ".join(qc.slots) if qc.covered else ", ".join(qc.topics) or "(no task topics)"
            click.secho(f"  {mark}{qc.question.label:<6} {what}", fg=None if qc.covered else "yellow")


@main.command()
def schema() -> None:
    """Print the JSON Schema of sheet specs."""
    click.echo(json.dumps(service.sheet_schema(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
