"""
Exact integer factorization.

Small factors by 8-way 30-wheel trial (updates √n as it shrinks). Composite
remainders split with Fermat (close factors), two-band cubic search
(Lehman + rising-product wheel), deterministic Brent–Pollard
(fixed c = 1,2,3,… — no RNG), then deterministic ECM and SIQS for larger
balanced composites. Each prime factor is confirmed with is_prime.
"""

from __future__ import annotations

import math
from collections import Counter

from .is_prime import _parse_n, is_prime

# 30-wheel steps starting at 7 (residues 1,7,11,13,17,19,23,29).
_W30 = (4, 2, 4, 2, 4, 6, 2, 6)


def _strip(n: int, p: int, out: list[int]) -> int:
    if n % p:
        return n
    while True:
        n //= p
        out.append(p)
        if n % p:
            return n


def _trial_30(n: int, out: list[int], limit: int | None = None) -> int:
    """Divide n by 7,11,13,… up to limit (default isqrt(n), refreshed)."""
    if n < 49:
        return n
    cap = limit if limit is not None else math.isqrt(n)
    p = 7
    wi = 0
    # 8-way unroll matches one 30-wheel turn (7..31).
    while p + 28 <= cap:
        if n % p == 0:
            n = _strip(n, p, out)
            if n == 1:
                return 1
            cap = math.isqrt(n)
            if p > cap:
                return n
        p += _W30[wi]
        wi += 1
        if n % p == 0:
            n = _strip(n, p, out)
            if n == 1:
                return 1
            cap = math.isqrt(n)
            if p > cap:
                return n
        p += _W30[wi]
        wi += 1
        if n % p == 0:
            n = _strip(n, p, out)
            if n == 1:
                return 1
            cap = math.isqrt(n)
            if p > cap:
                return n
        p += _W30[wi]
        wi += 1
        if n % p == 0:
            n = _strip(n, p, out)
            if n == 1:
                return 1
            cap = math.isqrt(n)
            if p > cap:
                return n
        p += _W30[wi]
        wi += 1
        if n % p == 0:
            n = _strip(n, p, out)
            if n == 1:
                return 1
            cap = math.isqrt(n)
            if p > cap:
                return n
        p += _W30[wi]
        wi += 1
        if n % p == 0:
            n = _strip(n, p, out)
            if n == 1:
                return 1
            cap = math.isqrt(n)
            if p > cap:
                return n
        p += _W30[wi]
        wi += 1
        if n % p == 0:
            n = _strip(n, p, out)
            if n == 1:
                return 1
            cap = math.isqrt(n)
            if p > cap:
                return n
        p += _W30[wi]
        wi += 1
        if n % p == 0:
            n = _strip(n, p, out)
            if n == 1:
                return 1
            cap = math.isqrt(n)
            if p > cap:
                return n
        p += _W30[wi]
        wi += 1
        if wi == 8:
            wi = 0
    while p <= cap:
        if n % p == 0:
            n = _strip(n, p, out)
            if n == 1:
                return 1
            cap = math.isqrt(n)
            if p > cap:
                return n
        p += _W30[wi]
        wi += 1
        if wi == 8:
            wi = 0
    return n


def _fermat_split(n: int, rounds: int = 65_536) -> int | None:
    """Factor of n if it has two factors within ~rounds of √n."""
    a = math.isqrt(n)
    if a * a < n:
        a += 1
    # a^2 - n = b^2 ⇒ n = (a-b)(a+b)
    for _ in range(rounds):
        b2 = a * a - n
        b = math.isqrt(b2)
        if b * b == b2 and b != 0:
            f = a - b
            if 1 < f < n:
                return f
        a += 1
    return None


def _brent(n: int, c: int, x0: int = 2, max_r: int = 1 << 22) -> int:
    """Deterministic Brent–Pollard cycle. Returns a divisor of n (maybe n).

    Product-of-differences + rarer GCDs (m=512) cuts modular GCDs on
    multi-limb n−1 cofactors without changing the fixed trajectory.
    """
    y = x0 % n
    g = 1
    q = 1
    ys = y
    r = 1
    m = 512
    x = y
    # Cap growth so hostile composites do not run unbounded on next_prime.
    while g == 1 and r <= max_r:
        x = y
        for _ in range(r):
            y = (y * y + c) % n
        k = 0
        while k < r and g == 1:
            ys = y
            lim = r - k
            if lim > m:
                lim = m
            for _ in range(lim):
                y = (y * y + c) % n
                diff = x - y
                if diff < 0:
                    diff = -diff
                q = (q * diff) % n
            g = math.gcd(q, n)
            k += m
        r <<= 1
    if g == 1:
        return n
    if g == n:
        while True:
            ys = (ys * ys + c) % n
            g = math.gcd(abs(x - ys), n)
            if g > 1:
                break
    return g


def _split(n: int) -> int:
    """A proper factor of composite n > 1."""
    f = _fermat_split(n)
    if f is not None:
        return f
    # Cubic search: complete through 64-bit (n^{1/3} ≤ 2.6e6); bounded
    # probe after that. Does not replace is_prime's trial-to-√n contract.
    from .factor_lehman import lehman_factor

    if n.bit_length() <= 64:
        f = lehman_factor(n)
    else:
        f = lehman_factor(n, k_max=100_000)
    if f is not None and 1 < f < n:
        return f
    # Fixed c sequence: 1,2,3,… (c=0 is x^2, often degenerate).
    for c in range(1, 64):
        g = _brent(n, c)
        if 1 < g < n:
            return g
    # Medium / large balanced composites: ECM then SIQS (deterministic schedules).
    bits = n.bit_length()
    if bits >= 28:
        from .factor_ecm import ecm_factor

        g = ecm_factor(n)
        if g is not None and 1 < g < n:
            return g
    if bits >= 28:
        from .factor_siqs import siqs_factor

        g = siqs_factor(n)
        if g is not None and 1 < g < n:
            return g
    # Last resort: full 30-wheel trial (always finds a factor of a composite).
    out: list[int] = []
    rem = _trial_30(n, out)
    if out:
        return out[0]
    if rem != n and rem > 1:
        return rem
    raise RuntimeError(f"failed to split composite {n}")


def _factor_rec(n: int, out: list[int], *, parallel: bool) -> None:
    if n == 1:
        return
    if n < 4 or is_prime(n, parallel=parallel):
        out.append(n)
        return
    f = _split(n)
    _factor_rec(f, out, parallel=parallel)
    _factor_rec(n // f, out, parallel=parallel)


def prime_factors(n: int | str, *, parallel: bool = True) -> list[int]:
    """Prime factors of n with multiplicity, ascending. ``[]`` for n < 2."""
    n_int = _parse_n(n)
    if n_int < 2:
        return []
    out: list[int] = []
    n_int = _strip(n_int, 2, out)
    n_int = _strip(n_int, 3, out)
    n_int = _strip(n_int, 5, out)
    if n_int == 1:
        return out
    # Cheap small-prime pass (√n shrinks when factors appear).
    n_int = _trial_30(n_int, out, limit=1021 if n_int.bit_length() > 40 else None)
    if n_int == 1:
        return out
    rest: list[int] = []
    _factor_rec(n_int, rest, parallel=parallel)
    out.extend(rest)
    out.sort()
    return out


def factorint(n: int | str, *, parallel: bool = True) -> dict[int, int]:
    """Map prime → exponent. Empty for n < 2."""
    facs = prime_factors(n, parallel=parallel)
    return dict(Counter(facs))
