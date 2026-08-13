"""Regression: Auto-merge must recognize required CI / Determinism check names.

Branch protection requires:
  - ``Tests (ubuntu-latest / Python 3.12)``
  - ``Determinism`` (gate job; not matrix cells)

PR-lite CI only runs the Linux 3.12 cell; auto-merge must not wait for the
full OS/Python matrix (macOS/Windows/other Pythons).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTO_MERGE = (ROOT / ".github/workflows/auto-merge.yml").read_text(encoding="utf-8")
CI = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
DET = (ROOT / ".github/workflows/determinism.yml").read_text(encoding="utf-8")

# Keep in sync with auto-merge.yml (branch-protection gates only).
REQUIRED_TEST_RE = re.compile(
    r"^Tests\s*\((?:ubuntu-latest\s*/\s*)?Python\s*3\.12\)$",
    re.I,
)
DET_GATE_RE = re.compile(r"^Determinism$", re.I)
PERF_RE = re.compile(r"Performance", re.I)


def test_ci_job_name_template_is_cross_platform() -> None:
    assert "Tests (${{ matrix.os }} / Python ${{ matrix.python-version }})" in CI


def test_ci_has_single_required_test_job() -> None:
    assert "Tests (${{ matrix.os }} / Python ${{ matrix.python-version }})" in CI
    assert "test-docs-skip" not in CI
    assert "Docs/meta-only — required check green" in CI
    assert "plan:" in CI


def test_auto_merge_ignores_skipped_duplicate_required_checks() -> None:
    assert "testJobs.some(succeeded)" in AUTO_MERGE
    assert "detJobs.some(succeeded)" in AUTO_MERGE


def test_ci_tiers_full_matrix_on_main() -> None:
    assert "needs.plan.outputs.full" in CI
    assert "needs.plan.outputs.code" in CI
    assert "if: needs.plan.outputs.full == 'true'" in CI
    assert "if: needs.plan.outputs.code == 'true'" in CI


def test_ci_avoids_double_pytest_on_linux_312() -> None:
    assert 'pytest -q -m "not slow" --cov=best_prime' in CI
    assert CI.count("--cov=best_prime") == 1


def test_ci_attestation_is_main_only_and_lightweight() -> None:
    assert "Certificate of correctness" in CI
    assert "Write attestation from green gates" in CI
    # Must not re-run full pytest inside attestation
    att_section = CI.split("attestation:")[1] if "attestation:" in CI else ""
    assert "pytest" not in att_section


def test_determinism_workflow_publishes_required_gate_name() -> None:
    assert re.search(r"(?m)^\s+name:\s*Determinism\s*$", DET), (
        "determinism.yml must have a job named exactly Determinism "
        "(branch protection required context)"
    )


def test_determinism_tiers_matrix() -> None:
    assert "plan:" in DET
    assert '["3.12"]' in DET
    assert "3.9" in DET


def test_auto_merge_embeds_required_test_regex() -> None:
    # Workflow must define the narrow required-test matcher (not all Tests(*) cells).
    assert "requiredTestRe" in AUTO_MERGE
    assert r"Python\s*3\.12" in AUTO_MERGE or "Python 3.12" in AUTO_MERGE
    # Must not use the old "every Tests(*Python*) cell" gate.
    assert not re.search(
        r"testJobs\s*=\s*runs\.filter\(c\s*=>\s*/\^Tests\\s\*\\\(\.\*Python",
        AUTO_MERGE,
    )


def test_auto_merge_only_requires_linux_312_tests() -> None:
    must_match = [
        "Tests (Python 3.12)",
        "Tests (ubuntu-latest / Python 3.12)",
    ]
    must_not = [
        "Tests (ubuntu-latest / Python 3.9)",
        "Tests (ubuntu-latest / Python 3.10)",
        "Tests (ubuntu-latest / Python 3.11)",
        "Tests (ubuntu-latest / Python 3.13)",
        "Tests (macos-latest / Python 3.12)",
        "Tests (windows-latest / Python 3.12)",
        "Lint (ruff + mypy)",
        "Stdlib fallback (no compiler)",
        "Certificate of correctness",
        "Merge if gates green",
        "Repeated-trial determinism (Python 3.12)",
        "Determinism",
    ]
    for name in must_match:
        assert REQUIRED_TEST_RE.search(name), f"should match {name!r}"
    for name in must_not:
        assert not REQUIRED_TEST_RE.search(name), f"should not match {name!r}"


def test_auto_merge_only_requires_determinism_gate_not_matrix_cells() -> None:
    assert "Determinism" in AUTO_MERGE
    assert DET_GATE_RE.search("Determinism")
    assert not DET_GATE_RE.search("Repeated-trial determinism (Python 3.12)")
    assert not DET_GATE_RE.search("Repeated-trial determinism (Python 3.9)")
    # Workflow must filter by exact gate name, not /determinism/i
    assert re.search(r"/\^Determinism\$/i", AUTO_MERGE)
    assert not re.search(r"detJobs\s*=\s*runs\.filter\(c\s*=>\s*/determinism/i", AUTO_MERGE)


def test_auto_merge_recognizes_perf_names() -> None:
    assert PERF_RE.search("E2E performance vs baseline / base branch")
    assert not PERF_RE.search("Tests (ubuntu-latest / Python 3.12)")
    assert re.search(r"perf\s*=\s*runs\.filter\(c\s*=>\s*/Performance/i", AUTO_MERGE)


def test_ci_change_scope_script_exists() -> None:
    script = ROOT / "scripts/ci_change_scope.sh"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "code=" in text
    assert "full=" in text
    assert "best_prime/" in text
