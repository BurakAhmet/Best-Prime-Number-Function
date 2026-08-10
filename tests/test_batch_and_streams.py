"""Batch is_prime, next/prev streams, prime_count ceiling."""

from __future__ import annotations

import pytest

from best_prime.is_prime import is_prime
from best_prime.next_prime import NEXT_PRIME_SIEVE_ISQRT_MAX, next_prime, next_primes
from best_prime.prev_prime import prev_prime, prev_primes
from best_prime.prime_sieve import PRIME_COUNT_MAX_N, prime_count


class TestBatchIsPrime:
    def test_list(self):
        assert is_prime([17, 18, 19, 1, 0]) == [True, False, True, False, False]

    def test_tuple(self):
        assert is_prime((2, 3, 4)) == [True, True, False]

    def test_numpy_array(self):
        np = pytest.importorskip("numpy")
        out = is_prime(np.array([17, 18, 19]))
        assert list(out) == [True, False, True]
        assert getattr(out, "dtype", None) is not None

    def test_scalar_still_bool(self):
        assert is_prime(17) is True
        assert is_prime(18) is False


class TestStreams:
    def test_next_primes_finite(self):
        assert list(next_primes(14, 3)) == [17, 19, 23]
        assert list(next_primes(14, 3)) == [
            next_prime(14, 1),
            next_prime(14, 2),
            next_prime(14, 3),
        ]

    def test_prev_primes_finite(self):
        assert list(prev_primes(14, 2)) == [13, 11]
        assert list(prev_primes(10, 3)) == [7, 5, 3]

    def test_prev_primes_unbounded_stops_at_two(self):
        assert list(prev_primes(8)) == [7, 5, 3, 2]

    def test_sieve_bound_exported(self):
        assert NEXT_PRIME_SIEVE_ISQRT_MAX == 2_000_000


class TestPrimeCountCeiling:
    def test_max_constant(self):
        assert PRIME_COUNT_MAX_N == (1 << 64) - 1

    def test_above_ceiling_raises(self):
        with pytest.raises(ValueError, match="PRIME_COUNT_MAX_N"):
            prime_count(PRIME_COUNT_MAX_N + 1)

    def test_small(self):
        assert prime_count(10) == 4
