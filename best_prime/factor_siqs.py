"""Self-initializing quadratic sieve with a fixed A-product schedule.

Polynomials are ``Q(x) = (A x + B)² − n`` where ``A`` is a product of
factor-base primes near ``√(2n)/M`` (SIQS) and ``B² ≡ n (mod A)`` via
Tonelli–Shanks + CRT. No RNG. Relations feed a GF(2) nullspace; a
dependency yields ``gcd(X − Y, n)``.

Does not import ``ntheory`` / ``prime_factors``.
"""

from __future__ import annotations

import math
import time
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


def _primes_upto(limit: int) -> list[int]:
    if limit < 2:
        return []
    n = (limit + 1) >> 1
    mark = bytearray(b"\x01") * n
    mark[0] = 0
    r = math.isqrt(limit)
    for i in range(1, (r + 1) >> 1):
        if mark[i]:
            p = (i << 1) + 1
            start = (p * p) >> 1
            mark[start:n:p] = b"\x00" * (((n - 1 - start) // p) + 1)
    out = [2]
    last = (limit - 1) >> 1
    out.extend(((i << 1) + 1) for i in range(1, last + 1) if mark[i])
    return out


def _tonelli(n: int, p: int) -> int | None:
    """Square root of n mod prime p, or None."""
    n %= p
    if n == 0:
        return 0
    if p == 2:
        return n
    if pow(n, (p - 1) // 2, p) != 1:
        return None
    if p % 4 == 3:
        return pow(n, (p + 1) // 4, p)
    q = p - 1
    s = 0
    while (q & 1) == 0:
        q >>= 1
        s += 1
    z = 2
    while pow(z, (p - 1) // 2, p) != p - 1:
        z += 1
        if z >= p:
            return None
    m = s
    c = pow(z, q, p)
    r = pow(n, (q + 1) // 2, p)
    t = pow(n, q, p)
    while t != 1:
        i = 1
        tt = (t * t) % p
        while tt != 1:
            tt = (tt * tt) % p
            i += 1
            if i == m:
                return None
        b = pow(c, 1 << (m - i - 1), p)
        r = (r * b) % p
        c = (b * b) % p
        t = (t * c) % p
        m = i
    return r


def _crt_pair(a1: int, m1: int, a2: int, m2: int) -> tuple[int, int]:
    """x ≡ a1 (mod m1), x ≡ a2 (mod m2); moduli coprime."""
    inv = pow(m1, -1, m2)
    x = a1 + m1 * ((a2 - a1) * inv % m2)
    return x, m1 * m2


def _factor_base(n: int, bound: int) -> list[tuple[int, int]]:
    """(p, sqrt(n) mod p) for p = 2 and odd p with (n/p)=1."""
    fb: list[tuple[int, int]] = []
    for p in _primes_upto(bound):
        if p == 2:
            fb.append((2, n % 2))
            continue
        if _jacobi(n, p) != 1:
            continue
        root = _tonelli(n, p)
        if root is None:
            continue
        fb.append((p, root))
    return fb


def _trial_smooth(val: int, primes: list[int]) -> list[int] | None:
    """Return exponents (incl. sign bit 0) if ``val`` is FB-smooth, else None.

    Vector is ``[sign, e_p0, e_p1, …]`` with sign=1 if val < 0.
    """
    if val == 0:
        return None
    sign = 0
    if val < 0:
        sign = 1
        val = -val
    exps = [sign]
    for p in primes:
        e = 0
        while val % p == 0:
            val //= p
            e += 1
        exps.append(e)
    if val != 1:
        return None
    return exps


def _gf2_nullspace(rows: list[int], nbits: int) -> list[list[int]]:
    """Each row is a bit-packed GF(2) vector. Return index-lists in the kernel."""
    m = len(rows)
    if m == 0:
        return []
    # Augment with identity so we track the combination.
    aug = [rows[i] | (1 << (nbits + i)) for i in range(m)]
    rank_at = [-1] * nbits
    row = 0
    for col in range(nbits):
        pivot = None
        for i in range(row, m):
            if (aug[i] >> col) & 1:
                pivot = i
                break
        if pivot is None:
            continue
        aug[row], aug[pivot] = aug[pivot], aug[row]
        rank_at[col] = row
        for i in range(m):
            if i != row and ((aug[i] >> col) & 1):
                aug[i] ^= aug[row]
        row += 1
        if row == m:
            break
    deps: list[list[int]] = []
    used = [False] * m
    # Free columns: any row that is zero on the original nbits.
    for i in range(m):
        if (aug[i] & ((1 << nbits) - 1)) == 0:
            combo = aug[i] >> nbits
            idxs = [j for j in range(m) if (combo >> j) & 1]
            if idxs:
                deps.append(idxs)
                for j in idxs:
                    used[j] = True
    return deps


def _pick_a(fb: list[tuple[int, int]], target: int, which: int) -> list[int]:
    """Deterministic product of FB primes near ``target`` (skip first ``which``)."""
    primes = [p for p, _ in fb if p > 2]
    if not primes:
        return []
    # Start near sqrt(target) in the list.
    best_i = 0
    best = abs(primes[0] - max(target, 2))
    for i, p in enumerate(primes):
        d = abs(p - max(3, int(math.isqrt(max(target, 2)))))
        if d < best:
            best = d
            best_i = i
    start = (best_i + which) % len(primes)
    chosen: list[int] = []
    prod = 1
    i = start
    guard = 0
    while prod < target and guard < len(primes) * 2:
        p = primes[i]
        if p not in chosen:
            chosen.append(p)
            prod *= p
        i = (i + 1) % len(primes)
        guard += 1
    return chosen


def _sqrt_mod_a(n: int, factors: list[int]) -> tuple[int, int] | None:
    """B, A with B² ≡ n (mod A), A = prod(factors)."""
    if not factors:
        return None
    a = 1
    b = 0
    for p in factors:
        root = _tonelli(n, p)
        if root is None:
            return None
        if a == 1:
            b, a = root, p
        else:
            b, a = _crt_pair(b, a, root, p)
    return b % a, a


def _sieve_poly(
    n: int,
    a: int,
    b: int,
    fb: list[tuple[int, int]],
    m: int,
) -> list[tuple[int, int, list[int]]]:
    """Sieve Q(x)=(A x + B)² − n on x ∈ [-M, M]. Return (x, Q, exponents)."""
    width = 2 * m + 1
    logv = [0.0] * width
    primes = [p for p, _ in fb]
    logs = {p: math.log(p) for p in primes}
    # Q(x) ≡ 0 (mod p)  ⇒  A x + B ≡ ±root (mod p)
    for p, root in fb:
        if p == 2:
            # handle even Q separately in trial
            continue
        if a % p == 0:
            continue
        inv_a = pow(a, -1, p)
        for r in (root, (-root) % p):
            # A x + B ≡ r  ⇒  x ≡ (r-B) A^{-1}
            x0 = ((r - (b % p)) * inv_a) % p
            start = x0 - m
            # first t >= 0 with -m + t ≡ x0 (mod p)
            t = (-m - start) % p
            idx = t
            lg = logs[p]
            while idx < width:
                logv[idx] += lg
                idx += p
    # Threshold: log|Q| minus slack for missing small primes / rounding.
    rels: list[tuple[int, int, list[int]]] = []
    # |Q(x)| ≈ 2 |A| M √n / something; use computed Q.
    slack = math.log(max(primes[-1], 3)) * 2.5
    for i in range(width):
        x = i - m
        axb = a * x + b
        qv = axb * axb - n
        if qv == 0:
            continue
        target = math.log(abs(qv))
        if logv[i] + slack < target:
            continue
        exps = _trial_smooth(qv, primes)
        if exps is None:
            continue
        rels.append((x, qv, exps))
    return rels


def _dependency_split(
    n: int, a: int, b: int, rels: list[tuple[int, int, list[int]]]
) -> int | None:
    if len(rels) < 2:
        return None
    nbits = len(rels[0][2])
    rows = []
    for _x, _q, exps in rels:
        bits = 0
        for i, e in enumerate(exps):
            if e & 1:
                bits |= 1 << i
        rows.append(bits)
    for idxs in _gf2_nullspace(rows, nbits):
        left = 1
        right = 1
        for j in idxs:
            x, qv, _exps = rels[j]
            axb = a * x + b
            left = (left * axb) % n
            # qv may be negative; take abs for the square root side.
            right *= abs(qv)
        # right should be a square
        yr = math.isqrt(right)
        if yr * yr != right:
            continue
        g = math.gcd((left - yr) % n, n)
        if 1 < g < n:
            return g
        g = math.gcd((left + yr) % n, n)
        if 1 < g < n:
            return g
    return None


def _bounds(bits: int) -> tuple[int, int, int]:
    """(factor-base bound, sieve half-width M, polynomial count)."""
    if bits <= 36:
        return 80, 2_000, 4
    if bits <= 48:
        return 200, 8_000, 6
    if bits <= 64:
        return 500, 20_000, 8
    if bits <= 80:
        return 1_200, 40_000, 10
    if bits <= 100:
        return 2_500, 80_000, 12
    return 5_000, 120_000, 14


def siqs_factor(
    n: int,
    *,
    fb_bound: int | None = None,
    interval: int | None = None,
    max_ms: int | None = None,
) -> int | None:
    """Proper factor of composite ``n`` via SIQS, or None.

    ``max_ms`` is a wall-clock abort; on exhaust return None (do not raise).
    """
    if n < 4 or n % 2 == 0:
        return 2 if n % 2 == 0 and n > 2 else None
    try:
        return _siqs_factor_body(n, fb_bound=fb_bound, interval=interval, max_ms=max_ms)
    except (MemoryError, ValueError):
        return None


def _siqs_factor_body(
    n: int,
    *,
    fb_bound: int | None,
    interval: int | None,
    max_ms: int | None,
) -> int | None:
    bits = n.bit_length()
    b0, m0, npoly = _bounds(bits)
    if fb_bound is None:
        fb_bound = b0
    if interval is None:
        interval = m0
    deadline = None if max_ms is None else time.perf_counter() + max_ms / 1000.0
    fb = _factor_base(n, fb_bound)
    if len(fb) < 6:
        return None
    if deadline is not None and time.perf_counter() >= deadline:
        return None
    # Target A ≈ √(2n) / M  (SIQS heuristic).
    target_a = max(3, math.isqrt(max(n * 2, 1)) // max(interval, 1))
    # First polynomial: classical QS (A=1) — cheap and enough for small n.
    r = math.isqrt(n)
    if r * r < n:
        r += 1
    rels = _sieve_poly(n, 1, r, fb, interval)
    g = _dependency_split(n, 1, r, rels)
    if g is not None:
        return g
    for which in range(npoly):
        if deadline is not None and time.perf_counter() >= deadline:
            return None
        factors = _pick_a(fb, target_a, which)
        got = _sqrt_mod_a(n, factors)
        if got is None:
            continue
        b, a = got
        # Prefer the B closest to 0 in [0, A).
        if b > a - b:
            b = a - b
        rels = _sieve_poly(n, a, b, fb, interval)
        g = _dependency_split(n, a, b, rels)
        if g is not None:
            return g
    return None
