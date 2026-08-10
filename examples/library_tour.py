#!/usr/bin/env python3
"""Tour of every public best_prime API. Run from a clone: python3 examples/library_tour.py"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from best_prime import (  # noqa: E402
    DEFAULT_N,
    PRIME_COUNT_MAX_N,
    TOTIENT_RANGE_MAX,
    __version__,
    bigomega,
    carmichael_lambda,
    crt,
    divisor_count,
    divisor_sum,
    divisors,
    egcd,
    euler_phi,
    factorint,
    gcd,
    is_carmichael,
    is_perfect_power,
    is_prime,
    is_prime_power,
    is_semiprime,
    is_squarefree,
    jacobi,
    lab,
    modinv,
    next_prime,
    nth_prime,
    omega,
    prev_prime,
    prime_count,
    prime_factors,
    primerange,
    primes,
    primorial,
    radical,
    totient,
    totient_range,
)


def show(expr: str, value: object) -> None:
    print(f"  {expr:<42} -> {value}")


def main() -> None:
    print(f"best_prime {__version__}")
    print("Full reference: https://burakahmet.github.io/Best-Prime-Number-Function/guide/")
    print("Wiki copy:      docs/wiki/Library.md")
    print()

    print("constants")
    show("DEFAULT_N", DEFAULT_N)
    show("PRIME_COUNT_MAX_N", PRIME_COUNT_MAX_N)
    show("TOTIENT_RANGE_MAX", TOTIENT_RANGE_MAX)

    print("\nprimality")
    show("is_prime(17)", is_prime(17))
    show("is_prime(100)", is_prime(100))
    show("is_prime('00017')", is_prime("00017"))
    show("is_prime(10**9+7)", is_prime(10**9 + 7))
    info = lab(97)
    show("lab(97)['path']", info["path"])
    show("lab(97)['is_prime']", info["is_prime"])

    print("\nneighbours / nth")
    show("next_prime(14)", next_prime(14))
    show("next_prime(14, 3)", next_prime(14, 3))
    show("prev_prime(14)", prev_prime(14))
    show("prev_prime(10, 3)", prev_prime(10, 3))
    show("nth_prime(1)", nth_prime(1))
    show("nth_prime(5)", nth_prime(5))
    show("nth_prime(10001)", nth_prime(10_001))

    print("\ncounting / listing")
    show("prime_count(10)", prime_count(10))
    show("prime_count(100)", prime_count(100))
    show("primes(10)", primes(10))
    show("list(primerange(10, 20))", list(primerange(10, 20)))
    show("sum(primerange(1, 100))", sum(primerange(1, 100)))

    print("\nfactoring / powers")
    show("prime_factors(360)", prime_factors(360))
    show("factorint(360)", factorint(360))
    show("is_perfect_power(36)", is_perfect_power(36))
    show("is_perfect_power(12)", is_perfect_power(12))
    show("is_prime_power(8)", is_prime_power(8))
    show("is_prime_power(36)", is_prime_power(36))

    print("\nmultiplicative")
    show("totient(10)", totient(10))
    show("euler_phi(10)", euler_phi(10))
    show("totient_range(10)", totient_range(10))
    show("carmichael_lambda(15)", carmichael_lambda(15))
    show("primorial(7)", primorial(7))
    show("primorial(4, nth=True)", primorial(4, nth=True))
    show("divisors(12)", divisors(12))
    show("divisor_count(12)", divisor_count(12))
    show("divisor_sum(12)", divisor_sum(12))
    show("divisor_sum(12, 0)", divisor_sum(12, 0))
    show("omega(12)", omega(12))
    show("bigomega(12)", bigomega(12))
    show("radical(12)", radical(12))
    show("is_squarefree(6)", is_squarefree(6))
    show("is_squarefree(12)", is_squarefree(12))
    show("is_semiprime(6)", is_semiprime(6))
    show("is_carmichael(561)", is_carmichael(561))

    print("\nmodular arithmetic")
    show("gcd(12, 18, 30)", gcd(12, 18, 30))
    g, x, y = egcd(240, 46)
    show("egcd(240, 46)", (g, x, y))
    show("modinv(3, 11)", modinv(3, 11))
    show("crt([2, 3, 2], [3, 5, 7])", crt([2, 3, 2], [3, 5, 7]))
    show("jacobi(2, 15)", jacobi(2, 15))
    show("jacobi(2, 5)", jacobi(2, 5))


if __name__ == "__main__":
    main()
