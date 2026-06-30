#!/usr/bin/env python3
"""
Compare optimized timings: candidate (current checkout) vs baseline (file or JSON).

Fails if candidate is slower than baseline by more than --threshold (default 15%)
on any shared case with a measurable baseline time.

Used by CI to ensure a new push is not slower than the reference (main / committed baseline).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load(path: Path) -> dict:
    data = json.loads(path.read_text())
    by_case = {r["case"]: r for r in data["results"]}
    return {"meta": {k: data[k] for k in data if k != "results"}, "by_case": by_case}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument(
        "--threshold",
        type=float,
        default=0.15,
        help="Max allowed slowdown fraction (0.15 = 15%% slower fails)",
    )
    p.add_argument(
        "--min-ms",
        type=float,
        default=0.05,
        help="Ignore cases where baseline optimized_ms is below this (noise)",
    )
    args = p.parse_args()

    base = load(args.baseline)
    cand = load(args.candidate)

    print(f"Baseline:  {args.baseline}")
    print(f"Candidate: {args.candidate}")
    print(f"Threshold: {args.threshold * 100:.0f}% slower fails (min baseline {args.min_ms} ms)")
    print()
    print(f"{'Case':<22} {'Base ms':>12} {'Cand ms':>12} {'Delta':>10} {'Status':>10}")
    print("-" * 70)

    failed = []
    compared = 0
    for case, br in sorted(base["by_case"].items()):
        if case not in cand["by_case"]:
            continue
        cr = cand["by_case"][case]
        bms = br.get("optimized_ms")
        cms = cr.get("optimized_ms")
        if bms is None or cms is None:
            continue
        if bms < args.min_ms:
            status = "skip-noise"
            delta = "—"
        else:
            compared += 1
            ratio = cms / bms if bms > 0 else float("inf")
            pct = (ratio - 1.0) * 100
            delta = f"{pct:+.1f}%"
            if ratio > 1.0 + args.threshold:
                status = "REGRESS"
                failed.append((case, bms, cms, ratio))
            elif ratio < 1.0 - 0.02:
                status = "faster"
            else:
                status = "ok"
        print(f"{case:<22} {bms:>12.3f} {cms:>12.3f} {delta:>10} {status:>10}")

    print()
    if not compared:
        print("No comparable cases with baseline >= min-ms; nothing to enforce.")
        return 0
    if failed:
        print("Performance regression detected (candidate slower than baseline):")
        for case, bms, cms, ratio in failed:
            print(f"  - {case}: {cms:.3f} ms vs {bms:.3f} ms ({ratio:.2f}x)")
        return 1
    print("No regressions beyond threshold. Candidate is as fast or faster (within tolerance).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
