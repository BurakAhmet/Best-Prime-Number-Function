#!/usr/bin/env python3
"""Compare end-to-end CLI TIME JSON from compare_e2e.py.

Fails if candidate e2e_ms is slower than baseline by more than --threshold
on any shared case with baseline e2e_ms >= --min-ms.
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
    p.add_argument("--threshold", type=float, default=0.25,
                   help="Max allowed slowdown fraction (0.25 = 25%%)")
    p.add_argument("--min-ms", type=float, default=1.0,
                   help="Ignore baseline cases below this e2e_ms (noise)")
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
        bms = br.get("e2e_ms")
        cms = cr.get("e2e_ms")
        if bms is None or cms is None:
            continue
        if bms < args.min_ms:
            status, delta = "skip-noise", "—"
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
        print("No comparable e2e cases with baseline >= min-ms; nothing to enforce.")
        return 0
    if failed:
        print("E2E performance regression detected:")
        for case, bms, cms, ratio in failed:
            print(f"  - {case}: {cms:.3f} ms vs {bms:.3f} ms ({ratio:.2f}x)")
        return 1
    print("No e2e regressions beyond threshold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
