"""Two-band cubic factor search (Lehman + rising-product wheel).

Reorganizes the classical interval [2, √n] instead of walking it:

* **Small band.** Every candidate ≤ ⌈n^{1/3}⌉ is still examined, but as
  30-wheel *batches*: one ``gcd(∏ batch, n)`` proves a whole block has
  no factor (Pollard–Strassen / product-tree idea, no FFT).
* **Balanced band.** If every prime factor exceeds n^{1/3}, Lehman's
  theorem says a short Fermat window on some multiple ``k n`` with
  ``k ≤ n^{1/3}`` splits n. That replaces the long walk from n^{1/3}
  up to √n.

Deterministic. No RNG. Not a Miller–Rabin test. Mid-size 64-bit
``is_prime`` stays exact trial through √n; on the hard path this module
is the **fallback** after n−1 Pocklington (see ``primality_nm1``).

Literature this synthesis sits on: Lehman 1974; Pollard 1974 / Strassen
1977; Bernstein product/remainder trees; Hales–Hiary 2024 (Lehman for
power divisors); Harvey 2020 and Harvey–Hittmeir 2021 (theoretical
n^{1/5}, not implemented here).
"""

from __future__ import annotations

import math

from .is_prime import _load_c_core, _parse_n

# 30-wheel steps starting at 7 (residues 1,7,11,13,17,19,23,29).
_W30 = (4, 2, 4, 2, 4, 6, 2, 6)

# Rising-product batch length. math.prod of this many ~n^{1/3} integers
# stays cheap in CPython; one gcd then covers the block.
_PRODUCT_BATCH = 128

# A full budget of k ≤ ceil(n^{1/3}) is complete (None ⇒ prime / 0 / 1)
# only while the cube root is this small.
# - Pure Python: 3e6 covers every 64-bit n.
# - OpenMP C: no artificial cub cap — completeness is gated only by
#   4·k·n fitting in 128 bits (see _fits_c_lehman / cubic_complete_ready).
#   LEHMAN_COMPLETE_CUB_MAX_C is kept as a documented upper bound on the
#   uint64 cube-root domain of the C engine (~2^64−1), not a product limit.
LEHMAN_COMPLETE_CUB_MAX = 3_000_000
LEHMAN_COMPLETE_CUB_MAX_C = (1 << 63) - 1


def _ceil_isqrt(n: int) -> int:
    s = math.isqrt(n)
    return s if s * s == n else s + 1


def _ceil_icbrt(n: int) -> int:
    """Smallest integer c with c³ ≥ n."""
    if n <= 1:
        return n
    x = 1 << ((n.bit_length() + 2) // 3)
    while True:
        y = (2 * x + n // (x * x)) // 3
        if y >= x:
            while x * x * x > n:
                x -= 1
            return x if x * x * x == n else x + 1
        x = y


def _lehman_extra(cub: int, k: int) -> int:
    """Integer overestimate of n^{1/6} / (4 √k), never short of the theorem."""
    # Smallest e ≥ 0 with 16 k e² ≥ cub ≥ n^{1/3}.
    need = (cub + 16 * k - 1) // (16 * k)
    s = math.isqrt(need)
    return s if s * s == need else s + 1


def _scan_batch(n: int, batch: list[int]) -> int | None:
    """Proper factor from a batch whose product shares a factor with n."""
    g = math.gcd(math.prod(batch), n)
    if g == 1:
        return None
    if 1 < g < n:
        return g
    acc = 1
    for p in batch:
        acc *= p
        g = math.gcd(acc, n)
        if 1 < g < n:
            return g
        if n % p == 0:
            return p
    return None


def _rising_product_factor(n: int, limit: int) -> int | None:
    """Factor of n in (5, limit] via 30-wheel rising-product gcds."""
    if limit < 7:
        return None
    batch: list[int] = []
    p = 7
    wi = 0
    while p <= limit:
        batch.append(p)
        if len(batch) == _PRODUCT_BATCH:
            f = _scan_batch(n, batch)
            if f is not None:
                return f
            batch.clear()
        p += _W30[wi]
        wi = (wi + 1) & 7
    if batch:
        return _scan_batch(n, batch)
    return None


# Hard 64-bit is_prime uses cubic C only when trial is the slow path.
# Mid-size (isqrt < 10^7, e.g. 10^9+7 / 12-digit) stays u64_wheel_c.
U64_CUBIC_ISQRT_MIN = 10_000_000


def cubic_complete_ready(n: int) -> bool:
    """True when OpenMP C can finish a full cubic proof used by ``is_prime``.

    Gated only by the C engine: ``lehman_factor_u128`` present and
    ``4·k·n`` fits in 128 bits for every ``k ≤ ⌈n^{1/3}⌉``. No separate
    artificial cube-root product cap. Hard 64-bit only when
    ``isqrt(n) ≥ U64_CUBIC_ISQRT_MIN`` (mid-size stays wheel trial).
    """
    cub = _ceil_icbrt(n)
    if not (_c_lehman_ready() and _fits_c_lehman(n, cub)):
        return False
    if n >= (1 << 64):
        return True
    return math.isqrt(n) >= U64_CUBIC_ISQRT_MIN


def _fits_c_lehman(n: int, cub: int) -> bool:
    """4·k·n fits in 128 bits for every k ≤ cub."""
    if n.bit_length() > 128 or cub <= 0:
        return False
    return (4 * cub * n).bit_length() <= 128


_C_LEHMAN_BOUND = False


def _c_lehman_ready() -> bool:
    global _C_LEHMAN_BOUND
    lib = _load_c_core()
    if not lib or not hasattr(lib, "lehman_factor_u128"):
        return False
    if not _C_LEHMAN_BOUND:
        import ctypes

        lib.lehman_factor_u128.argtypes = [
            ctypes.c_uint64,
            ctypes.c_uint64,
            ctypes.c_uint64,
            ctypes.c_int,
        ]
        lib.lehman_factor_u128.restype = ctypes.c_uint64
        _C_LEHMAN_BOUND = True
    return True


def _c_lehman_factor(n: int, budget: int, *, parallel: bool) -> int | None:
    """C core. 0 from C means no factor. Caller must check ``_c_lehman_ready``."""
    lib = _load_c_core()
    lo = n & ((1 << 64) - 1)
    hi = n >> 64
    f = int(lib.lehman_factor_u128(lo, hi, int(budget), 1 if parallel else 0))
    return f if f else None


def _lehman_windows(n: int, cub: int, k_max: int) -> int | None:
    """Lehman k-loop. ``k_max`` inclusive, already ≤ cub."""
    for k in range(1, k_max + 1):
        fourkn = 4 * k * n
        a0 = _ceil_isqrt(fourkn)
        extra = _lehman_extra(cub, k)
        for a in range(a0, a0 + extra + 1):
            b2 = a * a - fourkn
            b = math.isqrt(b2)
            if b * b != b2:
                continue
            g = math.gcd(a + b, n)
            if 1 < g < n:
                return g
            g = math.gcd(abs(a - b), n)
            if 1 < g < n:
                return g
    return None


def lehman_factor(
    n: int | str, *, k_max: int | None = None, parallel: bool = True
) -> int | None:
    """Return a nontrivial factor of ``n``, or ``None`` if none is found.

    With the default budget (``k_max is None`` and cube root under the
    complete cap) the search is *complete*: ``None`` means ``n`` is 0, 1,
    or prime. OpenMP C raises the cap to ``LEHMAN_COMPLETE_CUB_MAX_C``
    so the multi-limb CLI default is a full proof. A smaller ``k_max`` is a
    probe, not a primality proof.

    ``is_prime`` uses this when ``cubic_complete_ready`` is true: every
    ``n ≥ 2^{64}`` in budget, and hard 64-bit n (``isqrt ≥ 10^7``).
    Smaller 64-bit n stay exact trial through ``⌊√n⌋``.
    """
    n_int = _parse_n(n)
    if n_int < 4:
        return None
    if n_int % 2 == 0:
        return 2
    if n_int % 3 == 0:
        return 3
    if n_int % 5 == 0:
        return 5 if n_int > 5 else None

    r = math.isqrt(n_int)
    if r * r == n_int and 1 < r < n_int:
        return r

    cub = _ceil_icbrt(n_int)
    use_c = _c_lehman_ready() and _fits_c_lehman(n_int, cub)
    complete_cap = LEHMAN_COMPLETE_CUB_MAX_C if use_c else LEHMAN_COMPLETE_CUB_MAX
    if k_max is None:
        budget = cub if cub <= complete_cap else complete_cap
    else:
        if k_max < 0:
            raise ValueError("k_max must be >= 0")
        budget = min(cub, k_max)

    if use_c:
        return _c_lehman_factor(n_int, budget, parallel=parallel)

    f = _rising_product_factor(n_int, budget)
    if f is not None:
        return f
    return _lehman_windows(n_int, cub, budget)
