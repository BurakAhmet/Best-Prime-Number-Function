"""Unit tests for the Optimize hunt verdict (no gcc / .so required)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "optimize_hunt", ROOT / "scripts" / "optimize_hunt.py"
)
hunt = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(hunt)


def _case(*, ratio: float, pair_wins: int = 3, pairs: int = 3, ok: bool = True, name="x"):
    return {
        "case": name,
        "ratio": ratio,
        "pair_wins": pair_wins,
        "pairs": pairs,
        "answers_ok": ok,
        "orig_mean_ms": 100.0,
        "cand_mean_ms": 100.0 * ratio,
    }


def test_decide_rejects_answer_mismatch():
    rows = [_case(ratio=0.8, ok=False, name="bad")]
    d = hunt.decide(rows)
    assert d["win"] is False
    assert any("answer" in r for r in d["reasons"])


def test_decide_rejects_noise_sized_delta():
    # 2% across the board is inside the noise gate.
    rows = [_case(ratio=0.98, name=n) for n, *_ in hunt.HARD]
    d = hunt.decide(rows)
    assert d["win"] is False


def test_decide_rejects_one_case_regression():
    rows = [
        _case(ratio=0.80, name="a"),
        _case(ratio=0.80, name="b"),
        _case(ratio=0.80, name="c"),
        _case(ratio=1.10, name="d"),
    ]
    d = hunt.decide(rows)
    assert d["win"] is False
    assert any("regress" in r for r in d["reasons"])


def test_decide_accepts_clear_same_machine_win():
    rows = [
        _case(ratio=0.88, name="a"),
        _case(ratio=0.90, name="b"),
        _case(ratio=0.92, name="c"),
        _case(ratio=0.91, name="d"),
    ]
    d = hunt.decide(rows)
    assert d["win"] is True
    assert d["n_faster"] >= 2
    assert d["geomean_ratio"] < 0.94


def test_catalog_skips_known_failures():
    ids = {c["id"] for c in hunt.CANDIDATES}
    joined = " ".join(ids).lower()
    assert "210" not in joined
    assert "16-way" not in joined
    for c in hunt.CANDIDATES:
        knobs = hunt.knobs_of(c)
        # Tiling *all* primes (pmax >= 8192) loses; default 4096 is the
        # 12-thread L1 cutoff. Catalog pmax tweaks stay at or below that.
        assert knobs["tile_p_max"] <= hunt.DEFAULTS["tile_p_max"]
        assert knobs["tile_bytes"] >= 8192


def test_apply_regex_roundtrip(tmp_path, monkeypatch):
    src = (ROOT / "scripts" / "generate_wheel_core_c.py").read_text(encoding="utf-8")
    dest = tmp_path / "generate_wheel_core_c.py"
    dest.write_text(src, encoding="utf-8")
    monkeypatch.setattr(hunt, "GEN", dest)

    def fake_generate(*_a, **_k):
        return None

    monkeypatch.setattr(hunt.subprocess, "check_call", fake_generate)
    hunt.apply_knobs({"tile_bytes": 32768, "tile_p_max": 384, "parallel_seg_min": 20_000_000})
    out = dest.read_text(encoding="utf-8")
    assert "TILE_BYTES = 32768" in out
    assert "TILE_P_MAX = 384" in out
    assert "PARALLEL_SEG_MIN = 20_000_000" in out
