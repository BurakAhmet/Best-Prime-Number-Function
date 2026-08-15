"""Deterministic Lenstra ECM (fixed sigma schedule; no RNG).

Factoring uses Suyama/Montgomery curves with ``sigma = 6, 7, 8, …``.
Stage 1 multiplies per prime power ``p^k ≤ B1`` (gcd on Z). Affine
Weierstrass ``_add`` / Jacobian ``_mul`` remain for ECPP point search.

Does not import ``ntheory`` / ``prime_factors`` (those import this module).
"""

from __future__ import annotations

import math
import time
from typing import Optional

Point = Optional[tuple[int, int]]


def _lcm_upto(lo: int, hi: int) -> int:
    """lcm(lo, lo+1, …, hi). ``lo`` may be 1."""
    if hi < lo:
        return 1
    # Prime-power covering: for each prime p, take the largest p^k ≤ hi
    # that is still ≥ lo, or the smallest p^k ≥ lo if that is ≤ hi.
    sieve = bytearray(b"\x01") * (hi + 1)
    if hi >= 0:
        sieve[0] = 0
    if hi >= 1:
        sieve[1] = 0
    r = math.isqrt(hi)
    for i in range(2, r + 1):
        if sieve[i]:
            start = i * i
            sieve[start : hi + 1 : i] = b"\x00" * (((hi - start) // i) + 1)
    acc = 1
    for p in range(2, hi + 1):
        if not sieve[p]:
            continue
        pk = p
        while pk <= hi // p:
            pk *= p
        # pk is the largest p^k ≤ hi. Use it if it is ≥ lo; else the
        # smallest p^k ≥ lo (which is just p if p ≥ lo).
        if pk >= lo:
            acc *= pk
        elif p >= lo:
            acc *= p
    return acc


def _add(p1: Point, p2: Point, a: int, n: int) -> tuple[Point, int]:
    """Elliptic add. Second value is a proper factor of n, or 1."""
    if p1 is None:
        return p2, 1
    if p2 is None:
        return p1, 1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2:
        if (y1 + y2) % n == 0:
            return None, 1
        num = (3 * x1 * x1 + a) % n
        den = (2 * y1) % n
    else:
        num = (y2 - y1) % n
        den = (x2 - x1) % n
    g = math.gcd(den, n)
    if g > 1:
        return None, g
    if den == 0:
        return None, 1
    inv = pow(den, -1, n)
    m = (num * inv) % n
    x3 = (m * m - x1 - x2) % n
    y3 = (m * (x1 - x3) - y1) % n
    return (x3, y3), 1


def _mul(k: int, p: Point, a: int, n: int) -> tuple[Point, int]:
    """Scalar mul via Jacobian coordinates (one inversion at the end)."""
    if p is None:
        return None, 1
    if k <= 0:
        return None, 1
    x, y = p
    # Jacobian (X:Y:Z) with affine (x,y) = (X/Z^2, Y/Z^3).
    jx, jy, jz = x % n, y % n, 1
    rx = ry = rz = 0  # rz=0 is infinity
    kk = k
    while kk:
        if kk & 1:
            if rz == 0:
                rx, ry, rz = jx, jy, jz
            else:
                g = _jac_add(rx, ry, rz, jx, jy, jz, n)
                if g is None:
                    g = _jac_dbl(rx, ry, rz, a, n)
                if isinstance(g, int):
                    return None, g
                rx, ry, rz = g
        kk >>= 1
        if kk:
            if jz == 0:
                continue
            g = _jac_dbl(jx, jy, jz, a, n)
            if isinstance(g, int):
                return None, g
            jx, jy, jz = g
    if rz == 0:
        return None, 1
    try:
        zinv = pow(rz, -1, n)
    except ValueError:
        g = math.gcd(rz, n)
        return None, g if 1 < g < n else 1
    z2 = (zinv * zinv) % n
    return ((rx * z2) % n, (ry * z2 * zinv) % n), 1


def _jac_dbl(x: int, y: int, z: int, a: int, n: int):
    if y == 0:
        return 0, 0, 0
    y2 = (y * y) % n
    s = (4 * x * y2) % n
    z2 = (z * z) % n
    m = (3 * x * x + a * z2 * z2) % n
    x3 = (m * m - 2 * s) % n
    y3 = (m * (s - x3) - 8 * y2 * y2) % n
    z3 = (2 * y * z) % n
    g = math.gcd(z3, n) if z3 else 1
    if 1 < g < n:
        return g
    return x3, y3, z3


def _jac_add(x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, n: int):
    if z1 == 0:
        return x2, y2, z2
    if z2 == 0:
        return x1, y1, z1
    z1z1 = (z1 * z1) % n
    z2z2 = (z2 * z2) % n
    u1 = (x1 * z2z2) % n
    u2 = (x2 * z1z1) % n
    s1 = (y1 * z2 * z2z2) % n
    s2 = (y2 * z1 * z1z1) % n
    h = (u2 - u1) % n
    r = (s2 - s1) % n
    if h == 0:
        if r == 0:
            return None  # caller should dbl; treat as inf-or-dbl signal
        return 0, 0, 0
    hh = (h * h) % n
    hhh = (h * hh) % n
    v = (u1 * hh) % n
    x3 = (r * r - hhh - 2 * v) % n
    y3 = (r * (v - x3) - s1 * hhh) % n
    z3 = (z1 * z2 * h) % n
    g = math.gcd(z3, n) if z3 else 1
    if 1 < g < n:
        return g
    return x3, y3, z3


def _curve(sigma: int, n: int) -> tuple[int, Point, int] | tuple[None, None, int]:
    """Weierstrass curve from integer sigma. Third value is a factor or 1."""
    x0 = sigma % n
    y0 = 1
    a = sigma % n
    b = (y0 * y0 - (x0 * x0 % n) * x0 - a * x0) % n
    # disc = -16 (4a³ + 27b²); a singular curve still yields a factor often.
    disc = (4 * pow(a, 3, n) + 27 * (b * b % n)) % n
    g = math.gcd(disc, n)
    if 1 < g < n:
        return None, None, g
    if g == n:
        return None, None, 1
    return a, (x0, y0), 1


def _schedule(bits: int) -> tuple[int, int, int]:
    """(B1, B2, max_sigma_count) from bit length. Fixed, no RNG.

    bits ≤ 160 keeps the historical triple so DEFAULT_N-class leftovers
    do not silently get a heavier ECM. Larger n (the 131-digit yardstick
    class) uses a p25-oriented Montgomery budget.
    """
    if bits <= 40:
        return 200, 1_000, 8
    if bits <= 64:
        return 2_000, 25_000, 24
    if bits <= 80:
        return 5_000, 50_000, 40
    if bits <= 100:
        return 2_000, 2_000, 20
    if bits <= 160:
        return 5_000, 5_000, 24
    if bits <= 280:
        return 8_000, 8_000, 8
    if bits <= 512:
        return 6_000, 6_000, 6
    # bits > 512 only — DEFAULT_N leftovers are 147-bit and never land here.
    if bits <= 1100:
        return 25_000, 200_000, 40
    if bits <= 1700:
        return 50_000, 250_000, 60
    return 8_000, 8_000, 8


_PRIME_CACHE: tuple[int, ...] = ()
_PRIME_CACHE_LIM = 0
_LCM_CACHE: dict[tuple[int, int], int] = {}


def _primes_upto(limit: int) -> tuple[int, ...]:
    global _PRIME_CACHE, _PRIME_CACHE_LIM
    need = int(limit)
    if need <= 2:
        return (2,) if need >= 2 else ()
    if _PRIME_CACHE_LIM >= need:
        return tuple(p for p in _PRIME_CACHE if p <= need)
    sieve = bytearray(b"\x01") * (need + 1)
    sieve[0:2] = b"\x00\x00"
    r = math.isqrt(need)
    for i in range(2, r + 1):
        if sieve[i]:
            sieve[i * i : need + 1 : i] = b"\x00" * (((need - i * i) // i) + 1)
    _PRIME_CACHE = tuple(i for i in range(2, need + 1) if sieve[i])
    _PRIME_CACHE_LIM = need
    return _PRIME_CACHE


def _lcm_upto_cached(lo: int, hi: int) -> int:
    key = (int(lo), int(hi))
    hit = _LCM_CACHE.get(key)
    if hit is not None:
        return hit
    val = _lcm_upto(lo, hi)
    if len(_LCM_CACHE) < 16:
        _LCM_CACHE[key] = val
    return val


def _mont_dbl(x: int, z: int, a24: int, n: int) -> tuple[int, int]:
    """Montgomery double in XZ coordinates. ``a24 = (A + 2) / 4``."""
    xp = (x + z) % n
    xm = (x - z) % n
    xp = (xp * xp) % n
    xm = (xm * xm) % n
    t = (xp - xm) % n
    return (xp * xm) % n, (t * (xm + a24 * t)) % n


def _mont_add(
    x1: int, z1: int, x2: int, z2: int, xd: int, zd: int, n: int
) -> tuple[int, int]:
    """Montgomery add: (P+Q) given P−Q = (xd : zd)."""
    a = ((x1 - z1) * (x2 + z2)) % n
    b = ((x1 + z1) * (x2 - z2)) % n
    ap = (a + b) % n
    am = (a - b) % n
    return (zd * ap * ap) % n, (xd * am * am) % n


def _mont_ladder(k: int, x: int, a24: int, n: int) -> tuple[int, int]:
    """x-only ladder. Input affine x (Z=1). Returns (X : Z) of [k]P."""
    if k <= 0:
        return 1, 0
    if k == 1:
        return x % n, 1
    x0, z0 = x % n, 1
    x1, z1 = _mont_dbl(x0, z0, a24, n)
    for bit in bin(k)[3:]:
        if bit == "0":
            x1, z1 = _mont_add(x0, z0, x1, z1, x, 1, n)
            x0, z0 = _mont_dbl(x0, z0, a24, n)
        else:
            x0, z0 = _mont_add(x0, z0, x1, z1, x, 1, n)
            x1, z1 = _mont_dbl(x1, z1, a24, n)
    return x0, z0


def _suyama(sigma: int, n: int):
    """Suyama Montgomery parameters. Returns ('ok', x, a24) or a factor."""
    u = (sigma * sigma - 5) % n
    v = (4 * sigma) % n
    x = pow(u, 3, n)
    num = (pow((v - u) % n, 3, n) * ((3 * u + v) % n)) % n
    den = (16 * x * v) % n
    g = math.gcd(den, n)
    if 1 < g < n:
        return ("factor", g)
    if g == n or den == 0:
        return None
    try:
        a24 = (num * pow(den, -1, n)) % n
    except ValueError:
        g = math.gcd(den, n)
        return ("factor", g) if 1 < g < n else None
    g = math.gcd(x, n)
    if 1 < g < n:
        return ("factor", g)
    if g == n:
        return None
    return ("ok", x, a24)


def _mont_stage1(x: int, a24: int, n: int, b1: int, primes: tuple[int, ...]) -> int | None:
    """Per-prime stage 1. Returns a proper factor or None."""
    xx, zz = x % n, 1
    for p in primes:
        if p > b1:
            break
        pe = p
        while pe <= b1 // p:
            pe *= p
        g = math.gcd(zz, n)
        if 1 < g < n:
            return g
        if g == n or zz == 0:
            return None
        try:
            inv = pow(zz, -1, n)
        except ValueError:
            g = math.gcd(zz, n)
            return g if 1 < g < n else None
        xx = (xx * inv) % n
        xx, zz = _mont_ladder(pe, xx, a24, n)
    g = math.gcd(zz, n)
    return g if 1 < g < n else None


def _mont_stage2(
    x: int, z: int, a24: int, n: int, b1: int, b2: int, primes: tuple[int, ...]
) -> int | None:
    """Cheap continuation: ladder each prime in (B1, B2]."""
    g = math.gcd(z, n)
    if 1 < g < n:
        return g
    if g == n or z == 0:
        return None
    try:
        xx = (x * pow(z, -1, n)) % n
    except ValueError:
        g = math.gcd(z, n)
        return g if 1 < g < n else None
    for p in primes:
        if p <= b1:
            continue
        if p > b2:
            break
        _, zz = _mont_ladder(p, xx, a24, n)
        g = math.gcd(zz, n)
        if 1 < g < n:
            return g
    return None


def ecm_factor(
    n: int,
    *,
    B1: int | None = None,
    B2: int | None = None,
    max_curves: int | None = None,
    sigma0: int = 6,
    max_ms: int | None = None,
) -> int | None:
    """Return a proper factor of composite ``n``, or None.

    ``sigma`` runs ``sigma0, sigma0+1, …``. Bounds default from ``n.bit_length()``.
    ``max_ms`` is a wall-clock abort; on exhaust return None (do not raise).
    """
    if n < 4:
        return None
    try:
        return _ecm_factor_body(
            n, B1=B1, B2=B2, max_curves=max_curves, sigma0=sigma0, max_ms=max_ms
        )
    except MemoryError:
        return None


def _ecm_factor_body(
    n: int,
    *,
    B1: int | None,
    B2: int | None,
    max_curves: int | None,
    sigma0: int,
    max_ms: int | None,
) -> int | None:
    bits = n.bit_length()
    sb1, sb2, scount = _schedule(bits)
    if B1 is None:
        B1 = sb1
    if B2 is None:
        B2 = sb2
    if max_curves is None:
        max_curves = scount
    if B1 < 2:
        B1 = 2
    if B2 < B1:
        B2 = B1
    deadline = None if max_ms is None else time.perf_counter() + max_ms / 1000.0
    primes = _primes_upto(B2)
    for i in range(max_curves):
        if deadline is not None and time.perf_counter() >= deadline:
            return None
        sigma = sigma0 + i
        built = _suyama(sigma, n)
        if built is None:
            continue
        if built[0] == "factor":
            g = built[1]
            if 1 < g < n:
                return g
            continue
        _ok, x0, a24 = built
        g = _mont_stage1(x0, a24, n, B1, primes)
        if g is not None:
            return g
        # Naive per-prime stage 2 is only cheap on tiny (B1, B2] windows.
        if 1 < B2 - B1 <= 4_000:
            k1 = _lcm_upto_cached(1, B1)
            xs, zs = _mont_ladder(k1, x0 % n, a24, n)
            gz = math.gcd(zs, n)
            if 1 < gz < n:
                return gz
            if gz == 1 and zs:
                xq = (xs * pow(zs, -1, n)) % n
                g = _mont_stage2(xq, 1, a24, n, B1, B2, primes)
                if g is not None:
                    return g
    return None
