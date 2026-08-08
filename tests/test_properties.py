"""Deterministic property-based tests (Hypothesis with derandomize=True)."""

from __future__ import annotations

import math
import os
import sys

from hypothesis import HealthCheck, given, settings, strategies as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from is_prime import is_prime  # noqa: E402


def naive_is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    r = math.isqrt(n)
    for i in range(3, r + 1, 2):
        if n % i == 0:
            return False
    return True


_HYP = dict(
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


@settings(max_examples=300, **_HYP)
@given(st.integers(min_value=0, max_value=10_000))
def test_matches_naive_below_10k(n: int):
    assert is_prime(n, parallel=False) is naive_is_prime(n)


@settings(max_examples=80, **_HYP)
@given(st.integers(min_value=2, max_value=10_000))
def test_serial_equals_parallel_below_10k(n: int):
    assert is_prime(n, parallel=True) is is_prime(n, parallel=False)


@settings(max_examples=120, **_HYP)
@given(st.integers(min_value=2, max_value=10_000), st.integers(min_value=2, max_value=10_000))
def test_products_are_composite(a: int, b: int):
    assert is_prime(a * b) is False


@settings(max_examples=80, **_HYP)
@given(st.integers(min_value=2, max_value=50_000))
def test_squares_are_composite(n: int):
    assert is_prime(n * n) is False


@settings(max_examples=80, **_HYP)
@given(st.integers(min_value=1, max_value=10**12))
def test_evens_greater_than_two_are_composite(n: int):
    even = 2 * n + 2  # 4, 6, … ≤ 2·10^12+2
    assert is_prime(even) is False


@settings(max_examples=60, **_HYP)
@given(st.integers(min_value=0, max_value=10**18))
def test_string_decimal_matches_int(n: int):
    assert is_prime(str(n)) is is_prime(n)


@settings(max_examples=40, **_HYP)
@given(st.integers(min_value=10_000, max_value=2_000_000))
def test_serial_equals_parallel_mid_band(n: int):
    assert is_prime(n, parallel=True) is is_prime(n, parallel=False)
