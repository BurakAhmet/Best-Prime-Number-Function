"""Unit tests for the Copilot Optimization-round issue body."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "optimize_round_issue", ROOT / "scripts" / "optimize_round_issue.py"
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


def test_round_body_includes_catalog_and_copilot_brief():
    md = mod.build(
        {
            "sha": "abc1234",
            "omp": "2",
            "hard": [
                {
                    "case": "DEFAULT_N",
                    "n": 18446744073709551557,
                    "path": "u64_wheel_c",
                    "elapsed_ms": 800,
                }
            ],
            "e2e": {"results": [{"case": "small prime", "n": 97, "e2e_ms": 0.2}]},
        },
        {
            "winner": None,
            "tried": [
                {
                    "id": "tile-32k",
                    "knobs": {"tile_bytes": 32768},
                    "geomean_ratio": 0.99,
                    "win": False,
                }
            ],
        },
        "https://example.test/run",
    )
    assert "Copilot" in md
    assert "tile-32k" in md
    assert "DEFAULT_N" in md
    assert "F1–F13" in md or "F1-F13" in md
    assert "do not merge" in md.lower() or "Do **not** merge" in md
    assert "https://example.test/run" in md
