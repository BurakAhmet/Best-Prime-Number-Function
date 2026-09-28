"""Regression suite for prime_factors / factors across widths.

These lock the complete factorization, not one tuned example. A later
commit that brings back a digit-band cutoff or a long n±1 hunt on a
prime cofactor fails here.
"""

from __future__ import annotations

import math
import time

import pytest

from best_prime.errors import UnsettledFactorError
from best_prime.ntheory import factors
from best_prime.prime_factors import prime_factors

# (label, n, prime factors with multiplicity, seconds the suite allows)
_CASES = (
    ("two digits", 91, (7, 13), 2),
    (
        "50 digits",
        10**49 + 21,
        (18911, 11009568919, 580056567656257, 82802765617112334317),
        30,
    ),
    (
        "50-digit specimen",
        79185315571712867764058754405752299798556947238073,
        (3, 13, 24989, 32843, 578907174457, 1152531999403, 3707886428938171),
        30,
    ),
    (
        "90 digits",
        10**89 + 9,
        (
            7,
            7,
            7,
            13,
            53,
            103,
            263,
            997,
            9302577834136361,
            1684206015194423425017762911431830297136994720047296251534459,
        ),
        40,
    ),
    (
        # 91 digits. The 56-digit prime is 186 bits: the old factor path
        # proved it with a long n±1 search (~13 s here, minutes in the
        # browser) while the 203-bit prime inside 10^89+9 skipped that.
        "91 digits",
        10**90 + 9,
        (
            28511929,
            3533942033,
            131316266047656409,
            75578009974633661101991422665652594983985823897845085993,
        ),
        120,
    ),
    (
        "91 digits, smaller factors",
        10**90 + 3,
        (
            166303,
            403895669461,
            8974986752701,
            1658810987591830795547164323164711490089752199766030492869341,
        ),
        40,
    ),
)


@pytest.mark.parametrize(
    ("label", "n", "expected", "limit_s"),
    _CASES,
    ids=[row[0] for row in _CASES],
)
def test_prime_factors_complete(label: str, n: int, expected: tuple[int, ...], limit_s: int):
    del label
    started = time.perf_counter()
    got = prime_factors(n)
    elapsed = time.perf_counter() - started
    assert got == list(expected)
    assert math.prod(got) == n
    assert elapsed < limit_s


@pytest.mark.parametrize(
    ("label", "n", "expected", "limit_s"),
    _CASES,
    ids=[row[0] for row in _CASES],
)
def test_factors_lists_every_divisor(label: str, n: int, expected: tuple[int, ...], limit_s: int):
    del label, limit_s
    got = factors(n)
    assert got[0] == 1 and got[-1] == n
    for prime in expected:
        assert prime in got
    # Divisors are exactly the products of the prime factorization.
    built = [1]
    counted: dict[int, int] = {}
    for prime in expected:
        counted[prime] = counted.get(prime, 0) + 1
    for prime, exp in counted.items():
        step = []
        power = 1
        for _ in range(exp):
            power *= prime
            step.extend(d * power for d in built)
        built.extend(step)
    built.sort()
    assert got == built


# 4405…5209. After 103 and an 11-digit factor, the cofactor is 79 digits
# and its smallest prime factor is 31 digits. That factor is σ=484 at
# B1=250_000. A 16-curve sample at that bound never reaches it.
_USER_91 = 4405534351621172144485300162991104082034261209371735440164784129999970703283215812210875209
_USER_91_FACTORS = (
    103,
    24389542339,
    1185427688742314546183690475871,
    1479389899150408870626090235887201665115900796187,
)


def test_user_91_digit_reaches_the_31_digit_curve():
    from best_prime.factor_ecm import ecm_one_curve
    from best_prime.prime_factors import _ecm_ladder

    cofactor = _USER_91 // 103 // 24389542339
    started = time.perf_counter()
    found = ecm_one_curve(cofactor, 484, 250_000, 500_000)
    assert time.perf_counter() - started < 15
    assert found is not None and cofactor % found == 0
    assert min(found, cofactor // found) == _USER_91_FACTORS[2]
    row = [item for item in _ecm_ladder(cofactor.bit_length()) if item[0] == 250_000]
    assert row and row[0][1] >= 500_000 and row[0][2] >= 479
    assert math.prod(_USER_91_FACTORS) == _USER_91


@pytest.mark.slow
def test_user_91_digit_factors_completely():
    started = time.perf_counter()
    got = prime_factors(_USER_91)
    assert time.perf_counter() - started < 900
    assert got == list(_USER_91_FACTORS)
    assert math.prod(got) == _USER_91


def test_max_ms_still_stops_a_hard_semiprime():
    """A cap must return. It must not walk up to the square root."""
    hard = 1000100000000000000000077 * 1000700000000000000000059
    started = time.perf_counter()
    try:
        listed = prime_factors(hard, max_ms=4_000)
    except UnsettledFactorError as exc:
        assert math.prod(exc.found) * exc.leftover == hard
        listed = None
    assert time.perf_counter() - started < 20
    if listed is not None:
        assert math.prod(listed) == hard
