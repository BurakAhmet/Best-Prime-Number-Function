"""Detailed unit tests for deterministic is_prime."""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

# Allow `python -m pytest` from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from is_prime import (  # noqa: E402
    RES_TO_WI,
    W30030,
    _isqrt_u64,
    is_prime,
)


# ---------------------------------------------------------------------------
# Reference helpers
# ---------------------------------------------------------------------------

def naive_is_prime(n: int) -> bool:
    """Slow reference: trial division by all integers up to sqrt(n)."""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    r = math.isqrt(n)
    for i in range(3, r + 1, 2):
        if n % i == 0:
            return False
    return True


# Small primes and composites for exhaustive checks
SMALL_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
    73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151,
    157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233,
    239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317,
    331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419,
    421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503,
    509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 601, 607,
    613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 701,
    709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809, 811,
    821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887, 907, 911,
    919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997,
]

# Famous / awkward cases
LARGE_64BIT_PRIME = 9223372036854775783  # near 2^63
MERSENNE_COMPOSITE = (1 << 63) - 1  # 2^63 - 1 = 9223372036854775807, composite

# Large primes in the 64-bit range (fast path: 30030-wheel + Numba)
# Verified with this project's deterministic trial division.
LARGE_PRIMES = [
    1_000_000_007,  # 10^9 + 7
    1_000_000_009,  # 10^9 + 9
    (1 << 31) - 1,  # 2^31 - 1 (Mersenne prime M31)
    4_294_967_291,  # large 32-bit prime
    999_999_999_989,
    1_000_000_000_039,
    999_999_999_999_999_989,
    2_305_843_009_213_693_951,  # 2^61 - 1 (Mersenne prime M61)
    9_223_372_036_854_775_783,  # near 2^63
    18_446_744_073_709_551_557,  # largest prime below 2^64
]

# Large composites (same magnitude class as the primes above)
LARGE_COMPOSITES = [
    MERSENNE_COMPOSITE,  # 2^63 - 1
    (1 << 32) - 1,  # 2^32 - 1 = 3 * 5 * 17 * 257 * 65537
    1_000_000_000_000,  # 10^12
    9_223_372_036_854_775_782,  # even neighbour of LARGE_64BIT_PRIME
    18_446_744_073_709_551_556,  # even neighbour of largest 64-bit prime
    1_000_000_007 * 1_000_000_009,  # product of two large primes
]


# ---------------------------------------------------------------------------
# Basic API / validation
# ---------------------------------------------------------------------------

class TestAPI:
    def test_negative_raises(self):
        with pytest.raises(ValueError):
            is_prime(-1)

    def test_non_int_raises(self):
        with pytest.raises(TypeError):
            is_prime(3.14)  # type: ignore[arg-type]

    def test_string_decimal(self):
        assert is_prime("17") is True
        assert is_prime(" 100 ") is False

    def test_zero_and_one(self):
        assert is_prime(0) is False
        assert is_prime(1) is False
        assert is_prime("0") is False
        assert is_prime("1") is False


# ---------------------------------------------------------------------------
# Exhaustive small-n vs reference
# ---------------------------------------------------------------------------

class TestExhaustiveSmall:
    @pytest.mark.parametrize("n", range(0, 5000))
    def test_matches_naive_0_to_4999(self, n):
        assert is_prime(n) is naive_is_prime(n)

    def test_all_listed_small_primes(self):
        for p in SMALL_PRIMES:
            assert is_prime(p) is True, p

    def test_composites_from_products(self):
        for a in SMALL_PRIMES[:30]:
            for b in SMALL_PRIMES[:30]:
                n = a * b
                if n < 5000:
                    continue
                assert is_prime(n) is False


# ---------------------------------------------------------------------------
# Wheel tables
# ---------------------------------------------------------------------------

class TestWheelTables:
    def test_w30030_length(self):
        assert W30030.shape == (5760,)

    def test_wheel_steps_sum_to_primorial(self):
        assert int(W30030.sum()) == 30030

    def test_res_to_wi_covers_coprime_residues(self):
        # Every residue coprime to 30030 (except those before start) maps validly
        # when walking from 17
        x = 17
        seen = set()
        for wi in range(5760):
            assert RES_TO_WI[x % 30030] == wi
            seen.add(x % 30030)
            x += int(W30030[wi])
        assert len(seen) == 5760

    def test_non_coprime_residues_are_ffff(self):
        for r in range(30030):
            if math.gcd(r, 30030) != 1:
                assert RES_TO_WI[r] == 0xFFFF


# ---------------------------------------------------------------------------
# Integer square root (Numba helper)
# ---------------------------------------------------------------------------

class TestIsqrt:
    @pytest.mark.parametrize(
        "n",
        [
            0, 1, 2, 3, 4, 10, 100, 10**9,
            2**53 - 1, 2**53, 2**53 + 1,
            2**63 - 1, LARGE_64BIT_PRIME,
        ],
    )
    def test_matches_math_isqrt(self, n):
        got = int(_isqrt_u64(np.uint64(n)))
        assert got == math.isqrt(n)

    def test_many_random_u64(self):
        rng = np.random.default_rng(0)
        for n in rng.integers(0, 2**63 - 1, size=200, dtype=np.uint64):
            nn = int(n)
            assert int(_isqrt_u64(np.uint64(nn))) == math.isqrt(nn)


# ---------------------------------------------------------------------------
# Parallel vs serial consistency
# ---------------------------------------------------------------------------

class TestParallelSerial:
    @pytest.mark.parametrize(
        "n",
        [97, 10_007, 1_000_003, 10**9 + 7, LARGE_64BIT_PRIME, MERSENNE_COMPOSITE],
    )
    def test_parallel_matches_serial(self, n):
        assert is_prime(n, parallel=True) is is_prime(n, parallel=False)


# ---------------------------------------------------------------------------
# Large 64-bit cases
# ---------------------------------------------------------------------------

class TestLarge64Bit:
    @pytest.mark.parametrize("n", LARGE_PRIMES)
    def test_large_primes(self, n):
        assert is_prime(n) is True
        assert is_prime(str(n)) is True

    @pytest.mark.parametrize("n", LARGE_COMPOSITES)
    def test_large_composites(self, n):
        assert is_prime(n) is False

    def test_near_int64_max_prime(self):
        assert is_prime(LARGE_64BIT_PRIME) is True

    def test_two_pow_63_minus_one_composite(self):
        assert is_prime(MERSENNE_COMPOSITE) is False

    def test_largest_prime_below_2_64(self):
        assert is_prime(18_446_744_073_709_551_557) is True

    def test_mersenne_61(self):
        assert is_prime((1 << 61) - 1) is True

    def test_squares_not_prime(self):
        for k in (10**6, 10**7, 10**8):
            assert is_prime(k * k) is False

    def test_even_large_not_prime(self):
        assert is_prime(10**18) is False
        assert is_prime((1 << 62)) is False

    def test_large_primes_parallel_matches_serial(self):
        # Subset: full list would be slow under serial for the biggest primes
        for n in LARGE_PRIMES[-3:]:
            assert is_prime(n, parallel=True) is is_prime(n, parallel=False)


# ---------------------------------------------------------------------------
# Arbitrary precision (beyond 64-bit)
# ---------------------------------------------------------------------------

class TestBigIntegers:
    def test_100_digit_all_nines_not_prime(self):
        n = int("9" * 100)
        assert is_prime(n) is False
        assert is_prime("9" * 100) is False

    def test_power_of_ten_not_prime(self):
        assert is_prime(10**99) is False
        assert is_prime("1" + "0" * 99) is False

    def test_small_factor_huge_number(self):
        assert is_prime(7 * 10**50) is False

    def test_string_matches_int_for_medium(self):
        n = 10**20 + 7 * 10**10 + 3
        assert is_prime(str(n)) is is_prime(n)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_repeated_calls_identical(self):
        samples = [0, 1, 2, 4, 97, 100, LARGE_64BIT_PRIME, MERSENNE_COMPOSITE]
        for n in samples:
            a = is_prime(n)
            b = is_prime(n)
            c = is_prime(n, parallel=False)
            assert a is b is c or (a == b == c)


# ---------------------------------------------------------------------------
# Known primes / pseudoprime traps (should not matter: we do not use MR)
# ---------------------------------------------------------------------------

class TestKnownValues:
    def test_carmichael_numbers_are_composite(self):
        # Carmichael numbers fool Fermat tests; trial division must reject them
        for n in (561, 1105, 1729, 2465, 2821, 6601, 8911):
            assert is_prime(n) is False

    def test_mersenne_primes_small(self):
        # 2^p - 1 for small Mersenne primes
        for p in (2, 3, 5, 7, 13, 17, 19, 31):
            assert is_prime((1 << p) - 1) is True

    def test_mersenne_composites_small(self):
        for p in (11, 23, 29):
            assert is_prime((1 << p) - 1) is False
