# Course materials (LaTeX sources)

```
materials/
├── sem1/ sem2/
│   ├── lectures/NN-topic/   notes.tex (ca-notes), slides.tex (ca-slides)
│   ├── seminars/NN-topic/   handout.tex (ca-handout); task sheets live in sheets/semN/*.yaml
│   └── exam/                questions-body.tex + questions.tex / questions-refs.tex (ca-exam)
└── capstone/NN-topic/       spec.tex (ca-capstone); reference implementation later (Plan 4)
```

Lecture/seminar counts are **TBD until the syllabus is final**. The
`00-template/` directories are working templates: copy one to `NN-topic/`
(e.g. `sem1/lectures/02-big-integer-arithmetic/`) and fill it in.

Build any document: `make pdf FILE=materials/sem1/lectures/00-template/notes.tex`
→ `build/materials/sem1/lectures/00-template/notes.pdf`. `make demos` builds all templates.

Shared styles are in `latex/` (found automatically via `TEXINPUTS`):

| class | for | notes |
|---|---|---|
| `ca-notes` | lecture notes | `\lecture{N}{title}`, `\makelecturetitle`, theorem envs, `\checkyourself{}`, `\checkyourselfsection`, `furtherreading` env |
| `ca-slides` | lecture slides | beamer 16:9 + `ca` theme; `\titleframe`, `canvasframe`, `\notearea[h]`, `\penspace[h]` for pen annotation |
| `ca-handout` | seminar handouts | `\seminar{N}{title}`, `\makehandouttitle`, `reminder` box |
| `ca-sheet` | task sheets | option `solutions`; `\solution{}`; used by taskgen templates |
| `ca-exam` | exam questions | option `refs`; `\examtitle`, `\topic`, `\question{text}{refs}`, `literature` env |
| `ca-capstone` | capstone specs | `\capstonetitle`, `\goal`, `\functionality`, `\requirements`, `\details`, `\schedule`, `\references` |

All load `ca-common.sty` (pdfLaTeX, T2A/utf8, Russian babel, math macros such as
`\ZZ`, `\Zn{n}`, `\Znx{n}`, `\GF{q}`, `\Mod{m}`, `\congr{a}{b}{m}`, `\ord`, `\legendre`).
