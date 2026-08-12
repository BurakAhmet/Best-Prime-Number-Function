"""lab() diagnostic contract: paths, timings, serial/parallel agreement."""
from __future__ import annotations

import math

import pytest

from best_prime.is_prime import _load_c_core, is_prime, lab
from tests.numbers import (
    LARGEST_PRIME_LT_2_64,
    P10_20,
    P10_9_7,
    P12_DIGIT,
    SEMIPRIME_1E9,
)

REQUIRED_KEYS = {
    "n",
    "bit_length",
    "path",
    "parallel",
    "isqrt",
    "elapsed_ms",
    "e2e_ms",
    "is_prime",
    "note",
}


class TestLabContract:
    @pytest.mark.parametrize(
        "n,expect_prime",
        [
            (0, False),
            (1, False),
            (2, True),
            (97, True),
            (100, False),
            (P10_9_7, True),
            (P12_DIGIT, True),
            (SEMIPRIME_1E9, False),
            (1 << 64, False),
        ],
    )
    def test_keys_and_consistency(self, n, expect_prime):
        info = lab(n)
        assert set(info) >= REQUIRED_KEYS
        assert info["n"] == n
        assert info["bit_length"] == n.bit_length()
        assert info["is_prime"] is expect_prime
        assert info["is_prime"] is is_prime(n)
        assert info["elapsed_ms"] >= 0.0
        assert info["e2e_ms"] >= 0.0
        assert isinstance(info["note"], str) and info["note"]
        if n >= 2:
            assert info["isqrt"] == math.isqrt(n)
        else:
            assert info["isqrt"] is None

    def test_tiny_path(self):
        assert lab(97)["path"] == "python_small"

    def test_midsize_c_or_wheel_path(self):
        info = lab(P10_9_7)
        if _load_c_core():
            assert info["path"] == "u64_wheel_c"
        else:
            assert info["path"] in {"python_wheel", "u64_wheel_numba"}

    def test_two_pow_64_not_u64_path(self):
        info = lab(1 << 64)
        assert info["path"] in {
            "u128_lehman_c",
            "u128_wheel_c",
            "bigint_wheel",
            "bigint_trial_or_aks",
        }
        assert info["is_prime"] is False

    def test_u128_path_when_core_present(self):
        if not _load_c_core() or not hasattr(_load_c_core(), "is_prime_u128_core"):
            pytest.skip("no u128 core")
        info = lab(P10_20)
        from best_prime.factor_lehman import _c_lehman_ready

        if _c_lehman_ready():
            assert info["path"] == "u128_lehman_c"
        else:
            assert info["path"] == "u128_wheel_c"
        assert info["is_prime"] is True
        assert info["bit_length"] == 67

    def test_huge_path_is_aks_family(self):
        # isqrt(7·10^50) ≫ 2.5e10 → partial-trial / AKS band; factor 7 is instant.
        n = 7 * 10**50
        info = lab(n)
        assert info["path"] == "bigint_trial_or_aks"
        assert info["is_prime"] is False

    def test_path_stable_across_repeated_calls(self):
        paths = {lab(P10_9_7)["path"] for _ in range(5)}
        assert len(paths) == 1

    def test_serial_parallel_same_boolean(self):
        n = P12_DIGIT
        a = lab(n, parallel=True)
        b = lab(n, parallel=False)
        assert a["is_prime"] is b["is_prime"]
        assert a["path"] == b["path"]

    def test_hard_64bit_uses_cubic_when_c_ready(self):
        info = lab(SEMIPRIME_1E9)
        from best_prime.factor_lehman import _c_lehman_ready

        assert info["is_prime"] is False
        if _c_lehman_ready():
            assert info["path"] == "u64_lehman_c"
        elif _load_c_core():
            assert info["path"] == "u64_wheel_c"

    @pytest.mark.slow
    def test_default_hard_prime_lab(self):
        info = lab(LARGEST_PRIME_LT_2_64)
        assert info["is_prime"] is True
        assert info["isqrt"] == (1 << 32) - 1
        if _load_c_core():
            from best_prime.factor_lehman import _c_lehman_ready

            if _c_lehman_ready():
                assert info["path"] == "u64_lehman_c"
            else:
                assert info["path"] == "u64_wheel_c"
