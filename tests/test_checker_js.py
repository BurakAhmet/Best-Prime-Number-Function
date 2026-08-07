"""Smoke-check the in-browser 30-wheel lab (Pages assets)."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "docs" / "wiki" / "assets" / "checker-worker.js"
UI = ROOT / "docs" / "wiki" / "assets" / "checker.js"
NEAR_2_63 = 9223372036854775783


def test_lab_assets_allow_near_2_63_prime():
    src = WORKER.read_text(encoding="utf-8")
    ui = UI.read_text(encoding="utf-8")
    assert WORKER.is_file() and UI.is_file()
    m = re.search(r"REFUSE_ISQRT\s*=\s*([0-9_]+)n", src)
    assert m, "REFUSE_ISQRT missing in checker-worker.js"
    refuse = int(m.group(1).replace("_", ""))
    x = NEAR_2_63
    y = (x + 1) // 2
    z = x
    while y < z:
        z = y
        y = (y + x // y) // 2
    assert refuse >= z
    assert "Too large here" in ui  # still used for absurd n
    assert "checker-worker.js" in ui


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_checker_worker_self_test():
    r = subprocess.run(
        ["node", str(WORKER), "--self-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "self-test OK" in r.stdout
