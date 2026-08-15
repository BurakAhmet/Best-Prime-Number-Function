"""Timing-table bands: PR never runs the 200-digit row."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "benchmarks" / "timing_table.py"
    spec = importlib.util.spec_from_file_location("timing_table", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pr_band_has_p100_not_p200():
    mod = _load()
    pr = [name for name, _n, _e in mod.PR_ROWS]
    assert "P100" in pr
    assert "P200" not in pr
    assert "P150" not in pr
    assert mod.NIGHTLY_EXTRA[0][0] == "P200"
    assert all(name != "P200" for name, _n, _e in mod._rows("pr"))
    assert any(name == "P150" for name, _n, _e in mod._rows("main"))
    assert any(name == "P200" for name, _n, _e in mod._rows("nightly"))
