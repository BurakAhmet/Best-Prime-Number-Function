#!/usr/bin/env python3
"""
Verify that is_prime is deterministic on a fixed suite of inputs.

Runs many repeated calls (serial and parallel where applicable) and asserts
that every trial returns the same boolean. Exits with status 1 on any mismatch.

Used by CI so a new push cannot silently introduce non-determinism (e.g. RNG,
unordered parallelism bugs affecting the result, etc.).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from is_prime import is_prime  # noqa: E402


# Mix of edges, small primes/composites, and medium-large 64-bit values
# (avoid multi-minute primes so CI stays fast).
DEFAULT_CASES: list[tuple[str, object, bool]] = [
    ("int 0", 0, False),
    ("int 1", 1, False),
    ("int 2", 2, True),
    ("int 3", 3, True),
    ("int 4", 4, False),
    ("str 0", "0", False),
    ("str 1", "1", False),
    ("str 17", "17", True),
    ("str 100", "100", False),
    ("str leading zeros 007", "007", True),
    ("str whitespace", "  97  ", True),
    ("str +17", "+17", True),
    ("prime 97", 97, True),
    ("prime 7919", 7919, True),
    ("composite 561 Carmichael", 561, False),
    ("prime 10^9+7", 1_000_000_007, True),
    ("prime 10^9+9", 1_000_000_009, True),
    ("Mersenne M31", (1 << 31) - 1, True),
    ("composite 2^32-1", (1 << 32) - 1, False),
    ("prime 12-digit", 999_999_999_989, True),
    ("composite 10^12", 10**12, False),
    ("100 nines", "9" * 100, False),
    ("10^50 * 7", 7 * 10**50, False),
    ("2^64", 1 << 64, False),
]


def check_case(label: str, n: object, expected: bool, trials: int) -> None:
    # Serial
    results_serial = [is_prime(n, parallel=False) for _ in range(trials)]
    if len(set(results_serial)) != 1:
        raise AssertionError(
            f"{label!r} serial results not unique: {results_serial}"
        )
    if results_serial[0] is not expected:
        raise AssertionError(
            f"{label!r} serial got {results_serial[0]!r}, expected {expected!r}"
        )

    # Parallel (still must match; only affects thread split of trial division)
    results_par = [is_prime(n, parallel=True) for _ in range(trials)]
    if len(set(results_par)) != 1:
        raise AssertionError(
            f"{label!r} parallel results not unique: {results_par}"
        )
    if results_par[0] is not expected:
        raise AssertionError(
            f"{label!r} parallel got {results_par[0]!r}, expected {expected!r}"
        )
    if results_par[0] is not results_serial[0]:
        raise AssertionError(
            f"{label!r} serial/parallel disagree: "
            f"{results_serial[0]!r} vs {results_par[0]!r}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Repeated calls per case (default 5)",
    )
    args = parser.parse_args()

    threads = os.environ.get("NUMBA_NUM_THREADS") or os.environ.get("OMP_NUM_THREADS")
    print(f"Determinism check: {len(DEFAULT_CASES)} cases × {args.trials} trials")
    print(f"NUMBA/OMP threads env: {threads or '(default)'}")
    print()

    # Warm JIT once so first-trial quirks are less noisy (results must still match)
    is_prime(97, parallel=False)
    is_prime(97, parallel=True)

    failed = 0
    for label, n, expected in DEFAULT_CASES:
        try:
            check_case(label, n, expected, args.trials)
            print(f"  OK  {label}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL  {label}: {exc}")

    # Interleaved order must not change outcomes (paranoia for shared state)
    interleaved_expected = [e for _, _, e in DEFAULT_CASES]
    interleaved_got = []
    for _ in range(args.trials):
        for _, n, _ in DEFAULT_CASES:
            interleaved_got.append(is_prime(n, parallel=True))
    chunk = len(DEFAULT_CASES)
    for t in range(args.trials):
        slice_ = interleaved_got[t * chunk : (t + 1) * chunk]
        if slice_ != interleaved_expected:
            print(f"  FAIL  interleaved trial {t}: {slice_} != {interleaved_expected}")
            failed += 1
            break
    else:
        print("  OK  interleaved multi-case order")

    print()
    if failed:
        print(f"Determinism check FAILED ({failed} problem(s)).")
        return 1
    print("Determinism check PASSED: all repeated trials agreed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
