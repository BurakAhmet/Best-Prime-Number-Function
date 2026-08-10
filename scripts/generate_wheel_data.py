#!/usr/bin/env python3
"""Regenerate precomputed wheel tables in is_prime_data/ (deterministic)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "is_prime_data"


def build_steps(primes: tuple[int, ...], start: int) -> np.ndarray:
    mod = 1
    for p in primes:
        mod *= p
    coprime = np.ones(mod, dtype=np.bool_)
    for p in primes:
        coprime[0::p] = False
    residues = np.flatnonzero(coprime).astype(np.int64)
    nW = int(residues.size)
    idx = int(np.where(residues == start)[0][0])
    ordered = np.empty(nW + 1, dtype=np.int64)
    ordered[: nW - idx] = residues[idx:]
    ordered[nW - idx : nW] = residues[:idx] + mod
    ordered[nW] = residues[idx] + mod
    steps = np.diff(ordered).astype(np.uint8)
    assert int(steps.sum()) == mod
    return steps


def derive_res(steps: np.ndarray, mod: int, start: int, invalid, dtype):
    nW = int(steps.size)
    cs = np.empty(nW, dtype=np.int64)
    cs[0] = start
    if nW > 1:
        cs[1:] = start + np.cumsum(steps[:-1], dtype=np.int64)
    res = np.full(mod, invalid, dtype=dtype)
    res[cs % mod] = np.arange(nW, dtype=dtype)
    return res


def main() -> None:
    OUT.mkdir(exist_ok=True)
    w30 = build_steps((2, 3, 5, 7, 11, 13), 17)
    r30 = derive_res(w30, 30030, 17, np.uint16(0xFFFF), np.uint16)
    w96 = build_steps((2, 3, 5, 7, 11, 13, 17, 19), 23)
    # Raw bytes are the committed source of truth. .npy is optional/local.
    (OUT / "w30030_steps.u8").write_bytes(w30.tobytes())
    (OUT / "w9699690_steps.u8").write_bytes(w96.tobytes())
    (OUT / "res30030.u16").write_bytes(r30.tobytes())
    print(f"Wrote raw wheel tables to {OUT}")
    for p in sorted(OUT.glob("*.u8")) + sorted(OUT.glob("*.u16")):
        print(f"  {p.name:22} {p.stat().st_size / 1024:8.1f} KiB")


if __name__ == "__main__":
    main()
