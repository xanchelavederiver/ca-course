#!/bin/sh
# Compile every .tex file of a generated run directory to PDF next to it
# (runs inside the `latex` container).
#
#   scripts/latex-build-dir.sh <run-dir>
set -eu

dir="$1"
found=0
for tex in "$dir"/*.tex; do
    [ -e "$tex" ] || continue
    found=1
    "$(dirname "$0")/latex-build.sh" "$tex" "$dir"
done
[ "$found" = 1 ] || { echo "no .tex files in $dir" >&2; exit 1; }
