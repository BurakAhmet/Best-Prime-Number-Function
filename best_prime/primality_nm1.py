"""n−1 primality (Pocklington) — complete deterministic proofs from factoring n−1.

Classical Pocklington / Brillhart–Lehmer–Selfridge:

* Fermat filter with fixed bases (composite if a^{n−1} ≢ 1 mod n).
* Factor **enough** of n−1 so F | (n−1), F fully prime-factored, and
  F > √n (no need to factor the cofactor R = (n−1)/F).
* For every prime q | F, a fixed base a with a^{n−1} ≡ 1 and
  gcd(a^{(n−1)/q} − 1, n) = 1.

Then every prime divisor of n is ≡ 1 (mod F); with F > √n, n is prime.

Deterministic. No RNG. Not Miller–Rabin as the engine.
"""

from __future__ import annotations

import math
from typing import Optional

_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)

_TRIAL_BOUND = 100_000
_TRIAL_PRIME_CACHE_MAX = 5_000_000
# Pollard p−1 stage-1 bound (smooth factors of n−1 cofactors).
_P1_B1 = 100_000

Result = Optional[bool]

_primes_cache: tuple[int, ...] | None = None
_primes_cache_limit = 0


def _primes_upto(limit: int) -> tuple[int, ...]:
    global _primes_cache, _primes_cache_limit
    need = min(int(limit), _TRIAL_PRIME_CACHE_MAX)
    if _primes_cache is None or _primes_cache_limit < need:
        from .prime_sieve import _sieve_primes_upto

        _primes_cache = tuple(_sieve_primes_upto(need))
        _primes_cache_limit = need
    return _primes_cache


def _adaptive_trial_bound(m: int) -> int:
    bits = m.bit_length()
    if bits <= 40:
        return _TRIAL_BOUND
    if bits <= 80:
        return 1_000_000
    return _TRIAL_PRIME_CACHE_MAX


def _trial_split(m: int, bound: int) -> tuple[dict[int, int], int]:
    """Peel prime powers ≤ bound. Returns (factors, remaining)."""
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


def _F_value(fac: dict[int, int]) -> int:
    prod = 1
    for q, e in fac.items():
        prod *= pow(q, e)
    return prod


def _cofactor_is_prime(c: int, *, parallel: bool) -> bool:
    if c < 2:
        return False
    if c < 10_000:
        from .is_prime import _is_prime_small

        return _is_prime_small(c)
    from .is_prime import is_prime

    return bool(is_prime(c, parallel=parallel))


def _pollard_p1(n: int, B1: int = _P1_B1) -> int | None:
    """Pollard p−1 stage 1 (fixed B1). Returns a proper factor or None."""
    if n < 4 or n % 2 == 0:
        return 2 if n % 2 == 0 and n > 2 else None
    a = 2
    for p in _primes_upto(B1):
        if p > B1:
            break
        # a := a^{p^e} mod n with p^e ≤ B1 maximal
        pe = p
        while pe <= B1 // p:
            pe *= p
        a = pow(a, pe, n)
        if a == 0:
            return None
    g = math.gcd(a - 1, n)
    if 1 < g < n:
        return g
    return None


def _try_split_cofactor(c: int, *, parallel: bool) -> int | None:
    """Proper factor of composite c, or None.

    Order: trial → Fermat → Brent → p−1 → short cubic → ECM.
    Brent before long cubic: ~1e9 factors often fall in tens of ms.
    """
    from .factor_ecm import ecm_factor
    from .factor_lehman import _c_lehman_ready, _ceil_icbrt, lehman_factor
    from .prime_factors import _brent, _fermat_split

    fac, rem = _trial_split(c, _adaptive_trial_bound(c))
    if fac:
        if rem == 1:
            return min(fac)
        if rem > 1 and rem < c:
            return min(fac)

    f = _fermat_split(c)
    if f is not None and 1 < f < c:
        return f

    for cv in range(1, 64):
        g = _brent(c, cv)
        if 1 < g < c:
            return g

    f = _pollard_p1(c)
    if f is not None:
        return f

    cub = _ceil_icbrt(c)
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


def _factor_enough(n: int, *, parallel: bool) -> dict[int, int] | None:
    """Factor n−1 until product of proven prime powers F > √n.

    Does **not** require factoring the full cofactor R = (n−1)/F.
    Returns the prime→exponent map for F, or None if F cannot be built.
    """
    target = math.isqrt(n)
    m = n - 1
    fac: dict[int, int] = {}
    bound = _adaptive_trial_bound(m)
    peeled, rem = _trial_split(m, bound)
    fac.update(peeled)
    stack: list[int] = [rem] if rem > 1 else []
    splits = 0
    max_splits = 48

    def done() -> bool:
        F = _F_value(fac)
        return F > target or n < 2 * F * F * F

    if done():
        return fac

    while stack and not done():
        c = stack.pop()
        if c <= 1:
            continue
        cb = _adaptive_trial_bound(c)
        sub, r2 = _trial_split(c, cb)
        for p, e in sub.items():
            fac[p] = fac.get(p, 0) + e
        if r2 == 1:
            if done():
                return fac
            continue
        c = r2
        if _cofactor_is_prime(c, parallel=parallel):
            fac[c] = fac.get(c, 0) + 1
            if done():
                return fac
            continue
        if splits >= max_splits:
            return None
        splits += 1
        f = _try_split_cofactor(c, parallel=parallel)
        if f is None or f <= 1 or f >= c:
            return None
        stack.append(f)
        stack.append(c // f)

    return fac if done() else None


def _pocklington(n: int, primes_of_F: list[int]) -> Result:
    """Pocklington: each q | F needs some fixed base a (bases may differ)."""
    # Cache a^{n-1} mod n so we do not recompute per q.
    fermat_ok: dict[int, bool] = {}
    for q in primes_of_F:
        found = False
        for a in _BASES:
            if a % n == 0:
                return n == a
            ok = fermat_ok.get(a)
            if ok is None:
                ok = pow(a, n - 1, n) == 1
                fermat_ok[a] = ok
            if not ok:
                return False  # exact composite
            if math.gcd(pow(a, (n - 1) // q, n) - 1, n) == 1:
                found = True
                break
        if not found:
            return None
    return True


def nm1_primality(n: int, *, parallel: bool = True) -> Result:
    """Try to settle primality of ``n`` via n−1 (Pocklington).

    True / False / None (inconclusive).
    """
    if n < 2:
        return False
    if n in (2, 3, 5, 7):
        return True
    if n % 2 == 0 or n % 3 == 0 or n % 5 == 0:
        return False

    # Fast composite filter (deterministic).
    for a in _BASES[:6]:  # 2..13 enough for almost all composites
        if a % n == 0:
            return n == a
        if pow(a, n - 1, n) != 1:
            return False

    fac = _factor_enough(n, parallel=parallel)
    if fac is None:
        return None

    # Sanity: F divides n−1
    F = _F_value(fac)
    if F <= 1 or (n - 1) % F != 0:
        return None
    sqrt_n = math.isqrt(n)
    cubic = n < 2 * F * F * F
    if F <= sqrt_n and not cubic:
        return None

    # Largest primes first → fewer witness conditions in practice
    primes = sorted(fac.keys(), reverse=True)
    target = sqrt_n if F > sqrt_n else _icbrt(n)
    used: list[int] = []
    prod = 1
    # Rebuild from largest primes with their full exponents in fac
    for q in primes:
        e = fac[q]
        for _ in range(e):
            if prod > target:
                break
            prod *= q
        used.append(q)
        if prod > target:
            break

    decided = _pocklington(n, used)
    if decided is True and prod <= sqrt_n and not _bls_cubic_ok(n, prod):
        return None
    return decided


def _icbrt(n: int) -> int:
    if n < 8:
        return 0 if n < 1 else 1
    x = 1 << ((n.bit_length() + 2) // 3)
    while True:
        y = (2 * x + n // (x * x)) // 3
        if y >= x:
            return x
        x = y


def _bls_cubic_ok(n: int, F: int) -> bool:
    """BLS n^{1/3} extra: n < 2F³, R = rF+s, r odd or s²−4r not square."""
    if F <= 1 or (n - 1) % F != 0:
        return False
    if n >= 2 * F * F * F:
        return False
    R = (n - 1) // F
    if R <= 0 or math.gcd(F, R) != 1:
        return False
    r, s = divmod(R, F)
    if not (0 < s < F):
        return False
    if r & 1:
        return True
    disc = s * s - 4 * r
    if disc < 0:
        return True
    root = math.isqrt(disc)
    return root * root != disc


def nm1_ready(n: int) -> bool:
    """Whether multi-limb / hard paths should try n−1."""
    if n >= (1 << 64):
        return True
    from .factor_lehman import cubic_complete_ready

    return cubic_complete_ready(n)
