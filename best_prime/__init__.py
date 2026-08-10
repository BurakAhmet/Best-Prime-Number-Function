"""
best-prime-number-function — fully deterministic primality testing.

Canonical implementation lives in the ``is_prime`` module; this package is a
stable, library-friendly import path.

Example
-------
>>> from best_prime import is_prime, lab, next_prime, nth_prime
>>> is_prime(17)
True
>>> next_prime(14, 3)
23
>>> nth_prime(5)
11
>>> lab(97)["path"]
'python_small'
"""

from __future__ import annotations

try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("best-prime-number-function")
    except PackageNotFoundError:  # pragma: no cover - editable / source tree
        __version__ = "1.8.2"
except ImportError:  # pragma: no cover
    __version__ = "1.8.2"

from is_prime import DEFAULT_N, is_prime, lab, main
from next_prime import next_prime
from prev_prime import prev_prime
from prime_factors import factorint, prime_factors
from prime_power import is_perfect_power, is_prime_power
from prime_sieve import PRIME_COUNT_MAX_N, nth_prime, prime_count, primerange, primes

__all__ = [
    "DEFAULT_N",
    "factorint",
    "is_perfect_power",
    "is_prime",
    "is_prime_power",
    "lab",
    "main",
    "next_prime",
    "nth_prime",
    "prev_prime",
    "PRIME_COUNT_MAX_N",
    "prime_count",
    "prime_factors",
    "primerange",
    "primes",
    "__version__",
]
