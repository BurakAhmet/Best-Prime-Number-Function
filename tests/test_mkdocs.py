"""MkDocs library guide: pages exist and (if mkdocs is installed) the site builds."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "guide"
REQUIRED = (
    "index.md",
    "install.md",
    "quickstart.md",
    "api.md",
    "cli.md",
    "engines.md",
    "performance.md",
    "restrictions.md",
    "faq.md",
    "bindings.md",
    "compare.md",
    "cubic-search.md",
)
API_NEEDLES = (
    "is_prime",
    "prime_count",
    "totient",
    "primorial",
    "primerange",
    "Miller",
    "docs/wiki/Library",
)


def test_guide_pages_exist():
    assert (ROOT / "mkdocs.yml").is_file()
    yml = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "docs/guide" in yml
    assert "/guide/" in yml
    for name in REQUIRED:
        path = GUIDE / name
        assert path.is_file(), path
        assert path.read_text(encoding="utf-8").strip(), name
        assert name.replace(".md", "") in yml or name == "index.md"
    api = (GUIDE / "api.md").read_text(encoding="utf-8")
    missing = [n for n in API_NEEDLES if n not in api]
    assert missing == [], f"docs/guide/api.md missing {missing}"


def test_mkdocs_strict_build(tmp_path: Path):
    pytest.importorskip("mkdocs")
    dest = tmp_path / "guide"
    r = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict", "--site-dir", str(dest)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert (dest / "index.html").is_file()
    assert (dest / "api" / "index.html").is_file()
    html = (dest / "api" / "index.html").read_text(encoding="utf-8")
    assert "is_prime" in html
    assert "totient" in html
    assert "primerange" in html
