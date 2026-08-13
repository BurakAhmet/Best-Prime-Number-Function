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

# Default trial bound (small n−1). Multi-limb uses _adaptive_trial_bound.
_TRIAL_BOUND = 100_000
# Prime-only trial cache ceiling (5e6 finds 3.8e6-class factors; larger
# factors use Brent/ECM). Avoid 2e7 sieves (~1s) on every multi-limb default.
_TRIAL_PRIME_CACHE_MAX = 5_000_000

# After trial + is_prime/cubic split attempts, give up only if a cofactor
# is still composite and larger than this (hostile n−1 → cubic on n).
_COFACTOR_BIT_GIVE_UP = 96

# True / False / None. Use Optional[bool] (not X | Y) so import works on 3.9:
# PEP 604 unions are 3.10+, and this alias is evaluated at runtime.
Result = Optional[bool]

_primes_cache: tuple[int, ...] | None = None
_primes_cache_limit = 0


def _primes_upto(limit: int) -> tuple[int, ...]:
    """Cached primes ≤ limit (grows the sieve as needed)."""
    global _primes_cache, _primes_cache_limit
    need = min(int(limit), _TRIAL_PRIME_CACHE_MAX)
    if _primes_cache is None or _primes_cache_limit < need:
        from .prime_sieve import _sieve_primes_upto

        _primes_cache = tuple(_sieve_primes_upto(need))
        _primes_cache_limit = need
    return _primes_cache


def _adaptive_trial_bound(m: int) -> int:
    """Higher prime trial for multi-limb n−1 (cheap vs ECM/Brent)."""
    bits = m.bit_length()
    if bits <= 40:
        return _TRIAL_BOUND
    if bits <= 80:
        return 1_000_000
    # Cap at sieve cache: peel ~1e6–5e6 factors; Brent gets ~1e7–1e8.
    return _TRIAL_PRIME_CACHE_MAX


def _trial_split(m: int, bound: int) -> tuple[dict[int, int], int]:
    """Peel prime powers ≤ bound from m. Returns (factors, remaining).

    Uses a prime table (not a dense 30-wheel of composites) so high bounds
    stay affordable.
    """
    fac: dict[int, int] = {}
    if m <= 1:
        return fac, m
    bound = min(int(bound), _TRIAL_PRIME_CACHE_MAX)
    for p in _primes_upto(bound):
        if p > bound or p * p > m:
            break
        if m % p == 0:
            e = 0
            while m % p == 0:
                m //= p
                e += 1
            fac[p] = fac.get(p, 0) + e
            if m == 1:
                break
    return fac, m


def _cofactor_is_prime(c: int, *, parallel: bool) -> bool:
    """Primality of a factor of n−1.

    Uses the full ``is_prime`` ladder (including n−1 Pocklington on the
    cofactor). Recursion is safe: every cofactor is strictly smaller than
    the original n.
    """
    if c < 2:
        return False
    if c < 10_000:
        from .is_prime import _is_prime_small

        return _is_prime_small(c)
    from .is_prime import is_prime

    return bool(is_prime(c, parallel=parallel))


def _try_split_cofactor(c: int, *, parallel: bool) -> int | None:
    """Find a proper factor of composite ``c``, or None.

    Order tuned for n−1 cofactors of multi-limb primes:

    1. prime trial (≤5e6)
    2. Fermat near-square split
    3. deterministic Brent (often finds ~1e9 factors in tens of ms)
    4. short cubic probe (avoid multi-second C k-loops that miss medium factors)
    5. ECM
    """
    from .factor_ecm import ecm_factor
    from .factor_lehman import (
        _c_lehman_ready,
        _ceil_icbrt,
        lehman_factor,
    )
    from .prime_factors import _brent, _fermat_split

    # Cheap peel of medium prime factors before heavy methods.
    fac, rem = _trial_split(c, _adaptive_trial_bound(c))
    if rem != c and rem > 1 and rem < c:
        return min(fac)
    if rem == 1 and fac:
        return min(fac)
    if fac and rem > 1:
        return min(fac)

    f = _fermat_split(c)
    if f is not None and 1 < f < c:
        return f

    # Brent before cubic: cubic with large 4kn-limited budgets is slow and
    # often misses unbalanced ~1e9 factors that Brent finds quickly.
    for cv in range(1, 64):
        g = _brent(c, cv)
        if 1 < g < c:
            return g

    cub = _ceil_icbrt(c)
    # Keep cubic probe short on multiprecision / large-limb numbers.
    if _c_lehman_ready() and c.bit_length() <= 128 and c > 1:
        max_k = ((1 << 128) - 1) // (4 * c)
        budget = min(max_k, cub, 100_000)
        if budget >= 16:
            f = lehman_factor(c, k_max=int(budget), parallel=parallel)
            if f is not None and 1 < f < c:
                return f
    else:
        budget = min(cub, 50_000)
        if budget >= 16:
            f = lehman_factor(c, k_max=int(budget), parallel=parallel)
            if f is not None and 1 < f < c:
                return f

    f = ecm_factor(c)
    if f is not None and 1 < f < c:
        return f
    return None


def _factor_completely(m: int, *, parallel: bool) -> dict[int, int] | None:
    """Full prime factorization of m, or None if a cofactor will not split."""
    bound = _adaptive_trial_bound(m)
    fac, rem = _trial_split(m, bound)
    stack = [rem] if rem > 1 else []
    # Bound effort: deep factoring of huge hostile n−1 must not hang next_prime.
    splits = 0
    max_splits = 32
    while stack:
        c = stack.pop()
        if c <= 1:
            continue
        # Another prime trial pass with adaptive bound (cheap vs ECM).
        cb = _adaptive_trial_bound(c)
        sub, r2 = _trial_split(c, cb)
        for p, e in sub.items():
            fac[p] = fac.get(p, 0) + e
        if r2 == 1:
            continue
        c = r2
        if _cofactor_is_prime(c, parallel=parallel):
            fac[c] = fac.get(c, 0) + 1
            continue
        # Composite — split before giving up (even for large bit length).
        if splits >= max_splits:
            return None
        splits += 1
        f = _try_split_cofactor(c, parallel=parallel)
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
