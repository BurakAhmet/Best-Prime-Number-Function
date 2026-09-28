"""Deterministic totient / divisors / primorial / Jacobi / CRT."""

from __future__ import annotations

import math
import time

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from best_prime.ntheory import (
    TOTIENT_RANGE_MAX,
    bigomega,
    carmichael_lambda,
    crt,
    divisor_count,
    divisor_sum,
    divisors,
    factors,
    egcd,
    euler_phi,
    gcd,
    is_carmichael,
    is_semiprime,
    is_squarefree,
    jacobi,
    modinv,
    omega,
    primorial,
    radical,
    totient,
    totient_range,
)
from best_prime.prime_sieve import primes

_HYP = dict(
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


def _naive_totient(n: int) -> int:
    if n == 0:
        return 0
    return sum(1 for k in range(1, n + 1) if math.gcd(k, n) == 1)


def _naive_divisors(n: int) -> list[int]:
    return [d for d in range(1, n + 1) if n % d == 0]


class TestGcdEgcd:
    def test_gcd(self):
        assert gcd(12, 18) == 6
        assert gcd(12, 18, 30) == 6
        assert gcd(-12, 18) == 6
        assert gcd() == 0
        assert gcd(7) == 7

    def test_egcd(self):
        g, x, y = egcd(240, 46)
        assert g == 2
        assert 240 * x + 46 * y == g

    def test_modinv(self):
        assert modinv(3, 11) == 4
        assert (3 * modinv(3, 11)) % 11 == 1
        with pytest.raises(ValueError):
            modinv(2, 4)

    def test_crt_coprime(self):
        x = crt([2, 3, 2], [3, 5, 7])
        assert x % 3 == 2 and x % 5 == 3 and x % 7 == 2

    def test_crt_non_coprime(self):
        x = crt([2, 3], [4, 5])  # 2 mod 4, 3 mod 5 → 18
        assert x == 18
        with pytest.raises(ValueError, match="no solution"):
            crt([1, 2], [4, 6])


class TestJacobi:
    def test_known(self):
        assert jacobi(0, 5) == 0
        assert jacobi(1, 5) == 1
        assert jacobi(2, 5) == -1
        assert jacobi(3, 5) == -1
        assert jacobi(4, 5) == 1
        assert jacobi(2, 15) == 1

    def test_even_n_rejected(self):
        with pytest.raises(ValueError):
            jacobi(1, 4)


class TestTotient:
    def test_small(self):
        assert totient(0) == 0
        assert totient(1) == 1
        assert totient(2) == 1
        assert totient(7) == 6
        assert totient(9) == 6
        assert totient(10) == 4
        assert totient(360) == 96
        assert totient("10") == 4
        assert euler_phi is totient

    def test_matches_naive(self):
        for n in range(0, 200):
            assert totient(n) == _naive_totient(n)

    def test_range_matches_single(self):
        tr = totient_range(200)
        assert tr[0] == 0
        for n in range(201):
            assert tr[n] == totient(n)

    def test_range_cap(self):
        assert TOTIENT_RANGE_MAX >= 1_000_000
        with pytest.raises(ValueError):
            totient_range(TOTIENT_RANGE_MAX + 1)


class TestCarmichaelLambda:
    def test_known(self):
        assert carmichael_lambda(1) == 1
        assert carmichael_lambda(8) == 2  # 2^3
        assert carmichael_lambda(15) == 4
        assert carmichael_lambda(16) == 4
        assert carmichael_lambda(21) == 6


class TestDivisors:
    def test_count_sum_list(self):
        assert divisor_count(1) == 1
        assert divisor_count(12) == 6
        assert divisor_sum(12) == 28
        assert divisor_sum(12, 0) == 6
        assert divisors(12) == [1, 2, 3, 4, 6, 12]
        assert divisors("12") == [1, 2, 3, 4, 6, 12]

    def test_matches_naive(self):
        for n in range(1, 150):
            d = _naive_divisors(n)
            assert divisors(n) == d
            assert divisor_count(n) == len(d)
            assert divisor_sum(n) == sum(d)
            assert divisor_sum(n, 2) == sum(x * x for x in d)

    def test_zero_undefined(self):
        with pytest.raises(ValueError):
            divisor_count(0)
        with pytest.raises(ValueError):
            divisors(0)


class TestOmegaRadical:
    def test_omega(self):
        assert omega(1) == 0
        assert omega(12) == 2
        assert bigomega(12) == 3
        assert radical(12) == 6
        assert radical(1) == 1
        assert radical(0) == 0

    def test_squarefree(self):
        assert is_squarefree(1) is True
        assert is_squarefree(6) is True
        assert is_squarefree(12) is False
        assert is_squarefree(4) is False
        assert is_squarefree(0) is False
        assert is_squarefree(30) is True

    def test_semiprime(self):
        assert is_semiprime(4) is True
        assert is_semiprime(6) is True
        assert is_semiprime(8) is False
        assert is_semiprime(9) is True
        assert is_semiprime(7) is False

    def test_carmichael(self):
        assert is_carmichael(561) is True
        assert is_carmichael(1105) is True
        assert is_carmichael(1729) is True
        assert is_carmichael(560) is False
        assert is_carmichael(7) is False
        assert is_carmichael(9) is False


class TestPrimorial:
    def test_primes_le_n(self):
        assert primorial(0) == 1
        assert primorial(1) == 1
        assert primorial(2) == 2
        assert primorial(7) == 210
        assert primorial(8) == 210
        assert primorial(10) == 210
        assert primorial(11) == 2310

    def test_nth(self):
        assert primorial(1, nth=True) == 2
        assert primorial(4, nth=True) == 210
        assert primorial(5, nth=True) == 2310

    def test_matches_product_of_primes(self):
        ps = primes(100)
        assert primorial(100) == math.prod(ps)
        assert primorial(10, nth=True) == math.prod(ps[:10])


@settings(max_examples=40, **_HYP)
@given(st.integers(min_value=1, max_value=400))
def test_totient_hypothesis(n: int):
    assert totient(n) == _naive_totient(n)


def test_factors_lists_every_positive_divisor():
    assert factors(1) == [1]
    assert factors(12) == [1, 2, 3, 4, 6, 12]
    assert factors(97) == [1, 97]
    assert factors(91) == [1, 7, 13, 91]
    assert factors("12") == factors(12)
    with pytest.raises(ValueError):
        factors(0)


def test_user_fifty_digit_factors_complete():
    """The lab number that listed four primes and a 40-digit unsplit cofactor."""
    n = 79185315571712867764058754405752299798556947238073
    t = time.perf_counter()
    got = factors(n)
    assert time.perf_counter() - t < 30
    for p in (3, 13, 24989, 32843, 578907174457, 1152531999403, 3707886428938171):
        assert p in got
    assert got[0] == 1 and got[-1] == n


def test_fifty_digit_cofactor_is_finished():
    """10^49+21 used to list two prime factors and leave a 35-digit cofactor."""
    n = 10**49 + 21
    t = time.perf_counter()
    got = factors(n)
    assert time.perf_counter() - t < 120
    assert 18911 in got
    assert 580056567656257 in got
    assert got[0] == 1 and got[-1] == n


def test_fifty_digit_factors_finish():
    """A 50-digit integer with a small prime factor must not enter the old cube-root search."""
    n = (10**12 + 39) * (10**37 + 9)
    t = time.perf_counter()
    got = factors(n)
    assert time.perf_counter() - t < 20
    assert got[0] == 1 and got[-1] == n and 19 in got
    # Two 25-digit primes. Stage-2 ECM finishes this; it must not walk √n.
    hard = 1000100000000000000000077 * 1000700000000000000000059
    t = time.perf_counter()
    listed = factors(hard)
    assert time.perf_counter() - t < 120
    assert listed[0] == 1 and listed[-1] == hard
    assert 1000100000000000000000077 in listed


def test_ninety_digit_factors_complete():
    """10^89+9 used to stop on a 77-digit composite cofactor."""
    from collections import Counter

    from best_prime.prime_factors import prime_factors

    n = 10**89 + 9
    t = time.perf_counter()
    primes = prime_factors(n)
    assert time.perf_counter() - t < 45
    assert math.prod(primes) == n
    assert Counter(primes)[7] == 3
    for p in (13, 53, 103, 263, 997, 9302577834136361):
        assert p in primes
    prime61 = 1684206015194423425017762911431830297136994720047296251534459
    assert prime61 in primes
    got = factors(n)
    assert got[0] == 1 and got[-1] == n and 343 in got


@settings(max_examples=30, **_HYP)
@given(st.integers(min_value=1, max_value=200))
def test_divisors_hypothesis(n: int):
    d = _naive_divisors(n)
    assert factors(n) == d
    assert divisors(n) == d
    assert divisor_count(n) == len(d)
    assert divisor_sum(n) == sum(d)
