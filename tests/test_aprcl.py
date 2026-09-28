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


def test_hundred_digit_prime_uses_aprcl_not_fastecpp():
    from best_prime.is_prime import is_prime, lab

    report = lab(10**99 + 289)
    assert report["is_prime"] is True
    assert report["path"] == "bigint_aprcl"
    assert is_prime(10**99 + 289) is True


def test_aprcl_ladder_covers_5000_digit_numbers():
    """The prepared modulus clears sqrt(n) for every 5000-digit integer."""
    import math

    from best_prime.primality_aprcl import _choose_R, _modulus

    old_s, _qs = _modulus(12252240)
    # The previous ladder stopped at lcm(1..17), whose square is 1026 digits.
    assert _choose_R(old_s * old_s - 1) == 12252240
    assert _choose_R(old_s * old_s) == 73513440
    n = 10**4999
    R = _choose_R(n)
    assert R is not None
    s, _qs = _modulus(R)
    assert s > math.isqrt(n)


def test_wider_modulus_rejects_a_multiple_of_its_prime():
    """A 1100-digit multiple of an Euclidean prime is composite, not unsettled."""
    from best_prime.primality_aprcl import _modulus

    _s, qs = _modulus(73513440)
    assert aprcl_primality(qs[-1] * (10**1099 + 73)) is False


def test_aprcl_hundred_digit_prime_is_quick():
    # Was about 15 s with one exponentiation per Galois conjugate.
    started = time.perf_counter()
    assert aprcl_primality(10**99 + 289) is True
    assert time.perf_counter() - started < 20
