#!/usr/bin/env python3
"""Fail if docs/wiki drifts from key README facts."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
WIKI = ROOT / "docs" / "wiki"

# Each entry: (wiki file, list of regexes that must match README AND that wiki page)
CHECKS = [
    (
        "Project-restrictions.md",
        [
            r"No stochastic Miller",
            r"No.*prime libraries",
            r"NumPy\s*/\s*Numba",
            r"AKS",
            r"primorial-wheel|9699690|30030",
        ],
    ),
    (
        "Algorithm-overview.md",
        [
            r"end-to-end|TIME",
            r"10\^4|10⁴|10\^4",
            r"wheel_core|OpenMP|Numba",
            r"30030|9699690",
            r"AKS",
        ],
    ),
    (
        "Benchmarks.md",
        [
            r"compare_e2e|end-to-end|e2e",
            r"compare_speed|deterministic",
        ],
    ),
    (
        "Hall-of-fame.md",
        [
            r"9223372036854775783|near.*2\^63|2\^\{63\}",
            r"18446744073709551557|largest prime",
            r"2305843009213693951|M61|2\^\{61\}",
        ],
    ),
    (
        "Library.md",
        [
            r"totient",
            r"primorial",
            r"primerange",
            r"No stochastic Miller",
            r"docs/wiki/Library",
        ],
    ),
]


def main() -> int:
    bad = []
    if not WIKI.is_dir():
        print("docs/wiki missing", file=sys.stderr)
        return 1
    for rel, patterns in CHECKS:
        path = WIKI / rel
        if not path.is_file():
            bad.append(f"missing wiki page: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for pat in patterns:
            rx = re.compile(pat, re.I)
            in_readme = bool(rx.search(README))
            in_wiki = bool(rx.search(text))
            if in_readme and not in_wiki:
                bad.append(f"{rel}: pattern /{pat}/ found in README but missing in wiki")
            if not in_readme and not in_wiki:
                bad.append(f"{rel}: pattern /{pat}/ missing in both README and wiki")
    if bad:
        print("Wiki sync check FAILED:")
        for b in bad:
            print(f"  - {b}")
        print("\nUpdate docs/wiki to match README key facts.")
        return 1
    print("Wiki sync check PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
