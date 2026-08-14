"""Class-number-1 Atkin–Morain ECPP skeleton."""

from __future__ import annotations

import math

from best_prime.primality_ecpp import ecpp_primality, gk_min_q
from tests.numbers import (
    CARMICHAEL,
    P10_9_7,
    P40_H1_A,
    P40_H1_C,
    P40_H1_FRIENDLY,
    P40_H1_Q,
    P40_H1_T,
    P40_H1_V,
    SMALL_PRIMES,
)


class TestGkMinQ:
    def test_rejects_r_plus_1_window(self):
        # n = (r+1)^4 − 1 ⇒ {n^{1/4}} is just below 1.
        r = 100
        n = (r + 1) ** 4 - 1
        assert math.isqrt(math.isqrt(n)) == r
        x = n**0.25
        q = (r + 1) ** 2 + 1
        assert (r + 1) ** 2 < q <= (x + 1) ** 2
        assert q < gk_min_q(n)
        assert not (q >= gk_min_q(n))

    def test_p40_q_meets_bound(self):
        assert P40_H1_Q >= gk_min_q(P40_H1_FRIENDLY)


class TestP40H1Friendly:
    def test_published_identities(self):
        n = P40_H1_FRIENDLY
        assert n == P40_H1_A**2 + P40_H1_V**2
        assert 4 * n == P40_H1_T**2 + 4 * P40_H1_V**2
        assert n + 1 + P40_H1_T == P40_H1_C * P40_H1_Q
        assert P40_H1_Q >= gk_min_q(n)

    def test_ecpp_true(self):
        n = P40_H1_FRIENDLY
        assert ecpp_primality(n) is True


class TestEcppDecisions:
    def test_modest_primes_never_false(self):
        for p in SMALL_PRIMES + [P10_9_7, 1_000_003]:
            assert ecpp_primality(p) is not False

    def test_composites_never_true(self):
        for n in (9, 15, 25, 91, 121, 561) + CARMICHAEL[:4]:
            assert ecpp_primality(n) is not True

    def test_serial_parallel_same_boolean(self):
        for n in (97, 91, 1_000_003, 9, P10_9_7):
            assert ecpp_primality(n, parallel=True) == ecpp_primality(
                n, parallel=False
            )

    def test_squares_false(self):
        for n in (9, 25, 121, 111**2):
            assert ecpp_primality(n) is False

    def test_below_two_false(self):
        assert ecpp_primality(0) is False
        assert ecpp_primality(1) is False
