# Computer Algebra course

Materials for the two-semester course «Компьютерная алгебра» (introduction to
mathematical cryptography): lecture slides and notes, seminar handouts, task
sheets with solution manuals, individual homework/exam variants, exam question
sheets and capstone project specs. See `.claude/specs/spec.md` for the spec and
`.claude/plans/` for the implementation plans.

Student-facing materials are in Russian; code and docs are in English.

## Requirements

Docker with the compose plugin, and `make`. Nothing else: TeX Live and SageMath
run in containers.

```sh
make images      # once: builds ca-course/latex and ca-course/taskgen (Sage, ~5 GB)
make test        # pytest + task validation + compile a generated sheet
make demos       # compile the template document of every LaTeX class
```

## Layout

```
docker/        latex (TeX Live, pdfLaTeX + cm-super) and taskgen (SageMath) images
latex/         shared LaTeX: ca-common.sty, ca-{notes,slides,handout,sheet,exam,capstone}.cls, beamer theme
materials/     LaTeX sources of course content (see materials/README.md)
taskgen/       task database + generator (Python, runs in the Sage container)
  core/          task model, registry, seeding, sheet specs, sampler, engine, audit
  render/        Jinja2 LaTeX templates for sheets
  tasks/         THE TASK DATABASE — one module per task family, by topic; taxonomy.yaml
  tests/
sheets/        sheet specs (YAML) by semester
archive/       audit trail of issued sheets (committed)
build/         generated artifacts (gitignored)
scripts/       latex-build.sh (used by the Makefile inside the latex container)
```

## Building documents

```sh
make pdf FILE=materials/sem1/lectures/00-template/notes.tex   # -> build/materials/.../notes.pdf
```

Documents use pdfLaTeX with `\documentclass{ca-notes}` etc.; `latex/` is on
`TEXINPUTS` inside the container. PDFs are reproducible (fixed
`SOURCE_DATE_EPOCH`, no trailer ID).

## Task sheets

### The CLI

```sh
docker compose run --rm taskgen list [--topic dlp] [-v]   # tasks: id, complexity, solution detail, topics
docker compose run --rm taskgen topics                    # taxonomy with task counts
docker compose run --rm taskgen preview dlp.shanks --seed 7 [--count 3] [--json]
docker compose run --rm taskgen validate [all|<task-id>[@preset]] [--count 50]
docker compose run --rm taskgen gen sheets/sem2/kontrolnaya.yaml [--seed N] [--draft] [--variant 6411/3]
docker compose run --rm taskgen regen archive/<sheet-id>/<run> [--variant 6411/3]
docker compose run --rm taskgen seal archive/<sheet-id>/<run>
```

(`make` exports `HOST_UID`/`HOST_GID` so containers write files as you; when
calling `docker compose` directly, `export HOST_UID=$(id -u) HOST_GID=$(id -g)` first.)

### Issuing a homework / контрольная

```sh
make draft SHEET=sheets/sem2/kontrolnaya.yaml        # preview: build/sheets/<id>/tasks{,_solutions}.pdf
make issue SHEET=sheets/sem2/kontrolnaya.yaml        # archive/<id>/<ts>/: .tex, PDFs, manifest.json
git add archive/ && git commit -m "Issue sem2 контрольная"
make regen RUN=archive/sem2-kontrolnaya/<ts>         # later: verify it reproduces identically
```

Commit your code changes **before** issuing: the manifest records the git
commit (and warns if the tree is dirty). Generation is deterministic: master
seed → per-variant seeds `sha256(master, sheet, variant, slot)`, so any single
variant can be regenerated alone (`--variant`).

### Sheet specs

`kind: classroom` — one sheet for a seminar: ordered `sections`, each a list
of task refs. `kind: individual` — one variant per student: `groups` (with
`count` or a `students` list), `slots` (each filled with one task from an
explicit `tasks` list or by `topics`, optionally filtered by `complexity`),
an optional `budget` (total complexity, an int or `{min, max}`), and
`distinct_families` (default true: e.g. Montgomery multiplication and
Montgomery exponentiation never share a variant). `preset: sem2` selects the
`sem2` value ranges of tasks that have them. Task refs are `"<id>"` or
`"<id>@<preset>"`. See `sheets/sem1/kontrolnaya.yaml`,
`sheets/sem2/kontrolnaya.yaml` and `sheets/sem2/seminar-demo.yaml`.

### Adding a task

Create a class in a module under `taskgen/tasks/<topic>/` (it is discovered
automatically):

```python
from taskgen.core.task import SolutionDetail, Task

class Shanks(Task):
    id = "dlp.shanks"                      # stable slug, never rename once issued
    title_ru = "Алгоритм Шенкса"
    topics = ("dlp.generic",)              # from taskgen/tasks/taxonomy.yaml
    complexity = 1                         # 1..3, spent against sheet budgets
    family = None                          # tasks of one family never share a variant
    solution_detail = SolutionDetail.FULL  # every task ships a step-by-step solution
    presets = {"default": {"primes": [...]}, "sem2": {...}}   # value ranges -> self.cfg
    statement = r"Решить ... \[\VAR{g}^x \equiv \VAR{h}\ (\textrm{mod}\ \VAR{p}).\]"
    solution = r"\[x = \VAR{answer}.\]"

    def sample(self, rng):                 # ALL randomness from rng (never Sage's global RNG)
        ...
        return {"g": g, "h": h, "p": p, "answer": x}

    def check(self, p):                    # independent self-check on the JSON params
        assert pow(p["g"], p["answer"], p["p"]) == p["h"]
```

Templates use Jinja2 with LaTeX-safe delimiters: `\VAR{expr}`,
`\BLOCK{for ...}...\BLOCK{endfor}`. Then run
`docker compose run --rm taskgen validate <id>` and `make test`.

Changing a task's sampling or text changes the output for old seeds; that is
fine (archived PDFs are the ground truth), but bump `taskgen.__version__` so
manifests show it.

### Reviewing tasks

`make draft SHEET=sheets/catalog/all-tasks.yaml` builds one instance of every
task and preset (statement + full step-by-step solution) into
`build/sheets/catalog-all-tasks/`. Every task must provide a full solution
(`solution_detail = FULL`, enforced by the tests); algorithm traces live in
`taskgen/core/steps.py`, shared LaTeX fragments (Euclid/CRT/REDC/Gauss tables)
in `taskgen/render/templates/macros.tex.j2` (import with
`\BLOCK{import 'macros.tex.j2' as tx}` — don't name the alias like a template
variable).
