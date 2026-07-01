#!/usr/bin/env python3
"""Minimal library usage for best-prime-number-function / is_prime."""

from best_prime import __version__, is_prime, lab


def main() -> None:
    print(f"best_prime {__version__}")
    for n in (1, 2, 17, 100, 10**9 + 7, "00017"):
        print(f"  is_prime({n!r:20}) -> {is_prime(n)}")

    info = lab(10**9 + 7)
    print(
        f"  lab(10**9+7): path={info['path']} prime={info['is_prime']} "
        f"elapsed_ms={info['elapsed_ms']:.3f}"
    )


if __name__ == "__main__":
    main()
