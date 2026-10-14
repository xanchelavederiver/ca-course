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
make materials   # all lecture notes, slides, handouts + the two semester books
```

## Layout

```
course.yaml    the course map: semesters -> lectures/seminars, topics, exam questions
docker/        latex (TeX Live, pdfLaTeX + cm-super, biber, chktex) and taskgen (SageMath) images
latex/         shared LaTeX: ca-common.sty, ca-{notes,slides,handout,sheet,exam,capstone}.cls, beamer theme,
               ca-figures.sty (TikZ figures/traces), ca-biblio.sty + ca-refs.bib (shared bibliography)
materials/     LaTeX sources of course content (see materials/README.md)
taskgen/       task database + generator (Python, runs in the Sage container)
  core/          task model, registry, seeding, sheet specs, sampler, engine, audit
  render/        Jinja2 LaTeX templates for sheets
  tasks/         THE TASK DATABASE — one module per task family, by topic; taxonomy.yaml
  tests/
sheets/        sheet specs (YAML) by semester
archive/       audit trail of issued sheets (committed)
build/         generated artifacts (gitignored)
scripts/       latex-build{,-dir,-many}.sh (Makefile, inside the latex container), latex-worker.py (web app),
               pptx2beamer.py (PPTX deck -> ca-slides skeleton)
webapp/        local web app: backend/ (FastAPI, runs in the Sage image), frontend/ (React SPA)
```

## Building documents

```sh
make pdf FILE=materials/sem1/lectures/00-template/notes.tex   # -> build/materials/.../notes.pdf
```

Documents use pdfLaTeX with `\documentclass{ca-notes}` etc.; `latex/` is on
`TEXINPUTS` inside the container. PDFs are reproducible (fixed
`SOURCE_DATE_EPOCH`, no trailer ID).

## Course content

`course.yaml` is the single source of truth for the course: for each semester
the lectures (number, slug, title, the task-taxonomy topics they cover, the
exam questions they prepare for) and the seminars (lectures they belong to,
classroom sheet). Directory names follow it:
`materials/semN/lectures/NN-slug/`, `materials/semN/seminars/NN-slug/`,
`sheets/semN/seminar-NN-slug.yaml`.

```sh
make course-check          # gaps: missing notes/slides/handouts/sheets, exam questions no lecture
                           # covers, topics without tasks, stale worked examples, duplicate labels
docker compose run --rm taskgen course scaffold     # create missing directories/sheets from templates
make examples              # regenerate the taskgen worked examples of the notes
make materials [SEM=1]     # build notes, slides, handouts (+ the semester books)
make book SEM=1            # build/materials/sem1/notes-book.pdf: all notes of a semester
make seminar-sheets [SEM=1]   # drafts of the seminar classroom sheets
make lint                  # chktex on materials/**/*.tex (suppressions in .chktexrc)
```

- **Lecture notes**: the text is in `notes-body.tex` (`\begin{lecture}{N}{title}
  ... \end{lecture}`); `notes.tex` is a thin wrapper, and the semester book
  `\subimport`s every body as a chapter (theorems numbered
  lecture.section.k, one bibliography). Check-yourself questions are collected
  per lecture with page references; the reading list cites `latex/ca-refs.bib`
  with section locators (`\readitem[разд.~4.3]{knuth-taocp2}{...}`).
- **Worked examples**: `examples.yaml` next to the notes lists taskgen tasks
  with fixed seeds; `make examples` renders them to `examples/<name>.tex`
  (committed; `\taskexample{<name>}` includes one). Generation validates each
  instance, and `course check` reports fragments that no longer match.
- **Slides** are canvases for pen annotation: statements and figures, proofs
  are written live (`theoremframe`, `\proofarea`, `\penspace`, `\aside`).
  Decks of the legacy PPTX lectures were converted with
  `scripts/pptx2beamer.py` (text, bullet levels, native equations -> LaTeX,
  pictures, notes; `% TODO` where a picture of a formula or handwriting needs
  retyping) and then reviewed by hand; slide k of the port is slide k of the
  PPTX:

  ```sh
  docker compose run --rm --entrypoint sage taskgen -python scripts/pptx2beamer.py \
      "tmp/лекции/Lecture 2. ....pptx" materials/sem1/lectures/02-big-integer-arithmetic
  ```
- **Seminars**: a handout (1–2 pages, no proofs) and one classroom sheet,
  ordered warm-up -> core -> corner cases. Issue it once per seminar
  (`make issue SHEET=...`) so the archived PDFs are the ones used in class.

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
make draft SHEET=sheets/sem2/kontrolnaya.yaml        # preview: build/sheets/<id>/tasks{,_solutions}-<group>.pdf
make issue SHEET=sheets/sem2/kontrolnaya.yaml        # archive/<id>/<ts>/: .tex, PDFs, manifest.json
git add archive/ && git commit -m "Issue sem2 контрольная"
make regen RUN=archive/sem2-kontrolnaya/<ts>         # later: verify it reproduces identically
```

Individual sheets produce **one PDF per group** (`tasks-<group>.pdf`, with all
of that group's variants) plus one solutions PDF per group
(`tasks_solutions-<group>.pdf`); classroom sheets produce `tasks.pdf` and
`tasks_solutions.pdf`. The manifest records the layout, so runs issued before
engine 0.3 (one combined file) still regenerate identically.

Commit your code changes **before** issuing: the manifest records the git
commit (and warns if the tree is dirty). Generation is deterministic: master
seed → per-variant seeds `sha256(master, sheet, variant, slot)`, so any single
variant can be regenerated alone (`--variant`).

Slots that select tasks by `topics` draw from the task registry *as it is at
generation time*: adding a task to such a topic changes the slot's pool, and a
later `regen` of an archived run then reports a mismatch (the archived PDFs stay
the ground truth). Sheets meant to be issued should list their tasks
explicitly, as `sheets/sem1/kontrolnaya.yaml` and `sheets/sem2/kontrolnaya.yaml` do.

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
`build/sheets/catalog-all-tasks/`. The catalog is generated: run
`docker compose run --rm taskgen catalog` after adding tasks (a test checks it
is current). Every task must provide a full solution
(`solution_detail = FULL`, enforced by the tests); algorithm traces live in
`taskgen/core/steps.py`, shared LaTeX fragments (Euclid/CRT/REDC/Gauss tables)
in `taskgen/render/templates/macros.tex.j2` (import with
`\BLOCK{import 'macros.tex.j2' as tx}` — don't name the alias like a template
variable).

## Web app

A local, single-instructor UI over the same files the CLI uses (no database,
no authentication — it runs your task code, so it is only ever bound to
`127.0.0.1`):

```sh
make web          # build + start: http://127.0.0.1:8000  (make web-down to stop)
make web-dev      # API with auto-reload + Vite dev server on http://127.0.0.1:5173
make test-web     # backend pytest + frontend type-check and vitest
make test-e2e     # Playwright smoke test against a running `make web`
```

What it does:

- **Tasks** — browse by topic/complexity with the last validation status; the
  task editor has a metadata form, LaTeX editors for the statement and
  solution templates, the whole module in a Python editor (with a diff against
  `HEAD`), a live preview (MathJax while typing, or the canonical PDF) and a
  validation run whose failing seeds open in the preview. *New task* scaffolds
  a class in a new or existing module. Tasks stay Python classes: the form
  edits literal class attributes in place (`libcst`, everything else in the
  file is untouched); attributes computed in code (e.g. a statement built from
  shared constants) are shown read-only with a link to the Code tab. A module
  that does not import is reported and can still be opened and fixed — the
  other tasks keep working.
- **Sheets** — form editor (sections and drag & drop task order for classroom
  sheets; groups with counts or a pasted student list, slots, budget and
  family rule for individual sheets) and a raw YAML tab; form edits keep the
  file's comments. Sheets are validated before they are saved. *Draft*
  generates with unsaved edits and shows the sheet and solutions PDFs side by
  side per group, with a jump list of variants. *Variant statistics* shows how
  the slots and budget spread tasks and total complexity over the variants.
- **Issue** — the same path as `make issue` (generate → build every PDF →
  seal). Uncommitted changes only produce a warning; the manifest records
  `git.dirty: true` (as with the CLI), so commit first when the run must be
  exactly reproducible from git.
- **Archive** — every issued run: manifest, students ↔ variants with answers,
  the sealed PDFs, and *Verify* (regenerate everything or single variants and
  compare byte for byte).
- **Topics** (edit `taxonomy.yaml`), **Git** (status and diffs, read-only),
  **Jobs** (progress of long operations).

How it works: the FastAPI backend (`webapp/backend/taskgen_web`) runs in the
Sage image and never imports task modules itself. Engine operations
(`taskgen/service.py`, shared with the CLI) run in a warm worker process that
is restarted when anything under `taskgen/` changes, and killed if a call
hangs. PDFs are built by `latex-worker` (`scripts/latex-worker.py` in the
latex image, reachable only on the compose network). Long operations are jobs
streamed to the browser over Server-Sent Events. API docs:
http://127.0.0.1:8000/api/docs.
