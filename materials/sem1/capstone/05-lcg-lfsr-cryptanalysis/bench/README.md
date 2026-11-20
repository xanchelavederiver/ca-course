# LCG/LFSR cryptanalysis calibration

The vector mix covers every required operation. LCG parameter-recovery instances are sampled
until the modulus and parameters are uniquely determined; ambiguous cases are outside scope.
Period searches use bounded moduli. LFSR observations contain at least 2L bits, and Sage checks
both the minimal degree and characteristic polynomial independently.

`ReqBitsMax` refers to the LCG modulus, not an unbounded period search or LFSR length.
`ReqSeconds` uses the maximum b32 request with default slack. Decryption is verified by
re-encryption with an independently simulated keystream.
