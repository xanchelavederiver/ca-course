# C toolchain for compiled capstone references (Plan 4): gcc, clang, make; GMP is
# installed for the *oracle* only (unit tests), never linked into the operations under
# test. python3 runs taskgen.capstone (bench runner / checker, stdlib + PyYAML only).
# The repository is bind-mounted at /work (compose.yaml).
FROM debian:bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential clang make libgmp-dev \
      python3 python3-yaml python3-pytest python3-gmpy2 \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV HOME=/tmp \
    PYTHONPATH=/work \
    PYTHONDONTWRITEBYTECODE=1 \
    CA_IMAGE=capstone-c
WORKDIR /work
