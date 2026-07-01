"""Detailed unit tests for deterministic is_prime."""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from is_prime import (  # noqa: E402
    RES_TO_WI,
    RES_WHEEL,
    W30030,
    WHEEL_MOD,
    WHEEL_NW,
    W_WHEEL,
    _isqrt_u64,
    is_prime,
)


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

LARGE_64BIT_PRIME = 9223372036854775783
MERSENNE_COMPOSITE = (1 << 63) - 1

# Fast enough for default CI (parallel, but not multi-minute)
LARGE_PRIMES_FAST = [
    1_000_000_007,
    1_000_000_009,
    (1 << 31) - 1,
    4_294_967_291,
    999_999_999_989,
    1_000_000_000_039,
    999_999_999_999_999_989,
]

# Very large 64-bit primes — full wheel to sqrt(n); mark slow for CI
LARGE_PRIMES_SLOW = [
    2_305_843_009_213_693_951,  # M61
    9_223_372_036_854_775_783,  # near 2^63
    18_446_744_073_709_551_557,  # largest prime < 2^64
]

LARGE_PRIMES = LARGE_PRIMES_FAST + LARGE_PRIMES_SLOW

LARGE_COMPOSITES = [
    MERSENNE_COMPOSITE,
    (1 << 32) - 1,
    1_000_000_000_000,
    9_223_372_036_854_775_782,
    18_446_744_073_709_551_556,
    1_000_000_007 * 1_000_000_009,
]


# ---------------------------------------------------------------------------
# Edge cases / API validation
# ---------------------------------------------------------------------------

class TestEdgeCases:
    @pytest.mark.parametrize("n", [0, "0", "00", "000"])
    def test_zero_not_prime(self, n):
        assert is_prime(n) is False

    @pytest.mark.parametrize("n", [1, "1", "01", "001"])
    def test_one_not_prime(self, n):
        assert is_prime(n) is False

    @pytest.mark.parametrize("n", [2, "2", "02"])
    def test_two_is_prime(self, n):
        assert is_prime(n) is True

    @pytest.mark.parametrize("n", [3, "3"])
    def test_three_is_prime(self, n):
        assert is_prime(n) is True

    @pytest.mark.parametrize("n", [4, 6, 8, 9, 10, 15, 25, 27, 49, 121])
    def test_small_composites(self, n):
        assert is_prime(n) is False

    @pytest.mark.parametrize("n", [-1, -2, -17, -10**9, "-1", "-999"])
    def test_negative_raises(self, n):
        with pytest.raises(ValueError):
            is_prime(n)

    @pytest.mark.parametrize("bad", ["", "   ", "\t", "\n"])
    def test_empty_or_whitespace_string_raises(self, bad):
        with pytest.raises(ValueError):
            is_prime(bad)

    @pytest.mark.parametrize("bad", ["12a", "1.5", "0x10", "++1", "--1", "1 2", "ten"])
    def test_invalid_string_raises(self, bad):
        with pytest.raises(ValueError):
            is_prime(bad)

    def test_python_int_underscores_in_string_allowed(self):
        # int() accepts underscores; we inherit that behaviour
        assert is_prime("1_000_000_007") is True

    @pytest.mark.parametrize("bad", [3.14, 2.0, None, [2], {2}, (2,), object()])
    def test_wrong_types_raise(self, bad):
        with pytest.raises(TypeError):
            is_prime(bad)  # type: ignore[arg-type]

    def test_bool_rejected(self):
        with pytest.raises(TypeError):
            is_prime(True)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            is_prime(False)  # type: ignore[arg-type]

    def test_string_with_surrounding_whitespace(self):
        assert is_prime("  17  ") is True
        assert is_prime("\t100\n") is False

    def test_leading_zeros_in_string(self):
        assert is_prime("007") is True   # 7
        assert is_prime("000") is False  # 0
        assert is_prime("0010") is False  # 10

    def test_plus_prefix_string(self):
        assert is_prime("+17") is True
        assert is_prime("+0") is False

    def test_uint64_boundary(self):
        assert is_prime((1 << 64) - 1) is False  # odd but composite path / big
        # (2^64 - 1) is > 64-bit for our fast path? n < 2^64 so max is 2^64-1
        # 2^64 - 1 fits in uint64 and is composite
        n = (1 << 64) - 1
        assert n < (1 << 64) or n == (1 << 64) - 1
        assert is_prime(n) is False

    def test_first_integer_beyond_uint64(self):
        # 2^64 uses big-int path
        assert is_prime(1 << 64) is False  # even


class TestAPI:
    def test_string_decimal(self):
        assert is_prime("17") is True
        assert is_prime(" 100 ") is False

    def test_zero_and_one(self):
        assert is_prime(0) is False
        assert is_prime(1) is False


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

    def test_fast_wheel_modulus_and_length(self):
        assert WHEEL_MOD == 9_699_690
        assert WHEEL_NW == 1_658_880
        assert W_WHEEL.shape == (WHEEL_NW,)
        assert int(W_WHEEL.sum()) == WHEEL_MOD

    def test_fast_wheel_residues_cover_coprimes(self):
        x = 23
        seen = set()
        for wi in range(WHEEL_NW):
            assert RES_WHEEL[x % WHEEL_MOD] == wi
            seen.add(x % WHEEL_MOD)
            x += int(W_WHEEL[wi])
        assert len(seen) == WHEEL_NW

    def test_fast_wheel_non_coprime_invalid(self):
        for r in range(0, WHEEL_MOD, 17):  # sample stride; full scan is heavy
            if math.gcd(r, WHEEL_MOD) != 1:
                assert RES_WHEEL[r] == 0xFFFFFFFF
        # spot-check a dense prefix
        for r in range(10_000):
            if math.gcd(r, WHEEL_MOD) != 1:
                assert RES_WHEEL[r] == 0xFFFFFFFF


# ---------------------------------------------------------------------------
# Integer square root
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
# Parallel vs serial
# ---------------------------------------------------------------------------

class TestParallelSerial:
    @pytest.mark.parametrize(
        "n",
        [97, 10_007, 1_000_003, 10**9 + 7, *LARGE_PRIMES_FAST[:3], MERSENNE_COMPOSITE],
    )
    def test_parallel_matches_serial(self, n):
        assert is_prime(n, parallel=True) is is_prime(n, parallel=False)


# ---------------------------------------------------------------------------
# Large 64-bit cases
# ---------------------------------------------------------------------------

class TestLarge64Bit:
    @pytest.mark.parametrize("n", LARGE_PRIMES_FAST)
    def test_large_primes_fast(self, n):
        assert is_prime(n) is True
        assert is_prime(str(n)) is True

    @pytest.mark.slow
    @pytest.mark.parametrize("n", LARGE_PRIMES_SLOW)
    def test_large_primes_slow(self, n):
        assert is_prime(n) is True
        assert is_prime(str(n)) is True

    @pytest.mark.parametrize("n", LARGE_COMPOSITES)
    def test_large_composites(self, n):
        assert is_prime(n) is False

    def test_near_int64_max_prime_listed(self):
        assert LARGE_64BIT_PRIME in LARGE_PRIMES_SLOW

    def test_two_pow_63_minus_one_composite(self):
        assert is_prime(MERSENNE_COMPOSITE) is False

    def test_squares_not_prime(self):
        for k in (10**6, 10**7, 10**8):
            assert is_prime(k * k) is False

    def test_even_large_not_prime(self):
        assert is_prime(10**18) is False
        assert is_prime((1 << 62)) is False

    @pytest.mark.slow
    def test_large_primes_parallel_matches_serial(self):
        for n in LARGE_PRIMES_SLOW:
            assert is_prime(n, parallel=True) is is_prime(n, parallel=False)


# ---------------------------------------------------------------------------
# Big integers
# ---------------------------------------------------------------------------

class TestBigIntegers:
    def test_100_digit_all_nines_not_prime(self):
        assert is_prime(int("9" * 100)) is False
        assert is_prime("9" * 100) is False

    def test_power_of_ten_not_prime(self):
        assert is_prime(10**99) is False
        assert is_prime("1" + "0" * 99) is False

    def test_small_factor_huge_number(self):
        assert is_prime(7 * 10**50) is False

    def test_string_matches_int_for_medium(self):
        n = 10**20 + 7 * 10**10 + 3
        assert is_prime(str(n)) is is_prime(n)

    def test_two_pow_64_even(self):
        assert is_prime(1 << 64) is False

    def test_two_pow_64_plus_one_has_factor(self):
        # 2^64 + 1 = 18446744073709551617 = 274177 × 67280421310721
        assert is_prime((1 << 64) + 1) is False


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_repeated_calls_identical(self):
        samples = [0, 1, 2, 4, 97, 100, *LARGE_PRIMES_FAST[:2], MERSENNE_COMPOSITE]
        for n in samples:
            a = is_prime(n)
            b = is_prime(n)
            c = is_prime(n, parallel=False)
            assert a == b == c


# ---------------------------------------------------------------------------
# Known values
# ---------------------------------------------------------------------------

class TestKnownValues:
    def test_carmichael_numbers_are_composite(self):
        for n in (561, 1105, 1729, 2465, 2821, 6601, 8911):
            assert is_prime(n) is False

    def test_mersenne_primes_small(self):
        for p in (2, 3, 5, 7, 13, 17, 19, 31):
            assert is_prime((1 << p) - 1) is True

    def test_mersenne_composites_small(self):
        for p in (11, 23, 29):
            assert is_prime((1 << p) - 1) is False
