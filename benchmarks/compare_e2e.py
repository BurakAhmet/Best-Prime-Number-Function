#!/usr/bin/env python3
"""End-to-end CLI TIME benchmark (matches is_prime.py t0→result metric)."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIME_RE = re.compile(r"TIME:\s+(\d+)\s+ns\s+\(([0-9.]+)\s+ms\)")
RESULT_RE = re.compile(r"RESULT:\s+(prime|not prime)")

DEFAULT_CASES = [
    ("small prime", 97),
    ("4-digit prime", 7919),
    ("10^9+7", 1_000_000_007),
    ("10^9+9", 1_000_000_009),
    ("Mersenne M31", (1 << 31) - 1),
    ("12-digit prime", 999_999_999_989),
]
HARD_CASES = [
    ("near 2^63 prime", 9_223_372_036_854_775_783),
    ("Mersenne M61", (1 << 61) - 1),
]


def run_once(n: int, serial: bool = False) -> tuple[bool, float]:
    cmd = [sys.executable, str(ROOT / "is_prime.py"), str(n)]
    if serial:
        cmd.append("--serial")
    out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    prime = None
    ms = None
    for line in out.splitlines():
        m = RESULT_RE.match(line.strip())
        if m:
            prime = m.group(1) == "prime"
        m = TIME_RE.match(line.strip())
        if m:
            ms = float(m.group(2))
    if prime is None or ms is None:
        raise RuntimeError(f"failed to parse CLI output for n={n}:\n{out}")
    return prime, ms


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--include-hard", action="store_true")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--json", type=Path, default=None)
    p.add_argument("--serial", action="store_true")
    args = p.parse_args()

    cases = list(DEFAULT_CASES)
    if args.include_hard:
        cases.extend(HARD_CASES)

    # Warm stdlib path and (if hard cases follow) Numba parallel JIT.
    run_once(1_000_000_007, serial=args.serial)
    if args.include_hard:
        run_once((1 << 31) - 1, serial=args.serial)  # still stdlib
        # trigger hard-path compile once (result discarded)
        run_once(2_305_843_009_213_693_951, serial=args.serial)  # M61

    rows = []
    print(f"Repeats (best of): {args.repeats}")
    print(f"{'Case':<22} {'n':>22} {'Prim?':>6} {'E2E ms':>12}")
    print("-" * 68)
    for name, n in cases:
        reps = args.repeats if n < 10**12 else max(1, args.repeats - 1)
        best = float("inf")
        prime = None
        for _ in range(reps):
            pr, ms = run_once(n, serial=args.serial)
            if prime is None:
                prime = pr
            elif prime != pr:
                print(f"MISMATCH on {n}", file=sys.stderr)
                return 1
            best = min(best, ms)
        print(f"{name:<22} {n:>22} {'yes' if prime else 'no':>6} {best:>12,.3f}")
        rows.append({"case": name, "n": n, "is_prime": prime, "e2e_ms": best})

    if args.json:
        args.json.write_text(json.dumps({"repeats": args.repeats, "results": rows}, indent=2))
        print(f"Wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
