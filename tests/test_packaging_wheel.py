"""Regression: published artifacts must be platform wheels with a native core.

v1.11.0 cibuildwheel emitted ``py3-none-any`` (optional compile skipped) and
the slim Dockerfile lacked ``libc6-dev``, so GHCR / release assets failed.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_has_libc_headers() -> None:
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "libc6-dev" in text
    assert "gcc" in text
    assert "BEST_PRIME_REQUIRE_NATIVE=1" in text


def test_setup_py_forces_native_platform_wheels() -> None:
    text = (ROOT / "setup.py").read_text(encoding="utf-8")
    assert "BEST_PRIME_REQUIRE_NATIVE" in text
    assert "BEST_PRIME_PORTABLE" in text
    assert "root_is_pure" in text
    assert '"py3", "none"' in text or "'py3', 'none'" in text
    assert "def run(self)" in text
    assert "-march=native" in text  # local builds may still use it
    assert "PORTABLE" in text


def test_publish_pypi_builds_manylinux_not_cibuildwheel_any() -> None:
    text = (ROOT / ".github/workflows/publish-pypi.yml").read_text(encoding="utf-8")
    assert "BEST_PRIME_REQUIRE_NATIVE=1" in text
    assert "auditwheel repair" in text
    assert "manylinux_2_28" in text
    assert "none-any" in text  # the assertion that rejects it
