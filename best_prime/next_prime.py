"""
k-th prime strictly greater than n.

Candidate generation is deterministic: a tiny prime table for small n, an
interval sieve when k is large and √bound is practical, otherwise the
project's 30030-wheel (coprime to 2·3·5·7·11·13) plus a short prefilter of
our own small primes. Exact primality is always delegated to ``is_prime``
(OpenMP C / stdlib wheel / Numba / AKS) — no Miller–Rabin, no prime libraries.

End-to-end CLI ``TIME`` starts at import (``t0``) and stops after the answer.
"""

from __future__ import annotations

import math
import os
import sys
import time
from array import array
from bisect import bisect_right

t0 = time.perf_counter_ns()

from .is_prime import (  # noqa: E402
    _DATA_DIR,
    _SMALL_LIMIT,
    _get_steps_30030,
    _load_c_core,
    _parse_n,
    is_prime,
)
from .prime_sieve import (  # noqa: E402
    _TABLE_LIMIT,
    _parse_k,
    _primes_in_range,
    _primes_upto_cached,
    _sieve_primes_upto,
)

# 2·3·5·7·11·13. Wheel numbers start at 17; 2,3,5,7,11,13 are handled first.
_W30030 = 30_030
_RES_INVALID = 0xFFFF
# Prefilter primes (already past the wheel primes) before calling is_prime.
_PREFILTER_LIMIT = 1_021
# Interval sieve: only when k is large enough to repay setup and √hi is cheap.
_SIEVE_MIN_K = 8
_SIEVE_ISQRT_MAX = 2_000_000

_prefilter: tuple[int, ...] | None = None
_res30030: array | None = None


def _get_small_table() -> tuple[int, ...]:
    return _primes_upto_cached(_TABLE_LIMIT)


def _get_prefilter() -> tuple[int, ...]:
    """Odd primes 17.._PREFILTER_LIMIT (wheel already kills 2,3,5,7,11,13)."""
    global _prefilter
    if _prefilter is None:
        _prefilter = tuple(p for p in _sieve_primes_upto(_PREFILTER_LIMIT) if p >= 17)
    return _prefilter


def _get_res_30030() -> array:
    """Residue → 30030-wheel index (0xFFFF if gcd(r, 30030) ≠ 1)."""
    global _res30030
    if _res30030 is None:
        path = os.path.join(_DATA_DIR, "res30030.u16")
        buf = array("H")
        with open(path, "rb") as f:
            buf.fromfile(f, _W30030)
        _res30030 = buf
    return _res30030


def _align_wheel30030(cand: int) -> tuple[int, int]:
    """Next 30030-wheel number ≥ cand and its step index."""
    res = _get_res_30030()
    r = cand % _W30030
    # cand ≥ 17 after the small-prime special cases, so we stay on the wheel.
    while res[r] == _RES_INVALID:
        cand += 1
        r += 1
        if r == _W30030:
            r = 0
    return cand, int(res[r])


def _span_guess(n: int, k: int) -> int:
    """Overestimate of the distance to the k-th prime after n."""
    ln = math.log(max(n, 2))
    lnk = math.log(max(k, 2))
    span = int(k * (ln + lnk + 4)) + 32
    if n < 20 and k >= 6:
        # Dusart-style p_k < k (ln k + ln ln k) plus slack; hi must reach p_k.
        pk = int(k * (lnk + math.log(lnk) + 2)) + 16
        span = max(span, pk - n)
    return max(span, 48)


def _try_interval(n: int, k: int) -> int | None:
    """k-th prime > n via a segmented sieve, or None if the bound is too hard."""
    if k < _SIEVE_MIN_K:
        return None
    span = _span_guess(n, k)
    lo = max(n + 1, 2)
    hi = lo + span
    if math.isqrt(max(hi - 1, 1)) > _SIEVE_ISQRT_MAX:
        return None
    collected: list[int] = []
    start = lo
    for _ in range(12):
        if math.isqrt(max(hi - 1, 1)) > _SIEVE_ISQRT_MAX:
            break
        collected.extend(_primes_in_range(start, hi))
        if len(collected) >= k:
            return collected[k - 1]
        extra = max(span, hi - max(n, 1))
        start = hi
        hi += extra
    return None


def _next_prime_wheel(n: int, k: int, parallel: bool) -> int:
    steps = _get_steps_30030()
    nW = len(steps)
    cand, wi = _align_wheel30030(n + 1)
    pre = _get_prefilter()
    # When n ≥ _SMALL_LIMIT, cand > _PREFILTER_LIMIT, so cand % p == 0 ⇒ composite.
    found = 0
    while True:
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
        if not composite and (proven or is_prime(cand, parallel=parallel)):
            found += 1
            if found == k:
                return cand
        cand += steps[wi]
        wi += 1
        if wi == nW:
            wi = 0


def _next_after(n: int, k: int, parallel: bool) -> int:
    got = _try_interval(n, k)
    if got is not None:
        return got
    return _next_prime_wheel(n, k, parallel)


def next_prime(n: int | str, k: int = 1, *, parallel: bool = True) -> int:
    """Return the ``k``-th prime strictly greater than ``n``.

    ``k=1`` (default) is the usual successor. Fully deterministic. Accepts
    the same ``n`` as ``is_prime`` (natural ``int`` or decimal ``str``).
    ``k`` must be a positive ``int``. ``parallel`` is forwarded to
    ``is_prime`` and never changes the result.
    """
    n_int = _parse_n(n)
    k_int = _parse_k(k)
    if n_int < _SMALL_LIMIT:
        tbl = _get_small_table()
        i = bisect_right(tbl, n_int)
        j = i + k_int - 1
        if j < len(tbl):
            return tbl[j]
        remaining = k_int - (len(tbl) - i)
        return _next_after(tbl[-1], remaining, parallel)
    return _next_after(n_int, k_int, parallel)


def _print_result(arg: str, k: int, value: int, threads: int) -> None:
    print(f"TEST:    {arg} ({len(arg)} chars)")
    print(f"K:       {k}")
    print(f"THREADS: {threads}")
    print(f"RESULT:  {value}")
    dt = time.perf_counter_ns() - t0
    print(f"TIME:    {dt} ns  ({dt / 1e6:.6f} ms)")


def _looks_like_int_token(s: str) -> bool:
    t = s.strip()
    if len(t) >= 2 and t[0] in "+-" and t[1].isdigit():
        return t[1:].replace("_", "").isdigit()
    return t[:1].isdigit() and t.replace("_", "").isdigit()


def _main(argv: list[str]) -> int:
    serial = False
    positional: list[str] = []
    for a in argv:
        if a in {"-h", "--help"}:
            print(
                "usage: next-prime [--serial] n [k]\n"
                "k-th prime strictly greater than n (deterministic; k defaults to 1)."
            )
            return 0
        if a == "--serial":
            serial = True
        elif a.startswith("-") and not _looks_like_int_token(a):
            print(f"unknown option: {a}", file=sys.stderr)
            return 2
        else:
            positional.append(a)
    if not positional or len(positional) > 2:
        print("usage: next-prime [--serial] n [k]", file=sys.stderr)
        return 2
    arg = positional[0]
    try:
        n = _parse_n(arg)
    except (TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    k = 1
    if len(positional) > 1:
        raw = positional[1].strip()
        digits = raw[1:] if raw.startswith("+") else raw
        if not digits.isdigit():
            print(f"invalid k: {positional[1]!r}", file=sys.stderr)
            return 2
        try:
            k = _parse_k(int(digits))
        except (TypeError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
    parallel = not serial
    value = next_prime(n, k, parallel=parallel)
    from .is_prime import _thread_count

    threads = (
        _thread_count
        if (parallel and n >= _SMALL_LIMIT and _load_c_core())
        else 1
    )
    _print_result(str(n), k, value, threads)
    return 0


def main() -> None:
    raise SystemExit(_main(sys.argv[1:]))


if __name__ == "__main__":
    main()
