"""Deterministic Atkin–Morain ECPP.

``max_h=1`` is the class-number-1 skeleton (13 discriminants).
``max_h=16`` walks transcribed ``H_D`` with ``h(D) ≤ 16`` (small-h CM).
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
CZ_S_MAX = 256

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
# Nested ECPP must not clobber the outer witness payload.
_cert_stack: list[dict] = []


def _note(**kwargs: int) -> None:
    if _cert_stack:
        _cert_stack[-1].update(kwargs)


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


def _peel_m(
    m: int, parent: int, *, parallel: bool
) -> tuple[dict[int, int], int, list[int]]:
    """Trial / splitter peel of ``m``.

    Returns ``(fac, leftover, unproven)`` where ``leftover = m / ∏ fac``
    (or 1) and ``unproven`` is each isolated splitter piece not absorbed
    into ``fac``.
    """
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
        return fac, 1, []
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
        leftover = 1
    return fac, leftover, unproven


def _admissible_pairs(
    m: int, n: int, fac: dict[int, int], leftover: int, unproven: list[int]
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
    # Isolated splitter pieces (e.g. two large prime factors of m), then
    # the combined cofactor m/∏fac. All unproven until _prove_q.
    candidates: list[int] = []
    for q in unproven:
        if q > 1:
            candidates.append(q)
    if leftover > 1:
        candidates.append(leftover)
    for q in candidates:
        if q in seen or q < min_q or q >= n or m % q != 0:
            continue
        c = m // q
        if c >= 2:
            pairs.append((q, c, False))
            seen.add(q)
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
            _note(x=int(x), y=int(y))
            return True
        # [m]P ≠ O with inversions ok: this (curve, sign) has the wrong order.
        return None
    return None


def _prove_q(
    q: int, n: int, *, parallel: bool, proven: bool, max_h: int
) -> Result:
    if proven:
        return True
    if q <= 1 or q >= n:
        return None
    from .primality_nm1 import _prove_strictly_smaller

    return _prove_strictly_smaller(
        q, n, parallel=parallel, allow_ecpp=True, max_h=max_h
    )


def _try_curve(
    n: int, a: int, b: int, m: int, *, parallel: bool, max_h: int
) -> Result:
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
    fac, leftover, unproven = _peel_m(m, n, parallel=parallel)
    for q, c, proven in _admissible_pairs(m, n, fac, leftover, unproven):
        hit = _point_search(n, a, b, c, q)
        if hit is False:
            return False
        if hit is True:
            dec = _prove_q(q, n, parallel=parallel, proven=proven, max_h=max_h)
            if dec is True:
                _note(a=int(a), b=int(b), m=int(m), c=int(c), q=int(q))
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


def _try_d_neg4(n: int, t: int, *, parallel: bool, max_h: int) -> Result:
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
            dec = _try_curve(n, a, 0, m, parallel=parallel, max_h=max_h)
            if dec is not None:
                return dec
    return None


def _try_d_neg3(n: int, t: int, *, parallel: bool, max_h: int) -> Result:
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
            dec = _try_curve(n, 0, b, m, parallel=parallel, max_h=max_h)
            if dec is not None:
                return dec
    return None


def _try_curve_from_j(n: int, j: int, t: int, *, parallel: bool, max_h: int) -> Result:
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
            dec = _try_curve(n, a, b, m, parallel=parallel, max_h=max_h)
            if dec is not None:
                return dec
    return None


def _try_d_from_j(n: int, D: int, t: int, *, parallel: bool, max_h: int) -> Result:
    j = _J_INVARIANT[D] % n
    return _try_curve_from_j(n, j, t, parallel=parallel, max_h=max_h)


def _try_discriminant(D: int, n: int, *, parallel: bool, max_h: int) -> Result:
    cr = cornacchia(D, n)
    if cr[0] == "factor":
        g = cr[1]
        return False if 1 < g < n else None
    if cr[0] != "ok":
        return None
    t = cr[1]
    v = cr[2]
    if t <= 0:
        return None
    if D == -4:
        dec = _try_d_neg4(n, t, parallel=parallel, max_h=max_h)
    elif D == -3:
        dec = _try_d_neg3(n, t, parallel=parallel, max_h=max_h)
    else:
        dec = _try_d_from_j(n, D, t, parallel=parallel, max_h=max_h)
    if dec is True:
        _note(D=int(D), t=int(t), v=int(v), j=int(_J_INVARIANT[D]))
    return dec


class _ModFactor(Exception):
    """Proper factor of n found during (Z/nZ)[X] arithmetic."""

    def __init__(self, g: int) -> None:
        self.g = g


def _square_free_int(k: int) -> bool:
    m = abs(k)
    if m == 0:
        return False
    if m % 4 == 0:
        return False
    if m % 2 == 0:
        m //= 2
    p = 3
    while p * p <= m:
        if m % p == 0:
            m //= p
            if m % p == 0:
                return False
        p += 2
    return True


def _is_fundamental_discriminant(D: int) -> bool:
    if D >= 0 or D % 4 not in (0, 1):
        return False
    if D % 4 == 1:
        return _square_free_int(D)
    m = D // 4
    if m % 4 not in (2, 3):
        return False
    return _square_free_int(m)


def reduced_form_class_number(D: int) -> int:
    """Number of reduced positive-definite forms of discriminant D."""
    if D >= 0 or D % 4 not in (0, 1):
        return 0
    count = 0
    a_max = math.isqrt((-D) // 3)
    for a in range(1, a_max + 1):
        for b in range(-a, a + 1):
            rhs = b * b - D
            four_a = 4 * a
            if rhs % four_a != 0:
                continue
            c = rhs // four_a
            if a > c:
                continue
            if (a == c or a == abs(b)) and b < 0:
                continue
            count += 1
    return count


def _inv_mod(a: int, n: int) -> int:
    a %= n
    if a == 0:
        raise _ModFactor(n)
    try:
        return pow(a, -1, n)
    except ValueError:
        g = math.gcd(a, n)
        if 1 < g < n:
            raise _ModFactor(g)
        raise _ModFactor(n)


# Polynomials over Z/nZ are low-degree-first lists. Empty = 0.


def _pdeg(p: list[int]) -> int:
    return len(p) - 1 if p else -1


def _pstrip(p: list[int]) -> list[int]:
    while p and p[-1] == 0:
        p.pop()
    return p


def _pnorm_h(coeffs: tuple[int, ...], n: int) -> list[int]:
    """Reduce H_D mod n (high-degree-first input). gcd-extract on coeffs."""
    out: list[int] = []
    for c in reversed(coeffs):
        c %= n
        if c:
            g = math.gcd(c, n)
            if 1 < g < n:
                raise _ModFactor(g)
        out.append(c)
    return _pstrip(out)


def _pmake_monic(p: list[int], n: int) -> list[int]:
    if not p:
        return p
    inv = _inv_mod(p[-1], n)
    if inv == 1:
        return p
    return [(c * inv) % n for c in p]


def _padd(a: list[int], b: list[int], n: int) -> list[int]:
    if len(a) < len(b):
        a, b = b, a
    out = a[:]
    for i, c in enumerate(b):
        out[i] = (out[i] + c) % n
    return _pstrip(out)


def _psub(a: list[int], b: list[int], n: int) -> list[int]:
    out = a[:] if len(a) >= len(b) else a + [0] * (len(b) - len(a))
    for i, c in enumerate(b):
        out[i] = (out[i] - c) % n
    return _pstrip(out)


def _pmul(a: list[int], b: list[int], n: int) -> list[int]:
    if not a or not b:
        return []
    out = [0] * (len(a) + len(b) - 1)
    for i, ca in enumerate(a):
        if ca == 0:
            continue
        for j, cb in enumerate(b):
            if cb:
                out[i + j] = (out[i + j] + ca * cb) % n
    return _pstrip(out)


def _pdivmod(f: list[int], g: list[int], n: int) -> tuple[list[int], list[int]]:
    if not g:
        raise _ModFactor(n)
    inv = _inv_mod(g[-1], n)
    q = [0] * max(0, len(f) - len(g) + 1)
    r = f[:]
    while r and len(r) >= len(g):
        coef = (r[-1] * inv) % n
        shift = len(r) - len(g)
        q[shift] = coef
        if coef:
            for i, gc in enumerate(g):
                if gc:
                    r[shift + i] = (r[shift + i] - coef * gc) % n
        r.pop()
        _pstrip(r)
    _pstrip(q)
    return q, r


def _pgcd(f: list[int], g: list[int], n: int) -> list[int]:
    while g:
        _q, r = _pdivmod(f, g, n)
        f, g = g, r
    return _pmake_monic(f, n)


def _pderiv(p: list[int], n: int) -> list[int]:
    if len(p) < 2:
        return []
    return _pstrip([(i * p[i]) % n for i in range(1, len(p))])


def _pmod(f: list[int], g: list[int], n: int) -> list[int]:
    return _pdivmod(f, g, n)[1]


def _ppowmod(base: list[int], exp: int, modp: list[int], n: int) -> list[int]:
    result = [1]
    base = _pmod(base, modp, n)
    while exp:
        if exp & 1:
            result = _pmod(_pmul(result, base, n), modp, n)
        base = _pmod(_pmul(base, base, n), modp, n)
        exp >>= 1
    return result


def _linear_root(p: list[int], n: int) -> int | None:
    if _pdeg(p) != 1:
        return None
    # Monic X + c0  ⇒  root = −c0.
    p = _pmake_monic(p, n)
    return (-p[0]) % n


def hilbert_root_mod_n(coeffs: tuple[int, ...], n: int):
    """One root of monic H_D mod n, or a proper factor, or None.

    Numbered Cantor–Zassenhaus: ``X+s`` for ``s = 1 .. CZ_S_MAX``.
    """
    if n <= 2 or (n & 1) == 0:
        return None
    try:
        h = _pnorm_h(coeffs, n)
        if _pdeg(h) < 1:
            return None
        h = _pmake_monic(h, n)
        # Square-free: U = gcd(H, H'); keep H/U if U is non-constant.
        u = _pgcd(h, _pderiv(h, n), n)
        if _pdeg(u) >= 1:
            q, r = _pdivmod(h, u, n)
            if r:
                return None
            h = _pmake_monic(q, n)
            if _pdeg(h) < 1:
                return None
        # Distinct-degree: gcd(X^n − X, H) must be non-constant.
        xn = _ppowmod([0, 1], n, h, n)
        ddf = _pgcd(_psub(xn, [0, 1], n), h, n)
        if _pdeg(ddf) < 1:
            return None
        h = ddf
        # Equal-degree (linear), restart on a proper factor.
        while _pdeg(h) > 1:
            split = None
            for s in range(1, CZ_S_MAX + 1):
                a = _ppowmod([s, 1], (n - 1) // 2, h, n)
                g = _pgcd(_psub(a, [1], n), h, n)
                dg = _pdeg(g)
                if dg < 1 or dg >= _pdeg(h):
                    continue
                q, r = _pdivmod(h, g, n)
                if r:
                    continue
                q = _pmake_monic(q, n)
                g = _pmake_monic(g, n)
                split = g if _pdeg(g) <= _pdeg(q) and _pdeg(g) >= 1 else q
                if _pdeg(split) < 1:
                    split = g if _pdeg(g) >= 1 else q
                break
            if split is None:
                return None
            h = split
        return _linear_root(h, n)
    except _ModFactor as exc:
        g = exc.g
        if 1 < g < n:
            return ("factor", g)
        return None


def _try_discriminant_small_h(
    D: int, coeffs: tuple[int, ...], n: int, *, parallel: bool, max_h: int
) -> Result:
    cr = cornacchia(D, n)
    if cr[0] == "factor":
        g = cr[1]
        return False if 1 < g < n else None
    if cr[0] != "ok":
        return None
    t = cr[1]
    v = cr[2]
    if t <= 0:
        return None
    root = hilbert_root_mod_n(coeffs, n)
    if isinstance(root, tuple):
        g = root[1]
        return False if 1 < g < n else None
    if root is None:
        return None
    dec = _try_curve_from_j(n, root, t, parallel=parallel, max_h=max_h)
    if dec is True:
        _note(D=int(D), t=int(t), v=int(v), j=int(root))
    return dec


def _small_h_walk(n: int, *, parallel: bool, max_h: int) -> Result:
    """Fundamental D after the 13 h=1 list, increasing |D|, transcribed H_D."""
    from ._classpoly_h16 import D_TABLE_MAX, H_CAP, HILBERT_CLASS_POLY

    cap = min(max_h, H_CAP)
    if cap < 2:
        return None
    seen_h1 = set(CLASS_NUMBER_1_D)
    for absd in range(3, D_TABLE_MAX + 1):
        D = -absd
        if D % 4 not in (0, 1) or D in seen_h1:
            continue
        if not _is_fundamental_discriminant(D):
            continue
        if reduced_form_class_number(D) > cap:
            continue
        coeffs = HILBERT_CLASS_POLY.get(D)
        if coeffs is None or len(coeffs) - 1 > cap:
            continue
        dec = _try_discriminant_small_h(
            D, coeffs, n, parallel=parallel, max_h=max_h
        )
        if dec is not None:
            return dec
    return None


def _ecpp_search(
    n: int, *, parallel: bool = True, max_h: int = 1
) -> tuple[Result, dict | None]:
    """True / False / None plus an ECPP witness when the proof succeeds."""
    _cert_stack.append({})
    try:
        if n < 2:
            return False, None
        if n in (2, 3):
            return True, None
        if (n & 1) == 0:
            return False, None
        if math.isqrt(n) ** 2 == n:
            return False, None
        if max_h < 1:
            return None, None
        if n in _proving:
            return None, None
        if len(_proving) >= n.bit_length():
            return None, None
        _proving.add(n)
        try:
            for D in CLASS_NUMBER_1_D[:MAX_D_TRIALS_2A]:
                dec = _try_discriminant(D, n, parallel=parallel, max_h=max_h)
                if dec is not None:
                    rec = dict(_cert_stack[-1]) if dec is True else None
                    return dec, rec
            if max_h > 1:
                dec = _small_h_walk(n, parallel=parallel, max_h=max_h)
                rec = dict(_cert_stack[-1]) if dec is True else None
                return dec, rec
            return None, None
        finally:
            _proving.discard(n)
    finally:
        _cert_stack.pop()


def ecpp_primality(n: int, *, parallel: bool = True, max_h: int = 1) -> Optional[bool]:
    """True / False / None. Fully deterministic Atkin–Morain.

    ``max_h=1`` uses only the 13 class-number-1 discriminants.
    ``max_h=16`` then walks transcribed ``H_D`` with ``h(D) ≤ 16``.

    ``parallel`` may speed cofactor engines; it does not change which
    (D, twist, point) wins. Returns a boolean only — no certificate tree.
    """
    decided, _rec = _ecpp_search(n, parallel=parallel, max_h=max_h)
    return decided


def ecpp_certificate_data(
    n: int, *, parallel: bool = True, max_h: int = 1
) -> dict | None:
    """Witness payload for an ECPP prime proof. None if ECPP does not settle prime."""
    decided, rec = _ecpp_search(n, parallel=parallel, max_h=max_h)
    if decided is True and rec and "q" in rec:
        return rec
    return None

