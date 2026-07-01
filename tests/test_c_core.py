"""Tests for the optional OpenMP C extension path."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from is_prime import _load_c_core, is_prime, lab  # noqa: E402

pytestmark = pytest.mark.skipif(
    not _load_c_core(),
    reason="wheel_core.so not built (run scripts/compile_wheel_core.sh)",
)

NEAR_2_63 = 9_223_372_036_854_775_783
M61 = (1 << 61) - 1
SEMIPRIME = 1_000_000_007 * 1_000_000_009
LARGEST_PRIME_LT_2_64 = 18_446_744_073_709_551_557

# 32-bit-ish primes whose products exercise high uint64 bits (no RNG).
_LARGE_P = [
    4_294_967_291,
    4_294_967_279,
    4_294_967_231,
    4_294_967_197,
    2_147_483_647,
    2_147_483_629,
    1_000_000_007,
    1_000_000_009,
]
_SMALL_P = [10007, 10009, 10037, 10039, 10061, 10067, 10069, 10079]


class TestCPathEngine:
    def test_lab_reports_c_path(self):
        info = lab(1_000_000_007)
        assert info["path"] == "u64_wheel_c"
        assert info["is_prime"] is True

    def test_hard_prime_uses_c_path(self):
        info = lab(NEAR_2_63)
        assert info["path"] == "u64_wheel_c"
        assert info["is_prime"] is True


class TestCSerialParallelAgree:
    @pytest.mark.parametrize(
        "n",
        [
            97,
            1_000_000_007,
            1_000_000_009,
            (1 << 31) - 1,
            999_999_999_989,
            SEMIPRIME,
            NEAR_2_63,
            M61,
            LARGEST_PRIME_LT_2_64,
            (1 << 63) - 1,
        ],
    )
    def test_serial_equals_parallel(self, n):
        assert is_prime(n, parallel=True) is is_prime(n, parallel=False)


class TestCSemiprimes:
    @pytest.mark.parametrize("a", _SMALL_P)
    @pytest.mark.parametrize("b", _SMALL_P)
    def test_small_products_composite(self, a, b):
        n = a * b
        assert is_prime(n) is False
        assert is_prime(n, parallel=True) is is_prime(n, parallel=False)

    @pytest.mark.parametrize(
        "a,b",
        [
            (_LARGE_P[i], _LARGE_P[j])
            for i in range(len(_LARGE_P))
            for j in range(i, len(_LARGE_P))
            if _LARGE_P[i] * _LARGE_P[j] < (1 << 64)
        ],
    )
    def test_large_products_composite(self, a, b):
        n = a * b
        assert n < (1 << 64)
        assert is_prime(n, parallel=True) is False
        assert is_prime(n, parallel=False) is False

    def test_large_factors_are_prime(self):
        for p in _LARGE_P:
            assert is_prime(p) is True
