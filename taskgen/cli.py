"""taskgen command line interface.

    taskgen list [--topic T] [-v]
    taskgen topics
    taskgen preview <task-id[@preset]> [--seed N] [--count K]
    taskgen validate [<task-id[@preset]>|all] [--count N] [--seed S]
    taskgen gen <sheet.yaml> [--seed N] [--draft] [--variant KEY ...]
    taskgen regen <manifest.json|run-dir> [--variant KEY ...] [--out DIR]
    taskgen seal <run-dir>
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

import click

import taskgen
from taskgen.core import audit, engine, registry, taxonomy
from taskgen.core.rng import derive_seed, make_rng, new_master_seed
from taskgen.core.sheet import load_sheet


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
    tasks = registry.tasks_matching(list(topics)) if topics else registry.all_tasks()
    w = max((len(c.id) for c in tasks), default=10)
    for c in tasks:
        click.echo(f"{c.id:<{w}}  c={c.complexity}  {c.solution_detail.value:<11}  "
                   f"{','.join(c.topics):<34}  {c.title_ru}")
        if verbose:
            click.echo(f"{'':<{w}}  family={c.family_name()}  presets={','.join(c.presets)}")
            if c.notes:
                click.echo(f"{'':<{w}}  notes: {c.notes}")
    click.echo(f"\n{len(tasks)} task(s)", err=True)


@main.command()
def topics() -> None:
    """Show the topic taxonomy with task counts."""
    for slug, title in taxonomy.taxonomy().items():
        n = len(registry.tasks_matching([slug]))
        indent = "  " * slug.count(".")
        click.echo(f"{indent}{slug:<{34 - len(indent)}} {n:>3}  {title}")


@main.command()
@click.argument("ref")
@click.option("--seed", type=int, default=None, help="Instance seed (default: random).")
@click.option("--count", type=int, default=1, show_default=True)
@click.option("--json", "as_json", is_flag=True, help="Print full instances as JSON.")
def preview(ref: str, seed: int | None, count: int, as_json: bool) -> None:
    """Generate and print instance(s) of a task."""
    task = registry.get_task(ref)
    base = new_master_seed() if seed is None else seed
    for k in range(count):
        s = base if k == 0 else derive_seed(base, k)
        inst = task.generate(make_rng(s), seed=s)
        if as_json:
            click.echo(json.dumps(inst.to_dict(), ensure_ascii=False, indent=2))
            continue
        click.secho(f"--- {inst.ref}  seed={s}", fg="cyan")
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
    problems = taxonomy.check_taxonomy() if target == "all" else []
    for p in problems:
        click.secho(f"TAXONOMY  {p}", fg="red")
    if target == "all":
        tasks = [cls(p) for cls in registry.all_tasks() for p in cls.presets]
    else:
        tid, preset = registry.parse_ref(target)
        cls = registry.task_class(tid)
        tasks = [cls(preset)] if preset else [cls(p) for p in cls.presets]
    failed = 0
    for t in tasks:
        try:
            for k in range(count):
                s = derive_seed(seed, t.ref, k)
                a = t.generate(make_rng(s), seed=s)
                b = t.generate(make_rng(s), seed=s)
                if a != b:
                    raise AssertionError(f"non-deterministic for seed {s}")
            click.echo(f"ok    {t.ref}")
        except Exception as e:  # report and continue
            failed += 1
            click.secho(f"FAIL  {t.ref}: {e}", fg="red")
            if show_tb:
                traceback.print_exc()
    if failed or problems:
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
    spec, source = load_sheet(sheet)
    master = new_master_seed() if seed is None else seed
    only = set(variants) or None
    run = engine.generate(spec, master, only=only)
    if draft or only:
        out = audit.REPO_ROOT / "build" / "sheets" / spec.id
    else:
        out = audit.new_run_dir(spec.id)
        git = audit.git_info()
        if git["dirty"]:
            click.secho("warning: working tree has uncommitted changes; the manifest's git "
                        "commit does not fully describe the generator", fg="yellow", err=True)
    manifest = audit.write_run(run, source, _rel(sheet), out)
    if quiet:
        click.echo(_rel(out))
        return
    n_tasks = sum(len(v.instances) for v in run.variants)
    click.echo(f"{spec.id}: {len(run.variants)} variant(s), {n_tasks} task(s), master seed {master}")
    click.echo(f"{'draft' if (draft or only) else 'issued'}: {_rel(manifest)}")
    click.echo(_rel(out))


@main.command()
@click.argument("manifest", type=click.Path(exists=True, path_type=Path))
@click.option("--variant", "variants", multiple=True, help="Only regenerate these variant keys.")
@click.option("--out", type=click.Path(file_okay=False, path_type=Path), default=None,
              help="Output directory (default: build/regen/<sheet-id>/<run>).")
def regen(manifest: Path, variants: tuple[str, ...], out: Path | None) -> None:
    """Reproduce an archived run and verify it is identical."""
    mpath = manifest / audit.MANIFEST if manifest.is_dir() else manifest
    data = audit.load_manifest(mpath)
    out = out or audit.REPO_ROOT / "build" / "regen" / data["sheet_id"] / mpath.parent.name
    report = audit.regen(mpath, out, only=set(variants) or None)
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
    added = audit.seal(run_dir)
    if not added:
        click.secho("no PDFs found", fg="yellow", err=True)
        raise SystemExit(1)
    click.echo(f"sealed {', '.join(added)} in {_rel(run_dir / audit.MANIFEST)}")


if __name__ == "__main__":
    main()
