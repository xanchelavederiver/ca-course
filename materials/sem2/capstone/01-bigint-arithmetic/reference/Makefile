# bigint reference (capstone 01): a static library + three programs, all in build/.
#
#   build/bigint-solver   JSON-lines solver used by the bench (never linked with GMP)
#   build/bigint-oracle   randomized test driver: compares the library with GMP (tests only)
#   build/bigint-tune     measures the Karatsuba thresholds and per-operation times
#
# The target is plain x86-64 without AVX (the spec: "x86-64 без расширения AVX"):
# -march=x86-64 is the baseline ISA (SSE2, no AVX/BMI2/ADX), so the binary runs on any
# 64-bit x86 machine at the defence and the timings do not depend on the build host.
# Override with `make ARCH=` for other hosts.
CC      ?= cc
ARCH    ?= -march=x86-64 -mno-avx
CFLAGS  ?= -O2 -g
CFLAGS  += $(ARCH) -std=c11 -Wall -Wextra -Wshadow
BUILD   := build

LIB_SRC := src/limbs.c src/mul.c src/div.c src/bigint.c src/gcd.c src/mont.c src/pow.c
LIB_OBJ := $(LIB_SRC:src/%.c=$(BUILD)/%.o)
HDR     := $(wildcard src/*.h)

.PHONY: all clean
all: $(BUILD)/bigint-solver $(BUILD)/bigint-oracle $(BUILD)/bigint-tune

$(BUILD):
	mkdir -p $@

$(BUILD)/%.o: src/%.c $(HDR) | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/libbigint.a: $(LIB_OBJ)
	ar rcs $@ $^

$(BUILD)/bigint-solver: $(BUILD)/solver.o $(BUILD)/json.o $(BUILD)/libbigint.a
	$(CC) $(CFLAGS) $^ -o $@

$(BUILD)/bigint-tune: $(BUILD)/tune.o $(BUILD)/libbigint.a
	$(CC) $(CFLAGS) $^ -o $@

# GMP is the oracle of the tests only.
$(BUILD)/bigint-oracle: tests/oracle.c $(BUILD)/libbigint.a $(HDR) | $(BUILD)
	$(CC) $(CFLAGS) -Isrc tests/oracle.c $(BUILD)/libbigint.a -lgmp -o $@

clean:
	rm -rf $(BUILD)
