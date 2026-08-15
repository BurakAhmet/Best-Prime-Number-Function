"""Standalone scripts/verify_cert.py: no best_prime import, arithmetic only."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from best_prime.certificate import dump_certificate, primality_certificate, write_certificate
from tests.numbers import P40_H1_FRIENDLY

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_cert.py"
COMBINED_BLS_PRIME = 10159


def _run_script(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def test_script_source_is_independent():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "import best_prime" not in text
    assert "from best_prime" not in text
    assert "import random" not in text
    assert "numpy" not in text.lower()


def test_pratt_round_trip(tmp_path: Path):
    cert = primality_certificate(17)
    path = tmp_path / "17.json"
    write_certificate(cert, path)
    r = _run_script(str(path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "verified=True" in r.stdout


def test_composite_round_trip(tmp_path: Path):
    cert = primality_certificate(91)
    path = tmp_path / "91.json"
    write_certificate(cert, path)
    r = _run_script(str(path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "verified=True" in r.stdout


def test_ecpp_p40_round_trip(tmp_path: Path):
    cert = primality_certificate(P40_H1_FRIENDLY, kind="ecpp")
    path = tmp_path / "p40.json"
    write_certificate(cert, path)
    r = _run_script(str(path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "verified=True" in r.stdout


def test_bls_combined_round_trip(tmp_path: Path):
    cert = primality_certificate(COMBINED_BLS_PRIME, kind="bls")
    path = tmp_path / "bls.json"
    write_certificate(cert, path)
    r = _run_script(str(path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "verified=True" in r.stdout


def test_stdin_pipe():
    cert = primality_certificate(17)
    r = _run_script("-", stdin=dump_certificate(cert))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "verified=True" in r.stdout


def test_tampered_rejected(tmp_path: Path):
    cert = primality_certificate(17)
    cert["witness"] = 1
    path = tmp_path / "bad.json"
    write_certificate(cert, path)
    r = _run_script(str(path))
    assert r.returncode == 1
    assert "verified=False" in r.stdout


def test_cli_json_then_verify():
    from io import StringIO
    import contextlib

    from best_prime.prime_cli import primality_certificate_main

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        with pytest.raises(SystemExit) as ei:
            primality_certificate_main(["--json", "17"])
    assert ei.value.code == 0
    payload = json.loads(buf.getvalue())
    assert payload["kind"] == "pratt"
    r = _run_script("-", stdin=buf.getvalue())
    assert r.returncode == 0, r.stdout + r.stderr
