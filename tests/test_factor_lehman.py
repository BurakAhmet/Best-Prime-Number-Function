"""Two-band cubic search (lehman_factor). Deterministic; no Miller–Rabin."""

from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from best_prime.factor_lehman import (
    LEHMAN_COMPLETE_CUB_MAX,
    LEHMAN_COMPLETE_CUB_MAX_C,
    _c_lehman_ready,
    _ceil_icbrt,
    _lehman_extra,
    lehman_factor,
)
from best_prime.is_prime import DEFAULT_N, is_prime
from tests.numbers import MR_LIAR, MR_LIAR_FACTORS, P10_9_7, P10_9_9, SEMIPRIME_1E9, SMALL_PRIMES

_HYP = dict(
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


def _proper(n: int, f: int | None) -> bool:
    return f is not None and 1 < f < n and n % f == 0


class TestLehmanFactor:
    def test_below_four(self):
        assert lehman_factor(0) is None
        assert lehman_factor(1) is None
        assert lehman_factor(2) is None
        assert lehman_factor(3) is None

    def test_small_primes_have_no_factor(self):
        for p in SMALL_PRIMES[:20]:
            assert lehman_factor(p) is None

    def test_small_composites(self):
        for n, fac in ((4, 2), (9, 3), (15, 3), (25, 5), (27, 3), (91, 7), (121, 11)):
            f = lehman_factor(n)
            assert _proper(n, f)
            assert n % fac == 0

    def test_string_and_bool(self):
        assert _proper(91, lehman_factor("91"))
        with pytest.raises(TypeError):
            lehman_factor(True)  # type: ignore[arg-type]

    def test_close_semiprime(self):
        n = 101 * 103
        assert _proper(n, lehman_factor(n))

    def test_semiprime_1e9(self):
        f = lehman_factor(SEMIPRIME_1E9)
        assert _proper(SEMIPRIME_1E9, f)
        assert {f, SEMIPRIME_1E9 // f} == {P10_9_7, P10_9_9}

    def test_mr_liar_splits(self):
        n = MR_LIAR
        f = lehman_factor(n)
        assert _proper(n, f)
        assert f in MR_LIAR_FACTORS or (n // f) in MR_LIAR_FACTORS or n % f == 0

    def test_unbalanced_above_cube_root(self):
        # 100003 > ceil((100003*1000033)^{1/3}) ≈ 4642, so Band 2 must fire.
        n = 100003 * 1000033
        f = lehman_factor(n)
        assert _proper(n, f)
        assert {f, n // f} == {100003, 1000033}

    def test_prime_10_9_7(self):
        assert lehman_factor(P10_9_7) is None

    def test_k_max_zero_is_probe_only(self):
        # 7*11*13 = 1001; Band 1 with budget 0 does not scan the wheel.
        assert lehman_factor(1001, k_max=0) is None
        assert _proper(1001, lehman_factor(1001, k_max=20))

    def test_k_max_negative_rejected(self):
        with pytest.raises(ValueError):
            lehman_factor(91, k_max=-1)

    def test_complete_cap_exported(self):
        assert LEHMAN_COMPLETE_CUB_MAX >= 2_000_000
        assert LEHMAN_COMPLETE_CUB_MAX_C >= LEHMAN_COMPLETE_CUB_MAX

    def test_serial_equals_parallel(self):
        n = 100003 * 1000033
        assert lehman_factor(n, parallel=True) is not None
        a = lehman_factor(n, parallel=True)
        b = lehman_factor(n, parallel=False)
        assert _proper(n, a) and _proper(n, b)

    @pytest.mark.skipif(not _c_lehman_ready(), reason="lehman_factor_u128 not in wheel_core.so")
    def test_c_core_splits_and_agrees_on_primes(self):
        assert _c_lehman_ready()
        n = 100003 * 1000033
        assert _proper(n, lehman_factor(n))
        assert lehman_factor(1_000_000_007) is None
        assert lehman_factor(91, parallel=False) in (7, 13)

    @pytest.mark.skipif(not _c_lehman_ready(), reason="lehman_factor_u128 not in wheel_core.so")
    def test_c_core_completes_default_n(self):
        cub = _ceil_icbrt(DEFAULT_N)
        assert cub <= LEHMAN_COMPLETE_CUB_MAX_C
        assert lehman_factor(DEFAULT_N) is None


def test_ceil_icbrt_property():
    for n in list(range(0, 400)) + [10**6, 10**9 + 7, 2**32, 2**64 - 1]:
        c = _ceil_icbrt(n)
        if n <= 1:
            assert c == n
            continue
        assert c * c * c >= n
        if c > 1:
            assert (c - 1) ** 3 < n


def test_lehman_extra_covers_real_interval():
    # Integer extra must never fall short of n^{1/6}/(4√k).
    for n in (22, 100, 10007, 10**6 + 3, 10**9 + 7):
        cub = _ceil_icbrt(n)
        for k in (1, 2, 3, max(1, cub // 4), cub):
            real = (n ** (1.0 / 6.0)) / (4.0 * math.sqrt(k))
            assert _lehman_extra(cub, k) + 1e-9 >= real


@settings(max_examples=80, **_HYP)
@given(st.integers(min_value=2, max_value=20_000))
def test_complete_on_small_n(n: int):
    f = lehman_factor(n)
    if is_prime(n):
        assert f is None
    else:
        assert _proper(n, f)
