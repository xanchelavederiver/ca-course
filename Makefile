# Computer Algebra course — build entry points. Everything runs in Docker;
# no host TeX or Sage installation is required.
#
#   make images                     build the docker images
#   make pdf FILE=path/to/doc.tex   any .tex -> build/<dir>/<name>.pdf
#   make demos                      compile the template/demo document of every class
#   make draft SHEET=sheets/...yaml draft sheet + solutions -> build/sheets/<id>/ (not archived)
#   make sheets                     drafts of all sheets
#   make issue SHEET=sheets/...yaml issue: archive/<id>/<ts>/ with manifest + PDFs
#   make regen RUN=archive/<id>/<ts>  reproduce an archived run and verify it
#   make test                       pytest + taskgen validate + compile a generated sheet
#
# Course content (Plan 3; the course map is course.yaml):
#   make materials [SEM=n]          notes, slides, handouts of course.yaml + the semester books
#   make book SEM=n                 build/materials/semN/notes-book.pdf (all notes of a semester)
#   make seminar-sheets [SEM=n]     drafts of the seminar classroom sheets
#   make course-check               taskgen course check (gaps, stale worked examples)
#   make examples                   regenerate the taskgen worked examples of the notes
#   make lint                       chktex on materials/**/*.tex
#   make shell-taskgen / shell-latex
#
# Web app (Plan 2; http://127.0.0.1:8000, never published beyond localhost):
#   make web                        build + start the web app and its latex worker
#   make web-dev                    API with reload + Vite dev server (http://127.0.0.1:5173)
#   make web-down                   stop them
#   make test-web                   backend pytest + frontend vitest + type-check
#   make test-e2e                   Playwright smoke test against a running `make web`

export HOST_UID := $(shell id -u)
export HOST_GID := $(shell id -g)

COMPOSE ?= docker compose
DC_RUN  := $(COMPOSE) run --rm -T
LATEX   := $(DC_RUN) latex
TASKGEN := $(DC_RUN) taskgen
SAGEPY  := $(DC_RUN) --entrypoint sage taskgen -python

DEMOS := $(filter-out %-body.tex,$(wildcard materials/*/*/00-template/*.tex materials/capstone/00-template/*.tex)) \
         materials/sem1/exam/questions.tex materials/sem1/exam/questions-refs.tex \
         latex/examples/sheet-demo.tex
SHEETS := $(wildcard sheets/*/*.yaml)

.PHONY: help images pdf demos draft sheets issue regen test test-py validate smoke \
        shell-taskgen shell-latex clean web web-dev web-down test-web test-e2e \
        materials book books seminar-sheets course-check examples lint

help:
	@sed -n '1,/^$$/p' Makefile | sed 's/^# \{0,1\}//'

images:
	$(COMPOSE) build

pdf:
	@test -n "$(FILE)" || { echo "usage: make pdf FILE=path/to/doc.tex"; exit 2; }
	$(LATEX) scripts/latex-build.sh "$(FILE)"

demos:
	@for f in $(DEMOS); do $(LATEX) scripts/latex-build.sh "$$f" || exit 1; done

# Generate (draft or issued) + compile every .tex of the run directory
# (individual sheets: one sheet + one solutions file per group).
define build_sheet
	dir=$$($(TASKGEN) gen "$(1)" $(2) --quiet) && \
	echo "generated $$dir" && \
	$(LATEX) scripts/latex-build-dir.sh "$$dir"
endef

draft:
	@test -n "$(SHEET)" || { echo "usage: make draft SHEET=sheets/semN/<name>.yaml [SEED=n]"; exit 2; }
	@$(call build_sheet,$(SHEET),--draft $(if $(SEED),--seed $(SEED)))

sheets:
	@for s in $(SHEETS); do $(MAKE) --no-print-directory draft SHEET=$$s || exit 1; done

issue:
	@test -n "$(SHEET)" || { echo "usage: make issue SHEET=sheets/semN/<name>.yaml [SEED=n]"; exit 2; }
	@$(call build_sheet,$(SHEET),$(if $(SEED),--seed $(SEED))) && \
	$(TASKGEN) seal "$$dir" && \
	echo "issued $$dir — commit it: git add $$dir"

regen:
	@test -n "$(RUN)" || { echo "usage: make regen RUN=archive/<sheet-id>/<run-ts>"; exit 2; }
	$(TASKGEN) regen "$(RUN)"

validate:
	$(TASKGEN) validate

test-py:
	$(SAGEPY) -m pytest -q taskgen/tests

# Compile a generated sheet end-to-end (CI-style smoke test).
smoke:
	@$(call build_sheet,sheets/sem2/kontrolnaya.yaml,--draft --seed 1)

test: test-py validate smoke

# --- course content (course.yaml) -------------------------------------------------
SEMS := $(if $(SEM),$(SEM),1 2)

materials:
	@docs=$$($(TASKGEN) course docs $(if $(SEM),--sem $(SEM))) && \
	$(LATEX) scripts/latex-build-many.sh $$docs
	@$(MAKE) --no-print-directory books SEMS="$(SEMS)"

book:
	@test -n "$(SEM)" || { echo "usage: make book SEM=1|2"; exit 2; }
	@book=$$($(TASKGEN) course book $(SEM)) && \
	$(LATEX) scripts/latex-build.sh "$$book" "$$(dirname $$book)"

books:
	@for s in $(SEMS); do $(MAKE) --no-print-directory book SEM=$$s || exit 1; done

seminar-sheets:
	@for s in $$($(TASKGEN) course docs --sheets $(if $(SEM),--sem $(SEM))); do \
	  $(MAKE) --no-print-directory draft SHEET=$$s || exit 1; done

course-check:
	$(TASKGEN) course check

examples:
	$(TASKGEN) course examples

lint:
	$(LATEX) sh -c 'find materials -name "*.tex" ! -path "*/examples/*" | sort | \
	  xargs chktex -q -l .chktexrc'

# --- web app ---------------------------------------------------------------------
WEB := $(COMPOSE) --profile web
NODE := docker run --rm -u $(HOST_UID):$(HOST_GID) -e HOME=/tmp -v $(CURDIR):/work \
        -w /work/webapp/frontend node:22-bookworm-slim

web:
	$(COMPOSE) build taskgen latex
	$(WEB) up -d --build web latex-worker
	@echo "web app: http://127.0.0.1:$${WEB_PORT:-8000}"

web-dev:
	$(COMPOSE) build taskgen latex
	$(COMPOSE) --profile dev up --build web-dev latex-worker vite

web-down:
	$(COMPOSE) --profile web --profile dev --profile e2e down

test-web:
	$(COMPOSE) --profile dev build web-dev
	$(DC_RUN) --no-deps --entrypoint sage web-dev -python -m pytest -q webapp/backend/tests
	$(NODE) sh -c "npm ci --no-audit --no-fund && npx tsc --noEmit -p . && npx vitest run"

test-e2e:
	$(COMPOSE) --profile e2e run --rm e2e

shell-taskgen:
	$(COMPOSE) run --rm --entrypoint bash taskgen

shell-latex:
	$(COMPOSE) run --rm latex bash

clean:
	rm -rf build
