"""CLI contract: exit codes, default n, --lab / --serial flags."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from is_prime import DEFAULT_N
from tests.numbers import LARGEST_PRIME_LT_2_64, P10_9_7

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "is_prime.py"


def _run(*args: str, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
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


class TestCliExitCodes:
    def test_prime_exits_zero(self):
        r = _run("97")
        assert r.returncode == 0
        assert "prime" in r.stdout
        assert "not prime" not in r.stdout.split("RESULT:", 1)[-1]

    def test_composite_exits_one(self):
        r = _run("100")
        assert r.returncode == 1
        assert "not prime" in r.stdout

    def test_invalid_exits_two(self):
        r = _run("12a")
        assert r.returncode == 2
        assert r.stdout == "" or "invalid" in r.stderr.lower() or "invalid" in r.stdout.lower()

    def test_negative_exits_two(self):
        r = _run("-17")
        assert r.returncode == 2, r.stdout + r.stderr


class TestCliDefault:
    def test_package_default_is_largest_64bit_prime(self):
        assert DEFAULT_N == LARGEST_PRIME_LT_2_64
        assert DEFAULT_N.bit_length() == 64
        assert DEFAULT_N < (1 << 64)

    def test_source_default_string_matches(self):
        src = SCRIPT.read_text(encoding="utf-8")
        assert "DEFAULT_N" in src
        assert "18_446_744_073_709_551_557" in src or str(LARGEST_PRIME_LT_2_64) in src

    @pytest.mark.slow
    def test_no_args_checks_largest_64bit_prime(self):
        r = _run(timeout=120.0)
        assert r.returncode == 0
        assert str(LARGEST_PRIME_LT_2_64) in r.stdout
        assert "RESULT:  prime" in r.stdout
        assert "TIME:" in r.stdout


class TestCliLab:
    def test_lab_midsize_path(self):
        r = _run("--lab", str(P10_9_7))
        assert r.returncode == 0
        assert "PATH:" in r.stdout
        assert "RESULT:    prime" in r.stdout
        assert "ISQRT:" in r.stdout

    def test_lab_json_has_keys(self):
        r = _run("--lab", "--json", "97")
        assert r.returncode == 0
        import json

        info = json.loads(r.stdout)
        for key in ("n", "is_prime", "path", "isqrt", "elapsed_ms", "e2e_ms", "note"):
            assert key in info
        assert info["n"] == 97
        assert info["is_prime"] is True
        assert info["path"] == "python_small"

    def test_serial_flag_accepted(self):
        r = _run("--serial", str(P10_9_7))
        assert r.returncode == 0
        assert "prime" in r.stdout
