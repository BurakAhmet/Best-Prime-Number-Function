"""Unit tests for deterministic next_prime."""

from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from best_prime import next_prime as best_prime_next_prime
from is_prime import _SMALL_LIMIT, is_prime
from next_prime import (
    _TABLE_LIMIT,
    _W30030,
    _align_wheel30030,
    _get_res_30030,
    _get_small_table,
    _sieve_primes_upto,
    next_prime,
)
from tests.numbers import P10_9_7, P10_9_9, P12_DIGIT, SMALL_PRIMES

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "next_prime.py"

_HYP = dict(
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


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


def naive_next_prime(n: int) -> int:
    cand = n + 1
    while not naive_is_prime(cand):
        cand += 1
    return cand


class TestEdgeCases:
    @pytest.mark.parametrize("n,expect", [(0, 2), (1, 2), ("0", 2), ("1", 2)])
    def test_zero_and_one(self, n, expect):
        assert next_prime(n) == expect

    @pytest.mark.parametrize(
        "n,expect",
        [(2, 3), (3, 5), (4, 5), (8, 11), (13, 17), (14, 17), (24, 29), (88, 89), (96, 97)],
    )
    def test_small_known_pairs(self, n, expect):
        assert next_prime(n) == expect

    @pytest.mark.parametrize("n", [-1, -2, -17, "-1", "-999"])
    def test_negative_raises(self, n):
        with pytest.raises(ValueError):
            next_prime(n)

    @pytest.mark.parametrize("bad", ["", "   ", "\t"])
    def test_empty_string_raises(self, bad):
        with pytest.raises(ValueError):
            next_prime(bad)

    @pytest.mark.parametrize("bad", ["12a", "1.5", "0x10", "ten"])
    def test_invalid_string_raises(self, bad):
        with pytest.raises(ValueError):
            next_prime(bad)

    @pytest.mark.parametrize("bad", [3.14, None, [2], (2,)])
    def test_wrong_types_raise(self, bad):
        with pytest.raises(TypeError):
            next_prime(bad)  # type: ignore[arg-type]

    def test_bool_rejected(self):
        with pytest.raises(TypeError):
            next_prime(True)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            next_prime(False)  # type: ignore[arg-type]

    def test_string_whitespace_and_leading_zeros(self):
        assert next_prime("  14  ") == 17
        assert next_prime("00008") == 11
        assert next_prime("+96") == 97

    def test_strictly_after(self):
        for p in SMALL_PRIMES[:40]:
            assert next_prime(p) > p
            assert next_prime(p) != p

    def test_exported_from_best_prime(self):
        assert best_prime_next_prime is next_prime
        assert best_prime_next_prime(14) == 17

    def test_lazy_export_from_is_prime(self):
        import is_prime as ip

        assert ip.next_prime(14) == 17


class TestExhaustiveSmall:
    @pytest.mark.parametrize("n", range(0, 2000))
    def test_matches_naive_0_to_1999(self, n):
        assert next_prime(n) == naive_next_prime(n)

    def test_matches_naive_2000_to_4999(self):
        for n in range(2000, 5000):
            assert next_prime(n) == naive_next_prime(n), n

    def test_after_each_listed_small_prime(self):
        for a, b in zip(SMALL_PRIMES, SMALL_PRIMES[1:]):
            assert next_prime(a) == b
            assert next_prime(a - 1) == a

    def test_table_covers_small_limit(self):
        tbl = _get_small_table()
        assert tbl[0] == 2
        assert tbl[-1] == _TABLE_LIMIT
        assert tbl[-1] > _SMALL_LIMIT
        assert next_prime(_SMALL_LIMIT - 1) == 10007


class TestWheel:
    def test_align_skips_non_coprime(self):
        res = _get_res_30030()
        for n in range(17, 200):
            cand, wi = _align_wheel30030(n)
            assert cand >= n
            assert math.gcd(cand, _W30030) == 1
            assert res[cand % _W30030] == wi

    def test_sieve_helper_matches_small_primes(self):
        got = _sieve_primes_upto(997)
        assert list(got) == SMALL_PRIMES


class TestMidSize:
    def test_twin_around_1e9(self):
        assert next_prime(P10_9_7) == P10_9_9
        assert next_prime(P10_9_7 - 1) == P10_9_7
        assert next_prime(str(P10_9_7)) == P10_9_9

    def test_after_12_digit_prime_is_prime_and_minimal(self):
        p = next_prime(P12_DIGIT)
        assert p > P12_DIGIT
        assert is_prime(p) is True
        # Gap around 12 digits is tiny; prove minimality by is_prime on the range.
        for k in range(P12_DIGIT + 1, p):
            assert is_prime(k) is False

    def test_serial_equals_parallel_mid(self):
        for n in (10_007, 10**6, P10_9_7, P10_9_7 - 1, P12_DIGIT):
            assert next_prime(n, parallel=True) == next_prime(n, parallel=False)


class TestProperties:
    @settings(max_examples=200, **_HYP)
    @given(st.integers(min_value=0, max_value=8_000))
    def test_result_is_prime_and_minimal(self, n: int):
        p = next_prime(n)
        assert is_prime(p) is True
        assert p > n
        for k in range(n + 1, p):
            assert is_prime(k) is False

    @settings(max_examples=40, **_HYP)
    @given(st.integers(min_value=0, max_value=10**12))
    def test_string_decimal_matches_int(self, n: int):
        assert next_prime(str(n)) == next_prime(n)

    @settings(max_examples=30, **_HYP)
    @given(st.integers(min_value=10_000, max_value=2_000_000))
    def test_serial_equals_parallel_mid_band(self, n: int):
        assert next_prime(n, parallel=True) == next_prime(n, parallel=False)


class TestCli:
    def _run(self, *args: str, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.setdefault("OMP_NUM_THREADS", "2")
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )

    def test_next_after_100(self):
        r = self._run("100")
        assert r.returncode == 0, r.stderr
        assert "RESULT:  101" in r.stdout
        assert "TIME:" in r.stdout

    def test_serial_flag(self):
        r = self._run("--serial", "96")
        assert r.returncode == 0, r.stderr
        assert "RESULT:  97" in r.stdout

    def test_missing_n_exits_two(self):
        r = self._run()
        assert r.returncode == 2

    def test_invalid_exits_two(self):
        r = self._run("12a")
        assert r.returncode == 2

    def test_negative_exits_two(self):
        r = self._run("-17")
        assert r.returncode == 2

    def test_help_exits_zero(self):
        r = self._run("--help")
        assert r.returncode == 0
        assert "next-prime" in r.stdout
