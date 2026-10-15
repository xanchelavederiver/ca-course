# Capstone projects (мини-курсовые)

Eight capstone specs plus, for each, an instructor-only reference implementation,
seeded test vectors, a benchmark and a generated `requirements.tex`. Students get
**only the spec PDF** (`make capstones` → `build/materials/capstone/NN-slug/spec.pdf`).
Plan: `.claude/plans/4-capstones-and-exams.md`; pipeline code: `taskgen/capstone/`.

| # | slug | reference | image |
|---|---|---|---|
| 1 | `bigint-arithmetic` | C (no GMP in the operations under test) | `capstone-c` |
| 2 | `pohlig-hellman` | Python + Sage (bigints only) | `taskgen` |
| 3 | `index-calculus` | Python + Sage (bigints, linear algebra) | `taskgen` |
| 4 | `quadratic-sieve` | Python + Sage (bigints, linear algebra mod 2) | `taskgen` |
| 5 | `lenstra-ecm` | Python + Sage (bigints) | `taskgen` |
| 6 | `ec-arithmetic` | Python + Sage (bigints) | `taskgen` |
| 7 | `pollard-rho-ecdlp` | Python + Sage (bigints) | `taskgen` |
| 8 | `lll` | Python + Sage (exact rationals) | `taskgen` |

## Layout

```
capstone.yaml                 shared defaults (slack: 10, timeout, check limits) + the list
NN-slug/
  spec.tex                    ca-capstone; \input{requirements} for the measured numbers
  requirements.tex            GENERATED (make bench): \ReqSlack, \Req... macros
  reference/                  reference solver: README.md, tests/ (pytest vs the oracle)
  vectors/                    GENERATED (make vectors): <size>.jsonl, manifest.json, .gitignore
  bench/config.yaml           generator, seed, image, build, command, size classes, requirements
  bench/README.md             calibration notes: original spec numbers vs measured, decisions
  bench/results.{json,md}, plot.{png,pdf}   GENERATED (make bench)
taskgen/capstone/gens/<name>.py   vector generator + verifier of the capstone
```

## Rules

- **The reference obeys the student's restrictions.** It implements every item of the
  spec's «Требуемый функционал», optional ones included, by hand. It may use exactly what
  the spec allows students: for example, bigints and linear algebra for the DLP capstones,
  but not Sage's `discrete_log`, `factor`, `E.order()` or `LLL()`. Those built-ins act only
  as the **oracle** that computes the expected answers of the test vectors.
- **Broaden, don't restrict.** Vectors keep the valid corner cases: p−1 with a large
  prime-power factor, a base that is not a generator, n with repeated factors, degenerate
  lattice bases, and so on. Each vector has `tags`, and `verify` accepts every correct
  answer, not only `expected`.
- **Determinism.** Generators draw randomness only from the `rng` they get, never from
  Sage's `random_prime` or `randint`. `make vectors` is byte-reproducible, and
  `python -m taskgen.capstone vectors <slug> --check` verifies it.
- **Requirements are measured.** The spec's thresholds are the reference time × slack
  (default 10×; `slack:` in `capstone.yaml` or `bench/config.yaml`, or `make bench SLACK=20`).
  The timings depend on the machine, and `results.json` records it.

## Solver contract (JSON lines)

A long-running process reads `{"id": ..., "input": {...}}` lines on stdin and answers each
one with a `{"id": ..., "output": {...}}` line on stdout. The answer can also carry
`"extra"` (intermediate data) or `"error"`. The solver flushes after every line. The
timing is the wall time per request. One process serves each size class, and a request
that times out kills the process; the runner then starts a new one. Students are **not**
told the contract. At the defence, the instructor wraps a submission with a small adapter
and runs:

```sh
make check-capstone CAPSTONE=pohlig-hellman DIR=~/sub/ivanov CMD="python3 adapter.py" [SIZE=p60]
```

The check runs in a container with no network, a memory and CPU limit, and the repo
read-only. It prints ok/n, the maximum time and the limit (reference × slack) per size class.

## Commands

```sh
make capstones                          # all spec PDFs
make vectors [CAPSTONE=slug] [FORCE=1]  # seeded vectors (skips classes that are up to date)
make bench [CAPSTONE=slug] [SIZE=..] [LIMIT=n] [SLACK=x]   # run reference -> results + requirements.tex
make test-capstones [CAPSTONE=slug]     # reference unit tests (vs Sage/GMP oracles)
docker compose run --rm --entrypoint sage taskgen -python -m taskgen.capstone verify-reference <slug>
```

Calibrate on a quiet machine. Concurrent benchmarks skew the timings.
