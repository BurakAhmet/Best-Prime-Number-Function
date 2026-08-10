"""
Smallest prime strictly greater than n.

Candidate generation is deterministic: a tiny prime table for small n, then
the project's 30030-wheel (coprime to 2·3·5·7·11·13) plus a short prefilter
of our own small primes. Exact primality is always delegated to ``is_prime``
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

from is_prime import (  # noqa: E402
    _DATA_DIR,
    _SMALL_LIMIT,
    _get_steps_30030,
    _load_c_core,
    _parse_n,
    is_prime,
)

# 2·3·5·7·11·13. Wheel numbers start at 17; 2,3,5,7,11,13 are handled first.
_W30030 = 30_030
_RES_INVALID = 0xFFFF
# First prime strictly above _SMALL_LIMIT (10_000). Table must include it.
_TABLE_LIMIT = 10_007
# Prefilter primes (already past the wheel primes) before calling is_prime.
_PREFILTER_LIMIT = 1_021

_small_table: tuple[int, ...] | None = None
_prefilter: tuple[int, ...] | None = None
_res30030: array | None = None


def _sieve_primes_upto(limit: int) -> tuple[int, ...]:
    """Deterministic Eratosthenes. Ours — not a prime-library engine."""
    if limit < 2:
        return ()
    mark = bytearray(b"\x01") * (limit + 1)
    mark[0] = 0
    mark[1] = 0
    r = math.isqrt(limit)
    for p in range(2, r + 1):
        if mark[p]:
            start = p * p
            mark[start : limit + 1 : p] = b"\x00" * (((limit - start) // p) + 1)
    return tuple(i for i in range(2, limit + 1) if mark[i])


def _get_small_table() -> tuple[int, ...]:
    global _small_table
    if _small_table is None:
        _small_table = _sieve_primes_upto(_TABLE_LIMIT)
    return _small_table


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


def _next_prime_table(n: int) -> int:
    tbl = _get_small_table()
    i = bisect_right(tbl, n)
    if i < len(tbl):
        return tbl[i]
    # n is at least the last tabulated prime; caller should use the wheel.
    return _next_prime_wheel(n, True)


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


def _next_prime_wheel(n: int, parallel: bool) -> int:
    steps = _get_steps_30030()
    nW = len(steps)
    cand, wi = _align_wheel30030(n + 1)
    pre = _get_prefilter()
    # n ≥ _SMALL_LIMIT ⇒ cand > _PREFILTER_LIMIT, so cand % p == 0 ⇒ composite.
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
            return cand
        cand += steps[wi]
        wi += 1
        if wi == nW:
            wi = 0


def next_prime(n: int | str, *, parallel: bool = True) -> int:
    """Return the smallest prime strictly greater than ``n``.

    Fully deterministic. Accepts the same ``n`` as ``is_prime`` (natural
    ``int`` or decimal ``str``). ``parallel`` is forwarded to ``is_prime``
    and never changes the result.
    """
    n_int = _parse_n(n)
    if n_int < _SMALL_LIMIT:
        return _next_prime_table(n_int)
    return _next_prime_wheel(n_int, parallel)


def _print_result(arg: str, value: int, threads: int) -> None:
    print(f"TEST:    {arg} ({len(arg)} chars)")
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
                "usage: next-prime [--serial] n\n"
                "Smallest prime strictly greater than n (deterministic)."
            )
            return 0
        if a == "--serial":
            serial = True
        elif a.startswith("-") and not _looks_like_int_token(a):
            print(f"unknown option: {a}", file=sys.stderr)
            return 2
        else:
            positional.append(a)
    if not positional:
        print("usage: next-prime [--serial] n", file=sys.stderr)
        return 2
    arg = positional[0]
    try:
        n = _parse_n(arg)
    except (TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    parallel = not serial
    value = next_prime(n, parallel=parallel)
    from is_prime import _thread_count

    threads = (
        _thread_count
        if (parallel and n >= _SMALL_LIMIT and _load_c_core())
        else 1
    )
    _print_result(str(n), value, threads)
    return 0


def main() -> None:
    raise SystemExit(_main(sys.argv[1:]))


if __name__ == "__main__":
    main()
