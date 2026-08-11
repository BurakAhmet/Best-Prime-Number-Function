"""Regression: Auto-merge must recognize current CI / Determinism check names.

PR #40 renamed CI jobs to ``Tests (<os> / Python X)``. Auto-merge still
looked for ``Tests (Python X)`` and skipped merge. Branch protection
requires a check literally named ``Determinism``, which the matrix cells
do not report.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTO_MERGE = (ROOT / ".github/workflows/auto-merge.yml").read_text(encoding="utf-8")
CI = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
DET = (ROOT / ".github/workflows/determinism.yml").read_text(encoding="utf-8")


def _js_filter_regex(assignment: str) -> re.Pattern[str]:
    match = re.search(
        rf"const {assignment} = runs\.filter\(c => /(.+?)/([a-z]*)\.test\(c\.name\)\)",
        AUTO_MERGE,
    )
    assert match, f"could not find {assignment} regex in auto-merge.yml"
    flags = re.I if "i" in match.group(2) else 0
    return re.compile(match.group(1), flags)


def test_ci_job_name_template_is_cross_platform() -> None:
    assert "Tests (${{ matrix.os }} / Python ${{ matrix.python-version }})" in CI


def test_determinism_workflow_publishes_required_gate_name() -> None:
    assert re.search(r"(?m)^\s+name:\s*Determinism\s*$", DET), (
        "determinism.yml must have a job named exactly Determinism "
        "(branch protection required context)"
    )


def test_auto_merge_recognizes_test_job_names() -> None:
    pattern = _js_filter_regex("testJobs")
    must_match = [
        "Tests (Python 3.12)",
        "Tests (ubuntu-latest / Python 3.9)",
        "Tests (ubuntu-latest / Python 3.12)",
        "Tests (macos-latest / Python 3.12)",
        "Tests (windows-latest / Python 3.12)",
    ]
    must_not = [
        "Lint (ruff + mypy)",
        "Stdlib fallback (no compiler)",
        "Certificate of correctness",
        "Merge if gates green",
        "Repeated-trial determinism (Python 3.12)",
        "Determinism",
    ]
    for name in must_match:
        assert pattern.search(name), f"{pattern.pattern!r} should match {name!r}"
    for name in must_not:
        assert not pattern.search(name), f"{pattern.pattern!r} should not match {name!r}"


def test_auto_merge_recognizes_determinism_and_perf_names() -> None:
    det = _js_filter_regex("detJobs")
    perf = _js_filter_regex("perf")
    for name in (
        "Repeated-trial determinism (Python 3.9)",
        "Repeated-trial determinism (Python 3.12)",
        "Determinism",
    ):
        assert det.search(name), f"determinism regex should match {name!r}"
    assert not det.search("Tests (ubuntu-latest / Python 3.12)")
    assert perf.search("E2E performance vs baseline / base branch")
    assert not perf.search("Tests (ubuntu-latest / Python 3.12)")
