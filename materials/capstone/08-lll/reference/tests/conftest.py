import sys
from pathlib import Path

# the reference modules (lattice, gauss, crypto, main) live one directory up
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.set_int_max_str_digits(0)
