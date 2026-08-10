"""
Perfect powers and prime powers.

is_perfect_power(n): n = a^b with a>1, b>1.
is_prime_power(n): n = p^k with p prime and k>=1 (so primes count).

Integer k-th roots via Newton; only prime exponents (a perfect power is an
ℓ-th power for some prime ℓ). No RNG, no Miller–Rabin.
"""

from __future__ import annotations

import math

from .is_prime import _parse_n, is_prime
from .prime_sieve import _primes_upto_cached


def _iroot(n: int, k: int) -> int:
    """floor(n^(1/k)) for n>=1, k>=2."""
    if n < 2:
        return n
    # Initial guess from bit length (exact enough to Newton-converge).
    bl = n.bit_length()
    x = 1 << ((bl + k - 1) // k)
    k1 = k - 1
    while True:
        y = (k1 * x + n // pow(x, k1)) // k
        if y >= x:
            # May still be 1 too high from the bit guess on some edges.
            while pow(x, k) > n:
                x -= 1
            return x
        x = y


def is_perfect_power(n: int | str) -> bool:
    """True iff n = a^b for integers a>1 and b>1. 0, 1, primes → False."""
    n_int = _parse_n(n)
    if n_int < 4:
        return False
    r = math.isqrt(n_int)
    if r * r == n_int:
        return True
    max_e = n_int.bit_length()  # 2^(max_e-1) <= n < 2^max_e
    for e in _primes_upto_cached(max_e):
        if e == 2:
            continue
        if e >= max_e:
            break
        a = _iroot(n_int, e)
        if a >= 2 and pow(a, e) == n_int:
            return True
    return False


def is_prime_power(n: int | str, *, parallel: bool = True) -> bool:
    """True iff n = p^k for a prime p and k >= 1."""
    n_int = _parse_n(n)
    if n_int < 2:
        return False
    # Peel p^k by taking prime-exponent roots until a prime (or failure).
    while True:
        if is_prime(n_int, parallel=parallel):
            return True
        max_e = n_int.bit_length()
        peeled = False
        for e in _primes_upto_cached(max_e):
            if e >= max_e:
                break
            a = _iroot(n_int, e)
            if a >= 2 and pow(a, e) == n_int:
                n_int = a
                peeled = True
                break
        if not peeled:
            return False
