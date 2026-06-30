#!/usr/bin/env python3
"""Write a CI attestation JSON for the current commit."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "attestation.json")
    sha = os.environ.get("GITHUB_SHA") or git("rev-parse", "HEAD")
    ref = os.environ.get("GITHUB_REF", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    payload = {
        "schema": "best-prime-number-function.attestation/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": sha,
        "git_ref": ref,
        "github_run_id": run_id,
        "checks": {
            "pytest_not_slow": os.environ.get("ATTEST_PYTEST", "unknown"),
            "determinism_script": os.environ.get("ATTEST_DETERMINISM", "unknown"),
            "restriction_linter": os.environ.get("ATTEST_LINT", "unknown"),
        },
        "python_versions": os.environ.get("ATTEST_PYTHONS", ""),
        "notes": "Deterministic is_prime; no stochastic MR. AI-generated project — review before production.",
    }
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
