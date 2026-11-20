# Semester 1 capstone projects (мини-курсовые)

Five capstones, each with a student specification, an instructor-only theory refresher,
a reference implementation, seeded vectors and a calibrated benchmark. **Students receive
only `spec.pdf`.** `refresher.pdf`, `reference/`, `vectors/` and `bench/` are instructor-only.

| # | slug | expected student workload |
|---|---|---|
| 1 | `fast-multiplication` | 36–40 h |
| 2 | `montgomery-exponentiation` | 36–40 h |
| 3 | `euclid-orders-primitive-roots` | 38–42 h |
| 4 | `primality-testing` | 38–42 h |
| 5 | `lcg-lfsr-cryptanalysis` | 35–39 h |

The target is one month at approximately 10 hours per week. There are no optional extensions.
Factorizations needed by the order/primitive-root and Korselt calculations are supplied.
LCG/LFSR recovery inputs have unique answers.

## Layout

```
capstone.yaml                 shared defaults + the ordered project list
NN-slug/
  spec.tex                    student task description (ca-capstone)
  refresher.tex               instructor theory refresher (ca-capstone), NOT for students
  requirements.tex            GENERATED (make bench): measured \Req... macros
  reference/                  reference solver and pytest suite vs independent oracles
  vectors/                    GENERATED: <size>.jsonl, manifest.json, .gitignore
  bench/config.yaml           generator, seed, command, size classes, requirements
  bench/README.md             calibration notes
  bench/results.{json,md}, plot.{png,pdf}   GENERATED (make bench)
taskgen/capstone/gens/<name>.py   deterministic vector generator + verifier
```

The reference obeys the same restrictions as the student implementation. Built-in algorithms
under study are oracles only. Generators use only their supplied RNG, preserve valid corner
cases and tag every vector. Verifiers accept every correct answer. Time limits are measured
from the reference with the configured slack (default 10×), never chosen before calibration.

## Commands

```sh
make capstones CAP_SEM=1                 # all spec and refresher PDFs
make capstone-refreshers CAP_SEM=1       # instructor refreshers only
make vectors CAP_SEM=1 [CAPSTONE=slug] [FORCE=1]
make bench CAP_SEM=1 [CAPSTONE=slug] [SIZE=..] [LIMIT=n] [SLACK=x]
make test-capstones CAP_SEM=1 [CAPSTONE=slug]
make check-capstone CAP_SEM=1 CAPSTONE=slug DIR=~/sub/ivanov CMD="python3 adapter.py"
docker compose run --rm --entrypoint sage taskgen -python \
  -m taskgen.capstone --sem 1 vectors all --check
```

Calibrate serially on a quiet machine. The JSON-lines solver contract is identical to the
semester 2 contract in `materials/sem2/capstone/README.md` and remains instructor-only.
