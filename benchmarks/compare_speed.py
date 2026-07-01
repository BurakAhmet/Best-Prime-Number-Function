#!/usr/bin/env python3
"""
Compare a *primitive* (naive) primality test against the optimized is_prime.

Primitive = trial division by every odd integer up to floor(sqrt(n))
            (after even check) — classic teaching algorithm, no wheel, no Numba.

Optimized = is_prime() from this package (tiered wheel (stdlib, OpenMP .so, Numba fallback)).

Usage:
  NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py
  python benchmarks/compare_speed.py --json benchmarks/results.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from is_prime import is_prime  # noqa: E402


def primitive_is_prime(n: int) -> bool:
    """Naive deterministic trial division (baseline)."""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    limit = math.isqrt(n)
    for i in range(3, limit + 1, 2):
        if n % i == 0:
            return False
    return True


def _time_call(fn, n: int, repeats: int) -> tuple[bool, float]:
    """Return (result, best_ms over repeats)."""
    result = fn(n)
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        r = fn(n)
        dt = (time.perf_counter() - t0) * 1000.0
        if r != result:
            raise RuntimeError(f"inconsistent result for {fn.__name__}({n})")
        best = min(best, dt)
    return result, best


DEFAULT_CASES = [
    ("small prime", 97),
    ("4-digit prime", 7919),
    ("10^9+7", 1_000_000_007),
    ("10^9+9", 1_000_000_009),
    ("Mersenne M31", (1 << 31) - 1),
    ("12-digit prime", 999_999_999_989),
]

# Hard 64-bit primes: optimized is timed; primitive optional via --primitive-hard
HARD_CASES = [
    ("near 2^63 prime", 9_223_372_036_854_775_783),
    ("Mersenne M61", (1 << 61) - 1),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-hard",
        action="store_true",
        help="Also run huge 64-bit primes for the optimized method",
    )
    parser.add_argument(
        "--primitive-hard",
        action="store_true",
        help="With --include-hard, also time the primitive method (very slow)",
    )
    parser.add_argument("--repeats", type=int, default=3, help="Timing repeats (best kept)")
    parser.add_argument("--json", type=Path, default=None, help="Write results JSON")
    args = parser.parse_args()

    # Warm serial + parallel JIT paths (parallel triggers only for larger isqrt).
    is_prime(97, parallel=False)
    is_prime(1_000_003, parallel=True)
    is_prime(1_000_000_007, parallel=True)
    is_prime((1 << 31) - 1, parallel=True)

    threads = os.environ.get("NUMBA_NUM_THREADS") or os.environ.get("OMP_NUM_THREADS") or "?"
    cases = list(DEFAULT_CASES)
    hard_ns = {n for _, n in HARD_CASES}
    if args.include_hard:
        cases.extend(HARD_CASES)

    rows = []
    print(f"Threads (Numba/OMP env): {threads}")
    print(f"Repeats (best of): {args.repeats}")
    print()
    hdr = f"{'Case':<22} {'n':>22} {'Prim?':>6} {'Primitive ms':>14} {'Optimized ms':>14} {'Speedup':>10}"
    print(hdr)
    print("-" * len(hdr))

    for name, n in cases:
        is_hard = n in hard_ns
        run_primitive = (not is_hard) or args.primitive_hard
        p_ms = None
        if run_primitive:
            reps_p = args.repeats if n < 10**10 else 1
            pr, p_ms = _time_call(primitive_is_prime, n, reps_p)
        else:
            pr = None

        reps_o = args.repeats if n < 10**12 else max(1, args.repeats - 1)
        or_, o_ms = _time_call(lambda x: is_prime(x, parallel=True), n, reps_o)

        if pr is not None and pr != or_:
            print(f"MISMATCH on {n}: primitive={pr} optimized={or_}", file=sys.stderr)
            return 1

        if p_ms is None:
            p_str = "skipped*"
            speed = None
            speed_str = "—"
        else:
            p_str = f"{p_ms:,.3f}"
            speed = p_ms / o_ms if o_ms > 0 else float("inf")
            speed_str = f"{speed:,.1f}×"

        print(
            f"{name:<22} {n:>22} {'yes' if or_ else 'no':>6} "
            f"{p_str:>14} {o_ms:>14,.3f} {speed_str:>10}"
        )
        rows.append(
            {
                "case": name,
                "n": n,
                "is_prime": or_,
                "primitive_ms": p_ms,
                "optimized_ms": o_ms,
                "speedup": speed,
            }
        )

    print()
    if args.include_hard and not args.primitive_hard:
        print("* Hard cases: primitive timing skipped (use --primitive-hard; can take many minutes).")
    print()
    print("Primitive = odd trial division up to isqrt(n), pure Python.")
    print("Optimized = tiered wheel (embedded/C OpenMP/Numba fallback).")

    if args.json:
        payload = {"threads": str(threads), "repeats": args.repeats, "results": rows}
        args.json.write_text(json.dumps(payload, indent=2))
        print(f"Wrote {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
