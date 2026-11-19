# Plan 4 — Capstone projects & exam materials

Status: **implemented** 2026-10-14 (M1–M5; calibrated serially on the reference machine), pending instructor review
Spec: `.claude/specs/spec.md` ([capstone] project, Exam questions; exam task sheets)
Depends on: Plan 1 (LaTeX classes, taskgen, Docker). Uses `course.yaml` and `ca-refs.bib` from
Plan 3 if they exist; otherwise it works standalone.

## Goal

1. **Capstones (мини-курсовые).** Port the 8 existing specs to `ca-capstone` LaTeX. Add a
   **dockerized reference implementation** for each, with a reproducible **test-vector
   generator** and a **benchmark harness**, so that the performance requirements in each spec
   ("50–100 bits in tens of seconds", "2048-bit arithmetic") are measured, not guessed.
2. **Exam questions.** Turn the зачёт and экзамен question lists into structured sources that
   build both PDFs (questions / questions with references) and can be cross-checked against
   the lectures.
3. **Exam task sheets.** Individual-variant sheets for the зачёт and экзамен written tasks on
   top of the expanded task corpus.

## Inputs

`tmp/курсовые` contains 8 specs:

| # | Slug | Spec title | Reference impl language |
|---|---|---|---|
| 1 | `bigint-arithmetic` | Арифметика больших чисел | **C** (students are pushed to compiled languages; target 2048-bit operations) |
| 2 | `pohlig-hellman` | Алгоритм Полига–Хеллмана | Python + Sage (bigints/linear algebra only) |
| 3 | `index-calculus` | Метод исчисления индексов | Python + Sage |
| 4 | `quadratic-sieve` | Метод квадратичного решета | Python + Sage (an optional C sieve if Python is too slow to calibrate) |
| 5 | `lenstra-ecm` | Алгоритм факторизации Ленстры | Python + Sage |
| 6 | `ec-arithmetic` | Арифметика эллиптических кривых | Python + Sage |
| 7 | `pollard-rho-ecdlp` | ρ-алгоритм Полларда для ECDLP | Python + Sage |
| 8 | `lll` | LLL | Python + Sage |

`tmp/вопросы на экзамен` contains the зачёт list (Dec 2025, 22 questions, 8 references) and
the экзамен list (Jun 2026, 24 questions, 5 references), each in a "questions" version and a
"questions with references" version.

## Decisions

Confirmed 2026-10-13: C for the arithmetic reference; default slack 10×, configurable; no
exam tickets; students get only the spec (vectors, references and checker stay
instructor-only). The remaining rows are proposed.


| Topic | Decision |
|---|---|
| Capstone layout | `materials/capstone/NN-slug/` holds `spec.tex`, `reference/`, `vectors/`, `bench/`, and a generated `requirements.tex` |
| Reference impl rule | Implement the algorithm **by hand under the same restrictions as students** (e.g. the arithmetic capstone must not use GMP for the operations under test; the DLP ones may use bigints and linear algebra but not Sage's `discrete_log`). Sage built-ins act only as the **oracle** for test vectors |
| Images | Python capstones run in the existing taskgen (Sage) image. A new `docker/capstone-c` image (gcc, clang, make, GMP for the oracle only) serves the C reference |
| I/O contract | Each reference is a CLI that reads JSON lines (test vectors) on stdin and writes JSON lines (answers + optional intermediate data) on stdout. Instructor-only: students get just the spec |
| Requirements numbers | `bench` outputs `results.json` plus a `requirements.tex` macro file (`\ReqBits`, `\ReqSeconds`, ...). `spec.tex` `\input`s it, so the spec text always matches the measured calibration |
| Slack factor | Students get **10×** the reference time by default. Configurable in `materials/capstone/capstone.yaml` (`slack: 10`) with a per-capstone override in `NN-slug/bench/config.yaml` (`slack`, size classes, timeouts). Overridable on the command line: `make bench SLACK=20` |
| Exam question source | YAML per exam (`materials/semN/exam/questions.yaml`). A renderer (in taskgen, `taskgen exam`) emits the shared `questions-body.tex`; the two existing `ca-exam` wrappers stay |
| Question references | Bibliography keys into `ca-refs.bib` + a locator ("Глава 2", "Раздел 3.8"); the numbering of the literature list is generated, never typed |

## Workstreams

### 1. Capstone specs → LaTeX

- Port all 8 specs to `materials/capstone/NN-slug/spec.tex` with `ca-capstone`, keeping
  their structure: goal, functionality, requirements, implementation details, schedule,
  remarks, references.
- Keep the footnoted "why?" questions; they are pedagogical.
- References go through `ca-refs.bib` (Plan 3), with a local `thebibliography` fallback if
  Plan 3 has not landed.
- Extend `ca-capstone` only as needed (e.g. a `remarks` section, footnote style).
- Acceptance: all 8 compile via `make capstones`. The instructor reviews a side-by-side PDF
  against the originals.

### 2. Reference implementations

For each capstone, `reference/` contains the implementation of every item of the spec's
"Требуемый функционал" list, including the optional ones, so the calibration covers the full
scope. Examples:

- **Arithmetic (C):**
  - signed bigints on 64-bit limbs;
  - add/sub, schoolbook and Karatsuba multiplication (with a threshold), division with
    remainder (Knuth D), Euclid and xgcd, shifts;
  - Montgomery reduction and multiplication;
  - binary left-to-right and q-ary (q ∈ {2, 4, 8, 16}) exponentiation, plain and modular via
    Montgomery;
  - x86-64 without AVX, as the spec says.
- **Pohlig–Hellman:** BSGS, prime-power reduction, CRT; it records the intermediate
  congruence system as the spec asks.
- **Index calculus / QS:** factor base, sieving, linear algebra mod 2 or mod (p−1) by hand
  over Sage matrices (allowed per spec), and parameter choice from the L-notation estimates.
- **ECM, EC arithmetic, ρ-ECDLP, LLL:** the same principle; ρ with Floyd and with
  distinguished points.

Unit tests compare each reference against the Sage/GMP oracle on random inputs (pytest; for
C, a small test driver plus pytest that calls it).

### 3. Test vectors

- `capstone/vectors.py` (in taskgen, reusing `core/rng`): a seeded, per-capstone generator
  of instances by size class, e.g. DLP with p of 30/50/70/100 bits and a chosen factorization
  shape of p−1; QS composites of 40–80 bits with balanced factors; EC curves with prime-order
  subgroups of k bits.
- Expected answers come from Sage's independent implementations (`discrete_log`, `factor`,
  `E.order()`, `LLL()`).
- Vectors are written to `vectors/<size>.jsonl` together with the seed and the generator
  version, using the same determinism guarantees as task sheets. Small files are committed;
  large ones are regenerated from the seed.
- Corner cases are kept, not filtered: p−1 with a large prime-power factor, an order not
  equal to p−1, non-generator bases, n with repeated factors for ECM, degenerate lattice
  bases. These follow the "broaden, don't restrict" rule. Each vector gets a `tags` field.

### 4. Benchmarks → requirements

- `make bench CAPSTONE=pohlig-hellman` runs the reference over the size classes with timeouts
  and records wall time, peak RSS and the success rate.
- The run also records the machine info (CPU model, cores, governor). Machine dependence is
  explicit, so the calibration is "on the reference machine".
- `bench/report.py` writes:
  - `bench/results.json`;
  - a Markdown table;
  - a plot of time vs. bits (matplotlib, PNG/PDF);
  - `requirements.tex`, which derives the spec's thresholds with the slack factor (default
    10×, see Decisions). The factor used is recorded in `results.json`.
- The spec includes the derived numbers. The instructor sees both the measured curve and
  the requirement it implies.
- Acceptance: for every capstone, the current spec numbers are either confirmed or adjusted
  with a recorded justification (commit message + `bench/README.md`).

### 5. Instructor-only submission check (stretch, not grading)

- `make check-capstone CAPSTONE=... CMD="python main.py"` runs an arbitrary student command
  against a vector file using the JSON-lines contract and reports correctness and timing per
  vector.
- It runs in a container with no network and with resource limits.
- This is not a grading system (spec non-goal). It is a tool the instructor runs during the
  defence ("во время сдачи должна быть возможность проверить работу").
- **Students receive only the spec PDF** (decided 2026-10-13). Vectors, references,
  benchmarks and the checker stay instructor-only. The spec does not describe the
  JSON-lines contract; during the defence the instructor wraps a submission with a small
  adapter if needed.

### 6. Exam questions

- Schema (`materials/semN/exam/questions.yaml`):
  ```yaml
  title: Вопросы на зачёт
  date: декабрь 2026
  literature: [knuth2, welschenbach, crandall-pomerance, chernov-korepanov, msu-ent, galbraith, hps]
  topics:
    - title: Арифметика больших чисел и операции в $\Zn{n}$
      questions:
        - id: sem1:1
          text: Школьные алгоритмы сложения, умножения и деления с остатком больших целых чисел, оценки сложности.
          refs: [{key: knuth2, loc: "Раздел 4.3"}, {key: welschenbach, loc: "Глава 4"}]
          span: 1            # questions "14-15" are one item worth 2 numbers
          lectures: [sem1/2] # optional; else derived from course.yaml
  ```
- The renderer:
  - keeps the `N-M` numbering of multi-number questions;
  - emits the literature list in order of first citation, or in a fixed order;
  - produces `questions-body.tex`, from which the existing `questions.tex` and
    `questions-refs.tex` build both PDFs.
- Port the 2025 зачёт list and the 2026 экзамен list verbatim as the starting point.
  The "не скажу ☺" reference is kept as free text.
- `taskgen course check` (Plan 3) gains checks for questions without a lecture, lectures
  without questions, and question topics without tasks.
- Add questions on the lattices block (Gauss reduction, Babai, LLL, the congruential
  cryptosystem) to the экзамен list, since lattices are part of semester 2 (Plan 3). The
  instructor reviews their wording and references.

### 7. Exam task sheets

- `sheets/sem1/zachet.yaml` and `sheets/sem2/exam.yaml`: individual sheets with wider topic
  coverage than the контрольные (spec: "essentially the same but cover more topics"). They
  use slots per topic block and a complexity budget.
- They depend on the Plan 3 task-gap work for full coverage. Until then, slots use the
  existing pools, and the coverage report lists the blocks that are missing.

## Repo layout (additions)

```
materials/capstone/NN-slug/
├── spec.tex
├── requirements.tex          # generated by bench/report.py
├── reference/                # C (Makefile) or Python package; README with usage
├── vectors/                  # small committed *.jsonl + generator seed manifest
└── bench/                    # results.json, plot, README (calibration notes)
materials/capstone/capstone.yaml  # shared bench defaults (slack: 10, timeouts)
taskgen/capstone/             # vector generators + oracle wrappers, bench runner, report
docker/capstone-c/Dockerfile
materials/semN/exam/questions.yaml
sheets/sem1/zachet.yaml  sheets/sem2/exam.yaml
```

Make targets: `make capstones` (all specs), `make bench [CAPSTONE=...]`,
`make vectors [CAPSTONE=...]`, `make check-capstone`, `make exams` (both question PDFs per
semester).

## Milestones

1. **M1 — specs ported:** 8 `spec.tex` + `make capstones`; exam `questions.yaml` for both lists + renderer; both PDFs match the originals.
2. **M2 — first reference end-to-end:** Pohlig–Hellman (reference, vectors, bench, generated `requirements.tex`) proves the pipeline.
3. **M3 — arithmetic in C:** `docker/capstone-c`, reference + GMP oracle tests + bench at 512–4096 bits.
4. **M4 — remaining references:** index calculus, QS, ECM, EC arithmetic, ρ-ECDLP, LLL; requirements recalibrated.
5. **M5 — exams:** coverage checks against `course.yaml`, lattice questions, `zachet.yaml` and `exam.yaml` task sheets, optional self-check runner.

## Out of scope

- Grading, plagiarism detection, submission collection (spec non-goals).
- New capstone topics beyond the existing 8. Adding one later means copying a directory and
  following the same pipeline.

## Risks

- **Reference-machine dependence of timings.** Hardware is recorded. Requirements are
  expressed with slack and in relative terms where possible.
- **Reference quality bias.** An expert reference is faster than a typical student solution.
  The slack factor is the knob, and the instructor's past experience calibrates it (the
  current numbers are the prior).
- **QS and index calculus in pure Python** may be too slow to cover the upper size classes.
  Allow an optional C/Cython sieve in the reference, and note it in the spec if students
  need the same hint.
- **Exam lists evolve yearly.** YAML + renderer makes the yearly edit a small diff, and
  archived PDFs keep past years.

## Open questions

1. ~~Arithmetic reference language~~ — C (2026-10-13).
2. ~~Slack factor~~ — 10× default, configurable (2026-10-13).
3. ~~Publish vectors/checker~~ — no, students get only the spec (2026-10-13).
4. ~~Exam tickets~~ — not needed (2026-10-13).
