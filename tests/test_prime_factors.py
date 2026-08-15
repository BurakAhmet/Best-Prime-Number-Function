"""Deterministic prime_factors / factorint."""

from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from best_prime.errors import UnsettledFactorError
from best_prime.is_prime import is_prime
from best_prime.prime_factors import factorint, prime_factors
from tests.numbers import (
    MR_LIAR,
    MR_LIAR_FACTORS,
    P10_9_7,
    P10_9_9,
    P40_H1_FRIENDLY,
    SEMIPRIME_1E9,
    SMALL_PRIMES,
)

_HYP = dict(
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


class TestPrimeFactors:
    def test_below_two(self):
        assert prime_factors(0) == []
        assert prime_factors(1) == []
        assert factorint(1) == {}

    def test_small(self):
        assert prime_factors(2) == [2]
        assert prime_factors(12) == [2, 2, 3]
        assert prime_factors(97) == [97]
        assert prime_factors(100) == [2, 2, 5, 5]
        assert prime_factors("12") == [2, 2, 3]
        assert factorint(12) == {2: 2, 3: 1}
        assert factorint(360) == {2: 3, 3: 2, 5: 1}

    def test_prime_powers_of_two(self):
        assert prime_factors(2**10) == [2] * 10
        assert factorint(2**16) == {2: 16}

    def test_product_of_small_primes(self):
        n = 1
        facs = []
        for p in SMALL_PRIMES[:12]:
            n *= p
            facs.append(p)
        assert prime_factors(n) == facs

    def test_semiprime_1e9(self):
        assert prime_factors(SEMIPRIME_1E9) == [P10_9_7, P10_9_9]
        assert factorint(SEMIPRIME_1E9) == {P10_9_7: 1, P10_9_9: 1}

    def test_mr_liar(self):
        got = prime_factors(MR_LIAR)
        assert got == sorted(MR_LIAR_FACTORS)
        prod = 1
        for p in got:
            prod *= p
        assert prod == MR_LIAR

    def test_product_reconstructs(self):
        for n in (2, 12, 97, 360, 1001, 10**6, 2**20 * 3**5 * 7):
            facs = prime_factors(n)
            prod = 1
            for p in facs:
                prod *= p
            assert prod == n
            assert all(is_prime(p) for p in set(facs))
            assert facs == sorted(facs)

    def test_bool_rejected(self):
        with pytest.raises(TypeError):
            prime_factors(True)  # type: ignore[arg-type]

    def test_max_ms_zero_raises_on_large_square(self):
        n = P40_H1_FRIENDLY * P40_H1_FRIENDLY
        with pytest.raises(UnsettledFactorError) as ei:
            prime_factors(n, max_ms=0)
        assert ei.value.leftover > 1
        assert n % ei.value.leftover == 0
        assert ei.value.n == n

    def test_square_factors_without_cap(self):
        n = P40_H1_FRIENDLY * P40_H1_FRIENDLY
        assert prime_factors(n) == [P40_H1_FRIENDLY, P40_H1_FRIENDLY]

    def test_max_ms_none_still_factors_small(self):
        assert prime_factors(97, max_ms=0) == [97]
        assert factorint(12, max_ms=50) == {2: 2, 3: 1}

    def test_ecm_classic(self):
        from best_prime.factor_ecm import ecm_factor

        n = 455839  # 13 × 35065? actually 599 × 761
        g = ecm_factor(n, B1=200, B2=2000, max_curves=20)
        assert g is not None and 1 < g < n and n % g == 0

    def test_montgomery_ecm_finds_p8_on_p131_curve_order(self):
        from best_prime.factor_ecm import ecm_factor

        # Leftover of n+1+t for n=10^130+1113, D=−19 after trial 7²·17.
        rem = 12004801920768307322929171668667466986794717887154861944777911164527598772363331844974638920327241985549465171925430057992153551
        g = ecm_factor(rem, B1=8000, B2=8000, max_curves=8, max_ms=2000)
        assert g is not None and rem % g == 0
        assert g == 57629443 or rem // g == 57629443

    def test_siqs_small_semiprime(self):
        from best_prime.factor_siqs import siqs_factor

        n = 10403  # 101 × 103
        g = siqs_factor(n, fb_bound=50, interval=400)
        assert g is not None and 1 < g < n and n % g == 0
        assert sorted((g, n // g)) == [101, 103]

    def test_factorint_uses_advanced_for_medium(self):
        n = 101 * 103
        assert factorint(n) == {101: 1, 103: 1}


@settings(max_examples=60, **_HYP)
@given(st.integers(min_value=0, max_value=50_000))
def test_factors_multiply_back(n: int):
    facs = prime_factors(n)
    prod = 1
    for p in facs:
        prod *= p
    assert prod == (n if n >= 2 else 1 if n == 1 else 1)
    if n < 2:
        assert facs == []
    else:
        assert prod == n
        d = factorint(n)
        rec = 1
        for p, e in d.items():
            rec *= p**e
        assert rec == n
