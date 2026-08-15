"""Deterministic FastECPP (computed class polynomials).

Walks fundamental discriminants, computes ``H_D`` in-tree
(``classpoly.hilbert_class_poly``), and reuses the Atkin–Morain
Cornacchia / Cantor–Zassenhaus / Goldwasser–Kilian ladder in
``primality_ecpp``. No RNG. No probable-prime control flow. No external
prime library.

M1: general 100-digit (``P100_DIGIT``).
M2: general 300- and 500-digit (``P300_DIGIT``, ``P500_DIGIT``).
M3: general 1000-digit (``P1000_DIGIT``); 10k-digit / 10 s is the
north-star and is measured, not claimed.
"""

from __future__ import annotations

import math
import os
import time
from typing import Optional

from .classpoly import class_number, hilbert_class_poly_cached_or_table
from .product_tree import batch_smooth_kernel, peel_kernel
from .primality_ecpp import (
    CLASS_NUMBER_1_D,
    Result,
    _PEEL_CACHE,
    _fermat_composite,
    _is_fundamental_discriminant,
    _jacobi,
    _peel_m,
    _prove_q_stack,
    _try_discriminant,
    _try_discriminant_small_h,
    cornacchia,
    gk_min_q,
)

# Inclusive bit window where is_prime may invoke this engine.
# 10k-digit n is ~33_219 bits. Below FASTECPP_MIN_BITS: existing ECPP / BLS.
FASTECPP_MIN_BITS = 256
FASTECPP_MAX_BITS = 40_000
# Cofactor downrun may use computed H_D down to the complete-engine wall.
FASTECPP_RECURSE_MIN_BITS = 80
# Default table used only when the caller does not pass d_max / h_cap.
FASTECPP_D_MAX = 4000
FASTECPP_H_CAP = 64
FASTECPP_TRIAL_BOUND = 1_000_000
# Cornacchia hits collected before one product-tree peel.
FASTECPP_BATCH = 32


def scaled_batch(bits: int) -> int:
    if bits <= 400:
        return 1
    if bits <= 1_700:
        return 16
    if bits <= 3_500:
        return 32
    # Each Cornacchia is a 10k-digit Tonelli. Do not wait for 32 hits.
    return 1

_proving: set[int] = set()


def _trace(msg: str) -> None:
    if os.environ.get("FASTECPP_TRACE"):
        print(f"[fastecpp] {msg}", flush=True)


def _in_band(n: int) -> bool:
    bits = n.bit_length()
    return FASTECPP_MIN_BITS <= bits <= FASTECPP_MAX_BITS


def _recurse_ok(n: int) -> bool:
    return n.bit_length() >= FASTECPP_RECURSE_MIN_BITS


def scaled_d_max(bits: int) -> int:
    if bits <= 400:
        return 4_000
    if bits <= 700:
        return 12_000
    if bits <= 1_100:
        return 25_000
    if bits <= 1_700:
        return 40_000
    if bits <= 3_500:
        return 80_000
    return 20_000


def scaled_h_cap(bits: int) -> int:
    if bits <= 400:
        return 64
    if bits <= 1_700:
        return 128
    return 256


def scaled_trial_bound(bits: int) -> int:
    if bits <= 400:
        return 1_000_000
    if bits <= 1_700:
        return 5_000_000
    return 1_000_000


def is_prime_fastecpp_max_ms(bits: int) -> int | None:
    """Wall-clock cap for ``is_prime`` FastECPP. ``None`` = no cap.

    ≤500-digit (M2) and 1000-digit (M3) run to completion. Wider n
    (10k-digit) get a short try so the CLI does not hang, then
    ``UnsettledPrimalityError``.
    """
    if bits <= 3_500:
        return None
    return 15_000


def _prove_q_fast(
    q: int, n: int, *, parallel: bool, proven: bool, max_h: int
) -> Result:
    if proven:
        return True
    if q <= 1 or q >= n:
        return None
    from .primality_nm1 import _prove_strictly_smaller

    _trace(f"prove_q digits={len(str(q))} bits={q.bit_length()}")
    decided = _prove_strictly_smaller(
        q, n, parallel=parallel, allow_ecpp=True, max_h=16
    )
    _trace(f"prove_q smaller/ecpp16 -> {decided}")
    if decided is not None:
        return decided
    if _recurse_ok(q):
        return fastecpp_primality(q, parallel=parallel, skip_small_h=True)
    return None


def _usable_from_kernel(n: int, m: int, kernel: int) -> bool:
    if m <= 2:
        return False
    g = math.gcd(m, n)
    if 1 < g < n:
        return True
    _smooth, rem = peel_kernel(m, kernel)
    min_q = gk_min_q(n)
    if rem <= 1 or rem >= n or rem < min_q:
        return False
    if rem > 1 and m // rem >= 2 and not _fermat_composite(rem):
        return True
    # Trial leftover is composite. A short deterministic ECM may expose
    # a Goldwasser–Kilian q. Cap is small so the 300-digit hang does not
    # return: only deepen when some smooth kernel already came out.
    if m // rem < 2:
        return False
    bits = rem.bit_length()
    if bits <= 512 or bits > 8_000:
        return False
    from .factor_ecm import ecm_factor
    from .primality_nm1 import _ecm_max_ms

    budget = min(400, _ecm_max_ms(bits))
    deadline = time.perf_counter() + budget / 1000.0
    cur = rem
    for _ in range(4):
        if time.perf_counter() >= deadline or cur < min_q:
            break
        if not _fermat_composite(cur):
            return cur > 1 and m // cur >= 2 and cur >= min_q
        f = ecm_factor(cur, max_ms=max(1, int((deadline - time.perf_counter()) * 1000)))
        if f is None or f <= 1 or f >= cur:
            break
        cur = cur // f
        while cur % f == 0:
            cur //= f
    return cur > 1 and cur < n and cur >= min_q and m // cur >= 2 and not _fermat_composite(cur)


def _discriminants(d_max: int, h_cap: int) -> list[tuple[int, int]]:
    """Fundamental ``(D, h)`` in increasing ``|D|``, excluding class-number-1.

    Uses the committed catalog when it covers ``d_max`` / ``h_cap``.
    """
    from ._fundamentals import D_CATALOG_MAX, FUNDAMENTAL_DH, H_CATALOG_MAX

    if d_max <= D_CATALOG_MAX and h_cap <= H_CATALOG_MAX:
        return [(d, h) for d, h in FUNDAMENTAL_DH if -d <= d_max and h <= h_cap]
    out: list[tuple[int, int]] = []
    seen_h1 = set(CLASS_NUMBER_1_D)
    for absd in range(3, d_max + 1):
        D = -absd
        if D % 4 not in (0, 1) or D in seen_h1:
            continue
        if not _is_fundamental_discriminant(D):
            continue
        h = class_number(D)
        if 2 <= h <= h_cap:
            out.append((D, h))
    return out


def _try_pending(
    n: int,
    pending: list[tuple[int, int, int]],
    *,
    parallel: bool,
    trial_bound: int,
    h_cap: int,
) -> Result:
    """Product-tree peel of a |D|-ordered batch, then Hilbert + GK."""
    if not pending:
        return None
    ms: list[int] = []
    owners: list[int] = []
    for i, (_D, t, _h) in enumerate(pending):
        for m in (n + 1 - t, n + 1 + t):
            if m > 2:
                ms.append(m)
                owners.append(i)
    if not ms:
        return None
    kernels = batch_smooth_kernel(ms, trial_bound)
    by_i: dict[int, list[tuple[int, int]]] = {}
    for m, ker, i in zip(ms, kernels, owners):
        by_i.setdefault(i, []).append((m, ker))
    for i, (D, t, h) in enumerate(pending):
        ok = False
        for m, ker in by_i.get(i, []):
            if _usable_from_kernel(n, m, ker):
                ok = True
                break
        if not ok:
            continue
        _trace(f"usable D={D} h={h} n_digits={len(str(n))}")
        try:
            coeffs = hilbert_class_poly_cached_or_table(D)
        except (ValueError, ArithmeticError):
            continue
        if len(coeffs) - 1 > h_cap:
            continue
        dec = _try_discriminant_small_h(
            D, coeffs, n, parallel=parallel, max_h=h_cap
        )
        _trace(f"try D={D} -> {dec}")
        if dec is not None:
            return dec
    return None


def _walk_computed(
    n: int,
    *,
    parallel: bool,
    d_max: int,
    h_cap: int,
    trial_bound: int,
    deadline: float | None,
) -> Result:
    pending: list[tuple[int, int, int]] = []
    for D, h in _discriminants(d_max, h_cap):
        if deadline is not None and time.perf_counter() >= deadline:
            break
        try:
            jac = _jacobi(D, n)
        except ValueError:
            continue
        if jac == 0:
            g = math.gcd(-D, n)
            if 1 < g < n:
                return False
            continue
        if jac != 1:
            continue
        cr = cornacchia(D, n)
        if cr[0] == "factor":
            g = cr[1]
            return False if 1 < g < n else None
        if cr[0] != "ok":
            continue
        t = cr[1]
        if t <= 0:
            continue
        pending.append((D, t, h))
        if len(pending) >= scaled_batch(n.bit_length()):
            dec = _try_pending(
                n,
                pending,
                parallel=parallel,
                trial_bound=trial_bound,
                h_cap=h_cap,
            )
            pending.clear()
            if dec is not None:
                return dec
    return _try_pending(
        n, pending, parallel=parallel, trial_bound=trial_bound, h_cap=h_cap
    )


def fastecpp_primality(
    n: int,
    *,
    parallel: bool = True,
    skip_small_h: bool = False,
    d_max: int | None = None,
    h_cap: int | None = None,
    max_ms: int | None = None,
) -> Optional[bool]:
    """True / False / None. Computed-``H_D`` Atkin–Morain.

    ``skip_small_h``: caller already ran ``ecpp_primality(..., max_h=16)``.
    Still tries the 13 class-number-1 discriminants when that is cheap
    (recursive cofactor). ``parallel`` must not change which ``D`` wins.
    ``d_max`` / ``h_cap`` default to a bit-length table. ``max_ms`` is a
    wall-clock abort for the computed walk (``None`` = no cap).
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if (n & 1) == 0:
        return False
    if math.isqrt(n) ** 2 == n:
        return False
    if n in _proving:
        return None
    if len(_proving) >= n.bit_length():
        return None
    from .primality_ecpp import _cert_stack, _ecpp_search

    bits = n.bit_length()
    use_d_max = FASTECPP_D_MAX if d_max is None else int(d_max)
    use_h_cap = FASTECPP_H_CAP if h_cap is None else int(h_cap)
    if d_max is None:
        use_d_max = scaled_d_max(bits)
    if h_cap is None:
        use_h_cap = scaled_h_cap(bits)
    trial_bound = scaled_trial_bound(bits)
    deadline = None if max_ms is None else time.perf_counter() + max_ms / 1000.0

    _proving.add(n)
    _prove_q_stack.append(_prove_q_fast)
    _PEEL_CACHE.clear()
    _cert_stack.append({})
    try:
        # In the ≥256-bit band the transcribed table is not the general
        # engine. Try h=1 (cheap; P131) then computed H_D. Smaller n
        # still use the table.
        _trace(f"start digits={len(str(n))} bits={bits} d_max={use_d_max} h_cap={use_h_cap}")
        # h=1 is cheap at 100–300 digits (P131). At 10k digits each of
        # the 13 discriminants is a full Tonelli; skip and use the catalog.
        if bits > 3_500:
            _trace("skip h=1 / transcribed (huge n)")
        elif skip_small_h or _in_band(n):
            for D in CLASS_NUMBER_1_D:
                dec = _try_discriminant(D, n, parallel=parallel, max_h=1)
                if dec is not None:
                    _trace(f"h=1 D={D} -> {dec}")
                    return dec
            _trace("h=1 miss")
        else:
            decided, _rec = _ecpp_search(n, parallel=parallel, max_h=16)
            if decided is not None:
                return decided
        if not _recurse_ok(n):
            return None
        return _walk_computed(
            n,
            parallel=parallel,
            d_max=use_d_max,
            h_cap=use_h_cap,
            trial_bound=trial_bound,
            deadline=deadline,
        )
    finally:
        _cert_stack.pop()
        _prove_q_stack.pop()
        _proving.discard(n)
