"""Shared pytest fixtures and markers for Best-Prime-Number-Function."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "slow: multi-second 64-bit / multi-limb full trial (skipped by default CI)",
    )


@pytest.fixture(scope="session")
def c_core_available() -> bool:
    from is_prime import _load_c_core

    return bool(_load_c_core())


@pytest.fixture(scope="session")
def omp_threads() -> int:
    raw = os.environ.get("OMP_NUM_THREADS") or os.environ.get("NUMBA_NUM_THREADS")
    if raw:
        return max(1, int(raw))
    return os.cpu_count() or 1
