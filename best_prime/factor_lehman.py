"""Two-band cubic factor search (Lehman + rising-product wheel).

Reorganizes the classical interval [2, √n] instead of walking it:

* **Small band.** Every candidate ≤ ⌈n^{1/3}⌉ is still examined, but as
  30-wheel *batches*: one ``gcd(∏ batch, n)`` proves a whole block has
  no factor (Pollard–Strassen / product-tree idea, no FFT).
* **Balanced band.** If every prime factor exceeds n^{1/3}, Lehman's
  theorem says a short Fermat window on some multiple ``k n`` with
  ``k ≤ n^{1/3}`` splits n. That replaces the long walk from n^{1/3}
  up to √n.

Engines:

* OpenMP C (``lehman_factor_u128``) when ``4·k·n`` fits in 128 bits.
* **Multiprecision pure Python** (unlimited ``int`` for ``4kn``) for a
  complete proof while ``⌈n^{1/3}⌉ ≤ LEHMAN_COMPLETE_CUB_MAX_MP``.
* Callers may pass a smaller ``k_max`` for a probe that is not a proof.

Deterministic. No RNG. Not Miller–Rabin.
"""

from __future__ import annotations

import math

from .is_prime import _load_c_core, _parse_n

# 30-wheel steps starting at 7 (residues 1,7,11,13,17,19,23,29).
_W30 = (4, 2, 4, 2, 4, 6, 2, 6)

_PRODUCT_BATCH = 128

# Pure-Python complete budget (64-bit and multiprecision).
LEHMAN_COMPLETE_CUB_MAX = 3_000_000
# Multiprecision complete: Python int 4kn; practical wall-clock bound.
LEHMAN_COMPLETE_CUB_MAX_MP = 8_000_000
# C engine domain sentinel (uint64 k); real gate is 4kn ≤ 128 bits.
LEHMAN_COMPLETE_CUB_MAX_C = (1 << 63) - 1

# Quadratic residues mod 64 (bit i set ⇒ i is a square mod 64).
_SQ_OK_MOD64 = 0
for _s in range(32):
    _SQ_OK_MOD64 |= 1 << ((_s * _s) & 63)


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
    need = (cub + 16 * k - 1) // (16 * k)
    s = math.isqrt(need)
    return s if s * s == need else s + 1


def _is_perfect_square(x: int) -> bool:
    """Fast reject via mod-64 QR, then isqrt."""
    if x < 0:
        return False
    if ((_SQ_OK_MOD64 >> (x & 63)) & 1) == 0:
        return False
    s = math.isqrt(x)
    return s * s == x


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


U64_CUBIC_ISQRT_MIN = 10_000_000


def cubic_complete_ready(n: int) -> bool:
    """True when a complete cubic proof is available for ``is_prime``.

    * OpenMP C when ``4·k·n`` fits in 128 bits, or
    * multiprecision pure Python when ``⌈n^{1/3}⌉ ≤ LEHMAN_COMPLETE_CUB_MAX_MP``.

    Hard 64-bit only when ``isqrt(n) ≥ U64_CUBIC_ISQRT_MIN``.
    """
    cub = _ceil_icbrt(n)
    if n < (1 << 64) and math.isqrt(n) < U64_CUBIC_ISQRT_MIN:
        return False
    if _c_lehman_ready() and _fits_c_lehman(n, cub):
        return True
    return cub <= LEHMAN_COMPLETE_CUB_MAX_MP


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
    """Multiprecision Lehman k-loop (Python int). ``k_max`` inclusive."""
    for k in range(1, k_max + 1):
        fourkn = 4 * k * n
        a0 = _ceil_isqrt(fourkn)
        extra = _lehman_extra(cub, k)
        # Incremental a^2: start at a0^2, step 2a+1
        a = a0
        a2 = a0 * a0
        a_end = a0 + extra
        while a <= a_end:
            b2 = a2 - fourkn
            if _is_perfect_square(b2):
                b = math.isqrt(b2)
                g = math.gcd(a + b, n)
                if 1 < g < n:
                    return g
                g = math.gcd(abs(a - b), n)
                if 1 < g < n:
                    return g
            a2 += (a << 1) + 1
            a += 1
    return None


def lehman_factor(
    n: int | str, *, k_max: int | None = None, parallel: bool = True
) -> int | None:
    """Return a nontrivial factor of ``n``, or ``None`` if none is found.

    Default budget is *complete* when the cube root is under the C / MP cap
    (``None`` ⇒ 0, 1, or prime). A smaller ``k_max`` is a probe only.
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
    if use_c:
        complete_cap = LEHMAN_COMPLETE_CUB_MAX_C
    else:
        complete_cap = LEHMAN_COMPLETE_CUB_MAX_MP
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
