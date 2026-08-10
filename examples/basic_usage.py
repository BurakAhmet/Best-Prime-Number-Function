#!/usr/bin/env python3
"""Minimal library usage for best-prime-number-function / is_prime."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from best_prime import __version__, is_prime, lab, next_prime  # noqa: E402


def main() -> None:
    print(f"best_prime {__version__}")
    for n in (1, 2, 17, 100, 10**9 + 7, "00017"):
        print(f"  is_prime({n!r:20}) -> {is_prime(n)}")

    for n in (0, 14, 96, 10**9 + 7):
        print(f"  next_prime({n!r:18}) -> {next_prime(n)}")

    info = lab(10**9 + 7)
    print(
        f"  lab(10**9+7): path={info['path']} prime={info['is_prime']} "
        f"elapsed_ms={info['elapsed_ms']:.3f}"
    )


if __name__ == "__main__":
    main()
