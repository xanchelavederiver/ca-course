# Archive — audit trail of issued sheets

Every `make issue SHEET=...` (or `taskgen gen <sheet.yaml>` without `--draft`)
creates `archive/<sheet-id>/<YYYYMMDD-HHMMSSZ>/` with:

| file | content |
|---|---|
| `manifest.json` | master seed, sheet spec snapshot (parsed + raw YAML), git commit + dirty flag, engine version, per-variant tasks (seed, answer, digest), SHA-256 of every file |
| `tasks.tex`, `tasks_solutions.tex` | generated LaTeX sources |
| `tasks.pdf`, `tasks_solutions.pdf` | the PDFs handed out / used for grading (hashes added by `taskgen seal`) |

**Commit every issued run.** The archived PDFs are the ground truth even if the
generator later changes.

Verify / reproduce a run (all variants or a single one):

```sh
make regen RUN=archive/<sheet-id>/<run>
docker compose run --rm taskgen regen archive/<sheet-id>/<run> --variant 6412/7
```
