"""
k-th prime strictly less than n.

Mirror of next_prime: tiny/moderate sieve, interval sieve for large k,
otherwise a backward 30030-wheel walk + is_prime. Fully deterministic.
"""

from __future__ import annotations

import math

from .is_prime import _parse_n
from .next_prime import (
    _RES_INVALID,
    _W30030,
    _WINDOW_SIEVE_MIN_N,
    _fermat_composite_fast,
    _get_deep_primes,
    _get_prefilter,
    _get_res_30030,
    _get_steps_30030,
    _prove_prime_candidate,
    _sieve_odd_window,
    _span_guess,
    _window_span,
)
from .prime_sieve import _SIEVE_PI_MAX, _parse_k, _primes_in_range, _primes_upto_cached

_SMALL_PREV = (13, 11, 7, 5, 3, 2)


def _align_wheel30030_down(cand: int) -> tuple[int, int] | None:
    """Largest 30030-wheel number ≤ cand and its step index, or None if < 17."""
    if cand < 17:
        return None
    res = _get_res_30030()
    r = cand % _W30030
    while res[r] == _RES_INVALID:
        cand -= 1
        if cand < 17:
            return None
        r -= 1
        if r < 0:
            r = _W30030 - 1
    return cand, int(res[r])


def _prev_prime_wheel(n: int, k: int, parallel: bool) -> int:
    steps = _get_steps_30030()
    nW = len(steps)
    aligned = _align_wheel30030_down(n - 1)
    pre = _get_prefilter()
    found = 0

    def _hit(p: int) -> int | None:
        nonlocal found
        found += 1
        if found == k:
            return p
        return None

    if aligned is None:
        for p in _SMALL_PREV:
            if p < n:
                got = _hit(p)
                if got is not None:
                    return got
        raise ValueError(f"no {k}-th prime strictly less than {n}")

    cand, wi = aligned
    deep = _get_deep_primes()
    pre = tuple(p for p in deep if p >= 17) if deep else pre
    while cand >= 17:
        lim = math.isqrt(cand)
        composite = False
        proven = False
        for p in pre:
            if p > lim:
                proven = True
                break
            if cand % p == 0:
                composite = True
                break
        if not composite and not proven:
            if _fermat_composite_fast(cand):
                composite = True
        if not composite and (proven or _prove_prime_candidate(cand, parallel)):
            got = _hit(cand)
            if got is not None:
                return got
        wi -= 1
        if wi < 0:
            wi = nW - 1
        cand -= steps[wi]
    for p in _SMALL_PREV:
        if p < n:
            got = _hit(p)
            if got is not None:
                return got
    raise ValueError(f"no {k}-th prime strictly less than {n}")


def _prev_prime_window(n: int, k: int, parallel: bool) -> int | None:
    """Deep window sieve walking downward. None if abandoned."""
    if n < _WINDOW_SIEVE_MIN_N:
        return None
    primes = _get_deep_primes()
    found = 0
    hi = n
    span = _window_span(n, k)
    for _expand in range(48):
        lo = hi - span
        if lo < 2:
            lo = 2
        if lo >= hi:
            break
        cands = _sieve_odd_window(lo, hi, primes)
        for c in reversed(cands):
            if c >= n or c < 2:
                continue
            if _fermat_composite_fast(c):
                continue
            if _prove_prime_candidate(c, parallel):
                found += 1
                if found == k:
                    return c
        if lo <= 2:
            break
        hi = lo
        span = min(span + (span >> 1), 16_000_000)
    return None


def _try_interval_prev(n: int, k: int) -> int | None:
    if k < 8:
        return None
    span = _span_guess(n, k)
    hi = n
    lo = n - span
    collected: list[int] = []
    end = hi
    for _ in range(12):
        if lo < 2:
            lo = 2
        if lo >= end:
            break
        if math.isqrt(max(end - 1, 1)) > 2_000_000:
            break
        chunk = _primes_in_range(lo, end)
        collected = chunk + collected
        if len(collected) >= k:
            return collected[-k]
        if lo == 2:
            break
        extra = max(span, end - lo)
        end = lo
        lo = lo - extra
    return None


def prev_primes(n: int | str, k: int | None = None, *, parallel: bool = True):
    """Yield primes strictly less than ``n``, descending.

    If ``k`` is set, stop after ``k`` primes (raises ``ValueError`` if
    fewer than ``k`` exist). If ``k`` is ``None``, yield until 2. Large
    ``k`` uses an interval sieve only while ``√n ≤ 2_000_000``; otherwise
    a backward 30030-wheel + ``is_prime`` walk.
    """
    n_int = _parse_n(n)
    if k is not None:
        k_int = _parse_k(k)
        p = prev_prime(n_int, 1, parallel=parallel)
        yield p
        for _ in range(k_int - 1):
            p = prev_prime(p, 1, parallel=parallel)
            yield p
        return
    p = n_int
    while p > 2:
        p = prev_prime(p, 1, parallel=parallel)
        yield p


def prev_prime(n: int | str, k: int = 1, *, parallel: bool = True) -> int:
    """Return the ``k``-th prime strictly less than ``n``.

    Raises ``ValueError`` if fewer than ``k`` primes exist below ``n``.
    Same ``n`` contract as ``is_prime``; ``k`` is a positive ``int``.
    """
    n_int = _parse_n(n)
    k_int = _parse_k(k)
    if n_int <= 2:
        raise ValueError(f"no {k_int}-th prime strictly less than {n_int}")

    # Every prime < n is ≤ n-1; a full sieve is cheapest while n is moderate.
    if n_int - 1 <= _SIEVE_PI_MAX:
        ps = _primes_upto_cached(n_int - 1)
        if len(ps) >= k_int:
            return ps[-k_int]
        raise ValueError(f"no {k_int}-th prime strictly less than {n_int}")

    got = _try_interval_prev(n_int, k_int)
    if got is not None:
        return got
    if n_int >= _WINDOW_SIEVE_MIN_N:
        got = _prev_prime_window(n_int, k_int, parallel)
        if got is not None:
            return got
    return _prev_prime_wheel(n_int, k_int, parallel)


def main(argv: list[str] | None = None) -> None:
    """``python -m best_prime.prev_prime n [k]`` — same as the ``prev-prime`` script."""
    from .prime_cli import prev_prime_main

    prev_prime_main(argv)


if __name__ == "__main__":
    main()
