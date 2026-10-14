#!/bin/sh
# Compile one .tex file to PDF (runs inside the `latex` container).
#
#   scripts/latex-build.sh <file.tex> [<pdf-out-dir>]
#
# Auxiliary files go to build/.aux/<path>/<name>/; only the PDF is copied
# to <pdf-out-dir> (default: build/<dir of file.tex>). Prints the PDF path.
set -eu

tex="$1"
dir=$(dirname "$tex")
name=$(basename "$tex" .tex)
out="${2:-build/$dir}"
aux="$PWD/build/.aux/$dir/$name"
mkdir -p "$aux" "$out"

build() {
    latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error \
        -cd -outdir="$aux" "$tex" >"$aux/latexmk.out" 2>&1
}
# A failed run can leave stale auxiliary files (e.g. a malformed biber .bcf) that make
# every later run fail: on failure, retry once from a clean aux directory.
if ! build && ! { find "$aux" -mindepth 1 -delete && build; }; then
    echo "LaTeX build failed: $tex" >&2
    grep -A6 -E '^(!|.*:[0-9]+:)' "$aux/$name.log" >&2 2>/dev/null \
        || tail -40 "$aux/latexmk.out" >&2
    exit 1
fi
cp "$aux/$name.pdf" "$out/$name.pdf"
echo "$out/$name.pdf"
