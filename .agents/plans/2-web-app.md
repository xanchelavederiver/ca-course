# Plan 2 — Web app for tasks & sheets

Status: **implemented** (2026-10-13) — see README.md "Web app"; deviations under "Implementation notes"
Spec: `.claude/specs/spec.md` (Task sheets project → "The desired UI")
Depends on: Plan 1 (taskgen engine, audit trail, latex/taskgen images)

## Goal

A local, single-instructor web application over the existing `taskgen` engine that covers
the spec's UI requirements:

- create/edit tasks (templates, tags, value-generation rules, presets);
- create/edit task sheets (classroom or individual variants);
- generate LaTeX and PDF (draft and issued runs);
- preview the results.

Additionally: browse the audit archive and verify runs (`regen`), because issuing from the UI
must keep the audit-trail guarantees from Plan 1.

The files in git stay the single source of truth. The web app reads and writes the same
`taskgen/tasks/**.py`, `sheets/**.yaml` and `archive/**` files the CLI uses. It has no database.

## Decisions

| Topic | Decision |
|---|---|
| Stack | FastAPI backend + React SPA (confirmed in the Plan 1 interview) |
| Frontend | React + TypeScript + Vite; TanStack Query; React Router; Mantine UI; Monaco editor; pdf.js (`react-pdf`) |
| Backend runtime | Runs in the **taskgen (Sage) image**: it imports `taskgen` directly |
| PDF builds | Long-running **latex worker** service (latex image + a tiny stdlib HTTP server) on the internal compose network |
| Task editing model | **Tasks stay Python classes** (confirmed 2026-10-13). The editor edits the module source (Monaco) and adds a structured metadata panel and a live preview. No new task DSL |
| Sheet editing model | Form editor driven by the pydantic sheet models, with a raw-YAML tab. Comment-preserving round-trip via `ruamel.yaml` |
| Auth | None. Bind to `127.0.0.1` only (non-goal: multi-user). The app executes the instructor's own task code, the same as the CLI |
| Persistence | Files in the bind-mounted repo. The UI shows git status and diffs **only**; committing and pushing stay in the instructor's own git tooling (decided 2026-10-13) |
| Output per group | Individual sheets produce **one PDF per group** containing all of that group's student variants, plus one solutions PDF per group (decided 2026-10-13). Student lists stay inline in the sheet spec (`count` or `students`), as in Plan 1 |

### Why tasks stay Python

Tasks combine sampling logic, Sage computations, `check()` and step traces
(`taskgen/core/steps.py`). A declarative YAML/DSL would cover only the simplest tasks and
would split the corpus into two formats. The UI therefore lowers the cost of editing Python
instead of replacing it:

- the metadata panel (id, title, topics, complexity, family, presets) is parsed from the
  class body with `ast`, edited in forms, and written back with `libcst`, which preserves
  formatting;
- the statement and solution templates get their own LaTeX-mode Monaco tabs, which edit the
  string literals in place;
- "New task" scaffolds a module from a template (topic picker → module path, id, class name);
- every save triggers a validation run and a preview of N instances.

## Architecture

```
browser ──HTTP──► web (taskgen image, uvicorn :8000, 127.0.0.1 only)
                   ├─ FastAPI routers: tasks, topics, sheets, runs, archive, git, builds
                   ├─ static: built SPA (webapp/frontend/dist)
                   ├─ engine worker process (spawned; imports taskgen; restarted on code change)
                   └─ HTTP ─► latex-worker (latex image, internal network only)
                                 POST /build {tex, outdir} → scripts/latex-build.sh
repo bind-mounted at /work in both containers (same as Plan 1)
```

- **Engine worker.** Importing Sage and the task registry takes seconds, so the API keeps a
  warm child process (`multiprocessing`, spawn context) that runs preview, validate and gen
  jobs. A file watcher (`watchfiles`) on `taskgen/` restarts it after task edits. This avoids
  stale modules in the registry (`registry.discover()` is import-once) and keeps a crashing
  or looping task from taking the API down. Each job has a timeout, and the worker is killed
  and respawned when it expires.
- **Jobs.** Long operations (gen, PDF build, regen, validate-all) are jobs: `POST` returns a
  job id, and the client follows progress over Server-Sent Events. A single in-process FIFO
  is enough because there is one user.
- **latex-worker.** Stdlib `http.server` script (`scripts/latex-worker.py`) in the latex
  image (add `python3` to `docker/latex/Dockerfile`). It accepts only repo-relative paths
  under `build/`, `archive/` and `materials/`, runs `latex-build.sh` and returns the PDF path
  plus the log excerpt on failure. It avoids giving the API container access to the docker
  socket.
- **Dev mode.** Vite dev server with a proxy to the API (`make web-dev`). In production mode
  the SPA is built in a `node:22` stage and served by FastAPI.

## Repo layout (additions)

```
webapp/
├── backend/taskgen_web/
│   ├── app.py              # FastAPI app factory, static SPA mount
│   ├── jobs.py             # job queue, SSE, timeouts
│   ├── worker.py           # engine worker process + file watcher
│   ├── latex.py            # client for latex-worker
│   ├── taskedit.py         # ast/libcst read/write of task class metadata & templates
│   ├── sheetedit.py        # ruamel.yaml round-trip, validation via taskgen.core.sheet
│   ├── gitops.py           # status, diff (read-only)
│   └── routers/            # tasks.py sheets.py runs.py archive.py git.py builds.py
│   └── tests/
└── frontend/               # Vite + React + TS
    ├── src/api/            # generated client (openapi-typescript) + TanStack Query hooks
    ├── src/pages/          # Tasks, TaskEditor, Sheets, SheetEditor, Runs, Archive, Git
    └── src/components/     # PdfViewer, LatexEditor, TopicPicker, BudgetChart, ...
docker/web/Dockerfile       # FROM ca-course/taskgen + uvicorn/fastapi/libcst/ruamel; SPA from node stage
scripts/latex-worker.py
```

## Workstreams

### 1. Engine API surface (taskgen refactor, no behaviour change)

- Move the logic of the CLI commands into importable service functions
  (`taskgen/service.py`): `list_tasks`, `topics`, `preview(ref, seed, count)`,
  `validate(target, count, seed)`, `generate(spec_text, seed, draft, only)`, `regen`, `seal`.
  `cli.py` becomes a thin wrapper, so the CLI and the web app cannot drift apart.
- Return the structured validation result (per task/preset: ok, error, traceback, seed)
  instead of only printing it.
- `registry`: add source-location lookup (`inspect.getsourcefile`, class line span) so the UI
  can open a task's module.
- Add a stable JSON Schema export of the sheet models (`ClassroomSheet`, `IndividualSheet`)
  and the taxonomy. The frontend forms are generated from this schema.
- `gen` with a spec **text** (not only a path), so unsaved sheet edits can be drafted.
- **Per-group output (engine change, engine version bump):**
  - Individual runs write `tasks-<group>.tex` and `tasks_solutions-<group>.tex` per group,
    instead of one `tasks.tex`/`tasks_solutions.tex` with all groups. Each per-group
    document has its own title page (sheet title + group name), ToC and variants. The
    group name is slugified for the file name, and the original name is shown in the
    title.
  - Classroom sheets keep the single `tasks.tex` / `tasks_solutions.tex`.
  - `render.write_sources` returns the file list; the Makefile's `build_sheet`, `seal` and
    the latex-worker build every `*.tex` of the run directory instead of the two hard-coded
    names.
  - The manifest gains `layout: "per-group"`. `regen` renders according to the manifest's
    layout (absent = legacy combined file), so runs archived before the change still verify
    as IDENTICAL.
  - Tests: one file pair per group; variant digests unchanged by the split; legacy-layout
    regen of a Plan 1 fixture manifest.
- Engine version bump only if the output changes (it should not).
- Acceptance: the existing pytest suite and `make test` pass unchanged. New unit tests cover
  the service functions.

### 2. Backend (FastAPI)

Endpoints (JSON; all paths repo-relative):

| Area | Endpoints |
|---|---|
| Tasks | `GET /tasks` (filters: topic, complexity, family, text) · `GET /tasks/{id}` (metadata, presets, source, file) · `PUT /tasks/{id}/source` · `PATCH /tasks/{id}/meta` · `POST /tasks` (scaffold) · `POST /tasks/{ref}/preview` {seed, count} · `POST /tasks/{ref}/validate` {count} |
| Topics | `GET /topics` (tree + counts) · `PUT /topics` (edit `taxonomy.yaml`, validated) |
| Sheets | `GET /sheets` · `GET /sheets/{path}` (parsed + raw) · `PUT /sheets/{path}` · `POST /sheets` · `POST /sheets/validate` {yaml} → problems · `GET /schema/sheet` |
| Runs | `POST /runs/draft` {sheet path or yaml, seed?, variants?} · `POST /runs/issue` {sheet path, seed?} → job · `GET /jobs/{id}` · `GET /jobs/{id}/events` (SSE) |
| Builds | `POST /builds` {tex} → PDF · `GET /files/{path}` (PDF/tex download, path-whitelisted) |
| Archive | `GET /archive` (sheets → runs) · `GET /archive/{sheet}/{run}` (manifest, variants, students, files) · `POST /archive/{sheet}/{run}/regen` {variants?} → job |
| Git | `GET /git/status` · `GET /git/diff` (read-only) |

Rules:

- **Issuing goes through the same path as `make issue`:** gen → build both PDFs → seal. A
  dirty tree shows a (non-blocking) warning listing the changed files; issuing proceeds and
  the manifest records it (`git.dirty: true`), as
  the CLI already does.
- Sheet saves validate before writing, and invalid YAML is never written.
- Task source saves are written as-is, even when invalid, so work in progress is not lost.
  The UI then shows the import, validation and preview status. A broken task module must not
  break the registry for the other tasks: the worker's discovery catches import errors per
  module and reports them.
- Path traversal protection on every file endpoint (resolve under the repo root and a
  whitelist).

### 3. Frontend (React SPA)

Pages:

1. **Tasks.** A table of all tasks (id, title, topics, complexity, family, presets,
   validation status) with filters by topic tree and complexity. "New task" opens the
   scaffold wizard.
2. **Task editor.** Split view:
   - left: tabs for *Metadata* (form), *Statement* / *Solution* (LaTeX Monaco), *Code*
     (whole module, Python Monaco);
   - right: *Preview*, which shows N instances for a seed. For each instance it has a
     rendered PDF snippet (canonical, via latex-worker), the LaTeX source and the
     params/answer JSON. Also *Validate*, which shows a 50-instance run with failing seeds
     clickable.
   - Save shortcuts; the editor shows a diff against `HEAD`.
3. **Sheets.** List by semester; kind badge; last draft/issue.
4. **Sheet editor.**
   - Classroom: sections ⇄ ordered task refs (drag & drop, task picker with preset).
   - Individual: groups (count or a pasted student list), slots (task list or topics +
     complexity filter), budget, `distinct_families`, preset, document options.
   - Raw YAML tab with live validation.
   - **Draft** button: generates and shows the sheet and solutions PDFs side by side, with
     a group selector (one PDF pair per group for individual sheets) and a variant jump list.
   - **Variant statistics** for individual sheets: the distribution of total complexity,
     per-task frequency per slot, family collisions avoided. This shows the instructor
     whether the budget actually randomizes the variants.
5. **Issue dialog.** Shows the seed (random or fixed), the git state and the variant count,
   then progress over SSE, and ends with links to the archived PDFs and the manifest.
6. **Archive.** Runs per sheet, manifest viewer (seed, commit, engine version, students ↔
   variant keys, answers), PDFs, a "Verify (regen)" button with an identical/different
   report, and per-variant regen.
7. **Git panel.** Changed files and their diffs (read-only).

Quick preview: render statements with MathJax in the browser, using a macro shim generated
from `ca-common.sty` (`\ZZ`, `\Zn`, `\Mod`, ...), for instant feedback while typing. The PDF
remains the canonical preview because tables and custom environments will not render in
MathJax.

### 4. Docker & Make

- `docker/web/Dockerfile`: multi-stage. A `node:22` stage builds the SPA. The final stage is
  `FROM ca-course/taskgen` with the backend deps (`fastapi`, `uvicorn`, `libcst`,
  `ruamel.yaml`, `watchfiles`, `httpx`, `sse-starlette`).
- `compose.yaml`: services `web` (ports `127.0.0.1:8000:8000`) and `latex-worker` (latex
  image, no published ports). Both bind-mount the repo with the host uid/gid, as in Plan 1.
- Make targets: `make web` (build + up), `make web-dev` (API with reload + Vite dev server),
  `make test-web` (backend pytest + frontend vitest + type-check).

### 5. Tests

- Backend: pytest with FastAPI `TestClient` against a temp copy of the repo fixtures. Cover
  task meta round-trip (`libcst` edits do not change unrelated code), sheet YAML round-trip
  (comments preserved), path whitelist, issue flow writes a manifest equal to the CLI's for
  the same seed, and worker restart after a task file change.
- Frontend: vitest for form ⇄ YAML mapping and budget statistics. One Playwright smoke test
  (open the task, preview, draft the sheet, see the PDF) run in a container.
- Invariant: for the same sheet and seed, the web-issued run and the CLI-issued run produce
  byte-identical `.tex` and manifest variants. This is tested.

## Milestones

1. **M1 — service layer:** taskgen service functions, CLI on top of them, schema export; tests green.
2. **M2 — API + workers:** FastAPI, engine worker, latex-worker, jobs/SSE; draft/issue/regen work via HTTP.
3. **M3 — read-only UI:** task browser + preview, sheet list + draft PDFs, archive browser.
4. **M4 — editing:** task editor (metadata/templates/code, scaffold), sheet editor (forms + YAML), topics editor, git panel.
5. **M5 — polish:** variant statistics, MathJax quick preview, Playwright smoke, README section.

## Out of scope

- Remote/multi-user deployment, authentication, student access (spec non-goals).
- Editing LaTeX course materials (notes, slides, handouts) in the browser. They are edited in
  the instructor's editor. The app may list and build them later (Plan 3 adds `course.yaml`).
- A new task DSL.

## Risks

- **Sage startup latency.** Mitigated by the warm engine worker. The first request after a
  task edit pays the restart cost (seconds).
- **libcst edits of hand-written classes.** Metadata edits are limited to literal class
  attributes. If a task computes them dynamically, the form becomes read-only and points to
  the Code tab.
- **Arbitrary code execution.** This is inherent and acceptable for a localhost
  single-instructor tool. The API is never bound to a public interface.
- **Frontend scope creep.** M3 (read-only) is already useful. Editing can ship incrementally.

## Open questions

1. ~~Tasks stay Python?~~ Yes (2026-10-13).
2. ~~Git from the UI~~ — status and diffs only (2026-10-13).
3. ~~Student lists / output~~ — one PDF (+ one solutions PDF) per group with all its students' variants; student lists stay inline in sheets (2026-10-13).

## Implementation notes (2026-10-13)

- **Engine (M1).** `taskgen/service.py` holds every CLI operation; `cli.py` is a thin wrapper
  (`taskgen schema` added). Per-group layout: `tasks-<slug>.tex` / `tasks_solutions-<slug>.tex`
  (group names transliterated, collisions get `-2`), group in the title (`… Группа 6411`);
  manifest `layout` (absent = `combined`); engine **0.3.0**. Fixture
  `taskgen/tests/fixtures/legacy-run/` (generated with engine 0.2.0) proves legacy regen.
  `registry.discover(strict=False)` records `IMPORT_ERRORS` and drops classes a failing module
  registered before raising. `scripts/latex-build-dir.sh` builds every `.tex` of a run in one
  latex container (Makefile `build_sheet`). Drafts clear `build/sheets/<id>/` first.
- **Backend (M2).** As planned, plus: `/api` prefix; drafts are jobs too (they build PDFs);
  `POST /sheets/merge` (form data → YAML keeping comments; unchanged data returns the text
  byte-identical, ruamel may re-wrap long flow lists on real edits), `POST /sheets/stats`,
  `GET/PUT /modules?path=` (edit a module that does not import), `GET /git/head`,
  `GET /latex/macros` (MathJax shim parsed from `ca-common.sty`), `GET /engine`.
  SSE via a plain `StreamingResponse` (no `sse-starlette`). Task preview PDFs build one
  document for the N instances (`build/web/preview/`). Metadata editing accepts constant
  integer arithmetic (`10**6 + 1`) and keeps the expression of unchanged preset values;
  string literals are written as raw strings, long ones as an implicitly concatenated block.
- **Frontend.** API types are hand-written (`src/api/types.ts`) rather than generated with
  openapi-typescript (most responses are untyped dicts on the backend). Monaco, MathJax and
  pdf.js are bundled (no CDN). Variant jump list = the PDF outline (ca-sheet has bookmarks).
- **Docker.** `docker/web/Dockerfile` targets `backend` (API only; `web-dev`, tests) and
  `web` (+ SPA). Compose profiles: `web` (web, latex-worker), `dev` (web-dev, latex-worker,
  vite), `e2e` (Playwright image). `.dockerignore` whitelists the frontend sources.
