"""Deterministic Lenstra ECM (fixed sigma schedule; no RNG).

Each curve is built from an integer ``sigma = 6, 7, 8, …``: Weierstrass
``y² = x³ + a x + b`` with ``(x, y) = (σ, 1)`` and ``a = σ``. Stage 1
multiplies the point by ``lcm(1..B1)``; stage 2 continues with
``lcm(B1+1..B2)``. A failed inversion yields ``gcd(denominator, n)``.

Does not import ``ntheory`` / ``prime_factors`` (those import this module).
"""

from __future__ import annotations

import math
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
    result: Point = None
    q = p
    while k:
        if k & 1:
            result, g = _add(result, q, a, n)
            if g > 1:
                return None, g
        k >>= 1
        if k:
            q, g = _add(q, q, a, n)
            if g > 1:
                return None, g
    return result, 1


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
    """(B1, B2, max_sigma_count) from bit length. Fixed, no RNG."""
    if bits <= 40:
        return 200, 1_000, 8
    if bits <= 64:
        return 2_000, 25_000, 24
    if bits <= 80:
        return 5_000, 50_000, 40
    if bits <= 100:
        return 11_000, 100_000, 60
    return 50_000, 250_000, 80


def ecm_factor(
    n: int,
    *,
    B1: int | None = None,
    B2: int | None = None,
    max_curves: int | None = None,
    sigma0: int = 6,
) -> int | None:
    """Return a proper factor of composite ``n``, or None.

    ``sigma`` runs ``sigma0, sigma0+1, …``. Bounds default from ``n.bit_length()``.
    """
    if n < 4:
        return None
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
    k1 = _lcm_upto(1, B1)
    k2 = _lcm_upto(B1 + 1, B2) if B2 > B1 else 1
    for i in range(max_curves):
        sigma = sigma0 + i
        built = _curve(sigma, n)
        if built[0] is None:
            g = built[2]
            if 1 < g < n:
                return g
            continue
        a, p0, g = built
        if 1 < g < n:
            return g
        assert a is not None and p0 is not None
        q, g = _mul(k1, p0, a, n)
        if 1 < g < n:
            return g
        if k2 > 1 and q is not None:
            _, g = _mul(k2, q, a, n)
            if 1 < g < n:
                return g
    return None
