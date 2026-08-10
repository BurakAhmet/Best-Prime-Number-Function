#!/usr/bin/env python3
"""Minimal library usage for best-prime-number-function / is_prime."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from best_prime import (  # noqa: E402
    __version__,
    divisor_count,
    factorint,
    is_perfect_power,
    is_prime,
    is_prime_power,
    lab,
    next_prime,
    nth_prime,
    prev_prime,
    prime_count,
    prime_factors,
    primerange,
    primes,
    primorial,
    totient,
)


def main() -> None:
    print(f"best_prime {__version__}")
    for n in (1, 2, 17, 100, 10**9 + 7, "00017"):
        print(f"  is_prime({n!r:20}) -> {is_prime(n)}")

    for n in (0, 14, 96, 10**9 + 7):
        print(f"  next_prime({n!r:18}) -> {next_prime(n)}")
    print(f"  next_prime(14, 3)        -> {next_prime(14, 3)}")
    print(f"  prev_prime(14)           -> {prev_prime(14)}")
    print(f"  nth_prime(5)             -> {nth_prime(5)}")
    print(f"  prime_count(10)          -> {prime_count(10)}")
    print(f"  primes(10)               -> {primes(10)}")
    print(f"  list(primerange(10, 20)) -> {list(primerange(10, 20))}")
    print(f"  totient(10)              -> {totient(10)}")
    print(f"  primorial(7)             -> {primorial(7)}")
    print(f"  divisor_count(12)        -> {divisor_count(12)}")
    print(f"  prime_factors(360)       -> {prime_factors(360)}")
    print(f"  factorint(360)           -> {factorint(360)}")
    print(f"  is_perfect_power(36)     -> {is_perfect_power(36)}")
    print(f"  is_prime_power(36)       -> {is_prime_power(36)}")

    info = lab(10**9 + 7)
    print(
        f"  lab(10**9+7): path={info['path']} prime={info['is_prime']} "
        f"elapsed_ms={info['elapsed_ms']:.3f}"
    )


if __name__ == "__main__":
    main()
