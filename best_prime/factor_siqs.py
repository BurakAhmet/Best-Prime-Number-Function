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
    *,
    large_prime_bound: int,
) -> list[tuple[int, list[int], int]]:
    """Sieve Q(x)=(A x + B)² − n on x ∈ [-M, M].

    Each hit is ``(ax+b, exponents, large-prime counts)``. Counts are empty
    when Q is factor-base smooth.
    """
    width = 2 * m + 1
    logv = [0.0] * width
    primes = [p for p, _ in fb]
    logs = [math.log(p) for p in primes]
    max_p = primes[-1] if primes else 2
    # Q is divisible by A. Record those exponents and sieve only the cofactor.
    a_exp = [0] * len(primes)
    aval = a
    if a > 1:
        for i, p in enumerate(primes):
            while aval % p == 0:
                aval //= p
                a_exp[i] += 1
    # Q(x) ≡ 0 (mod p)  ⇒  A x + B ≡ ±root (mod p)
    for (p, root), lg in zip(fb, logs):
        if p == 2 or a % p == 0:
            continue
        inv_a = pow(a, -1, p)
        b_mod = b % p
        for r in (root, (-root) % p):
            x0 = ((r - b_mod) * inv_a) % p
            idx = (x0 - (-m)) % p
            while idx < width:
                logv[idx] += lg
                idx += p
    # Slack covers two leftover primes up to large_prime_bound, plus
    # the unsieved power of 2. One large prime does not yield enough
    # pairs on a 50-digit modulus.
    slack = 2.0 * math.log(max(large_prime_bound, 3)) + math.log(2) * 12
    rels: list[tuple[int, list[int], int]] = []
    for i in range(width):
        if logv[i] <= 0.0:
            continue
        x = i - m
        axb = a * x + b
        qv = axb * axb - n
        if qv == 0:
            continue
        if a > 1:
            if qv % a != 0:
                continue
            qv //= a
        if logv[i] + slack < math.log(abs(qv)):
            continue
        got = _trial_factor(qv, primes, large_prime_bound, max_p)
        if got is None:
            continue
        exps, counts = got
        for i, e in enumerate(a_exp):
            exps[i + 1] += e
        rels.append((axb, exps, counts))
    return rels


# Deterministic Miller–Rabin for cofactors below 2^64.
_MR64 = (2, 3, 5, 7, 11, 13, 23)


def _prime64(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if (n & 1) == 0:
        return False
    d = n - 1
    s = 0
    while (d & 1) == 0:
        d >>= 1
        s += 1
    for a in _MR64:
        if a >= n:
            continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        witness = True
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                witness = False
                break
        if witness:
            return False
    return True


def _brent_small(n: int, c: int) -> int | None:
    """One fixed-c Brent step on a cofactor. None if no proper factor."""
    if n < 4:
        return None
    y = 2 % n
    g = 1
    q = 1
    r = 1
    x = y
    ys = y
    while g == 1 and r <= (1 << 16):
        x = y
        for _ in range(r):
            y = (y * y + c) % n
        k = 0
        m = 128
        while k < r and g == 1:
            ys = y
            lim = r - k
            if lim > m:
                lim = m
            for _ in range(lim):
                y = (y * y + c) % n
                diff = abs(x - y)
                q = (q * diff) % n
            g = math.gcd(q, n)
            k += m
        r <<= 1
    if g == 1 or g == n:
        return None
    return g


def _lp_counts(val: int, large_prime_bound: int) -> dict[int, int] | None:
    """Prime factors of a cofactor, each strictly below ``large_prime_bound``.

    ``{}`` means the cofactor was 1. ``None`` means it is not a product of
    those primes (so the relation is dropped).
    """
    if val == 1:
        return {}
    if val >= large_prime_bound * large_prime_bound:
        return None
    counts: dict[int, int] = {}
    stack = [val]
    while stack:
        v = stack.pop()
        if v == 1:
            continue
        if _prime64(v):
            if v >= large_prime_bound:
                return None
            counts[v] = counts.get(v, 0) + 1
            continue
        g = None
        for c in (1, 2, 3, 5):
            g = _brent_small(v, c)
            if g is not None:
                break
        if g is None:
            return None
        stack.append(g)
        stack.append(v // g)
    return counts


def _trial_factor(
    val: int, primes: list[int], large_prime_bound: int, max_p: int
) -> tuple[list[int], dict[int, int]] | None:
    """Exponents over the factor base, plus large-prime exponents (maybe empty)."""
    del max_p
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
    counts = _lp_counts(val, large_prime_bound)
    if counts is None:
        return None
    return exps, counts


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


def _bounds(bits: int) -> tuple[int, int, int]:
    """(factor-base limit, sieve half-width M, polynomial cap)."""
    if bits <= 36:
        return 80, 2_000, 8
    if bits <= 48:
        return 300, 6_000, 16
    if bits <= 64:
        return 700, 12_000, 24
    if bits <= 80:
        return 1_500, 16_000, 32
    if bits <= 100:
        return 3_000, 24_000, 40
    if bits <= 120:
        return 6_000, 32_000, 48
    if bits <= 140:
        return 8_000, 24_000, 80
    if bits <= 170:
        # 50-digit semiprimes: a wider polynomial budget, still one large prime.
        return 12_000, 32_000, 400
    return 20_000, 48_000, 160


def _apply_sqrt(
    n: int,
    left: int,
    yr: int,
    exp_sum: list[int],
    primes: list[int],
) -> int | None:
    for e, p in zip(exp_sum[1:], primes):
        half = e >> 1
        if half:
            yr = (yr * pow(p, half, n)) % n
    g = math.gcd((left - yr) % n, n)
    if 1 < g < n:
        return g
    g = math.gcd((left + yr) % n, n)
    if 1 < g < n:
        return g
    return None


def _split_relations(
    n: int,
    rels: list[tuple[int, list[int], int]],
    primes: list[int],
) -> int | None:
    """One GF(2) pass. Third field is the large-prime square-root contribution."""
    if len(rels) < 2:
        return None
    nbits = 1 + len(primes)
    rows: list[int] = []
    for _axb, exps, _extra in rels:
        bits = 0
        for i, e in enumerate(exps):
            if e & 1:
                bits |= 1 << i
        rows.append(bits)
    for idxs in _gf2_nullspace(rows, nbits):
        if len(idxs) < 2:
            continue
        exp_sum = [0] * nbits
        left = 1
        yr = 1
        bad = False
        for j in idxs:
            axb, exps, extra = rels[j]
            left = (left * (axb % n)) % n
            if extra != 1:
                yr = (yr * (extra % n)) % n
            if len(exps) != nbits:
                bad = True
                break
            for i, e in enumerate(exps):
                exp_sum[i] += e
        if bad or any(e & 1 for e in exp_sum):
            continue
        g = _apply_sqrt(n, left, yr, exp_sum, primes)
        if g is not None:
            return g
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
    primes = [p for p, _ in fb]
    # Two large primes. 2^24 keeps the cofactor under 2^48 so Brent can split it.
    lp_bound = min(fb_bound * fb_bound, 1 << 20)
    need = len(primes) + 8
    full: list[tuple[int, list[int], int]] = []
    # prime -> (axb, exps, full large-prime exponents)
    reducers: dict[int, tuple[int, list[int], dict[int, int]]] = {}
    solved_at = 0

    def close_full() -> int | None:
        nonlocal solved_at
        if len(full) >= need and len(full) - solved_at >= 16:
            solved_at = len(full)
            if deadline is not None and time.perf_counter() >= deadline:
                return None
            return _split_relations(n, full, primes)
        return None

    def half_extra(counts: dict[int, int]) -> int:
        extra = 1
        for p, e in counts.items():
            half = e >> 1
            if half:
                extra = (extra * pow(p, half, n)) % n
        return extra

    def push(axb: int, exps: list[int], counts: dict[int, int]) -> int | None:
        """Add large-prime exponents. A dependency becomes one full relation."""
        guard = 0
        while True:
            hit = None
            for p, e in counts.items():
                if (e & 1) and p in reducers:
                    hit = p
                    break
            if hit is None:
                break
            rax, rex, rcounts = reducers[hit]
            axb = (axb * rax) % n
            exps = [a + b for a, b in zip(exps, rex)]
            for p, e in rcounts.items():
                counts[p] = counts.get(p, 0) + e
            guard += 1
            if guard > 10000:
                return None
        odd = [p for p, e in counts.items() if e & 1]
        if not odd:
            full.append((axb % n, exps, half_extra(counts)))
            return close_full()
        p = max(odd)
        reducers[p] = (axb % n, exps, dict(counts))
        return None

    def add(axb: int, exps: list[int], counts: dict[int, int]) -> int | None:
        axb %= n
        if axb < 0:
            axb += n
        return push(axb, list(exps), dict(counts))

    def ingest(batch: list[tuple[int, list[int], dict[int, int]]]) -> int | None:
        found = None
        for axb, exps, counts in batch:
            found = add(axb, exps, counts)
            if found is not None:
                return found
        return None

    if deadline is not None and time.perf_counter() >= deadline:
        return None
    # Target A ≈ √(2n) / M  (SIQS heuristic).
    target_a = max(3, math.isqrt(max(n * 2, 1)) // max(interval, 1))
    # Classical polynomial Q(x) = (x + ⌈√n⌉)² − n, then SIQS polynomials.
    root = math.isqrt(n)
    if root * root < n:
        root += 1
    polys: list[tuple[int, int]] = [(1, root)]
    for which in range(npoly):
        factors = _pick_a(fb, target_a, which)
        got = _sqrt_mod_a(n, factors)
        if got is None:
            continue
        b, a = got
        if b > a - b:
            b = a - b
        polys.append((a, b))

    for pi, (a, b) in enumerate(polys):
        if deadline is not None and time.perf_counter() >= deadline:
            return None
        batch = _sieve_poly(
            n, a, b, fb, interval, large_prime_bound=lp_bound
        )

        found = ingest(batch)
        if found is not None:
            return found
    if len(full) >= max(8, len(primes) // 2):
        got = _split_relations(n, full, primes)
        if got is not None:
            return got
    return None
