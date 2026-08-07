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


class TestPrecomputedPrimeBound:
    """Exercise the embedded prime-table path (isqrt ≤ 2^20) and just above it."""

    # Largest prime ≤ 2^20, plus the next primes just above the table bound.
    P_LE_2_20 = 1_048_573
    P_GT_2_20 = 1_048_583
    P_GT_2_20_B = 1_048_601
    P_NEAR = 999_983
    P_NEAR2 = 999_979

    def test_table_edge_primes(self):
        assert is_prime(self.P_LE_2_20) is True
        assert is_prime(self.P_GT_2_20) is True
        assert is_prime(self.P_NEAR) is True
        assert is_prime(self.P_NEAR2) is True

    def test_square_inside_table_is_composite(self):
        n = self.P_NEAR * self.P_NEAR
        assert n < (1 << 64)
        assert is_prime(n) is False
        assert is_prime(n, parallel=False) is False

    def test_semiprime_near_table_bound(self):
        n = self.P_NEAR * self.P_NEAR2
        assert is_prime(n, parallel=True) is False
        assert is_prime(n, parallel=False) is False

    def test_just_above_table_uses_c_path(self):
        # isqrt > 2^20 → segmented primes after the precomputed table.
        n = self.P_GT_2_20 * self.P_GT_2_20_B
        info = lab(n)
        assert info["path"] == "u64_wheel_c"
        assert info["is_prime"] is False
        assert info["isqrt"] > 1_048_576


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


class TestCU128Path:
    """65–128-bit full trial via is_prime_u128_core (no AKS)."""

    P10_20 = 100_000_000_000_000_000_039  # next prime after 10^20
    P10_19 = 10_000_000_000_000_000_051  # next prime after 10^19 (still < 2^64)

    def test_lab_reports_u128_path(self):
        info = lab(self.P10_20)
        assert info["path"] == "u128_wheel_c"
        assert info["is_prime"] is True
        assert info["bit_length"] == 67

    def test_ten_to_20_prime(self):
        assert is_prime(self.P10_20) is True
        assert is_prime(self.P10_20, parallel=False) is True

    def test_ten_to_20_composites(self):
        assert is_prime(10**20) is False
        assert is_prime(10**20 + 1) is False
        assert is_prime(self.P10_20 - 2) is False

    def test_u128_serial_equals_parallel(self):
        n = self.P10_20
        assert is_prime(n, parallel=True) is is_prime(n, parallel=False)

    def test_two_to_64_uses_big_path_not_u64(self):
        # 2^64 itself is composite power of two; path is big-int family.
        info = lab(1 << 64)
        assert info["path"] in {"u128_wheel_c", "bigint_wheel", "bigint_trial_or_aks"}
        assert info["is_prime"] is False


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
