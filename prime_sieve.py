"""
Deterministic prime enumeration: π(n), n-th prime, ranges.

Odds-only Eratosthenes for moderate n; Lucy–Hedgehog for large π(n);
segmented sieve for long ranges / large n-th primes. No RNG, no
Miller–Rabin, no prime libraries.
"""

from __future__ import annotations

import math
from bisect import bisect_right

from is_prime import _parse_n

# Tiny table used by next/prev_prime (first prime above 10^4).
_TABLE_LIMIT = 10_007
# Full odds-only sieve is the winner below this (Lucy has setup cost).
_SIEVE_PI_MAX = 2_000_000
# Lucy–Hedgehog needs O(√n) memory; refuse to allocate more than this.
_LUCY_MAX_V = 5_000_000  # n ≤ 25e12
# Segmented sieve window (bytes of odds ≈ this).
_SEG_ODDS = 262_144  # 256 KiB → 512 Ki odd numbers → span 524_288

_primes_cache: tuple[int, ...] = ()
_primes_cache_lim = -1
_lucy_kernel = None


def _parse_k(k: int) -> int:
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("k must be a positive int")
    if k < 1:
        raise ValueError("k must be a positive integer (k >= 1)")
    return k


def _sieve_primes_upto(limit: int) -> tuple[int, ...]:
    """Odds-only Eratosthenes. Index i ↔ 2i+1."""
    if limit < 2:
        return ()
    if limit == 2:
        return (2,)
    n = (limit + 1) >> 1
    mark = bytearray(b"\x01") * n
    mark[0] = 0
    r = math.isqrt(limit)
    for i in range(1, (r + 1) >> 1):
        if mark[i]:
            p = (i << 1) + 1
            start = (p * p) >> 1
            mark[start:n:p] = b"\x00" * (((n - 1 - start) // p) + 1)
    out = [2]
    # 2*i+1 <= limit ⇔ i <= (limit-1)//2 = n-1 when limit odd, else smaller
    last = (limit - 1) >> 1
    out.extend(((i << 1) + 1) for i in range(1, last + 1) if mark[i])
    return tuple(out)


def _primes_upto_cached(limit: int) -> tuple[int, ...]:
    global _primes_cache, _primes_cache_lim
    if limit <= _primes_cache_lim:
        if limit == _primes_cache_lim:
            return _primes_cache
        return _primes_cache[: bisect_right(_primes_cache, limit)]
    # Grow at least 2× to amortize (still exact for this call).
    grow = limit if _primes_cache_lim < 0 else max(limit, _primes_cache_lim * 2)
    _primes_cache = _sieve_primes_upto(grow)
    _primes_cache_lim = grow
    if grow == limit:
        return _primes_cache
    return _primes_cache[: bisect_right(_primes_cache, limit)]


def _odd_sieve_marks(limit: int) -> bytearray:
    """mark[i] = 1 iff 2i+1 is an odd prime ≤ limit."""
    n = (limit + 1) >> 1
    mark = bytearray(b"\x01") * n
    mark[0] = 0
    r = math.isqrt(limit)
    for i in range(1, (r + 1) >> 1):
        if mark[i]:
            p = (i << 1) + 1
            start = (p * p) >> 1
            mark[start:n:p] = b"\x00" * (((n - 1 - start) // p) + 1)
    return mark


def _count_sieve(n: int) -> int:
    if n < 2:
        return 0
    if n == 2:
        return 1
    mark = _odd_sieve_marks(n)
    last = (n - 1) >> 1
    # mark[0] is 1 (not prime); sum over 1..last
    return 1 + sum(mark[1 : last + 1])


def _primes_in_range(lo: int, hi: int) -> list[int]:
    """Primes p with lo ≤ p < hi. Requires lo ≥ 2."""
    if hi <= lo:
        return []
    if lo <= 2 < hi:
        return [2] + _primes_in_range(3, hi)
    if (lo & 1) == 0:
        lo += 1
        if hi <= lo:
            return []
    limit = math.isqrt(hi - 1)
    base = _primes_upto_cached(limit)
    # Odds-only segment: index i ↔ lo + 2i
    width = ((hi - 1 - lo) >> 1) + 1
    mark = bytearray(b"\x01") * width
    for p in base:
        if p == 2:
            continue
        # first odd multiple of p at or after lo, at least p^2
        start = ((lo + p - 1) // p) * p
        if (start & 1) == 0:
            start += p
        pp = p * p
        if start < pp:
            start = pp
            if (start & 1) == 0:
                start += p
        if start >= hi:
            continue
        off = (start - lo) >> 1
        mark[off:width:p] = b"\x00" * (((width - 1 - off) // p) + 1)
    return [lo + (i << 1) for i, bit in enumerate(mark) if bit]


def _nth_prime_upper(k: int) -> int:
    """Strict upper bound on the k-th prime (1-based)."""
    if k < 6:
        return 12
    ln = math.log(k)
    lnl = math.log(ln)
    # Dusart / Rosser–Schoenfeld with slack for float + tiny k.
    return int(k * (ln + lnl)) + 3


def _nth_prime_sieve(k: int) -> int:
    bound = _nth_prime_upper(k)
    while True:
        ps = _primes_upto_cached(bound)
        if len(ps) >= k:
            return ps[k - 1]
        bound += (bound >> 1) + 32


def _nth_prime_segmented(k: int) -> int:
    bound = _nth_prime_upper(k)
    while True:
        if math.isqrt(bound) > 50_000_000:
            # Fall back: expand bound only after a full scan failed.
            pass
        base = _primes_upto_cached(math.isqrt(bound))
        count = 0
        lo = 2
        found = None
        while lo <= bound:
            hi = min(lo + (_SEG_ODDS << 1), bound + 1)
            if lo == 2:
                chunk = _primes_in_range(2, hi)
            else:
                chunk = _seg_odds(lo, hi, base)
            nch = len(chunk)
            if count + nch >= k:
                found = chunk[k - count - 1]
                break
            count += nch
            lo = hi
        if found is not None:
            return found
        bound += (bound >> 1) + 32


def _seg_odds(lo: int, hi: int, base: tuple[int, ...]) -> list[int]:
    """Primes in [lo, hi), lo odd or even, hi exclusive. 2 not in range."""
    if hi <= lo:
        return []
    if (lo & 1) == 0:
        lo += 1
        if hi <= lo:
            return []
    width = ((hi - 1 - lo) >> 1) + 1
    mark = bytearray(b"\x01") * width
    for p in base:
        if p == 2:
            continue
        start = ((lo + p - 1) // p) * p
        if (start & 1) == 0:
            start += p
        pp = p * p
        if start < pp:
            start = pp
            if (start & 1) == 0:
                start += p
        if start >= hi:
            continue
        off = (start - lo) >> 1
        mark[off:width:p] = b"\x00" * (((width - 1 - off) // p) + 1)
    return [lo + (i << 1) for i, bit in enumerate(mark) if bit]


def _lucy_python(n: int) -> int:
    v = math.isqrt(n)
    smalls = [i - 1 for i in range(v + 1)]
    larges = [0] * (v + 1)
    for i in range(1, v + 1):
        larges[i] = n // i - 1
    for p in range(2, v + 1):
        if smalls[p - 1] == smalls[p]:
            continue
        pc = smalls[p - 1]
        p2 = p * p
        n_div_p2 = n // p2
        cap = v if v < n_div_p2 else n_div_p2
        for i in range(1, cap + 1):
            d = i * p
            if d <= v:
                larges[i] -= larges[d] - pc
            else:
                larges[i] -= smalls[n // d] - pc
        if p2 <= v:
            for i in range(v, p2 - 1, -1):
                smalls[i] -= smalls[i // p] - pc
    return larges[1]


def _get_lucy_kernel():
    global _lucy_kernel
    if _lucy_kernel is not None:
        return _lucy_kernel
    try:
        import numpy as np
        from numba import njit
    except ImportError:
        _lucy_kernel = False
        return _lucy_kernel

    @njit(cache=True)
    def _lucy_u64(n):
        v = int(n ** 0.5)
        while v * v > n:
            v -= 1
        while (v + 1) * (v + 1) <= n:
            v += 1
        smalls = np.empty(v + 1, dtype=np.int64)
        larges = np.empty(v + 1, dtype=np.int64)
        for i in range(v + 1):
            smalls[i] = i - 1
        larges[0] = 0
        for i in range(1, v + 1):
            larges[i] = n // i - 1
        for p in range(2, v + 1):
            if smalls[p - 1] == smalls[p]:
                continue
            pc = smalls[p - 1]
            p2 = p * p
            n_div_p2 = n // p2
            cap = v if v < n_div_p2 else n_div_p2
            for i in range(1, cap + 1):
                d = i * p
                if d <= v:
                    larges[i] -= larges[d] - pc
                else:
                    larges[i] -= smalls[n // d] - pc
            if p2 <= v:
                i = v
                while i >= p2:
                    smalls[i] -= smalls[i // p] - pc
                    i -= 1
        return int(larges[1])

    _lucy_kernel = _lucy_u64
    return _lucy_kernel


def _prime_count_large(n: int) -> int:
    v = math.isqrt(n)
    if v > _LUCY_MAX_V:
        raise ValueError(
            f"prime_count(n) needs O(sqrt(n)) memory; n is too large "
            f"(sqrt(n)={v}, max {_LUCY_MAX_V})"
        )
    # Numba pays off once √n is large; skip it below ~1e8 (import/JIT).
    if n >= 100_000_000 and n.bit_length() <= 63:
        kern = _get_lucy_kernel()
        if kern:
            return int(kern(n))
    return _lucy_python(n)


def primes(n: int | str) -> list[int]:
    """All primes ≤ n, ascending. Empty for n < 2."""
    n_int = _parse_n(n)
    if n_int < 2:
        return []
    return list(_primes_upto_cached(n_int))


def primerange(low: int | str, high: int | str) -> list[int]:
    """Primes p with low ≤ p < high (Python range convention)."""
    lo = _parse_n(low)
    hi = _parse_n(high)
    if hi <= lo or hi <= 2:
        return []
    if lo < 2:
        lo = 2
    # Whole prefix: reuse the growing cache (no second sieve).
    if lo == 2 and hi - 1 <= max(_primes_cache_lim, _SIEVE_PI_MAX):
        return list(_primes_upto_cached(hi - 1))
    return _primes_in_range(lo, hi)


def prime_count(n: int | str) -> int:
    """π(n): number of primes ≤ n."""
    n_int = _parse_n(n)
    if n_int < 2:
        return 0
    if n_int <= _primes_cache_lim:
        return bisect_right(_primes_cache, n_int)
    if n_int <= _SIEVE_PI_MAX:
        return _count_sieve(n_int)
    return _prime_count_large(n_int)


def nth_prime(k: int) -> int:
    """The k-th prime (1-based): nth_prime(1) == 2."""
    k_int = _parse_k(k)
    if k_int <= 5:
        return (2, 3, 5, 7, 11)[k_int - 1]
    bound = _nth_prime_upper(k_int)
    if bound <= _SIEVE_PI_MAX * 5:
        return _nth_prime_sieve(k_int)
    return _nth_prime_segmented(k_int)
