"""Runnable example scripts stay in sync with the public API."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOUR = ROOT / "examples" / "library_tour.py"
BASIC = ROOT / "examples" / "basic_usage.py"


def test_lehman_factor_import_does_not_shadow_is_prime():
    """Sibling lazy loads must not leave best_prime.is_prime as the module."""
    r = subprocess.run(
        [
            sys.executable,
            "-c",
            "from best_prime import lehman_factor, is_prime, factorint; "
            "assert is_prime(17) is True; "
            "assert lehman_factor(91) in (7, 13); "
            "assert factorint(91) == {7: 1, 13: 1}",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_library_tour_covers_every_export():
    text = TOUR.read_text(encoding="utf-8")
    from best_prime import __all__

    missing = [name for name in __all__ if name != "main" and name not in text]
    assert missing == [], f"library_tour.py missing exports: {missing}"


def test_library_tour_runs():
    r = subprocess.run(
        [sys.executable, str(TOUR)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout
    assert "is_prime(17)" in out and "True" in out
    assert "totient(10)" in out
    assert "primorial(7)" in out
    assert "[11, 13, 17, 19]" in out
    assert "is_carmichael(561)" in out
    assert "crt([2, 3, 2], [3, 5, 7])" in out


def test_basic_usage_script():
    r = subprocess.run(
        [sys.executable, str(BASIC)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "totient(10)" in r.stdout
    assert "primorial(7)" in r.stdout
    assert "list(primerange(10, 20))" in r.stdout
