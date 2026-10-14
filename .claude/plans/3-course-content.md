# Plan 3 — Course content: lectures, notes, seminars

Status: **implemented** (M1–M4, 2026-10-13); M5 (instructor review) pending — see
«Implementation notes» at the end. Syllabus = the inferred topic map below (decided 2026-10-13)
Spec: `.claude/specs/spec.md` (Lecture slides, Lecture notes, Seminar handouts and classroom task sheets)
Depends on: Plan 1 (LaTeX classes, taskgen). Independent of Plan 2.

## Goal

Fill `materials/` with real course content for both semesters, plus the tooling that keeps
the content consistent:

- a **course map** (`course.yaml`) as the single source of truth for lectures, seminars,
  topics, task taxonomy and exam questions;
- **lecture slides** (Beamer "canvas" decks for pen annotation), starting with a port of the
  existing PPTX decks;
- **lecture notes**: the primary student reference, with theorems/proofs/examples,
  check-yourself questions and further reading;
- **seminar handouts** (1–2 pages) and one **classroom task sheet** per seminar;
- **task corpus expansion** to cover every topic the exam lists ask about.

## Inputs

- **Syllabus (decided 2026-10-13):** the topic map below, reconstructed from the 2025/26
  зачёт and экзамен question lists (`tmp/вопросы на экзамен`), plus lattices as the last
  block of semester 2. Workstream 1 encodes it in `course.yaml`. Lecture and seminar counts
  follow the blocks and can be adjusted there later.
- Existing decks: `tmp/лекции/Lecture 1. Introduction.pptx` (12 slides) and
  `Lecture 2. Арифметика больших чисел.src.pptx` (18 slides). Most formulas are images,
  which have to be retyped as LaTeX.
- Bibliography from the question lists: Hoffstein–Pipher–Silverman, Galbraith, Crandall–
  Pomerance, Knuth vol. 2, Welschenbach, Chernov–Korepanov, Glukhov et al., the MSU ENT wiki.

### Topic map (= syllabus)

| Sem | Block | Topics (from question lists) | Task coverage today |
|---|---|---|---|
| 1 | Big-number arithmetic | schoolbook +, ×, ÷ with remainder; complexity | — (gap: division) |
| 1 | Fast multiplication | Karatsuba, Toom–Cook, convolutions, convolution theorem, FFT multiplication | karatsuba, toom_cook, fft_mul |
| 1 | Modular arithmetic | Montgomery reduction and multiplication, Montgomery exponentiation; Mersenne and Fermat rings, NTT | montgomery_*, fermat_mul, mersenne_mul (gap: NTT) |
| 1 | Exponentiation | binary and its modifications, q-ary | powmod.* |
| 1 | Number theory | Euclid/xgcd, inverses, element order (descent, product tree), primitive roots | order, order_product_tree (gaps: xgcd/inverse, primitive root search) |
| 1 | Primes | π(x), Wilson, Fermat test, Carmichael, Miller–Rabin, Solovay–Strassen | miller_rabin, solovay_strassen (gaps: Fermat test / Carmichael, Wilson) |
| 1 | PRNG | LCG max period theorem, LFSR | crypto.lcg (gap: LFSR) |
| 2 | DLP | DLP, DH, BSGS, prime-power subgroup reduction, CRT, Pohlig–Hellman | shanks, pohlig_hellman |
| 2 | Collision algorithms | collision theorem, orbits (ρ shape), Pollard ρ + Floyd, distinguished points | — (gaps: ρ-DLP, collision probability) |
| 2 | Index calculus | index calculus | index_calculus |
| 2 | Factoring | FTA, RSA, difference of squares, B-smooth, quadratic sieve, Pollard p−1 | quadratic_sieve, pollard_pm1, rsa_common_modulus (gap: Fermat difference-of-squares) |
| 2 | Square roots | Euler criterion, Cipolla, Hensel lifting | sqrt_cipolla (gap: Hensel) |
| 2 | Elliptic curves | Weierstrass form, discriminant, group law, curves over 𝔽_p, Hasse; scalar multiplication (binary, ternary/NAF) | double_and_add_* (gaps: point addition/group, point counting) |
| 2 | ECDLP | ECDLP, ECDH, Pollard ρ on curves, Lenstra ECM | — (gaps: ECDH, ρ-ECDLP small case, Lenstra) |
| 2 | Lattices | Gauss reduction, Babai, congruential cryptosystem | gauss, babai_*, congruential (sem 2, confirmed; the экзамен list gains lattice questions in Plan 4; gap: LLL) |

## Decisions

| Topic | Decision |
|---|---|
| Course map | `course.yaml` at the repo root: semesters → lectures/seminars (number, slug, title, taxonomy topics, related exam questions, related tasks) |
| Directory naming | `materials/semN/lectures/NN-slug/`, `materials/semN/seminars/NN-slug/` (as scaffolded); numbers from `course.yaml` |
| Bibliography | One shared `latex/ca-refs.bib`, biblatex + biber (add `biber`, `texlive-bibtex-extra` to the latex image). Notes, exams and capstones cite by key |
| PPTX → Beamer | A semi-automatic converter script produces a skeleton (text, bullet levels, images, speaker notes). Formulas are retyped by hand. Converted decks get reviewed slide by slide |
| Slides vs notes | Slides carry definitions, theorem statements and figures only, plus `\penspace` for live proofs. Notes carry the full proofs, examples and remarks. Both come from the same course-map entry, but their sources are separate |
| Slide handout | None (decided 2026-10-13). Students get the lecture notes; decks are only for live pen annotation |
| Classroom sheets | `sheets/semN/seminar-NN-slug.yaml`, one per seminar, `kind: classroom`, with a fixed seed recorded in the archive when issued |

## Workstreams

### 1. Syllabus → `course.yaml`

- Schema (pydantic, in `taskgen/core/course.py` so that Plan 2 and the build can read it):
  ```yaml
  semesters:
    - n: 1
      lectures:
        - n: 2
          slug: big-integer-arithmetic
          title: Арифметика больших чисел
          topics: [arithmetic, arithmetic.multiplication]
          exam_questions: [sem1:1, sem1:5]      # ids from Plan 4 question files
          decks: [legacy: "tmp/лекции/Lecture 2. ...pptx"]
      seminars:
        - n: 1
          slug: karatsuba-toom-cook
          lectures: [2]
          sheet: sheets/sem1/seminar-01-karatsuba-toom-cook.yaml
  ```
- `taskgen course check` reports: lectures without notes or slides, taxonomy topics with no
  tasks, seminars without sheets, and topics on the exam list that no lecture covers.
- `taskgen course scaffold` creates the `NN-slug/` directories from the templates for all
  entries that do not exist yet.
- **Per-semester book** (decided 2026-10-13): `make book SEM=1` builds
  `build/materials/semN/notes-book.pdf`, which aggregates all lecture notes of the semester
  in `course.yaml` order. It has one title page, a common ToC, lectures as chapters,
  continuous theorem numbering, one bibliography, and the check-yourself questions per
  chapter. Requirement for `ca-notes`: every `notes.tex` must compile both standalone and
  `\input` into the book (e.g. a `standalone`/`subfiles`-style body file
  `notes-body.tex` + thin wrapper, mirroring the exam `questions-body.tex` pattern).
- `make materials` builds every document listed in `course.yaml` (and both books) into `build/`. `make
  materials SEM=1` builds one semester.
- Fill `course.yaml` from the topic map: roughly one lecture and one seminar per block,
  in table order. Splitting large blocks (e.g. fast multiplication, elliptic curves) into
  two lectures is decided while writing the notes.

### 2. LaTeX layer extensions

- `ca-refs.bib`: the literature from both question lists, the capstone specs and the
  Plan 1 references. `\printbibliography` replaces the `furtherreading` env, or the env
  wraps it. Online resources (MOOCs, video lectures) are `@online` entries with `keywords`
  so the notes can list them separately.
- `ca-notes`: numbered `checkyourself` questions that are collected automatically into the
  end-of-notes section (via an aux list, as `\listoftheorems` does). This removes the manual
  duplication between the questions in the text and the section at the end.
- `ca-slides`: a theorem-statement environment with a `\penspace` proof area,
  and figure helpers for algorithm traces (e.g. Euclid tables, ρ diagrams in TikZ).
- Shared TikZ library `latex/ca-figures.sty` (Pollard ρ shape, EC point addition, lattice
  bases, convolution diagrams). Notes and slides reuse the same figures.

### 3. PPTX → Beamer port

- `scripts/pptx2beamer.py` (python-pptx, run in the taskgen image or a small tools image)
  converts each slide into a `canvasframe` with:
  - the title;
  - nested `itemize` for bullet levels;
  - extracted images under `NN-slug/img/`;
  - speaker notes as `% comments`;
  - `% TODO formula` markers where a picture or an OLE equation was found.
- Manual pass per deck:
  - retype the formulas;
  - replace raster diagrams with TikZ where it pays off;
  - add `\penspace` areas where proofs were written live.
- First targets: lectures 1 and 2. They prove the pipeline before mass porting.
- Acceptance: both decks compile and the slide count matches. The instructor reviews a
  side-by-side PDF against the original.

### 4. Lecture notes

Per lecture, `notes.tex` follows a fixed outline:

1. Motivation and context (the cryptographic application).
2. Definitions → theorems/lemmas with proofs → algorithms (pseudocode via `algorithm2e` or
   `algorithmicx`) with complexity analysis.
3. Worked examples. Where possible, generate them from taskgen (`\input` of a rendered task
   instance with a fixed seed), so examples and seminar tasks share code and stay correct.
4. Check-yourself questions inline, auto-collected at the end.
5. References and further reading (books, MOOCs, videos).

- Writing is content work. Claude drafts each lecture from the literature and the question
  list. The instructor reviews the math and the pedagogy. Every draft goes through a
  checklist:
  - every statement on the exam question list for this lecture is present;
  - proofs are complete or explicitly marked "без доказательства" (as the question list
    says);
  - examples are verified by Sage;
  - the bibliography has page or section pointers.
- Order: sem 1 first (needed earlier in the academic year), lecture by lecture following
  `course.yaml`.

### 5. Seminars: handouts + classroom sheets

- Handout (`ca-handout`, ≤ 2 pages): definitions, algorithm summaries and formulas needed
  for the seminar's tasks; no proofs.
- Classroom sheet: sections ordered from warm-up → core → corner cases (the corner cases are
  the point: even Montgomery modulus, composites in primality tests, primitive roots in
  order tasks, etc.; see the "broaden, don't restrict" rule).
- Each sheet is issued once per seminar via `make issue`, so the archived PDF and the
  solution manual are the ones used in class.

### 6. Task corpus expansion

New tasks for the gaps in the topic map, each with a full step-by-step solution, `check()`,
presets and broad instance spaces (harder variants become separate tasks or presets, not
exclusions):

- sem 1: schoolbook division with remainder (Knuth D), xgcd + modular inverse, primitive
  root search, Fermat test + Carmichael numbers, Wilson test (tiny n), NTT over Mersenne or
  Fermat rings, LFSR (period, matrix form, recovering taps via Berlekamp–Massey if the
  lecture covers it);
- sem 2: Pollard ρ for DLP with Floyd (small p, full trace table), distinguished-points
  variant, collision-probability estimate, Fermat difference-of-squares factoring, Hensel
  lifting of square roots mod pᵏ, EC point addition/doubling and the group table of a small
  curve, point counting + Hasse bound check, ECDH toy exchange, ρ on a small curve, Lenstra
  ECM step on a small n, CRT, LLL on a small basis (3×3, full trace).
- Taxonomy: new slugs (e.g. `number_theory.euclid`, `crypto.lfsr`, `dlp.rho`,
  `factoring.fermat`, `number_theory.hensel`, `ecc.group_law`, `ecc.ecdlp`,
  `factoring.ecm`).
- Update `sheets/catalog/all-tasks.yaml` and the sem1/sem2 контрольная specs to use the new
  pools.

### 7. Quality gates

- `make materials` and `make test` stay green. `taskgen course check` has no errors (it may
  still warn for `draft: true` entries).
- LaTeX lint (`chktex`, with project-specific suppressions) runs on `materials/**`.
- Worked examples generated from taskgen are covered by the same `validate` run.

## Milestones

1. **M1 — map & tooling:** `course.yaml`, course check/scaffold, bibliography, `ca-notes` auto-collected questions, `make materials`.
2. **M2 — pipeline proven on lectures 1–2:** both PPTX decks ported; notes, handout and classroom sheet for lecture 2 / seminar 1.
3. **M3 — semester 1 content:** remaining sem 1 lectures/notes/seminars + sem 1 task gaps.
4. **M4 — semester 2 content:** sem 2 lectures/notes/seminars + sem 2 task gaps.
5. **M5 — review pass:** the instructor's corrections, cross-check against the exam lists (Plan 4), semester books.

M3 and M4 are long and incremental. Each lecture is a mergeable unit (notes + slides +
handout + sheet + tasks), and its PR has its own checklist.

## Out of scope

- HTML/PPTX export (spec: optional, later).
- Exam questions and capstones (Plan 4).
- Video/MOOC content production; the notes only link external resources.

## Risks

- **Syllabus changes.** The syllabus is inferred, so blocks may later be split or reordered.
  Renumbering only touches `course.yaml` and directory names (scaffold/rename helper).
- **Formula-heavy PPTX.** Image formulas cannot be converted automatically, so the manual
  retyping cost is about 18 slides per deck. The skeleton converter still saves the
  structure and text.
- **Content correctness.** Mathematical errors in notes are worse than in code. Mitigations:
  Sage-verified examples, taskgen-generated worked examples, and instructor review per
  lecture.
- **Scope.** Two semesters of notes is the largest body of work in the project. Prioritize
  by teaching calendar, not by topic order.

## Open questions

1. ~~Syllabus~~ — use the inferred topic map (2026-10-13).
2. ~~Lattices~~ — semester 2, last block (2026-10-13).
3. ~~Combined notes~~ — yes: per-lecture notes **and** a per-semester book (2026-10-13).
4. ~~Slide handouts~~ — not needed (2026-10-13).

## Implementation notes (2026-10-13)

What exists now:

- `course.yaml` (9 + 12 lectures, 8 + 12 seminars, every зачёт/экзамен question mapped to a
  lecture); `taskgen/core/course.py` + `taskgen course check|scaffold|examples|docs|book`;
  `make materials|book|seminar-sheets|course-check|examples|lint`. `course check` is clean.
- LaTeX: `ca-biblio.sty` + `ca-refs.bib` (biber, GOST numeric; `@online` listed separately);
  `ca-notes` with `\begin{lecture}` bodies and class option `book` (lectures = chapters);
  `ca-figures.sty`; `ca-slides`: `theoremframe`, `\proofarea`, `\aside`, `canvasframe[opts]`.
- `scripts/pptx2beamer.py` (raw shape tree incl. `mc:AlternateContent`; native OMML
  equations are translated to LaTeX, so only pictures of formulas/handwriting need retyping).
  Lectures 1–2 ported 1:1 (12 and 18 slides) and reviewed; corrections against the PPTX are
  listed in the slides' header comments.
- Notes, slides, handout, classroom sheet and worked examples for every lecture/seminar; both
  semester books build (139 and 172 pages).
- Task corpus: 31 → 88 tasks (all gaps of the topic map plus warm-up/corner-case tasks); the
  контрольная pools use them; `taskgen catalog` regenerates the review catalog.

Deviations from the plan:

- Check-yourself questions are still collected in memory (no aux list): the end-of-lecture
  section is generated, so nothing is duplicated; entries got page references, and in the
  book the list is per chapter.
- The photos used for Alice/Bob/Eve in the lecture 1 deck are replaced by pictograms
  (`\personicon`): no third-party photos in the repo.
- All theorem-like environments start their paragraph at once (`ca-common.sty`): a theorem
  that began with a list lost its hyperref anchor.
- `latex-build.sh` retries once from a clean aux directory (a failed biber run used to poison
  later builds).

For the review pass (M5):

- Many section/chapter locators in the reading lists were cited from memory (especially
  Crandall–Pomerance in Russian translation, Galbraith, HPS 2nd ed. ch. 7, Washington,
  Vasilenko); historical/record facts in remarks likewise. Every numeric example was checked
  with Sage/Python.
- Notes are 13–19 pages per lecture (target 8–16).
- Archived runs whose slots select by `topics` will not regenerate identically now that the
  corpus has grown (README, «Issuing»).
