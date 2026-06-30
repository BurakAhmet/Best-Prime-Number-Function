"""Deterministic property-based tests (Hypothesis with fixed seed)."""

from __future__ import annotations

import math
import os
import sys

import pytest
from hypothesis import given, settings, strategies as st
from hypothesis import HealthCheck

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


@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
    # Fixed seed → reproducible CI / local runs (deterministic suite)
    derandomize=True,
)
@given(st.integers(min_value=0, max_value=10_000))
def test_matches_naive_below_10k(n: int):
    assert is_prime(n, parallel=False) is naive_is_prime(n)


@settings(max_examples=50, deadline=None, derandomize=True)
@given(st.integers(min_value=2, max_value=10_000))
def test_serial_equals_parallel_below_10k(n: int):
    assert is_prime(n, parallel=True) is is_prime(n, parallel=False)
