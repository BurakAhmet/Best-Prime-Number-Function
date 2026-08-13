"""n−1 Pocklington primality path (faster than cubic when n−1 factors)."""

from __future__ import annotations

import math

import pytest

from best_prime.is_prime import DEFAULT_N, is_prime, lab
from best_prime.primality_nm1 import nm1_primality, nm1_ready
from tests.numbers import (
    LARGEST_PRIME_LT_2_64,
    MR_LIAR,
    NEAR_2_63_PRIME,
    P10_9_7,
    SEMIPRIME_1E9,
    SMALL_PRIMES,
)

M61 = (1 << 61) - 1


class TestNm1Primality:
    def test_tiny(self):
        assert nm1_primality(0) is False
        assert nm1_primality(1) is False
        assert nm1_primality(2) is True
        assert nm1_primality(4) is False
        assert nm1_primality(9) is False

    def test_small_primes_optional(self):
        # Small primes may return True or None (not on hard path); never False.
        for p in SMALL_PRIMES[:15]:
            r = nm1_primality(p)
            assert r is not False

    def test_default_n_instant_proof(self):
        assert nm1_ready(DEFAULT_N)
        assert nm1_primality(DEFAULT_N) is True
        assert is_prime(DEFAULT_N) is True
        assert lab(DEFAULT_N)["path"] == "u128_nm1"

    def test_m61(self):
        assert nm1_primality(M61) is True
        assert is_prime(M61) is True
        assert lab(M61)["path"] == "u64_nm1"

    def test_near_2_63(self):
        assert nm1_primality(NEAR_2_63_PRIME) is True
        assert is_prime(NEAR_2_63_PRIME) is True

    def test_largest_64bit_prime(self):
        assert nm1_primality(LARGEST_PRIME_LT_2_64) is True
        assert is_prime(LARGEST_PRIME_LT_2_64) is True

    def test_semiprime_fermat_rejects(self):
        assert nm1_primality(SEMIPRIME_1E9) is False
        assert is_prime(SEMIPRIME_1E9) is False
        assert lab(SEMIPRIME_1E9)["path"] == "u64_nm1"

    def test_mr_liar_not_false_prime(self):
        # May be None (fallback cubic) or False; never True.
        assert nm1_primality(MR_LIAR) is not True
        assert is_prime(MR_LIAR) is False

    def test_midsize_not_nm1_engine(self):
        # 10^9+7 stays on wheel trial (faster than n−1 there).
        assert nm1_ready(P10_9_7) is False
        assert lab(P10_9_7)["path"] in {"u64_wheel_c", "python_wheel", "u64_wheel_numba"}

    def test_serial_parallel_agree_hard(self):
        for n in (M61, NEAR_2_63_PRIME, DEFAULT_N, SEMIPRIME_1E9):
            assert nm1_primality(n, parallel=True) == nm1_primality(n, parallel=False)
            assert is_prime(n, parallel=True) is is_prime(n, parallel=False)

    def test_pocklington_math_on_smooth_nm1(self):
        # DEFAULT_N − 1 = 2^21 · 3 · 5^20 is fully smooth.
        n = DEFAULT_N
        assert n - 1 == (1 << 21) * 3 * 5**20
        assert math.isqrt(n) ** 2 < n
