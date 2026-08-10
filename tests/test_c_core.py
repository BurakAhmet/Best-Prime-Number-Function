"""Tests for the optional OpenMP C extension path."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from is_prime import DEFAULT_N, _load_c_core, is_prime, lab  # noqa: E402
from tests.numbers import (  # noqa: E402
    LARGEST_PRIME_LT_2_64,
    M61,
    NEAR_2_63_PRIME,
    P10_20,
    P_GT_2_20,
    P_GT_2_20_B,
    P_LE_2_20,
    P_NEAR_1E6,
    P_NEAR_1E6_B,
    SEMIPRIME_1E9,
)

pytestmark = pytest.mark.skipif(
    not _load_c_core(),
    reason="wheel_core.so not built (run scripts/compile_wheel_core.sh)",
)

NEAR_2_63 = NEAR_2_63_PRIME
SEMIPRIME = SEMIPRIME_1E9

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
        info = lab(999_999_999_989)
        assert info["path"] == "u64_wheel_c"
        assert info["is_prime"] is True

    @pytest.mark.slow
    def test_default_hard_prime_uses_c_path(self):
        info = lab(LARGEST_PRIME_LT_2_64)
        assert info["path"] == "u64_wheel_c"
        assert info["is_prime"] is True
        assert info["isqrt"] == (1 << 32) - 1


class TestPrecomputedPrimeBound:
    """Exercise the embedded prime-table path (isqrt ≤ 2^20) and just above it."""

    def test_table_edge_primes(self):
        assert is_prime(P_LE_2_20) is True
        assert is_prime(P_GT_2_20) is True
        assert is_prime(P_NEAR_1E6) is True
        assert is_prime(P_NEAR_1E6_B) is True

    def test_square_inside_table_is_composite(self):
        n = P_NEAR_1E6 * P_NEAR_1E6
        assert n < (1 << 64)
        assert is_prime(n) is False
        assert is_prime(n, parallel=False) is False

    def test_semiprime_near_table_bound(self):
        n = P_NEAR_1E6 * P_NEAR_1E6_B
        assert is_prime(n, parallel=True) is False
        assert is_prime(n, parallel=False) is False

    def test_just_above_table_uses_c_path(self):
        # isqrt > 2^20 → segmented primes after the precomputed table.
        n = P_GT_2_20 * P_GT_2_20_B
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
            (1 << 63) - 1,
            P_GT_2_20 * P_GT_2_20_B,
        ],
    )
    def test_serial_equals_parallel_fast(self, n):
        assert is_prime(n, parallel=True) is is_prime(n, parallel=False)

    @pytest.mark.slow
    @pytest.mark.parametrize("n", [NEAR_2_63, M61, LARGEST_PRIME_LT_2_64])
    def test_serial_equals_parallel_hard(self, n):
        assert is_prime(n, parallel=True) is is_prime(n, parallel=False)

    def test_default_n_matches_largest_prime_constant(self):
        assert DEFAULT_N == LARGEST_PRIME_LT_2_64


class TestCU128Path:
    """65–128-bit full trial via is_prime_u128_core (no AKS)."""

    P10_20 = P10_20
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


class TestTwoAdicDivisibilityTheorem:
    """Exact wrap-mul identity used by the u64 segmented trial (no DIV).

    For odd p and n < 2^64: p | n  iff  (n * p^{-1} mod 2^64) * p < 2^64.
    """

    _P = [
        3,
        5,
        7,
        11,
        17,
        101,
        1_048_583,
        1_000_000_007,
        4_294_967_291,
    ]
    _N = [
        1,
        15,
        21,
        35,
        1_000_000_007,
        9_223_372_036_854_775_783,
        3 * 5 * 7 * 11,
        (1 << 64) - 1,
        1_048_583 * 1_048_601,
        1_000_000_007 * 1_000_000_009,
    ]

    def test_identity_matches_mod(self):
        mod = 1 << 64
        for p in self._P:
            inv = pow(p, -1, mod)
            assert (p * inv) % mod == 1
            for n in self._N:
                q = (n * inv) % mod
                fits = (q * p) < mod
                assert fits is (n % p == 0)

    def test_segmented_path_factors_above_pre_max(self):
        # Primes just above 2^20 → wheel-30 sieve + persist/presieve + 2-adic trial.
        ps = [1_048_583, 1_048_601, 1_048_609, 3_000_017, 3_000_029]
        for p in ps:
            assert is_prime(p) is True
        for i, a in enumerate(ps):
            for b in ps[i:]:
                n = a * b
                if n >= (1 << 64):
                    continue
                assert is_prime(n, parallel=True) is False
                assert is_prime(n, parallel=False) is False
