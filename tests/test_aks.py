"""Deterministic AKS engine + huge-n pre-trial (no stochastic tests)."""
from __future__ import annotations

import math

import pytest

from is_prime import (
    _aks_is_prime,
    _is_perfect_power,
    _poly_mul_mod,
    is_prime,
    lab,
)
from tests.numbers import CARMICHAEL, POULET, SMALL_PRIMES


class TestPerfectPower:
    @pytest.mark.parametrize("n", [4, 8, 9, 16, 25, 27, 32, 36, 49, 64, 81, 121, 125, 128, 243, 256, 729, 1024, 2187, 2401])
    def test_small_powers(self, n):
        assert _is_perfect_power(n) is True

    @pytest.mark.parametrize("n", [2, 3, 5, 6, 7, 10, 12, 15, 18, 20, 24, 26, 28, 30, 97])
    def test_non_powers(self, n):
        assert _is_perfect_power(n) is False

    def test_large_square_and_cube(self):
        assert _is_perfect_power((10**20 + 39) ** 2) is True
        assert _is_perfect_power((10**12 + 39) ** 3) is True
        assert _is_perfect_power((10**20 + 39) ** 2 + 1) is False


class TestKroneckerPolyMul:
    def test_mod_xr_minus_1_small(self):
        # (1 + X) * (1 + X) = 1 + 2X + X^2 ≡ 1 + 2X + 1 = 2 + 2X  (mod X^2-1, 17)
        a = [1, 1]
        got = _poly_mul_mod(a, a, 2, 17)
        assert got == [2, 2]

    def test_matches_naive_schoolbook(self):
        r, mod = 5, 97
        a = [3, 0, 5, 1, 0]
        b = [2, 7, 0, 4, 1]

        def naive(x, y):
            res = [0] * r
            for i in range(r):
                for j in range(r):
                    res[(i + j) % r] = (res[(i + j) % r] + x[i] * y[j]) % mod
            return res

        assert _poly_mul_mod(a, b, r, mod) == naive(a, b)


class TestAksSmall:
    @pytest.mark.parametrize("n", SMALL_PRIMES[:40])
    def test_small_primes(self, n):
        assert _aks_is_prime(n) is True

    @pytest.mark.parametrize("n", [0, 1, 4, 6, 8, 9, 15, 21, 25, 27, 35, 49, 77, 91])
    def test_small_composites(self, n):
        assert _aks_is_prime(n) is False

    @pytest.mark.parametrize("n", CARMICHAEL[:6])
    def test_carmichael(self, n):
        assert _aks_is_prime(n) is False

    @pytest.mark.parametrize("n", POULET[:5])
    def test_poulet(self, n):
        assert _aks_is_prime(n) is False

    def test_agrees_with_is_prime_below_400(self):
        for n in range(0, 400):
            assert _aks_is_prime(n) is is_prime(n), n

    def test_4digit_prime_direct(self):
        assert _aks_is_prime(7919) is True

    @pytest.mark.slow
    def test_1e9p7_direct(self):
        assert _aks_is_prime(1_000_000_007) is True


class TestHugePreAks:
    def test_smooth_huge_composite_is_fast(self):
        n = 100003 * 10**40
        info = lab(n)
        assert info["path"] == "bigint_trial_or_aks"
        assert info["is_prime"] is False
        assert info["elapsed_ms"] < 50.0

    def test_odd_perfect_power_huge(self):
        n = 3**80  # odd, > 2^64, isqrt ≫ full-trial bound
        assert n.bit_length() > 64
        assert math.isqrt(n) > 25_000_000_000
        assert is_prime(n) is False

    def test_semiprime_caught_by_wheel_bound(self):
        # 10007 < 1e8 wheel bound; product well into AKS-band size.
        n = 10007 * (10**25 + 3)
        assert n >= (1 << 64)
        assert is_prime(n) is False
