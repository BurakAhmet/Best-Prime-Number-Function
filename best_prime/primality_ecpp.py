"""Class-number-1 deterministic Atkin–Morain ECPP (skeleton).

Only the 13 class-number-1 discriminants. Not a general 100-digit engine.
True / False / None; no certificate tree. Deterministic. No RNG.
"""

from __future__ import annotations

import math
from typing import Optional

from .factor_ecm import _mul

POINT_X_MAX = 4096
TONELLI_Z_MAX = 10_000
TWIST_NONRESIDUE_MAX = 10_000
MAX_D_TRIALS_2A = 13

# Increasing |D|; prefix barrier: earlier D must fully fail before a later hit.
CLASS_NUMBER_1_D = (
    -3,
    -4,
    -7,
    -8,
    -11,
    -12,
    -16,
    -19,
    -27,
    -28,
    -43,
    -67,
    -163,
)

# Cohen Table 7.1 / Silverman AEC App. A / Atkin–Morain 1993.
_J_INVARIANT = {
    -3: 0,
    -4: 1728,
    -7: -(15**3),
    -8: 20**3,
    -11: -(32**3),
    -12: 2 * (30**3),
    -16: 66**3,
    -19: -(96**3),
    -27: -3 * (160**3),
    -28: 255**3,
    -43: -(960**3),
    -67: -(5280**3),
    -163: -(640320**3),
}

_FERMAT_BASES = (2, 3, 5, 7, 11, 13)

Result = Optional[bool]

_proving: set[int] = set()


def gk_min_q(n: int) -> int:
    """Smallest integer q that is guaranteed to satisfy q > (n^{1/4}+1)^2."""
    r = math.isqrt(math.isqrt(n))
    return (r + 2) ** 2


def _jacobi(a: int, n: int) -> int:
    """Jacobi (a/n) for odd positive n."""
    if n <= 0 or (n & 1) == 0:
        raise ValueError("jacobi requires odd positive n")
    a %= n
    t = 1
    while a:
        while (a & 1) == 0:
            a >>= 1
            r = n & 7
            if r == 3 or r == 5:
                t = -t
        a, n = n, a
        if (a & 3) == 3 and (n & 3) == 3:
            t = -t
        a %= n
    return t if n == 1 else 0


def _least_root(r: int, n: int) -> int | None:
    r %= n
    if r < 0:
        r += n
    alt = n - r
    if alt < r:
        r = alt
    if r < 1 or r > (n - 1) // 2:
        return None
    return r


def tonelli_mod_n(a: int, n: int):
    """Square root of ``a`` mod ``n``, or a proper factor, or None.

    Never treats ``n`` as known-prime. ``z`` is capped at ``TONELLI_Z_MAX``.
    """
    if n <= 2 or (n & 1) == 0:
        return None
    a %= n
    g = math.gcd(a, n)
    if 1 < g < n:
        return ("factor", g)
    try:
        jac = _jacobi(a, n)
    except ValueError:
        return None
    if jac != 1:
        return None
    z = None
    for cand in range(2, TONELLI_Z_MAX + 1):
        g = math.gcd(cand, n)
        if 1 < g < n:
            return ("factor", g)
        if _jacobi(cand, n) == -1:
            z = cand
            break
    if z is None:
        return None
    if n % 4 == 3:
        r = pow(a, (n + 1) // 4, n)
    else:
        q = n - 1
        s = 0
        while (q & 1) == 0:
            q >>= 1
            s += 1
        # Inner "find i" is bounded by s ≤ bit_length(n); never bump z.
        if s > n.bit_length():
            return None
        m = s
        c = pow(z, q, n)
        r = pow(a, (q + 1) // 2, n)
        t = pow(a, q, n)
        while t != 1:
            if m <= 1:
                return None
            i = 1
            tt = (t * t) % n
            while tt != 1:
                tt = (tt * tt) % n
                i += 1
                if i == m or i > s:
                    return None
            shift = m - i - 1
            if shift < 0:
                return None
            b = pow(c, 1 << shift, n)
            r = (r * b) % n
            c = (b * b) % n
            t = (t * c) % n
            m = i
    if (r * r) % n != a % n:
        return None
    return _least_root(r, n)


def cornacchia(D: int, n: int):
    """Solve t² + |D| v² = 4n. Least t > 0 over every hit; ties by min v."""
    if D >= 0 or n <= 2 or (n & 1) == 0:
        return ("no",)
    d = -D
    g = math.gcd(d, n)
    if 1 < g < n:
        return ("factor", g)
    if g == n:
        return ("no",)
    if _jacobi(D, n) != 1:
        return ("no",)
    root = tonelli_mod_n((-d) % n, n)
    if isinstance(root, tuple):
        return root
    if root is None:
        return ("no",)
    four_n = 4 * n
    cands: list[int] = []
    for base in (root, (n - root) % n):
        if base == 0:
            continue
        for raw in (base, four_n - base, base + n, base + 2 * n, base + 3 * n):
            r4 = raw % four_n
            if 0 < r4 < four_n:
                cands.append(r4)
    R: list[int] = []
    seen: set[int] = set()
    for r4 in cands:
        if r4 in seen:
            continue
        seen.add(r4)
        if (r4 * r4 + d) % four_n == 0:
            R.append(r4)
    if not R:
        return ("no",)
    R.sort()
    hits: list[tuple[int, int]] = []
    for r4 in R:
        aa, b = four_n, r4
        if b > 2 * n:
            b = four_n - b
        failed = False
        while b * b > four_n:
            aa, b = b, aa % b
            if b == 0:
                failed = True
                break
        if failed:
            continue
        t = abs(b)
        rem = four_n - t * t
        if rem < 0 or rem % d != 0:
            continue
        vv = rem // d
        v = math.isqrt(vv)
        if v * v != vv or t == 0:
            continue
        hits.append((t, v))
    if not hits:
        return ("no",)
    t, v = min(hits, key=lambda tv: (tv[0], tv[1]))
    return ("ok", t, v)


def twist_gen_neg4(n: int):
    """Least β ≥ 2 with jacobi = −1 that yields 4 distinct A = β^k."""
    for beta in range(2, TWIST_NONRESIDUE_MAX + 1):
        g = math.gcd(beta, n)
        if 1 < g < n:
            return ("factor", g)
        if _jacobi(beta, n) == -1:
            aset = {pow(beta, k, n) for k in range(4)}
            if len(aset) == 4:
                return beta
    return None


def twist_gen_neg3(n: int):
    """Least α ≥ 2: quadratic nonresidue, cubic nonresidue when 3 | n−1."""
    for alpha in range(2, TWIST_NONRESIDUE_MAX + 1):
        g = math.gcd(alpha, n)
        if 1 < g < n:
            return ("factor", g)
        if _jacobi(alpha, n) != -1:
            continue
        if (n - 1) % 3 == 0 and pow(alpha, (n - 1) // 3, n) == 1:
            continue
        bset = {pow(alpha, k, n) for k in range(6)}
        if len(bset) == 6:
            return alpha
    return None


def _fermat_composite(n: int) -> bool:
    """True iff a fixed-base Fermat witness proves ``n`` composite."""
    if n < 2:
        return True
    for a in _FERMAT_BASES:
        if a % n == 0:
            return n != a
        if pow(a, n - 1, n) != 1:
            return True
    return False


def _peel_m(m: int, parent: int, *, parallel: bool) -> tuple[dict[int, int], int]:
    """Trial / splitter peel of ``m``. Leftover is 1 if fully factored."""
    from .primality_nm1 import (
        _adaptive_trial_bound,
        _max_splits,
        _trial_split,
        _try_split_cofactor,
    )

    fac: dict[int, int] = {}
    peeled, rem = _trial_split(m, _adaptive_trial_bound(m))
    fac.update(peeled)
    if rem <= 1:
        return fac, 1
    stack = [rem]
    unproven: list[int] = []
    splits = 0
    max_splits = _max_splits(m.bit_length())
    while stack:
        c = stack.pop()
        if c <= 1:
            continue
        sub, r2 = _trial_split(c, _adaptive_trial_bound(c))
        for p, e in sub.items():
            fac[p] = fac.get(p, 0) + e
        if r2 <= 1:
            continue
        c = r2
        if c < parent and not _fermat_composite(c):
            unproven.append(c)
            continue
        if splits >= max_splits:
            unproven.append(c)
            continue
        splits += 1
        f = _try_split_cofactor(c, parallel=parallel)
        if f is None or f <= 1 or f >= c:
            unproven.append(c)
            continue
        stack.append(f)
        stack.append(c // f)
    prod = 1
    for p, e in fac.items():
        prod *= pow(p, e)
    leftover = m // prod if prod else m
    if leftover <= 1:
        return fac, 1
    return fac, leftover


def _admissible_pairs(
    m: int, n: int, fac: dict[int, int], leftover: int
) -> list[tuple[int, int, bool]]:
    """(q, c, proven) with q | m, c = m/q ≥ 2, q ≥ gk_min_q(n). Smallest q first."""
    min_q = gk_min_q(n)
    pairs: list[tuple[int, int, bool]] = []
    seen: set[int] = set()
    for q in fac:
        if q in seen or q < min_q or m % q != 0:
            continue
        c = m // q
        if c >= 2:
            pairs.append((q, c, True))
            seen.add(q)
    if leftover > 1 and leftover < n and leftover >= min_q and leftover not in seen:
        if m % leftover == 0:
            c = m // leftover
            if c >= 2:
                pairs.append((leftover, c, False))
    pairs.sort(key=lambda item: item[0])
    return pairs


def _point_search(n: int, a: int, b: int, c: int, q: int) -> Result:
    """GK point predicate. False = proper factor of n; None = this pair fails."""
    for x in range(1, POINT_X_MAX + 1):
        rhs = (pow(x, 3, n) + a * x + b) % n
        try:
            jac = _jacobi(rhs, n)
        except ValueError:
            return False
        if jac == 0:
            g = math.gcd(rhs, n)
            if 1 < g < n:
                return False
            continue
        if jac == -1:
            continue
        y = tonelli_mod_n(rhs, n)
        if isinstance(y, tuple):
            return False
        if y is None:
            continue
        pnt = (x, y)
        qpt, g = _mul(c, pnt, a, n)
        if 1 < g < n:
            return False
        if g > 1 or qpt is None:
            continue
        rpt, g = _mul(q, qpt, a, n)
        if 1 < g < n:
            return False
        if g > 1:
            continue
        if rpt is None:
            return True
        # [m]P ≠ O with inversions ok: this (curve, sign) has the wrong order.
        return None
    return None


def _prove_q(q: int, n: int, *, parallel: bool, proven: bool) -> Result:
    if proven:
        return True
    if q <= 1 or q >= n:
        return None
    from .primality_nm1 import _prove_strictly_smaller

    return _prove_strictly_smaller(q, n, parallel=parallel, allow_ecpp=True)


def _try_curve(n: int, a: int, b: int, m: int, *, parallel: bool) -> Result:
    """Run point search on E(a,b) with order m. False = n composite."""
    if m <= 2:
        return None
    g = math.gcd(m, n)
    if 1 < g < n:
        return False
    disc = (4 * pow(a, 3, n) + 27 * ((b * b) % n)) % n
    g = math.gcd(disc, n)
    if 1 < g < n:
        return False
    if g == n:
        return None
    fac, leftover = _peel_m(m, n, parallel=parallel)
    for q, c, proven in _admissible_pairs(m, n, fac, leftover):
        hit = _point_search(n, a, b, c, q)
        if hit is False:
            return False
        if hit is True:
            dec = _prove_q(q, n, parallel=parallel, proven=proven)
            if dec is True:
                return True
            # Unproven / composite leftover: try the next admissible q.
            continue
    return None


def _nonresidue(n: int):
    for c in range(2, TWIST_NONRESIDUE_MAX + 1):
        g = math.gcd(c, n)
        if 1 < g < n:
            return ("factor", g)
        if _jacobi(c, n) == -1:
            return c
    return None


def _try_d_neg4(n: int, t: int, *, parallel: bool) -> Result:
    beta = twist_gen_neg4(n)
    if isinstance(beta, tuple):
        return False
    if beta is None:
        return None
    for k in range(4):
        a = pow(beta, k, n)
        if a == 0:
            continue
        for m in (n + 1 - t, n + 1 + t):
            dec = _try_curve(n, a, 0, m, parallel=parallel)
            if dec is not None:
                return dec
    return None


def _try_d_neg3(n: int, t: int, *, parallel: bool) -> Result:
    alpha = twist_gen_neg3(n)
    if isinstance(alpha, tuple):
        return False
    if alpha is None:
        return None
    for k in range(6):
        b = pow(alpha, k, n)
        if b == 0:
            continue
        for m in (n + 1 - t, n + 1 + t):
            dec = _try_curve(n, 0, b, m, parallel=parallel)
            if dec is not None:
                return dec
    return None


def _try_d_from_j(n: int, D: int, t: int, *, parallel: bool) -> Result:
    j = _J_INVARIANT[D] % n
    g = math.gcd(j - 1728, n)
    if 1 < g < n:
        return False
    if g == n:
        return None
    try:
        inv = pow(j - 1728, -1, n)
    except ValueError:
        g = math.gcd(j - 1728, n)
        if 1 < g < n:
            return False
        return None
    k = (j * inv) % n
    c = _nonresidue(n)
    if isinstance(c, tuple):
        return False
    if c is None:
        return None
    for r in (0, 1):
        cr2 = pow(c, 2 * r, n)
        cr3 = pow(c, 3 * r, n)
        a = (-3 * k * cr2) % n
        b = (2 * k * cr3) % n
        for m in (n + 1 - t, n + 1 + t):
            dec = _try_curve(n, a, b, m, parallel=parallel)
            if dec is not None:
                return dec
    return None


def _try_discriminant(D: int, n: int, *, parallel: bool) -> Result:
    cr = cornacchia(D, n)
    if cr[0] == "factor":
        g = cr[1]
        return False if 1 < g < n else None
    if cr[0] != "ok":
        return None
    t = cr[1]
    if t <= 0:
        return None
    if D == -4:
        return _try_d_neg4(n, t, parallel=parallel)
    if D == -3:
        return _try_d_neg3(n, t, parallel=parallel)
    return _try_d_from_j(n, D, t, parallel=parallel)


def ecpp_primality(n: int, *, parallel: bool = True, max_h: int = 1) -> Optional[bool]:
    """True / False / None. Class-number-1 only when max_h==1.

    ``parallel`` may speed cofactor engines; it does not change which
    (D, twist, point) wins.
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if (n & 1) == 0:
        return False
    if math.isqrt(n) ** 2 == n:
        return False
    if max_h < 1:
        return None
    if n in _proving:
        return None
    if len(_proving) >= n.bit_length():
        return None
    _proving.add(n)
    try:
        # Prefix barrier: each D fully fails (incl. factoring) before the next.
        for D in CLASS_NUMBER_1_D[:MAX_D_TRIALS_2A]:
            dec = _try_discriminant(D, n, parallel=parallel)
            if dec is not None:
                return dec
        return None
    finally:
        _proving.discard(n)
