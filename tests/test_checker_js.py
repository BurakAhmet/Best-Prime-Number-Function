"""Smoke-check the in-browser 30-wheel lab (Pages assets)."""
from __future__ import annotations

import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "docs" / "wiki" / "assets" / "checker-worker.js"
UI = ROOT / "docs" / "wiki" / "assets" / "checker.js"
OG = ROOT / "docs" / "wiki" / "assets" / "og.png"
HOF = ROOT / "docs" / "wiki" / "Hall-of-fame.md"
NEAR_2_63 = 9223372036854775783


def test_lab_assets_allow_near_2_63_prime():
    src = WORKER.read_text(encoding="utf-8")
    ui = UI.read_text(encoding="utf-8")
    assert WORKER.is_file() and UI.is_file()
    m = re.search(r"TRIAL_SOFT_ISQRT\s*=\s*([0-9_]+)n", src)
    assert m, "TRIAL_SOFT_ISQRT missing in checker-worker.js"
    soft = int(m.group(1).replace("_", ""))
    x = NEAR_2_63
    y = (x + 1) // 2
    z = x
    while y < z:
        z = y
        y = (y + x // y) // 2
    assert soft >= z
    assert "ecmFactor" in src
    assert "COFACTOR_TRIAL_ISQRT" in src
    assert "Montgomery ECM" in ui or "ECM" in ui
    assert "checker-worker.js" in ui
    assert "lab-orrery" in ui
    assert "lab-stage" in ui
    assert 'data-phase="ecm"' in ui
    assert "viz-ecm-path" in ui
    assert "getPointAtLength" in ui
    assert "Math.sin(t * Math.PI)" not in ui
    assert "factorRows" in ui
    assert "Download SVG" in ui
    assert "WHEEL30" in ui
    assert "data-res=" in ui
    assert "extractFactor" in src
    assert "emit(onTick" in src or "function emit(" in src


def test_og_png_is_social_card():
    data = OG.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    assert (width, height) == (1200, 630)


def test_hall_of_fame_has_latest_potd_row():
    text = HOF.read_text(encoding="utf-8")
    start = text.find("<!-- potd-log:start -->")
    end = text.find("<!-- potd-log:end -->")
    assert 0 <= start < end
    block = text[start:end]
    assert re.search(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*`?\d+`?", block)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_checker_worker_self_test():
    r = subprocess.run(
        ["node", str(WORKER), "--self-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "self-test OK" in r.stdout


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_checker_worker_hard55_pocklington() -> None:
    """10^54+31: hostile n−1, proven via ECM + Pocklington in the Pages worker."""
    script = (
        "const api=require('./docs/wiki/assets/checker-worker.js');"
        "const n=1000000000000000000000000000000000000000000000000000031n;"
        "const r=api.checkPrime(n);"
        "if(!r || r.prime!==true || r.path!=='n-1-pocklington'){"
        "  console.error(JSON.stringify(r)); process.exit(1);"
        "}"
        "console.log('hard55 OK', r.path, r.ms);"
    )
    r = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
