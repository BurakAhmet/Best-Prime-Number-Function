"""Deterministic cyclotomic proof: small cases stay in the fast suite."""

from __future__ import annotations

import time

from best_prime.is_prime import is_prime
from best_prime.primality_aprcl import aprcl_primality


def test_aprcl_small_prime_and_composite():
    assert aprcl_primality(10007) is True
    assert aprcl_primality(10**9 + 7) is True
    assert aprcl_primality(91) is False
    assert aprcl_primality(15) is False
    assert aprcl_primality(10007 * (10**9 + 7)) is False
    assert aprcl_primality((10**9 + 7) ** 3) is False
    assert is_prime(10007) is True


def test_aprcl_hundred_digit_prime_is_quick():
    # Was about 15 s with one exponentiation per Galois conjugate.
    started = time.perf_counter()
    assert aprcl_primality(10**99 + 289) is True
    assert time.perf_counter() - started < 20
