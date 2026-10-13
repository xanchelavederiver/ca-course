# Plan 1 — Foundations & Task-Sheets Core

Status: **implemented** (2026-10-13) — see README.md; deviations noted under "Implementation notes"
Spec: `.claude/specs/spec.md`
Date: 2026-10-13

## Goal

Lay the project foundations (repo layout, dockerized LaTeX build, shared LaTeX styles for all
material types) and build the core of the **task sheets project**: a file-based task database,
a deterministic generation engine with a full audit trail, and a CLI. Port the existing
`tmp/практики и контрольные/main-{1,2}sem.py` task corpus into the new format.

## Decisions (from spec interview, 2026-10-13)

| Topic | Decision |
|---|---|
| Task format | Python classes/modules with declarative metadata + `generate()`/`solve()` code |
| Math engine | SageMath, run in Docker |
| Slides | LaTeX Beamer → PDF (pen-annotation friendly); existing PPTX ported over time |
| Web app | FastAPI + React SPA — **deferred to Plan 2** |
| Task storage | Files in git (no DB server); git is history/backup |
| Reproducibility | Full audit trail: seed + config + git commit + archived PDFs/answer keys per generation run |
| Plan 1 scope | Foundations + task-sheets core; web app & content authoring in later plans |
| Language | Student-facing materials in Russian; code/docs in English. Syllabus (lecture/seminar counts) TBD — scaffold with placeholders |

### Spec amendments to fold into `spec.md` (approved direction, pending edit)

- Fix typos: "Compute Algebra" → "Computer Algebra" (l.3), "generate exa, task sheets" (l.50).
- Slides: resolve PPTX/LaTeX contradiction → Beamer PDF is the target; HTML export optional later.
- Add requirements: deterministic seeded generation + archived variants/answer keys;
  per-instance validation (solution self-check, sane value bounds); non-goals (no student portal,
  no grading system, single-instructor tool).

## Repo layout (to create)

```
ca-course/
├── docker/
│   ├── latex/Dockerfile          # TeX Live + latexmk + Cyrillic fonts
│   └── taskgen/Dockerfile        # based on sagemath/sagemath + taskgen deps
├── latex/                        # shared LaTeX layer
│   ├── ca-common.sty             # fonts, Russian babel, math macros, theorem envs
│   ├── ca-notes.cls              # lecture notes (theorems, check-yourself Qs, refs)
│   ├── ca-handout.cls            # 1–2 page seminar handout
│   ├── ca-sheet.cls              # task sheets & solution manuals
│   ├── ca-exam.cls               # exam question sheets (+ references variant)
│   ├── ca-capstone.cls           # capstone project specs
│   └── beamer/ ca-beamer theme   # 16:9, high-contrast, whitespace for pen notes
├── taskgen/                      # Python package (runs inside Sage container)
│   ├── core/                     # Task base class, registry, rng, sampling, audit
│   ├── render/                   # Jinja2 → LaTeX rendering, PDF build driver
│   ├── tasks/                    # TASK DATABASE: one module per task, by topic
│   │   ├── arithmetic/  powmod/  modular/  number_theory/
│   │   ├── dlp/  factoring/  ecc/  lattices/  crypto/
│   ├── cli.py                    # entry point
│   └── tests/
├── sheets/                       # sheet definitions (YAML), by semester
│   ├── sem1/  sem2/
├── materials/                    # LaTeX sources for course content (scaffold only in Plan 1)
│   ├── sem1/{lectures,seminars,exam}/   # NN-topic/ dirs; counts TBD per syllabus
│   ├── sem2/{lectures,seminars,exam}/
│   └── capstone/
├── archive/                      # audit trail of issued sheets (committed)
├── build/                        # generated artifacts (gitignored)
├── Makefile
├── compose.yaml
└── README.md
```

## Workstreams

### 1. Build system (Docker + Make)

- `docker/latex`: TeX Live (scheme-full or curated set incl. `babel-russian`, T2A fonts,
  beamer, extsizes), `latexmk`. Standardize on **pdfLaTeX + T2A/utf8** — matches existing
  sources; revisit LuaLaTeX only if font needs grow.
- `docker/taskgen`: `sagemath/sagemath` base + `pip install` of taskgen deps
  (jinja2, pydantic, pyyaml, click, pytest).
- `compose.yaml` with `latex` and `taskgen` services; bind-mount repo.
- `Makefile`: `make pdf FILE=...` (any .tex → `build/`), `make sheets`, `make test`,
  `make images`. Every target runs in containers — no host TeX/Sage required.

### 2. Shared LaTeX layer

- `ca-common.sty`: Russian typography, theorem/definition/example environments,
  `\checkyourself` question macro, number-theory/crypto math macros.
- Document classes per material type (see layout). Keep them thin wrappers over
  `extarticle`/`beamer` so ported documents change minimally.
- Beamer theme designed as a "canvas": large type, margins and pauses left for
  live pen annotation (Cintiq), matching the style of `tmp/лекции` decks.
- Acceptance: a demo document per class compiles to PDF via `make pdf`.

### 3. Task engine core (`taskgen/core`, `taskgen/render`)

- **Task model**: `class Task` with class-level metadata — `id` (stable slug), `topics`
  (tags from a committed taxonomy file), `complexity: int`, `title_ru` — and methods
  `generate(rng) -> TaskInstance`, optional `validate(instance)`.
  `TaskInstance` = params + `statement_latex` + `solution_latex` (step-by-step) + `answer`.
- **Registry**: auto-discovery of `taskgen/tasks/**`; `taskgen list` shows id/topics/complexity.
- **Determinism**: master seed per generation run; per-variant child RNG seeded by
  `hash(master_seed, sheet_id, variant_no, task_slot)` so one variant can be regenerated alone.
- **Sheet specs (YAML)** — two kinds:
  - *classroom*: ordered list of task ids (single instance per sheet);
  - *individual* (homework/exam): groups of `{topics, complexity_budget}` + variant count
    (or student list); sampler spends the budget on tasks of varying complexity, respecting
    category-collision rules (as `taken[]` does in the current scripts).
- **Rendering**: Jinja2 LaTeX templates → `tasks.tex` + `tasks_solutions.tex` → PDF via the
  latex container, matching the current контрольная document structure (per-group sections,
  grading rubric preamble, ToC).
- **Audit trail**: every `generate` writes `archive/<sheet-id>/<run-ts>/` containing
  `manifest.json` (master seed, sheet spec snapshot, git commit, engine version),
  the `.tex` sources and the PDFs (sheet + answer key). `taskgen regen <manifest>` must
  reproduce identical output.
- **CLI** (`taskgen`): `list`, `preview <task-id> [--seed]`, `gen <sheet.yaml>`,
  `regen <manifest>`, `validate [task-id|all]`.

### 4. Port the existing task corpus

- Port all generators from `main-1sem.py` (~16 tasks) and `main-2sem.py` (~27 tasks,
  incl. DLP, factoring, ECC, lattices) into `taskgen/tasks/**` with metadata.
- Replace hand-rolled helpers (`ord_mod`, `xgcd`, rejection loops) with Sage primitives
  where it simplifies; keep pedagogical value ranges exactly as they are.
- Current solutions are mostly answer-only: port as-is, tag each task with
  `solution_detail: answer_only | full` so upgrading to step-by-step solutions is a
  visible, per-task backlog (content work, Plan 3+).
- Recreate the 1-sem контрольная as `sheets/sem1/kontrolnaya.yaml` and verify the
  generated document structurally matches the legacy output.

### 5. Validation & tests

- pytest (inside taskgen container): for every task, generate N instances per seed —
  assert validation passes, statements/solutions are non-empty LaTeX, determinism
  (same seed ⇒ identical instance), category-collision and budget invariants of the sampler.
- Smoke test: compile one generated sheet to PDF in CI-style run (`make test`).

### 6. Scaffold `materials/` + README

- Placeholder directory tree for both semesters (counts TBD until syllabus arrives),
  demo lecture-notes and handout documents, top-level README (how to build, how to add
  a task, how to issue a homework run).

## Suggested implementation order & milestones

1. **M1 — builds green**: docker images + Makefile compile a demo doc per document class.
2. **M2 — engine runs**: core + renderer + CLI generate a toy sheet deterministically with audit trail.
3. **M3 — corpus ported**: all legacy tasks ported, tests pass, 1-sem контрольная regenerated.
4. **M4 — scaffold & docs**: materials tree, README, spec.md amendments applied.

## Out of scope (later plans)

- **Plan 2**: web app — FastAPI backend over the taskgen engine + React SPA
  (task editor, sheet composer, PDF preview), docker-compose service.
- **Plan 3**: lecture slides/notes templates filled with real content; PPTX → Beamer port;
  step-by-step solution authoring backlog.
- **Plan 4**: capstone reference implementations (dockerized) + specs; exam question sheets.
- HTML/PPTX export pipeline (spec Misc) — revisit after Beamer baseline exists.

## Risks

- **SageMath image size/startup** (~3 GB): acceptable for a containerized dev tool; CLI must
  not require Sage for non-math commands if that ever hurts (mitigation: lazy imports).
- **Cyrillic LaTeX in containers**: lock font packages in the image; demo docs in M1 catch issues early.
- **Determinism across versions**: manifests pin git commit + engine version; archived PDFs are
  the ground truth even if later code drifts.
- **Step-by-step solutions are content work**, not engine work — tracked per task via
  `solution_detail`, so the engine ships without blocking on authoring.

## Implementation notes (2026-10-13)

- Extra class `latex/ca-slides.cls` wraps beamer (16:9) + `latex/beamer/beamerthemeca.sty`.
- Task model: class metadata + Jinja2 `statement`/`solution` templates (`\VAR{}` syntax),
  `sample(rng)` + optional `check(params)`; value ranges per semester via named `presets`
  (`"<id>@sem2"`, or sheet-level `preset: sem2`). `family` generalises the legacy `taken[]` rule.
- Sampling uses only the passed `random.Random`; Sage is used for deterministic computations
  (orders, factorization, EC arithmetic, lattices), never for randomness.
- CLI also has `topics` and `seal` (records PDF hashes after the latex container builds them).
- `taskgen gen --draft` writes to `build/` without archiving (for previews).
- PDFs are byte-reproducible (`SOURCE_DATE_EPOCH`, `\pdftrailerid{}`).
- 29 tasks ported (`solution_detail: full` for `powmod.binary_mod`, `crypto.lcg`).
  Legacy fixes: Montgomery modulus forced odd; Mersenne sem2 answer modulus; RSA/LCG/
  congruential/factoring instances that were unsolvable or degenerate are rejected.
- Sheets: `sheets/sem1/kontrolnaya.yaml`, `sheets/sem2/kontrolnaya.yaml` (budget 8 = legacy
  tier rule), `sheets/sem2/seminar-demo.yaml` (classroom).

### Review follow-up (2026-10-13)

- Every task has a full step-by-step solution (engine 0.2.0); traces in `taskgen/core/steps.py`.
- Montgomery: odd modulus (complexity 2) and new even-modulus tasks `arithmetic.montgomery_mul_even`,
  `powmod.montgomery_even` (complexity 3, CRT over 2^t and s).
- Congruential cryptosystem: any shortest vector that decrypts correctly is accepted.
- Order tasks allow primitive roots; primality tasks mix in composites (spf >= 7 or base-2 pseudoprimes).
- `integer_to_2f` replaced by the diminished-one code (legacy version was wrong except for 0).
- Ternary expansion = NAF; exponents without a -1 digit rejected. Index calculus requires a primitive root.
- `sheets/catalog/all-tasks.yaml`: one instance of every task/preset for review.
