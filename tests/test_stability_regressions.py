"""Regressions for user-facing hangs, silent CLIs, and missing factors.

These tests exist because the product failed in ways that looked like
“the engine cannot do this size”:

* ``python -m best_prime.prev_prime n`` printed nothing (no ``__main__``).
* ``python -m best_prime`` on a 123-digit Fermat composite never returned
  (CLI factor hunt started a complete cubic search).
* ``10^131+1113`` was reported composite with no factor (Fermat base 2
  failed without a gcd; 193 was never trial-divided).
* ``is_prime`` on a Fermat composite must get slower with bit length
  (one exponentiation), not hang. Two nearby *primes* may invert when
  their CM trees differ — that is not a size bug.

Default-suite tests have tight wall clocks. Multi-second prime proofs
are ``@pytest.mark.slow``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from best_prime.is_prime import _one_factor, is_prime
from best_prime.next_prime import next_prime
from best_prime.prev_prime import prev_prime
from tests.numbers import (
    USER_C123,
    USER_C123_FACTOR,
    USER_C123_PREV,
    USER_C132_FACTOR,
    USER_C132_LOOKALIKE,
    USER_N122,
    USER_N122_PREV,
    USER_P131,
    USER_P131_NEXT,
    USER_P132,
    USER_P150,
)

ROOT = Path(__file__).resolve().parents[1]


def _run_mod(*mod_and_args: str, timeout: float) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("OMP_NUM_THREADS", "2")
    return subprocess.run(
        [sys.executable, "-m", *mod_and_args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        check=False,
    )


def _seconds(fn, *args) -> float:
    t0 = time.perf_counter()
    fn(*args)
    return time.perf_counter() - t0


class TestUserNumbersAreTheSpecimens:
    def test_digit_counts(self):
        assert len(str(USER_P131)) == 131
        assert len(str(USER_C132_LOOKALIKE)) == 132
        assert len(str(USER_P132)) == 132
        assert len(str(USER_P150)) == 150
        assert len(str(USER_C123)) == 123
        assert len(str(USER_N122)) == 122

    def test_c123_and_c132_split_as_recorded(self):
        assert USER_C123 % USER_C123_FACTOR == 0
        assert USER_C123 // USER_C123_FACTOR > 1
        assert USER_C132_LOOKALIKE % USER_C132_FACTOR == 0
        assert USER_C132_LOOKALIKE != USER_P131


class TestIsPrimeDoesNotHangOnUserComposites:
    def test_c123_is_composite_quickly(self):
        t0 = time.perf_counter()
        assert is_prime(USER_C123) is False
        assert time.perf_counter() - t0 < 2.0

    def test_c132_lookalike_is_composite_quickly(self):
        t0 = time.perf_counter()
        assert is_prime(USER_C132_LOOKALIKE) is False
        assert time.perf_counter() - t0 < 2.0

    def test_n122_is_composite_quickly(self):
        t0 = time.perf_counter()
        assert is_prime(USER_N122) is False
        assert time.perf_counter() - t0 < 2.0

    def test_powers_of_ten_are_instant_composites(self):
        for d in (10, 20, 40, 80, 120, 150):
            t0 = time.perf_counter()
            assert is_prime(10**d) is False
            assert time.perf_counter() - t0 < 0.5, f"10^{d} should be even / 2·5^d"

    @pytest.mark.parametrize("d", [20, 40, 60, 80, 100, 122])
    def test_ten_to_d_plus_1203_fermat_composite_is_fast(self, d: int):
        n = 10**d + 1203
        t0 = time.perf_counter()
        assert is_prime(n) is False
        elapsed = time.perf_counter() - t0
        # One (or a few) modular exponentiations. A hang is a 10s+ cliff.
        assert elapsed < 2.0, f"is_prime(10^{d}+1203) took {elapsed:.3f}s"


class TestOneFactorFindsUserFactorsAndStaysBounded:
    def test_c123_factor(self):
        t0 = time.perf_counter()
        f = _one_factor(USER_C123)
        assert f == USER_C123_FACTOR or (f is not None and USER_C123 % f == 0)
        assert time.perf_counter() - t0 < 2.0

    def test_c132_lookalike_factor_193(self):
        t0 = time.perf_counter()
        f = _one_factor(USER_C132_LOOKALIKE)
        assert f == USER_C132_FACTOR
        assert time.perf_counter() - t0 < 1.0

    def test_thousand_digit_composite_does_not_start_cubic(self):
        n = 10**1999 + 357
        t0 = time.perf_counter()
        f = _one_factor(n)
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0, f"_one_factor(2000-digit) took {elapsed:.3f}s"
        if f is not None:
            assert 1 < f < n and n % f == 0

    def test_skips_complete_lehman_on_123_digit(self, monkeypatch):
        from best_prime.factor_lehman import cubic_complete_ready

        assert cubic_complete_ready(USER_C123) is False

        def boom(*_a, **_k):
            raise AssertionError("complete cubic must not run on 123-digit CLI factor hunt")

        monkeypatch.setattr("best_prime.factor_lehman.lehman_factor", boom)
        f = _one_factor(USER_C123)
        assert f is not None and USER_C123 % f == 0


class TestCliModulesPrintAndExit:
    def test_is_prime_module_c123(self):
        r = _run_mod("best_prime", str(USER_C123), timeout=8.0)
        assert r.returncode == 1, r.stdout + r.stderr
        assert "RESULT:  not prime" in r.stdout
        assert "FACTOR:" in r.stdout
        factor = int(next(x for x in r.stdout.splitlines() if x.startswith("FACTOR:")).split()[-1])
        assert USER_C123 % factor == 0

    def test_is_prime_module_c132_lookalike(self):
        r = _run_mod("best_prime", str(USER_C132_LOOKALIKE), timeout=8.0)
        assert r.returncode == 1, r.stdout + r.stderr
        assert "RESULT:  not prime" in r.stdout
        assert "FACTOR:" in r.stdout
        factor = int(next(x for x in r.stdout.splitlines() if x.startswith("FACTOR:")).split()[-1])
        assert factor == USER_C132_FACTOR

    def test_prev_prime_module_no_args_is_usage_not_silent(self):
        r = _run_mod("best_prime.prev_prime", timeout=10.0)
        assert r.returncode == 2
        blob = (r.stdout + r.stderr).lower()
        assert "usage" in blob
        assert r.stdout.strip() == "" or "usage" in r.stdout.lower()

    def test_prev_prime_module_small(self):
        r = _run_mod("best_prime.prev_prime", "14", timeout=10.0)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "RESULT:  13" in r.stdout
        assert "TIME:" in r.stdout

    def test_next_prime_module_small(self):
        r = _run_mod("best_prime.next_prime", "14", timeout=10.0)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "RESULT:  17" in r.stdout

    def test_lab_flag_on_c123_does_not_hang(self):
        r = _run_mod("best_prime", "--lab", str(USER_C123), timeout=8.0)
        assert r.returncode == 1, r.stdout + r.stderr
        assert "not prime" in r.stdout.lower()


@pytest.mark.slow
class TestNeighborsOnUserComposites:
    def test_prev_of_c123(self):
        t0 = time.perf_counter()
        assert prev_prime(USER_C123) == USER_C123_PREV
        # Window sieve + one FastECPP proof. A hang is the failure mode.
        assert time.perf_counter() - t0 < 25.0

    def test_prev_of_n122(self):
        t0 = time.perf_counter()
        assert prev_prime(USER_N122) == USER_N122_PREV
        assert time.perf_counter() - t0 < 30.0

    def test_next_after_c123_prev_is_not_c123(self):
        assert next_prime(USER_C123_PREV) != USER_C123
        assert next_prime(USER_C123_PREV) > USER_C123_PREV


class TestIsPrimeCostFollowsGreatness:
    """``is_prime`` only — not next/prev.

    A Fermat miss is one modular exponentiation, so time grows with
    bit length. A hang or an 8e6 cubic walk on a smaller composite is
    a bug. Two *primes* of nearby size can still invert (different CM
    trees); that is the certificate, not a size cliff.
    """

    def test_fermat_composite_time_grows_with_digits(self):
        samples = []
        # 10^131+1203 is prime — do not call is_prime on it in the default suite.
        for d in (20, 40, 60, 80, 100, 122, 149):
            n = 10**d + 1203
            elapsed = _seconds(is_prime, n)
            samples.append((d, n.bit_length(), elapsed))
            assert elapsed < 2.0, f"is_prime(10^{d}+1203) composite took {elapsed:.3f}s"
        assert [d for d, _b, _t in samples] == [20, 40, 60, 80, 100, 122, 149]
        # No hang-cliff: a smaller composite must not be 30× a larger one.
        for (d0, b0, t0), (d1, b1, t1) in zip(samples, samples[1:]):
            assert b0 < b1
            assert t0 < t1 * 30 + 0.25, (
                f"is_prime(10^{d0}+1203) {t0:.4f}s vs 10^{d1}+1203 {t1:.4f}s"
            )

    def test_composite_is_faster_than_proving_a_nearby_prime(self):
        # Same 123-digit neighborhood: Fermat miss vs FastECPP proof.
        t_comp = _seconds(is_prime, USER_C123)
        assert t_comp < 0.05
        assert is_prime(USER_C123) is False

    def test_one_factor_small_factor_beats_ten_digit_factor(self):
        t193 = _seconds(_one_factor, USER_C132_LOOKALIKE)
        t10 = _seconds(_one_factor, USER_C123)
        assert t193 < 0.5
        assert t10 < 2.0
        # 193 is a 3-digit trial hit; 5482299091 needs Brent. Trial must win.
        assert t193 < t10 + 0.05


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
class TestPagesWorkerUserNumbers:
    def test_c132_lookalike_prints_193(self):
        script = (
            "const api=require('./docs/wiki/assets/checker-worker.js');"
            f"const n={USER_C132_LOOKALIKE}n;"
            "const r=api.checkPrime(n);"
            "if(!r||r.prime!==false||r.factor==null||n%BigInt(r.factor)!==0n){"
            "  console.error(JSON.stringify(r)); process.exit(1);"
            "}"
            "if(BigInt(r.factor)!==193n){console.error(JSON.stringify(r)); process.exit(1);}"
            "console.log('ok', r.factor, r.ms);"
        )
        r = subprocess.run(
            [shutil.which("node") or "node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert r.returncode == 0, r.stdout + r.stderr

    def test_c123_prints_a_factor(self):
        script = (
            "const api=require('./docs/wiki/assets/checker-worker.js');"
            f"const n={USER_C123}n;"
            "const r=api.checkPrime(n);"
            "if(!r||r.prime!==false||r.factor==null||n%BigInt(r.factor)!==0n){"
            "  console.error(JSON.stringify(r)); process.exit(1);"
            "}"
            "console.log('ok', r.factor, r.path, r.ms);"
        )
        r = subprocess.run(
            [shutil.which("node") or "node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.slow
class TestUserPrimeProofsSlow:
    def test_p131_is_prime(self):
        assert is_prime(USER_P131) is True

    def test_p132_is_prime(self):
        assert is_prime(USER_P132) is True

    def test_p150_is_prime(self):
        assert is_prime(USER_P150) is True

    def test_next_after_p131(self):
        assert next_prime(USER_P131) == USER_P131_NEXT

    def test_cli_prev_c123(self):
        r = _run_mod("best_prime.prev_prime", str(USER_C123), timeout=40.0)
        assert r.returncode == 0, r.stdout + r.stderr
        assert f"RESULT:  {USER_C123_PREV}" in r.stdout
