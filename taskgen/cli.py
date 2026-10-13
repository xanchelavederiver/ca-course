"""taskgen command line interface (a thin wrapper over ``taskgen.service``).

    taskgen list [--topic T] [-v]
    taskgen topics
    taskgen preview <task-id[@preset]> [--seed N] [--count K]
    taskgen validate [<task-id[@preset]>|all] [--count N] [--seed S]
    taskgen gen <sheet.yaml> [--seed N] [--draft] [--variant KEY ...]
    taskgen regen <manifest.json|run-dir> [--variant KEY ...] [--out DIR]
    taskgen seal <run-dir>
    taskgen schema
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
def schema() -> None:
    """Print the JSON Schema of sheet specs."""
    click.echo(json.dumps(service.sheet_schema(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
