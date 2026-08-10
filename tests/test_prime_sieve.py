"""Deterministic primes / primerange / prime_count / nth_prime."""

from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from prime_sieve import (
    PRIME_COUNT_MAX_N,
    _LUCY_MAX_V,
    nth_prime,
    prime_count,
    primerange,
    primes,
)
from tests.numbers import SMALL_PRIMES

_HYP = dict(
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)

PI = {
    0: 0,
    1: 0,
    2: 1,
    3: 2,
    4: 2,
    10: 4,
    11: 5,
    100: 25,
    1000: 168,
    10_000: 1229,
    100_000: 9592,
    1_000_000: 78_498,
    5_000_000: 348_513,
    10_000_000: 664_579,
    100_000_000: 5_761_455,
}


class TestPrimes:
    def test_empty_below_two(self):
        assert primes(0) == []
        assert primes(1) == []
        assert primes("1") == []

    def test_ten(self):
        assert primes(10) == [2, 3, 5, 7]
        assert primes("10") == [2, 3, 5, 7]

    def test_matches_small_list(self):
        assert primes(997) == SMALL_PRIMES

    def test_bool_rejected(self):
        with pytest.raises(TypeError):
            primes(True)  # type: ignore[arg-type]


class TestPrimerange:
    def test_half_open(self):
        assert primerange(10, 20) == [11, 13, 17, 19]
        assert primerange(2, 3) == [2]
        assert primerange(2, 2) == []
        assert primerange(0, 2) == []
        assert primerange(14, 17) == []

    def test_low_clamped(self):
        assert primerange(0, 10) == [2, 3, 5, 7]
        assert primerange(1, 11) == [2, 3, 5, 7]

    def test_string(self):
        assert primerange("10", "20") == [11, 13, 17, 19]

    def test_matches_primes_prefix(self):
        assert primerange(2, 1001) == primes(1000)


class TestPrimeCount:
    @pytest.mark.parametrize("n,expect", list(PI.items()))
    def test_known_pi(self, n, expect):
        assert prime_count(n) == expect
        assert prime_count(str(n)) == expect

    def test_matches_len_primes(self):
        for n in (0, 1, 2, 30, 200, 997, 10_000):
            assert prime_count(n) == len(primes(n))

    def test_monotonic(self):
        last = 0
        for n in range(0, 200):
            c = prime_count(n)
            assert c >= last
            last = c

    def test_five_million_is_not_a_cap_on_n(self):
        assert prime_count(5_000_000) == 348_513
        assert PRIME_COUNT_MAX_N == (1 << 64) - 1
        assert _LUCY_MAX_V >= 5_000_000

    def test_over_max_raises_with_n_bound(self):
        with pytest.raises(ValueError, match="supports n <="):
            prime_count(PRIME_COUNT_MAX_N + 1)

    def test_pow2_table(self):
        from prime_sieve import _PI_POW2

        assert prime_count(1 << 10) == _PI_POW2[10]
        assert prime_count(1 << 20) == _PI_POW2[20]
        # 2^32 still fits Lucy (√n = 2^16); checks the OEIS seed table.
        assert prime_count(1 << 32) == _PI_POW2[32]

    def test_lucy_12_digit(self):
        # √(10^12) = 1e6 < Lucy cap — this is Lucy, not Meissel–Lehmer.
        assert prime_count(10**12) == 37_607_912_018

    def test_meissel_lehmer_matches_known(self):
        """Force the Lehmer loops on sizes Lucy would normally take."""
        from prime_sieve import _pi_ml, _reset_ml_state

        known = {
            10_000: 1_229,
            100_000: 9_592,
            1_000_000: 78_498,
            10_000_000: 664_579,
            (1 << 20): 82_025,
        }
        for n, expect in known.items():
            _reset_ml_state()
            assert _pi_ml(n, force_lehmer=True) == expect
            # Public API (Lucy/sieve) still agrees.
            assert prime_count(n) == expect


class TestNthPrime:
    def test_first_five(self):
        assert [nth_prime(k) for k in range(1, 6)] == [2, 3, 5, 7, 11]

    def test_project_euler_7(self):
        assert nth_prime(10_001) == 104_743

    def test_matches_small_list(self):
        for k, p in enumerate(SMALL_PRIMES, start=1):
            assert nth_prime(k) == p

    def test_inverse_of_prime_count(self):
        for k in (1, 2, 5, 25, 168, 1229):
            p = nth_prime(k)
            assert prime_count(p) == k
            assert prime_count(p - 1) == k - 1

    def test_k_rejected(self):
        with pytest.raises(ValueError):
            nth_prime(0)
        with pytest.raises(TypeError):
            nth_prime(True)  # type: ignore[arg-type]


@settings(max_examples=40, **_HYP)
@given(st.integers(min_value=0, max_value=5_000))
def test_pi_matches_sieve_list(n: int):
    assert prime_count(n) == len(primes(n))


@settings(max_examples=30, **_HYP)
@given(st.integers(min_value=1, max_value=500))
def test_nth_matches_list(k: int):
    assert nth_prime(k) == primes(nth_prime(k) + 1)[k - 1]
