"""Deterministic prev_prime."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from next_prime import next_prime
from prev_prime import prev_prime
from prime_sieve import primes
from tests.numbers import P10_9_7, P10_9_9, SMALL_PRIMES

_HYP = dict(
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


class TestPrevPrime:
    def test_small_known(self):
        assert prev_prime(3) == 2
        assert prev_prime(10) == 7
        assert prev_prime(10, 3) == 3
        assert prev_prime(14) == 13
        assert prev_prime(17) == 13
        assert prev_prime(100) == 97
        assert prev_prime("10") == 7

    def test_kth_from_list(self):
        ps = SMALL_PRIMES
        # prev_prime(p_{i+1}) == p_i; prev_prime(p_n, k) == p_{n-k}
        for i in range(1, len(ps)):
            assert prev_prime(ps[i]) == ps[i - 1]
        assert prev_prime(ps[10], 5) == ps[5]

    def test_inverse_of_next(self):
        for p in SMALL_PRIMES[1:40]:
            assert next_prime(prev_prime(p)) == p
            assert prev_prime(next_prime(p)) == p

    def test_no_prime_below_two(self):
        for n in (0, 1, 2):
            with pytest.raises(ValueError):
                prev_prime(n)
        with pytest.raises(ValueError):
            prev_prime(5, 3)  # primes < 5 are 3, 2 only

    def test_k_rejected(self):
        with pytest.raises(ValueError):
            prev_prime(10, 0)
        with pytest.raises(TypeError):
            prev_prime(10, True)  # type: ignore[arg-type]

    def test_mid_size(self):
        assert prev_prime(P10_9_9) == P10_9_7
        assert prev_prime(P10_9_9, 1) == P10_9_7
        assert prev_prime(P10_9_7 + 1) == P10_9_7

    def test_serial_equals_parallel(self):
        for n in (100, 10_007, P10_9_7):
            assert prev_prime(n, parallel=True) == prev_prime(n, parallel=False)


@settings(max_examples=80, **_HYP)
@given(st.integers(min_value=3, max_value=3_000), st.integers(min_value=1, max_value=8))
def test_prev_kth_matches_list(n: int, k: int):
    ps = [p for p in primes(n - 1)]
    if len(ps) < k:
        with pytest.raises(ValueError):
            prev_prime(n, k)
    else:
        assert prev_prime(n, k) == ps[-k]
