"""FastECPP skeleton: computed H_D, Goldwasser–Kilian, no AKS."""

from __future__ import annotations

import pytest

from best_prime.primality_ecpp import ecpp_primality
from best_prime.primality_fastecpp import (
    FASTECPP_MAX_BITS,
    FASTECPP_MIN_BITS,
    fastecpp_primality,
    scaled_batch,
)
from tests.numbers import (
    CARMICHAEL,
    P100_DIGIT,
    P300_DIGIT,
    P500_DIGIT,
    P1000_DIGIT,
    SMALL_PRIMES,
)


class TestFastEcppBand:
    def test_window_covers_p100_not_default_n(self):
        assert P100_DIGIT.bit_length() >= FASTECPP_MIN_BITS
        assert P100_DIGIT.bit_length() <= FASTECPP_MAX_BITS
        assert (10**44 + 31).bit_length() < FASTECPP_MIN_BITS

    def test_window_covers_m2_m3_fixtures(self):
        for n in (P300_DIGIT, P500_DIGIT, P1000_DIGIT):
            assert FASTECPP_MIN_BITS <= n.bit_length() <= FASTECPP_MAX_BITS
        assert P300_DIGIT == 10**299 + 669
        assert P500_DIGIT == 10**499 + 153
        assert P1000_DIGIT == 10**999 + 7

    def test_huge_batch_is_one(self):
        assert scaled_batch(P1000_DIGIT.bit_length()) == 32
        assert scaled_batch(3_501) == 1
        assert scaled_batch(33_220) == 1


class TestFastEcppSmall:
    def test_proves_59_via_existing_small_h(self):
        # Below FASTECPP_MIN_BITS the skeleton reuses transcribed H_D.
        assert ecpp_primality(59, max_h=1) is None
        assert fastecpp_primality(59) is True

    def test_modest_primes_never_false(self):
        for p in SMALL_PRIMES[:20] + [1_000_003]:
            assert fastecpp_primality(p) is not False

    def test_composites_never_true(self):
        for n in (9, 15, 25, 91, 121, 561) + CARMICHAEL[:3]:
            assert fastecpp_primality(n) is not True

    def test_serial_parallel_same_boolean(self):
        for n in (59, 97, 91, 9):
            assert fastecpp_primality(n, parallel=True) == fastecpp_primality(
                n, parallel=False
            )


@pytest.mark.slow
def test_p100_digit_fastecpp():
    """General 100-digit prime — M1 gate. Engine API only (not AKS)."""
    assert P100_DIGIT == 10**99 + 289
    assert fastecpp_primality(P100_DIGIT) is True


@pytest.mark.slow
def test_p300_digit_fastecpp():
    """General 300-digit prime — M2 gate (~15 min on this machine)."""
    assert P300_DIGIT == 10**299 + 669
    assert fastecpp_primality(P300_DIGIT) is True


@pytest.mark.slow
def test_p500_digit_fastecpp():
    """General 500-digit prime — M2 gate (same engine; longer downrun)."""
    assert P500_DIGIT == 10**499 + 153
    assert fastecpp_primality(P500_DIGIT) is True


@pytest.mark.slow
def test_p1000_digit_fastecpp():
    """General 1000-digit prime — M3 gate (same engine; longer downrun)."""
    assert P1000_DIGIT == 10**999 + 7
    assert fastecpp_primality(P1000_DIGIT) is True
