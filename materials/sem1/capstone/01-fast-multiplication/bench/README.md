# Fast multiplication calibration

Each vector selects one of the four required methods; tags identify the method and input
shape. The measured request time therefore covers one complete multiplication, including
finite-field prime/root selection for FFT requests. All methods have independent oracle tests
in the reference suite.

The required range extends to 2048-bit inputs. Small vectors are committed; b1024 and b2048
are reproducibly regenerated. `ReqSeconds` is the maximum b2048 request time with the default
10× slack, rounded upward. No FFT crossover point is a correctness requirement; the plot is
for instructor review of the method comparison.
