#!/bin/sh
# Compile several .tex files in one container run (runs inside `latex`).
#
#   scripts/latex-build-many.sh <file.tex>...
#
# Each PDF goes to build/<dir of file.tex>/ (see latex-build.sh). Builds every
# file even if some fail; exits non-zero if any failed.
set -u

failed=""
for tex in "$@"; do
    "$(dirname "$0")/latex-build.sh" "$tex" || failed="$failed $tex"
done
if [ -n "$failed" ]; then
    echo "FAILED:$failed" >&2
    exit 1
fi
