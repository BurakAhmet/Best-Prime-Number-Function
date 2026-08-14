"""
best-prime-number-function — fully deterministic primality testing.

Public import path. Implementations live in sibling modules; they load lazily
so ``python -m best_prime`` / ``from best_prime import is_prime`` do not pull
ntheory, sieves, and factoring into the end-to-end CLI ``TIME``.

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

from importlib import import_module
from typing import Any

try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("best-prime-number-function")
    except PackageNotFoundError:  # pragma: no cover - editable / source tree
        __version__ = "1.12.0"
except ImportError:  # pragma: no cover
    __version__ = "1.12.0"

# (submodule, attribute)
_EXPORTS: dict[str, tuple[str, str]] = {
    "DEFAULT_N": (".is_prime", "DEFAULT_N"),
    "PRIME_COUNT_MAX_N": (".prime_sieve", "PRIME_COUNT_MAX_N"),
    "TOTIENT_RANGE_MAX": (".ntheory", "TOTIENT_RANGE_MAX"),
    "bigomega": (".ntheory", "bigomega"),
    "carmichael_lambda": (".ntheory", "carmichael_lambda"),
    "crt": (".ntheory", "crt"),
    "divisor_count": (".ntheory", "divisor_count"),
    "divisor_sum": (".ntheory", "divisor_sum"),
    "divisors": (".ntheory", "divisors"),
    "egcd": (".ntheory", "egcd"),
    "euler_phi": (".ntheory", "euler_phi"),
    "factorint": (".prime_factors", "factorint"),
    "gcd": (".ntheory", "gcd"),
    "is_carmichael": (".ntheory", "is_carmichael"),
    "is_perfect_power": (".prime_power", "is_perfect_power"),
    "is_prime": (".is_prime", "is_prime"),
    "UnsettledPrimalityError": (".errors", "UnsettledPrimalityError"),
    "AKS_SKIP_BITS": (".is_prime", "AKS_SKIP_BITS"),
    "is_prime_power": (".prime_power", "is_prime_power"),
    "NEXT_PRIME_SIEVE_ISQRT_MAX": (".next_prime", "NEXT_PRIME_SIEVE_ISQRT_MAX"),
    "next_primes": (".next_prime", "next_primes"),
    "prev_primes": (".prev_prime", "prev_primes"),
    "primality_certificate": (".certificate", "primality_certificate"),
    "verify_certificate": (".certificate", "verify_certificate"),
    "is_semiprime": (".ntheory", "is_semiprime"),
    "is_squarefree": (".ntheory", "is_squarefree"),
    "jacobi": (".ntheory", "jacobi"),
    "lab": (".is_prime", "lab"),
    "lehman_factor": (".factor_lehman", "lehman_factor"),
    "main": (".is_prime", "main"),
    "modinv": (".ntheory", "modinv"),
    "next_prime": (".next_prime", "next_prime"),
    "nth_prime": (".prime_sieve", "nth_prime"),
    "omega": (".ntheory", "omega"),
    "prev_prime": (".prev_prime", "prev_prime"),
    "prime_count": (".prime_sieve", "prime_count"),
    "prime_factors": (".prime_factors", "prime_factors"),
    "primerange": (".prime_sieve", "primerange"),
    "primes": (".prime_sieve", "primes"),
    "primorial": (".ntheory", "primorial"),
    "radical": (".ntheory", "radical"),
    "totient": (".ntheory", "totient"),
    "totient_range": (".ntheory", "totient_range"),
}

__all__ = [
    "DEFAULT_N",
    "PRIME_COUNT_MAX_N",
    "TOTIENT_RANGE_MAX",
    "bigomega",
    "carmichael_lambda",
    "crt",
    "divisor_count",
    "divisor_sum",
    "divisors",
    "egcd",
    "euler_phi",
    "factorint",
    "gcd",
    "is_carmichael",
    "is_perfect_power",
    "is_prime",
    "is_prime_power",
    "UnsettledPrimalityError",
    "AKS_SKIP_BITS",
    "is_semiprime",
    "NEXT_PRIME_SIEVE_ISQRT_MAX",
    "next_primes",
    "prev_primes",
    "primality_certificate",
    "verify_certificate",
    "is_squarefree",
    "jacobi",
    "lab",
    "lehman_factor",
    "main",
    "modinv",
    "next_prime",
    "nth_prime",
    "omega",
    "prev_prime",
    "prime_count",
    "prime_factors",
    "primerange",
    "primes",
    "primorial",
    "radical",
    "totient",
    "totient_range",
    "__version__",
]


def __getattr__(name: str) -> Any:
    spec = _EXPORTS.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod_name, _attr = spec
    mod = import_module(mod_name, __name__)
    # import_module also sets ``best_prime.is_prime`` to the *module*. Re-bind
    # every export from that submodule so ``from best_prime import is_prime``
    # is the function.
    for exp, (m, a) in _EXPORTS.items():
        if m == mod_name:
            globals()[exp] = getattr(mod, a)
    # Sibling imports (factor_lehman → is_prime) bind the same way. Re-bind
    # any export that is still a module so ``lehman_factor, is_prime`` works.
    for exp, (m, a) in _EXPORTS.items():
        cur = globals().get(exp)
        if type(cur) is type(mod):
            globals()[exp] = getattr(import_module(m, __name__), a)
    return globals()[name]


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
