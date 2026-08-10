"""Deterministic is_perfect_power / is_prime_power."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from prime_power import is_perfect_power, is_prime_power
from tests.numbers import SMALL_PRIMES

_HYP = dict(
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


class TestPerfectPower:
    @pytest.mark.parametrize("n", [0, 1, 2, 3, 7, 10, 12, 24, 26])
    def test_non_powers(self, n):
        assert is_perfect_power(n) is False

    @pytest.mark.parametrize("n", [4, 8, 9, 16, 25, 27, 32, 36, 49, 64, 81, 100, 121, 128, 243])
    def test_powers(self, n):
        assert is_perfect_power(n) is True

    def test_large_square(self):
        assert is_perfect_power(10**6) is True
        assert is_perfect_power((10**6 + 3) ** 2) is True
        assert is_perfect_power(2**64) is True  # even; 2^64 is a square

    def test_string(self):
        assert is_perfect_power("36") is True
        assert is_perfect_power("37") is False


class TestPrimePower:
    def test_primes_are_prime_powers(self):
        for p in SMALL_PRIMES[:30]:
            assert is_prime_power(p) is True
            assert is_perfect_power(p) is False

    @pytest.mark.parametrize("n", [4, 8, 9, 16, 25, 27, 32, 49, 81, 125, 128])
    def test_p_to_k(self, n):
        assert is_prime_power(n) is True
        assert is_perfect_power(n) is True

    @pytest.mark.parametrize("n", [0, 1, 6, 12, 18, 24, 36, 48, 100, 144])
    def test_not_prime_power(self, n):
        assert is_prime_power(n) is False

    def test_36_is_perfect_not_prime_power(self):
        assert is_perfect_power(36) is True
        assert is_prime_power(36) is False

    def test_string(self):
        assert is_prime_power("8") is True
        assert is_prime_power("12") is False


@settings(max_examples=40, **_HYP)
@given(st.integers(min_value=2, max_value=200), st.integers(min_value=2, max_value=8))
def test_constructed_powers(a: int, b: int):
    n = a**b
    assert is_perfect_power(n) is True
    # 4^2 = 16 = 2^4, so the base need only be a prime power, not a prime.
    assert is_prime_power(n) is is_prime_power(a)
