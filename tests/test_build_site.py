"""Static wiki builder: Acta specimen, OG tags, potd.json."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "docs" / "wiki" / "build_site.py"

markdown = pytest.importorskip("markdown")


def test_parse_latest_potd_and_site_inject(tmp_path: Path):
    spec = import_build_site()
    hof = (ROOT / "docs" / "wiki" / "Hall-of-fame.md").read_text(encoding="utf-8")
    row = spec.parse_latest_potd(hof)
    assert row is not None
    assert row["n"].isdigit()
    assert row["source"] == "prime-of-the-day"

    dest = tmp_path / "site"
    r = subprocess.run(
        [sys.executable, str(BUILD), str(dest)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    index = (dest / "index.html").read_text(encoding="utf-8")
    assert 'class="acta"' in index
    assert row["n"] in index
    assert 'property="og:image"' in index
    assert "assets/og.png" in index
    potd = json.loads((dest / "assets" / "potd.json").read_text(encoding="utf-8"))
    assert potd["n"] == row["n"]
    assert (dest / "assets" / "og.png").is_file()
    assert "lab-orrery" in (dest / "assets" / "checker.js").read_text(encoding="utf-8")
    assert 'href="guide/"' in index
    assert "Library guide" in index or "Guide" in index


def import_build_site():
    import importlib.util

    name = "bpnf_build_site"
    module = sys.modules.get(name)
    if module:
        return module
    s = importlib.util.spec_from_file_location(name, BUILD)
    assert s and s.loader
    module = importlib.util.module_from_spec(s)
    sys.modules[name] = module
    s.loader.exec_module(module)
    return module
