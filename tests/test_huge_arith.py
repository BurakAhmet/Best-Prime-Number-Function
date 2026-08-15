"""In-tree Montgomery powmod matches CPython pow on odd moduli."""

from __future__ import annotations

import pytest

from best_prime.huge_arith import HUGE_POW_MIN_BITS, native_available, native_mul, powmod


def test_small_falls_back():
    assert powmod(2, 10, 97) == pow(2, 10, 97)
    assert powmod(3, 0, 97) == 1


def test_matches_pow_above_threshold():
    # 600-bit odd modulus (above HUGE_POW_MIN_BITS). Deterministic.
    n = (1 << 600) + 223
    assert n.bit_length() >= HUGE_POW_MIN_BITS
    assert n & 1
    for a, e in ((2, n - 1), (3, (n + 1) // 4), (5, n // 3), (2, 1), (7, 0)):
        assert powmod(a, e, n) == pow(a, e, n)


@pytest.mark.skipif(not native_available(), reason="huge_arith.so not built")
def test_native_600bit():
    n = (1 << 600) + 223
    assert powmod(2, n - 1, n) == pow(2, n - 1, n)


@pytest.mark.skipif(not native_available(), reason="huge_arith.so not built")
def test_native_p100_fermat():
    n = 10**99 + 289
    assert powmod(2, n - 1, n) == 1
    assert powmod(2, n - 1, n) == pow(2, n - 1, n)


@pytest.mark.skipif(not native_available(), reason="huge_arith.so not built")
def test_native_1000_digit_fermat_matches_pow():
    n = 10**999 + 7
    assert powmod(2, n - 1, n) == pow(2, n - 1, n)


@pytest.mark.skipif(not native_available(), reason="huge_arith.so not built")
def test_native_mul_matches_python():
    # School / Karatsuba / Toom-3 / odd-pad / uneven split.
    sizes = (
        1,
        2,
        8,
        15,
        16,
        17,
        31,
        32,
        33,
        47,
        48,
        49,
        51,
        52,
        53,
        64,
        65,
        80,
        200,
        256,
    )
    for nlimbs in sizes:
        bits = 64 * nlimbs
        a = (1 << (bits - 1)) + 12345 * nlimbs + 7
        b = (1 << (bits - 3)) + 99991 * nlimbs + 11
        got = native_mul(a, b)
        assert got is not None
        assert got == a * b
        ones = (1 << bits) - 1
        assert native_mul(ones, ones) == ones * ones
        assert native_mul(ones, 3) == ones * 3


@pytest.mark.skipif(not native_available(), reason="huge_arith.so not built")
def test_native_p1000_small_exponents():
    n = 10**999 + 7
    for e in (1, 2, 3, 5, 17, 100, 257):
        assert powmod(2, e, n) == pow(2, e, n)


@pytest.mark.skipif(not native_available(), reason="huge_arith.so not built")
def test_native_barrett_path_matches_pow():
    # 220 limbs = 14080 bits, above BARRETT_THRESH (200). Short exponent so CI stays fast.
    n = (1 << 14080) + 223
    assert n.bit_length() >= 14080
    assert n & 1
    for a, e in ((2, 1), (2, 3), (3, 10**5), (5, (1 << 12) + 17), (2, (1 << 11) - 1)):
        assert powmod(a, e, n) == pow(a, e, n)
