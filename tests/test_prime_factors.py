"""Deterministic prime_factors / factorint."""

from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from best_prime.is_prime import is_prime
from best_prime.prime_factors import factorint, prime_factors
from tests.numbers import MR_LIAR, MR_LIAR_FACTORS, P10_9_7, P10_9_9, SEMIPRIME_1E9, SMALL_PRIMES

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
