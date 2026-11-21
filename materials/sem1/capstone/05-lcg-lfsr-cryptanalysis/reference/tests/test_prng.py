import math
import random
import sys
from pathlib import Path

import pytest
from sage.all import GF, PolynomialRing
from sage.matrix.berlekamp_massey import berlekamp_massey as sage_bm

sys.path.insert(0, str(Path(__file__).parents[1]))

from prng import (berlekamp_massey, full_period_conditions, lcg_decrypt, lcg_generate, lcg_next,
                  lcg_period, lcg_recover, lfsr_decrypt, lfsr_generate, lfsr_period, lfsr_recover,
                  xor_stream)
from taskgen.tasks.crypto.lfsr import berlekamp_massey as task_bm, lfsr_bits


def test_lcg_generation_next_and_period():
    a, c, m, state = 5, 1, 16, 3
    outputs = lcg_generate(a, c, m, state, 40)
    assert outputs[:5] == [3, 0, 1, 6, 15]
    assert lcg_next(a, c, m, state) == outputs[1]
    assert lcg_period(a, c, m, state) == {"period": 16, "tail": 0, "repeated_state": 3}
    assert lcg_period(0, 1, 7, 0) == {"period": 1, "tail": 1, "repeated_state": 1}


def test_full_period_hull_dobell():
    assert full_period_conditions(5, 1, 16, [[2, 4]])["full_period"]
    assert not full_period_conditions(3, 1, 16, [[2, 4]])["full_period"]
    assert not full_period_conditions(5, 2, 16, [[2, 4]])["full_period"]
    assert full_period_conditions(16, 2, 15, [[3, 1], [5, 1]])["full_period"]


def test_lcg_unique_recovery():
    rng = random.Random(812)
    checked = 0
    while checked < 20:
        m = rng.randrange(100, 10000)
        a = rng.randrange(2, m)
        c = rng.randrange(m)
        state = rng.randrange(m)
        outputs = lcg_generate(a, c, m, state, 7)
        differences = [y - x for x, y in zip(outputs, outputs[1:])]
        determinants = [differences[i + 2] * differences[i] - differences[i + 1] ** 2
                        for i in range(len(differences) - 2)]
        if math.gcd(*determinants) != m or math.gcd(differences[0] % m, m) != 1:
            continue
        got = lcg_recover(outputs)
        assert got["a"] == a and got["c"] == c and got["m"] == m
        assert got["next"] == lcg_next(a, c, m, outputs[-1])
        stream = lcg_generate(a, c, m, state, 15)
        plaintext = [rng.randrange(m) for _ in stream]
        ciphertext = [plain ^ key for plain, key in zip(plaintext, stream)]
        decrypted = lcg_decrypt(ciphertext, plaintext[:7])
        assert decrypted["plaintext"] == plaintext
        assert (decrypted["a"], decrypted["c"], decrypted["m"]) == (a, c, m)
        checked += 1


def test_lfsr_against_independent_simulator():
    rng = random.Random(17)
    for _ in range(100):
        length = rng.randrange(1, 12)
        coefficients = [rng.randrange(2) for _ in range(length)]
        state = [rng.randrange(2) for _ in range(length)]
        count = rng.randrange(0, 50)
        assert lfsr_generate(coefficients, state, count) == lfsr_bits(coefficients, state, count)


def test_lfsr_period_and_preperiod():
    assert lfsr_period([1, 1], [0, 1]) == {"period": 3, "tail": 0, "repeated_state": [0, 1]}
    assert lfsr_period([0], [1]) == {"period": 1, "tail": 1, "repeated_state": [0]}
    assert lfsr_period([0], [0]) == {"period": 1, "tail": 0, "repeated_state": [0]}


def test_berlekamp_massey_against_sage():
    rng = random.Random(9917)
    for _ in range(50):
        length = rng.randrange(2, 8)
        coefficients = [rng.randrange(2) for _ in range(length)]
        state = [rng.randrange(2) for _ in range(length)]
        sequence = lfsr_generate(coefficients, state, 2 * length + 4)
        try:
            got = lfsr_recover(sequence)
        except ValueError:
            continue
        expected = task_bm(sequence)
        assert got["linear_complexity"] == expected["L"]
        oracle = sage_bm([GF(2)(bit) for bit in sequence])
        ring = PolynomialRing(GF(2), "x")
        if oracle.degree() == expected["L"]:
            assert ring(got["characteristic"]) == oracle
        assert lfsr_generate(got["coefficients"], got["state"], len(sequence)) == sequence


def test_berlekamp_massey_known_sequence_and_reproducibility():
    sequence = [0, 0, 1, 0, 1, 1, 1, 0]
    got = berlekamp_massey(sequence)
    assert got == berlekamp_massey(sequence)
    assert lfsr_generate(got["coefficients"], got["state"], len(sequence)) == sequence
    assert got["linear_complexity"] <= len(sequence) // 2


def test_xor_stream_decrypts_encryption():
    coefficients, state = [1, 0, 1, 1], [1, 0, 0, 1]
    plaintext = [1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1]
    ciphertext = xor_stream(coefficients, state, plaintext)
    assert xor_stream(coefficients, state, ciphertext) == plaintext


def test_lfsr_known_plaintext_attack():
    rng = random.Random(731)
    for _ in range(100):
        length = rng.randrange(2, 8)
        coefficients = [rng.randrange(2) for _ in range(length)]
        state = [rng.randrange(2) for _ in range(length)]
        plaintext = [rng.randrange(2) for _ in range(2 * length + 12)]
        ciphertext = xor_stream(coefficients, state, plaintext)
        try:
            got = lfsr_decrypt(ciphertext, plaintext[:2 * length + 4])
        except ValueError:
            continue
        assert got["plaintext"] == plaintext
        return
    raise AssertionError("no uniquely recoverable LFSR generated")


def test_degenerate_lfsr_and_short_input():
    assert berlekamp_massey([0, 0, 0, 0])["linear_complexity"] == 0
    with pytest.raises(ValueError):
        berlekamp_massey([1, 0, 1])
