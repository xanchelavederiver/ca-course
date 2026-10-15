"""Make the reference modules (qsieve, qs_linalg, qs_numtheory) importable."""

import sys
from pathlib import Path

REF = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REF))
