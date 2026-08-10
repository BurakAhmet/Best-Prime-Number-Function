"""CLI entry points for the v1.7 prime APIs."""

from __future__ import annotations

import pytest

from prime_cli import (
    divisors_main,
    is_perfect_power_main,
    is_prime_power_main,
    nth_prime_main,
    prev_prime_main,
    prime_count_main,
    prime_factors_main,
    primerange_main,
    primes_main,
    primorial_main,
    totient_main,
)


def _run(fn, *args: str) -> tuple[int, str]:
    from io import StringIO
    import sys

    buf = StringIO()
    old = sys.stdout
    try:
        sys.stdout = buf
        try:
            fn(list(args))
            code = 0
        except SystemExit as exc:
            code = int(exc.code or 0)
    finally:
        sys.stdout = old
    return code, buf.getvalue()


class TestPrimeCli:
    def test_prev_prime(self):
        code, out = _run(prev_prime_main, "14")
        assert code == 0
        assert "RESULT:  13" in out
        assert "TIME:" in out

    def test_prev_prime_k(self):
        code, out = _run(prev_prime_main, "10", "3")
        assert code == 0
        assert "RESULT:  3" in out
        assert "K:       3" in out

    def test_nth_prime(self):
        code, out = _run(nth_prime_main, "5")
        assert code == 0
        assert "RESULT:  11" in out

    def test_prime_count(self):
        code, out = _run(prime_count_main, "10")
        assert code == 0
        assert "RESULT:  4" in out

    def test_primes(self):
        code, out = _run(primes_main, "10")
        assert code == 0
        assert "RESULT:  2 3 5 7" in out
        assert "COUNT:   4" in out

    def test_primerange(self):
        code, out = _run(primerange_main, "10", "20")
        assert code == 0
        assert "RESULT:  11 13 17 19" in out

    def test_prime_factors(self):
        code, out = _run(prime_factors_main, "360")
        assert code == 0
        assert "RESULT:  2 2 2 3 3 5" in out

    def test_is_prime_power_yes(self):
        code, out = _run(is_prime_power_main, "8")
        assert code == 0
        assert "RESULT:  yes" in out

    def test_is_prime_power_no(self):
        code, out = _run(is_prime_power_main, "36")
        assert code == 1
        assert "RESULT:  no" in out

    def test_is_perfect_power(self):
        code, out = _run(is_perfect_power_main, "36")
        assert code == 0
        assert "RESULT:  yes" in out

    def test_totient(self):
        code, out = _run(totient_main, "10")
        assert code == 0
        assert "RESULT:  4" in out

    def test_primorial(self):
        code, out = _run(primorial_main, "7")
        assert code == 0
        assert "RESULT:  210" in out

    def test_divisors(self):
        code, out = _run(divisors_main, "12")
        assert code == 0
        assert "RESULT:  1 2 3 4 6 12" in out
        assert "COUNT:   6" in out

    def test_missing_args_exit_two(self):
        with pytest.raises(SystemExit) as ei:
            prev_prime_main([])
        assert ei.value.code == 2
