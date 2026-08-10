"""
Deterministic prime enumeration: π(n), n-th prime, ranges.

Odds-only Eratosthenes for moderate n; Lucy–Hedgehog for large π(n);
segmented sieve for long ranges / large n-th primes. No RNG, no
Miller–Rabin, no prime libraries.
"""

from __future__ import annotations

import math
import sys
from array import array
from bisect import bisect_left, bisect_right
from collections.abc import Iterator

# φ(x,a) recurses once per prime index; 64-bit uses a = π(2^16) = 6542.
if sys.getrecursionlimit() < 20_000:
    sys.setrecursionlimit(20_000)

from is_prime import _parse_n

# Tiny table used by next/prev_prime (first prime above 10^4).
_TABLE_LIMIT = 10_007
# Odds-only count sieve wins E2E below this (Lucy has Θ(√n) tables).
_SIEVE_PI_MAX = 20_000_000
# Lucy–Hedgehog uses two int64 arrays of length √n.
# 5e7 × 8 × 2 ≈ 800 MiB → n ≤ 2.5e15. Not a cap on n itself at 5e6.
_LUCY_MAX_V = 50_000_000
# Lucy tables stop at √n = 5e7 (n ≤ 2.5e15). Larger n uses Meissel–Lehmer
# (including every 64-bit n, e.g. 18446744073709551557).
PRIME_COUNT_MAX_N = (1 << 64) - 1
_ML_PRIME_MAX = 1 << 32  # primes stored as uint32 through 2^32
# π(2^k) from OEIS A007053 (Oliveira e Silva); seeds ML memo + tests.
_PI_POW2 = {
    0: 0, 1: 1, 2: 2, 3: 4, 4: 6, 5: 11, 6: 18, 7: 31, 8: 54, 9: 97,
    10: 172, 11: 309, 12: 564, 13: 1028, 14: 1900, 15: 3512, 16: 6542,
    17: 12251, 18: 23000, 19: 43390, 20: 82025, 21: 155611, 22: 295947,
    23: 564163, 24: 1077871, 25: 2063689, 26: 3957809, 27: 7603553,
    28: 14630843, 29: 28192750, 30: 54400028, 31: 105097565,
    32: 203280221, 33: 393615806, 34: 762939111, 35: 1480206279,
    36: 2874398515, 37: 5586502348, 38: 10866266172, 39: 21151907950,
    40: 41203088796, 41: 80316571436, 42: 156661034233, 43: 305761713237,
    44: 597116381732, 45: 1166746786182, 46: 2280998753949,
    47: 4461632979717, 48: 8731188863470, 49: 17094432576778,
    50: 33483379603407, 51: 65612899915304, 52: 128625503610475,
    53: 252252704148404, 54: 494890204904784, 55: 971269945245201,
    56: 1906879381028850, 57: 3745011184713964, 58: 7357400267843990,
    59: 14458792895301660, 60: 28423094496953330, 61: 55890484045084135,
    62: 109932807585469973, 63: 216289611853439384,
    64: 425656284035217743,
}
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


def _lucy_tables(n: int):
    """Compact int64 Lucy tables (8 bytes/entry, not Python ints)."""
    v = math.isqrt(n)
    # smalls[i] = i-1 initially; range(-1, v) is -1,0,...,v-1.
    smalls = array("q", range(-1, v))
    larges = array("q", ((n // i - 1) if i else 0 for i in range(v + 1)))
    return v, smalls, larges


def _lucy_python(n: int) -> int:
    v, smalls, larges = _lucy_tables(n)
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
    return int(larges[1])


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
    if v <= _LUCY_MAX_V:
        if n >= 10_000_000 and n.bit_length() <= 63:
            kern = _get_lucy_kernel()
            if kern:
                return int(kern(n))
        return _lucy_python(n)
    return _pi_ml(n, force_lehmer=True)


def _icbrt(n: int) -> int:
    if n < 8:
        return 1 if n else 0
    x = 1 << ((n.bit_length() + 2) // 3)
    while True:
        y = (2 * x + n // (x * x)) // 3
        if y >= x:
            break
        x = y
    while x * x * x > n:
        x -= 1
    while (x + 1) * (x + 1) * (x + 1) <= n:
        x += 1
    return x


# Meissel–Lehmer state.
_ml_primes: tuple[int, ...] | array = ()
_ml_plim = -1
_phi_memo: dict[tuple[int, int], int] = {}
_uint32_sieve_kernel = None


def _ml_init_memo() -> dict[int, int]:
    d = {0: 0, 1: 0}
    for k, v in _PI_POW2.items():
        d[1 << k] = v
    return d


_pi_memo: dict[int, int] = _ml_init_memo()


def _get_uint32_sieve_kernel():
    """Cached Numba bit-sieve; do not rebuild the njit wrapper per call."""
    global _uint32_sieve_kernel
    if _uint32_sieve_kernel is not None:
        return _uint32_sieve_kernel
    try:
        import numpy as np
        from numba import njit
    except ImportError:
        _uint32_sieve_kernel = False
        return _uint32_sieve_kernel

    @njit(cache=True)
    def _fill(limit_):
        nbits = (limit_ + 1) >> 1
        nwords = (nbits + 63) >> 6
        bits = np.empty(nwords, dtype=np.uint64)
        ones = np.uint64(0xFFFFFFFFFFFFFFFF)
        for w in range(nwords):
            bits[w] = ones
        bits[0] &= ~np.uint64(1)  # 1 is not prime
        r = int(limit_ ** 0.5)
        hi = (r + 1) >> 1
        for i in range(1, hi):
            if (bits[i >> 6] >> np.uint64(i & 63)) & np.uint64(1):
                p = (i << 1) + 1
                start = (p * p) >> 1
                step = p
                for j in range(start, nbits, step):
                    bits[j >> 6] &= ~(np.uint64(1) << np.uint64(j & 63))
        cnt = 1  # 2
        for i in range(1, nbits):
            if 2 * i + 1 > limit_:
                break
            if (bits[i >> 6] >> np.uint64(i & 63)) & np.uint64(1):
                cnt += 1
        out = np.empty(cnt, dtype=np.uint32)
        out[0] = 2
        k = 1
        for i in range(1, nbits):
            p = 2 * i + 1
            if p > limit_:
                break
            if (bits[i >> 6] >> np.uint64(i & 63)) & np.uint64(1):
                out[k] = p
                k += 1
        return out

    _uint32_sieve_kernel = _fill
    return _uint32_sieve_kernel


def _sieve_uint32_primes(limit: int):
    """Primes ≤ limit as compact uint32 (array), for the ML prime list."""
    if limit <= _SIEVE_PI_MAX * 5:
        return _primes_upto_cached(limit)
    kern = _get_uint32_sieve_kernel()
    if not kern:
        return _primes_upto_cached(limit)
    arr = kern(int(limit))
    return array("I", arr)


def _ensure_ml_primes(limit: int) -> None:
    """Primes ≤ min(limit, 2^32) for the ML prime list."""
    global _ml_primes, _ml_plim
    if limit < 2:
        limit = 2
    if limit > _ML_PRIME_MAX:
        limit = _ML_PRIME_MAX
    if limit <= _ml_plim:
        return
    if limit <= _SIEVE_PI_MAX * 5:
        _ml_primes = _primes_upto_cached(limit)
    else:
        _ml_primes = _sieve_uint32_primes(limit)
    _ml_plim = limit


def _pi_list(x: int) -> int:
    if x < 2:
        return 0
    return bisect_right(_ml_primes, x)


def _phi(x: int, a: int) -> int:
    """#{k ≤ x : every prime factor of k is > p_a}. φ(x, 0) = x."""
    if x < 1:
        return 0
    if a <= 0:
        return x
    while a > 0 and _ml_primes[a - 1] > x:
        a -= 1
        if a == 0:
            return x
    if a == 1:
        return (x + 1) // 2
    key = (x, a)
    hit = _phi_memo.get(key)
    if hit is not None:
        return hit
    pa = int(_ml_primes[a - 1])
    if a < len(_ml_primes) and x < int(_ml_primes[a]) * int(_ml_primes[a]):
        r = _pi_ml(x) - a + 1
        _phi_memo[key] = r
        return r
    r = _phi(x, a - 1) - _phi(x // pa, a - 1)
    _phi_memo[key] = r
    return r


def _lucy_or_sieve_pi(n: int) -> int:
    """π(n) when √n fits the Lucy tables (or smaller sieve)."""
    if n < 2:
        return 0
    if n <= _SIEVE_PI_MAX:
        return _count_sieve(n)
    if n >= 10_000_000 and n.bit_length() <= 63:
        kern = _get_lucy_kernel()
        if kern:
            return int(kern(n))
    return _lucy_python(n)


def _pi_ml(n: int, *, force_lehmer: bool = False) -> int:
    """Memoized π(n): Lucy when √n fits, else Lehmer; tests may force Lehmer."""
    if n < 2:
        return 0
    hit = _pi_memo.get(n)
    if hit is not None:
        return hit
    v = math.isqrt(n)
    if not force_lehmer and v <= _LUCY_MAX_V:
        r = _lucy_or_sieve_pi(n)
        _pi_memo[n] = r
        return r
    _ensure_ml_primes(v)
    if n <= _ml_plim:
        r = _pi_list(n)
        _pi_memo[n] = r
        return r
    a = _pi_ml(math.isqrt(v))
    b = _pi_ml(v)
    c = _pi_ml(_icbrt(n))
    res = _phi(n, a) + (b + a - 2) * (b - a + 1) // 2
    # Classic Lehmer P2/P3. Subcalls use Lucy whenever √w fits.
    # 64-bit n needs primes through ~2^32 (generated once).
    for idx in range(a + 1, b + 1):
        p = int(_ml_primes[idx - 1])
        w = n // p
        res -= _pi_ml(w)
        if idx <= c:
            bi = _pi_ml(math.isqrt(w))
            for j in range(idx, bi + 1):
                res -= _pi_ml(w // int(_ml_primes[j - 1])) - (j - 1)
    _pi_memo[n] = res
    return res


def _reset_ml_state() -> None:
    """Test helper: drop Lehmer memos (does not drop the Lucy/Numba kernels)."""
    global _ml_primes, _ml_plim, _pi_memo
    _ml_primes = ()
    _ml_plim = -1
    _phi_memo.clear()
    _pi_memo = _ml_init_memo()


def primes(n: int | str) -> list[int]:
    """All primes ≤ n, ascending. Empty for n < 2.

    Uses the shared cache when ``n`` is moderate; otherwise drains a
    segmented ``primerange`` so we do not double-sieve.
    """
    n_int = _parse_n(n)
    if n_int < 2:
        return []
    if n_int <= max(_primes_cache_lim, _SIEVE_PI_MAX):
        return list(_primes_upto_cached(n_int))
    return list(primerange(2, n_int + 1))


def primerange(low: int | str, high: int | str) -> Iterator[int]:
    """Primes ``p`` with ``low ≤ p < high`` (half-open, like ``range``).

    Yields one prime at a time (sympy-compatible). Materialize with
    ``list(primerange(a, b))`` when you need a list. Walks the prime cache
    when it already covers the interval; otherwise sieves in 256 KiB
    segments so a long range never holds every prime at once.
    """
    lo = _parse_n(low)
    hi = _parse_n(high)
    if hi <= lo or hi <= 2:
        return
    if lo < 2:
        lo = 2
    # Cache already covers [2, hi).
    if hi - 1 <= _primes_cache_lim:
        ps = _primes_cache
        i = bisect_left(ps, lo)
        end = bisect_left(ps, hi)
        for j in range(i, end):
            yield ps[j]
        return
    # Small prefix: one odds-only sieve, then yield from the tuple.
    if lo == 2 and hi - 1 <= _SIEVE_PI_MAX:
        yield from _primes_upto_cached(hi - 1)
        return
    # Segmented sieve; yield each window so peak RAM stays O(segment).
    if lo <= 2 < hi:
        yield 2
        lo = 3
    if (lo & 1) == 0:
        lo += 1
    span = _SEG_ODDS << 1
    start = lo
    while start < hi:
        seg_hi = start + span
        if seg_hi > hi:
            seg_hi = hi
        need = math.isqrt(seg_hi - 1) if seg_hi > 1 else 2
        base = _primes_upto_cached(need)
        for p in _seg_odds(start, seg_hi, base):
            yield p
        start = seg_hi


def prime_count(n: int | str) -> int:
    """π(n): number of primes ≤ n.

    ``n`` may be any natural number up to ``PRIME_COUNT_MAX_N`` (2⁶⁴−1).
    Moderate n uses an odds-only sieve / Lucy–Hedgehog; larger n uses
    memoized Meissel–Lehmer (correct for every 64-bit n; the hardest
    sizes need a one-time prime list through ∼2³²).
    """
    n_int = _parse_n(n)
    if n_int > PRIME_COUNT_MAX_N:
        raise ValueError(
            f"prime_count(n) supports n <= {PRIME_COUNT_MAX_N} "
            f"(got n={n_int})"
        )
    if n_int < 2:
        return 0
    if n_int <= _primes_cache_lim:
        return bisect_right(_primes_cache, n_int)
    if n_int <= _SIEVE_PI_MAX:
        return _count_sieve(n_int)
    return _prime_count_large(n_int)


def _nth_prime_pi_search(k: int) -> int:
    """Smallest n with π(n) ≥ k, i.e. p_k. log₂(p_k) calls to prime_count."""
    ln = math.log(k)
    lnl = math.log(ln)
    lo = max(2, int(k * (ln + lnl - 1.0)) - 2)
    hi = _nth_prime_upper(k)
    # Guarantee π(hi) ≥ k (float slack on the Dusart-style bound).
    while prime_count(hi) < k:
        hi += (hi >> 2) + 32
    while lo < hi:
        mid = lo + ((hi - lo) >> 1)
        if prime_count(mid) < k:
            lo = mid + 1
        else:
            hi = mid
    return lo


def nth_prime(k: int) -> int:
    """The k-th prime (1-based): nth_prime(1) == 2."""
    k_int = _parse_k(k)
    if k_int <= 5:
        return (2, 3, 5, 7, 11)[k_int - 1]
    bound = _nth_prime_upper(k_int)
    # A full sieve to p_k also fills the shared cache; worth it while cheap.
    if bound <= _SIEVE_PI_MAX:
        return _nth_prime_sieve(k_int)
    return _nth_prime_pi_search(k_int)
