"""n−1 primality (Pocklington) — faster than cubic search when n−1 factors.

Classical Pocklington / Brillhart–Lehmer–Selfridge style proof:

* Fermat filter with fixed bases (composite if a^{n−1} ≢ 1 mod n).
* Factor enough of n−1 so F | (n−1) and F > √n, using only our
  deterministic factoring (trial + cubic Lehman + cofactor trial).
* For every prime q | F, find a fixed small base a with
  a^{n−1} ≡ 1 (mod n) and gcd(a^{(n−1)/q} − 1, n) = 1.

Then every prime divisor of n is ≡ 1 (mod F). With F > √n that forces
n to be prime.

Deterministic. No RNG. Not Miller–Rabin (passing Fermat is only a
composite filter; primality requires the full Pocklington conditions).
Falls back to ``None`` when n−1 does not factor in budget so the cubic
path can finish the proof.

Literature: Pocklington 1914; Brillhart–Lehmer–Selfridge 1975;
Crandall–Pomerance §4.1. Recent surveys of deterministic factoring
exponents (Harvey n^{1/5}, Hales–Hiary Lehman, …) remain the cubic /
quartic *search* line; this module uses the orthogonal n−1 *proof* line,
which is O~(log n) modular exponentiations once n−1 is factored.
"""

from __future__ import annotations

import math
from typing import Optional

# Fixed witness list for Pocklington (and Fermat prefilter). Deterministic.
_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)

# Trial bound on n−1 before invoking is_prime / cubic on the cofactor.
# Kept modest: pure-Python trial to 1e6 dominates e2e on multi-limb n−1.
_TRIAL_BOUND = 100_000

# After trial + is_prime/cubic split attempts, give up only if a cofactor
# is still composite and larger than this (hostile n−1 → cubic on n).
_COFACTOR_BIT_GIVE_UP = 96

# True / False / None. Use Optional[bool] (not X | Y) so import works on 3.9:
# PEP 604 unions are 3.10+, and this alias is evaluated at runtime.
Result = Optional[bool]


def _trial_split(m: int, bound: int) -> tuple[dict[int, int], int]:
    """Peel prime powers ≤ bound from m. Returns (factors, remaining)."""
    fac: dict[int, int] = {}
    if m <= 1:
        return fac, m
    for p in (2, 3, 5):
        if p > bound:
            break
        while m % p == 0:
            fac[p] = fac.get(p, 0) + 1
            m //= p
    p = 7
    step = 4  # 7,11,13,17,… via 30-wheel steps 4,2,4,2,4,6,2,6 starting mid-cycle
    # Use full 30-wheel from 7.
    w30 = (4, 2, 4, 2, 4, 6, 2, 6)
    wi = 0
    while p <= bound and p * p <= m:
        while m % p == 0:
            fac[p] = fac.get(p, 0) + 1
            m //= p
        p += w30[wi]
        wi = (wi + 1) & 7
    return fac, m


def _cofactor_is_prime(c: int, *, parallel: bool) -> bool:
    """Primality of a factor of n−1.

    Uses the full ``is_prime`` ladder (including n−1 Pocklington on the
    cofactor). Recursion is safe: every cofactor is strictly smaller than
    the original n. Avoids proving large prime cofactors with a full cubic
    search when their own n−1 is smooth (often 100× faster).
    """
    if c < 2:
        return False
    if c < 10_000:
        from .is_prime import _is_prime_small

        return _is_prime_small(c)
    from .is_prime import is_prime

    return bool(is_prime(c, parallel=parallel))


def _factor_completely(m: int, *, parallel: bool) -> dict[int, int] | None:
    """Full prime factorization of m, or None if a cofactor will not split."""
    from .factor_lehman import cubic_complete_ready, lehman_factor

    fac, rem = _trial_split(m, _TRIAL_BOUND)
    stack = [rem] if rem > 1 else []
    while stack:
        c = stack.pop()
        if c <= 1:
            continue
        # Peel more small factors if the cofactor is still moderate.
        if c <= _TRIAL_BOUND * _TRIAL_BOUND:
            sub, r2 = _trial_split(c, _TRIAL_BOUND)
            for p, e in sub.items():
                fac[p] = fac.get(p, 0) + e
            if r2 == 1:
                continue
            c = r2
        if _cofactor_is_prime(c, parallel=parallel):
            fac[c] = fac.get(c, 0) + 1
            continue
        # Composite: try a complete cubic split when the engine can finish.
        if cubic_complete_ready(c):
            f = lehman_factor(c, parallel=parallel)
            if f is not None and 1 < f < c:
                stack.append(f)
                stack.append(c // f)
                continue
        if c.bit_length() > _COFACTOR_BIT_GIVE_UP:
            return None
        f = lehman_factor(c, parallel=parallel)
        if f is None or f <= 1 or f >= c:
            return None
        stack.append(f)
        stack.append(c // f)
    return fac


def _pocklington(n: int, primes_of_F: list[int]) -> Result:
    """True if Pocklington proves prime; False composite; None inconclusive."""
    for q in primes_of_F:
        found = False
        for a in _BASES:
            if a % n == 0:
                return n == a
            # Fermat filter (also required by Pocklington).
            if pow(a, n - 1, n) != 1:
                return False
            if math.gcd(pow(a, (n - 1) // q, n) - 1, n) == 1:
                found = True
                break
        if not found:
            return None
    return True


def nm1_primality(n: int, *, parallel: bool = True) -> Result:
    """Try to settle primality of ``n`` via an n−1 (Pocklington) proof.

    Returns
    -------
    True
        Proved prime.
    False
        Proved composite (Fermat witness or failed structure).
    None
        Inconclusive — caller should use cubic search / trial.
    """
    if n < 2:
        return False
    if n in (2, 3, 5, 7):
        return True
    if n % 2 == 0 or n % 3 == 0 or n % 5 == 0:
        return False

    # Fast composite filter (deterministic; not a primality claim).
    for a in _BASES:
        if a % n == 0:
            return n == a
        if pow(a, n - 1, n) != 1:
            return False

    # Factor n−1 completely (bounded). Need F = n−1 > √n (always for n > 1).
    fac = _factor_completely(n - 1, parallel=parallel)
    if fac is None:
        return None

    # Sanity: product of prime powers must equal n−1.
    prod = 1
    for q, e in fac.items():
        prod *= pow(q, e)
    if prod != n - 1:
        return None

    primes = list(fac.keys())
    # Optional early Pocklington with a prefix F > √n (fewer witnesses).
    target = math.isqrt(n)
    F = 1
    used: list[int] = []
    # Prefer larger primes first so F exceeds √n with fewer factors.
    for q in sorted(primes, reverse=True):
        e = fac[q]
        for _ in range(e):
            if F > target:
                break
            F *= q
        used.append(q)
        if F > target:
            break
    if F <= target:
        used = primes  # full n−1

    return _pocklington(n, used)


def nm1_ready(n: int) -> bool:
    """Whether multi-limb / hard paths should try n−1.

    True for every ``n ≥ 2^{64}``, and for hard 64-bit n in the cubic size
    class (``isqrt ≥ 10^7`` with C core). Mid-size 64-bit stays on wheel trial.
    """
    if n >= (1 << 64):
        return True
    from .factor_lehman import cubic_complete_ready

    return cubic_complete_ready(n)
