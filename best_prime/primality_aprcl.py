"""Deterministic cyclotomic primality (Adleman–Pomerance–Rumely / Lenstra).

For an odd ``n`` that is not a prime power, choose a fixed exponent ``R``
whose prime-product ``s = ∏_{q-1 | R} q`` exceeds ``√n``. Jacobi-sum tests
in ``Z[ζ_r]/(n)`` show that every prime divisor of ``n`` is ``n^k mod s``
for some ``k < R``. Those residues are then divided into ``n``. No randomness.

Schoof, "Four primality testing algorithms", §3 (following Lenstra's
Bourbaki lecture). ``R`` is ``lcm(1..16)`` or ``lcm(1..17)`` so that ``s``
clears ``√n`` through 1000 decimal digits.
"""

from __future__ import annotations

import math
from functools import lru_cache

# lcm(1..16) and lcm(1..17). s(R) has 231 and 512 digits respectively.
_R_SMALL = 720720
_R_LARGE = 12252240


def _factor(n: int) -> list[tuple[int, int]]:
    fac: list[tuple[int, int]] = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            c = 0
            while n % d == 0:
                n //= d
                c += 1
            fac.append((d, c))
        d += 1 if d == 2 else 2
    if n > 1:
        fac.append((n, 1))
    return fac


def _divisors(n: int) -> list[int]:
    ds = [1]
    for p, e in _factor(n):
        nd: list[int] = []
        pe = 1
        for _ in range(e + 1):
            nd.extend(d * pe for d in ds)
            pe *= p
        ds = nd
    return ds


def _is_prime_small(q: int) -> bool:
    if q < 2:
        return False
    if q % 2 == 0:
        return q == 2
    d = 3
    r = int(math.isqrt(q))
    while d <= r:
        if q % d == 0:
            return False
        d += 2
    return True


def _phi(r: int) -> int:
    v = r
    for p, _e in _factor(r):
        v = v // p * (p - 1)
    return v


def _primitive_root(q: int) -> int:
    fac = _factor(q - 1)
    g = 2
    while True:
        if all(pow(g, (q - 1) // p, q) != 1 for p, _e in fac):
            return g
        g += 1


def _phi_poly(r: int) -> list[int]:
    """``Φ_r`` for a prime power ``r``, low degree first, monic."""
    p, e = _factor(r)[0]
    pk = p ** (e - 1)
    deg = pk * (p - 1)
    coeffs = [0] * (deg + 1)
    for i in range(p):
        coeffs[i * pk] = 1
    return coeffs


def _mod_phi(raw: list[int], phi: list[int], n: int) -> list[int]:
    deg = len(phi) - 1
    r = [c % n for c in raw] + [0] * deg
    inv = pow(phi[-1], -1, n)
    while len(r) > deg:
        if r[-1] == 0:
            r.pop()
            continue
        coef = (r[-1] * inv) % n
        shift = len(r) - 1 - deg
        r.pop()
        if coef:
            for i in range(deg):
                r[shift + i] = (r[shift + i] - coef * phi[i]) % n
    if len(r) < deg:
        r.extend([0] * (deg - len(r)))
    return r[:deg]


def _ring_mul(a: list[int], b: list[int], phi: list[int], n: int) -> list[int]:
    deg = len(phi) - 1
    raw = [0] * (2 * deg)
    for i, ca in enumerate(a):
        if ca == 0:
            continue
        for j, cb in enumerate(b):
            if cb and i + j < len(raw):
                raw[i + j] += ca * cb
    for i, c in enumerate(raw):
        if c:
            raw[i] = c % n
    return _mod_phi(raw, phi, n)


def _ring_pow(base: list[int], exp: int, phi: list[int], n: int) -> list[int]:
    result = [0] * (len(phi) - 1)
    result[0] = 1
    b = base
    while exp:
        if exp & 1:
            result = _ring_mul(result, b, phi, n)
        if exp > 1:
            b = _ring_mul(b, b, phi, n)
        exp >>= 1
    return result


def _galois(a: list[int], m: int, phi: list[int], n: int) -> list[int]:
    raw = [0] * ((len(a) - 1) * m + 1)
    for i, c in enumerate(a):
        if c:
            raw[i * m] = c % n
    return _mod_phi(raw, phi, n)


def _reduce_sum(acc_len_r: list[int], phi: list[int], n: int) -> list[int]:
    return _mod_phi(acc_len_r, phi, n)


def _c_jacobi(q: int, r: int, which: int) -> list[int] | None:
    lib = _lib()
    if lib is None or q > 0xFFFFFFFF or r > 0xFFFFFFFF:
        return None
    import ctypes

    out = (ctypes.c_longlong * r)()
    try:
        rc = lib.aprcl_jacobi_sum(q, r, which, out)
    except Exception:
        return None
    if rc != 0:
        return None
    return [int(out[i]) for i in range(r)]


def _jacobi_sum(q: int, r: int) -> list[int]:
    """``j(χ,χ)`` in the power basis of ``ζ_r``, integer coefficients."""
    got = _c_jacobi(q, r, 1)
    if got is not None:
        return got
    g = _primitive_root(q)
    ind = [0] * q
    x = 1
    step = (q - 1) // r
    for i in range(q - 1):
        ind[x] = (i * step) % r
        x = x * g % q
    acc = [0] * r
    for t in range(1, q):
        u = (1 - t) % q
        if u == 0:
            continue
        acc[(ind[t] + ind[u]) % r] -= 1
    return acc


def _jacobi_sum_chi2(q: int, r: int) -> list[int]:
    """``j(χ, χ^2)`` for a character of order ``r``."""
    got = _c_jacobi(q, r, 2)
    if got is not None:
        return got
    g = _primitive_root(q)
    ind = [0] * q
    x = 1
    step = (q - 1) // r
    for i in range(q - 1):
        ind[x] = (i * step) % r
        x = x * g % q
    acc = [0] * r
    for t in range(1, q):
        u = (1 - t) % q
        if u == 0:
            continue
        acc[(ind[t] + (2 * ind[u]) % r) % r] -= 1
    return acc


@lru_cache(maxsize=4)
def _table(R: int) -> tuple[int, tuple[tuple[int, int, tuple[int, ...]], ...]]:
    """``(s, tests)`` where each test is ``(q, r, packed jacobi sum)``."""
    qs = tuple(sorted(d + 1 for d in _divisors(R) if _is_prime_small(d + 1)))
    s = 1
    for q in qs:
        s *= q
    tests: list[tuple[int, int, tuple[int, ...]]] = []
    for q in qs:
        for p, e in _factor(q - 1):
            r = p**e
            tests.append((q, r, tuple(_jacobi_sum(q, r))))
    return s, tuple(tests)


def _zeta_power(m: int, phi: list[int], n: int) -> list[int]:
    raw = [0] * (m + 1)
    raw[m] = 1
    return _mod_phi(raw, phi, n)


def _in_cyclic_subgroup(elem: list[int], r: int, phi: list[int], n: int) -> int:
    """Exponent ``m`` with ``elem = ζ^m``, or ``-1``."""
    for m in range(r):
        if _zeta_power(m, phi, n) == elem:
            return m
    return -1


def _product_test(n: int, r: int, base: list[int], idxs: list[int]) -> int:
    """Jacobi product of Theorem 3.2, via one large exponentiation.

    ``floor(n i / r) = (n // r) * i + ((n % r) * i) // r``, so
    ``∏ σ_{i^{-1}}(J^{floor(n i / r)}) = s1^{n // r} * α`` where the
    exponents that build ``s1`` and ``α`` are smaller than ``r``.
    Cohen–Lenstra, as in Schoof §3.
    """
    phi = _phi_poly(r)
    base = _mod_phi(base, phi, n)
    one = [0] * (len(phi) - 1)
    one[0] = 1
    cached: dict[int, list[int]] = {}

    def image(i: int) -> list[int]:
        inv = pow(i, -1, r)
        hit = cached.get(inv)
        if hit is None:
            hit = _galois(base, inv, phi, n)
            cached[inv] = hit
        return hit

    q, tmod = divmod(n, r)
    s1 = one
    alpha = one
    for i in idxs:
        g = image(i)
        s1 = _ring_mul(s1, _ring_pow(g, i, phi, n), phi, n)
        e = (tmod * i) // r
        if e:
            alpha = _ring_mul(alpha, _ring_pow(g, e, phi, n), phi, n)
    acc = _ring_mul(_ring_pow(s1, q, phi, n), alpha, phi, n)
    return _in_cyclic_subgroup(acc, r, phi, n)


def _coprime_idxs(r: int) -> list[int]:
    return [i for i in range(1, r) if math.gcd(i, r) == 1]


def _two_idxs(r: int, n: int) -> list[int]:
    if r >= 8 and n % 8 in (1, 3):
        return [i for i in range(1, r) if i % 8 in (1, 3)]
    return _coprime_idxs(r)


def _choose_R(n: int) -> int:
    root = math.isqrt(n)
    s_small, _ = _table(_R_SMALL)
    if s_small > root:
        return _R_SMALL
    return _R_LARGE


_LIB = None
_LIB_TRIED = False


def _lib():
    global _LIB, _LIB_TRIED
    if _LIB_TRIED:
        return _LIB
    _LIB_TRIED = True
    import ctypes
    from pathlib import Path

    candidates = [
        Path(__file__).resolve().parents[1] / "is_prime_data" / "aprcl_hot.so",
        Path(__file__).resolve().parent / "aprcl_hot.so",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            lib = ctypes.CDLL(str(path))
        except OSError:
            continue
        lib.aprcl_product_ok.restype = ctypes.c_int
        lib.aprcl_product_ok.argtypes = [
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.c_size_t,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint),
            ctypes.c_int,
        ]
        lib.aprcl_residue_divides.restype = ctypes.c_int
        lib.aprcl_residue_divides.argtypes = [
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.c_size_t,
            ctypes.c_uint64,
            ctypes.c_uint64,
        ]
        lib.aprcl_jacobi_sum.restype = ctypes.c_int
        lib.aprcl_jacobi_sum.argtypes = [
            ctypes.c_ulong,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_longlong),
        ]
        _LIB = lib
        return _LIB
    return None


def _c_product(n: int, r: int, base: list[int], idxs: list[int]) -> int:
    """1 if the product is a root of unity, 0 if not, -1 if the helper failed."""
    lib = _lib()
    if lib is None:
        return -1
    import ctypes
    from array import array

    limbs = (n.bit_length() + 63) // 64
    mod = array("Q", n.to_bytes(limbs * 8, "little"))
    buf = array("Q", [0]) * (limbs * len(base))
    width = limbs * 8
    for i, coeff in enumerate(base):
        raw = array("Q", int(coeff % n).to_bytes(width, "little"))
        buf[i * limbs : (i + 1) * limbs] = raw
    idx_a = array("I", idxs)
    try:
        return int(
            lib.aprcl_product_ok(
                (ctypes.c_uint64 * len(mod)).from_buffer(mod),
                limbs,
                r,
                (ctypes.c_uint64 * len(buf)).from_buffer(buf),
                len(base),
                (ctypes.c_uint * len(idx_a)).from_buffer(idx_a),
                len(idx_a),
            )
        )
    except Exception:
        return -1


class _BudgetExpired(Exception):
    """The wall-clock cap elapsed during a cyclotomic proof."""


def _one_test(n: int, q: int, r: int, packed: tuple[int, ...]) -> tuple[bool, int, int]:
    """Return ``(identity holds, prime of r, exponent of the root of unity)``.

    The exponent is ``-1`` when the helper did not report it. A failed identity
    has exponent ``-1`` as well.
    """
    from .progress import deadline_hit

    if deadline_hit():
        raise _BudgetExpired
    prime = _factor(r)[0][0]
    j = [c % n for c in packed]
    if r >= 8 and prime == 2 and n % 8 in (1, 3):
        both_raw = [0] * (2 * r)
        j2 = [c % n for c in _jacobi_sum_chi2(q, r)]
        for i, ca in enumerate(j):
            for k, cb in enumerate(j2):
                if ca and cb:
                    both_raw[i + k] = (both_raw[i + k] + ca * cb) % n
        base, idxs = both_raw, _two_idxs(r, n)
    else:
        base, idxs = j, _coprime_idxs(r)
    reduced = _mod_phi(base, _phi_poly(r), n)
    got = _c_product(n, r, reduced, idxs)
    if got >= 0:
        if got == 0:
            return False, prime, -1
        return True, prime, got - 1
    h = _product_test(n, r, base, idxs)
    return h >= 0, prime, h


def _lp_hit(n: int, q: int, prime: int, h: int) -> bool:
    """Proposition 3.3: the root of unity generates the l-part."""
    if h < 0 or h % prime == 0:
        return False
    if prime == 2:
        return pow(q, (n - 1) // 2, n) == n - 1
    return True


def _tests_ok(n: int, tests: tuple[tuple[int, int, tuple[int, ...]], ...]) -> set[int] | None:
    """Primes ``l`` whose first condition was witnessed, or None if composite."""
    satisfied: set[int] = set()

    def absorb(row: tuple[bool, int, int], q: int) -> bool:
        ok, prime, h = row
        if not ok:
            return False
        if _lp_hit(n, q, prime, h):
            satisfied.add(prime)
        return True

    if n.bit_length() < 1024 or len(tests) < 32:
        for q, r, packed in tests:
            if not absorb(_one_test(n, q, r, packed), q):
                return None
        return satisfied
    import os
    from concurrent.futures import ThreadPoolExecutor

    # The ring arithmetic is in the GMP helper, which releases the GIL.
    workers = min(os.cpu_count() or 1, 12, len(tests))
    chunks: list[list[tuple[int, int, tuple[int, ...]]]] = [[] for _ in range(workers)]
    # Spread expensive prime-power degrees across workers.
    ordered = sorted(tests, key=lambda t: t[1], reverse=True)
    for i, test in enumerate(ordered):
        chunks[i % workers].append(test)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_chunk_ok, n, tuple(ch)) for ch in chunks if ch]
        for fut in futs:
            got = fut.result()
            if got is None:
                return None
            satisfied.update(got)
    return satisfied


def _chunk_ok(n: int, tests: tuple[tuple[int, int, tuple[int, ...]], ...]) -> set[int] | None:
    satisfied: set[int] = set()
    for q, r, packed in tests:
        ok, prime, h = _one_test(n, q, r, packed)
        if not ok:
            return None
        if _lp_hit(n, q, prime, h):
            satisfied.add(prime)
    return satisfied


def _scan_chunk(n: int, s: int, root: int, base: int, start: int, count: int) -> bool:
    """True when some ``n^{start+j} mod s`` (``j = 1..count``) divides ``n``."""
    acc = pow(base, start, s)
    for _ in range(count):
        acc = (acc * base) % s
        if 1 < acc <= root and n % acc == 0:
            return True
    return False


def _c_scan(n: int, s: int, start: int, count: int) -> int:
    """1 if a residue divides ``n``, 0 if not, -1 if the helper is absent."""
    lib = _lib()
    if lib is None or count <= 0:
        return -1
    import ctypes
    from array import array

    def limbs(value: int) -> array:
        width = max((value.bit_length() + 63) // 64, 1)
        return array("Q", value.to_bytes(width * 8, "little"))

    mod = limbs(n)
    sm = limbs(s)
    try:
        return int(
            lib.aprcl_residue_divides(
                (ctypes.c_uint64 * len(mod)).from_buffer(mod),
                len(mod),
                (ctypes.c_uint64 * len(sm)).from_buffer(sm),
                len(sm),
                start,
                count,
            )
        )
    except Exception:
        return -1


def _residues_divide(n: int, s: int, root: int, base: int, span: int) -> bool:
    """True when some ``n^k mod s`` for ``k = 1..span`` is a proper divisor."""
    import os
    from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

    workers = min(os.cpu_count() or 1, 12)
    chunk = (span + workers - 1) // workers
    jobs = []
    for i in range(workers):
        start = i * chunk
        if start >= span:
            break
        jobs.append((start, min(chunk, span - start)))
    if _lib() is not None and jobs:
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            got = list(pool.map(lambda job: _c_scan(n, s, job[0], job[1]), jobs))
        if all(v >= 0 for v in got):
            return any(v == 1 for v in got)
    with ProcessPoolExecutor(max_workers=len(jobs)) as pool:
        futs = [
            pool.submit(_scan_chunk, n, s, root, base, start, count)
            for start, count in jobs
        ]
        for fut in futs:
            if fut.result():
                return True
    return False


def _witness_prime(n: int, prime: int, satisfied: set[int]) -> bool | None:
    """Hunt one more prime q ≡ 1 (mod ``prime``) that witnesses Proposition 3.3.

    False: a proper factor of ``n`` turned up. None: no witness in the bound.
    """
    tried = 0
    i = 1
    while tried < 48 and i < 2_000_000:
        q = prime * i + 1
        i += 1
        if not _is_prime_small(q) or math.gcd(n, q) != 1:
            if q > 1 and n % q == 0:
                return False
            continue
        k = 0
        qq = q - 1
        while qq % prime == 0:
            qq //= prime
            k += 1
        r = prime**k
        if r >= 40:
            continue
        tried += 1
        ok, got_p, h = _one_test(n, q, r, tuple(_jacobi_sum(q, r)))
        if not ok:
            return False
        if _lp_hit(n, q, got_p, h):
            satisfied.add(prime)
            return True
    return None


def aprcl_primality(n: int) -> bool | None:
    """True / False, or None when ``√n`` exceeds the prepared modulus.

    False means a proper factor was isolated or a Jacobi identity failed.
    Callers that only need compositeness still treat False as composite.
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if (n & 1) == 0:
        return False
    root = math.isqrt(n)
    if root * root == n:
        return False
    R = _choose_R(n)
    s, tests = _table(R)
    if s <= root:
        return None
    g = math.gcd(n, s)
    if g > 1:
        return False
    # First condition of Theorem 3.2 is free when n^{l-1} ≢ 1 (mod l^2).
    # Otherwise some Jacobi root of unity must generate the l-part
    # (Schoof, Proposition 3.3). A missing witness is not a proof.
    try:
        satisfied = _tests_ok(n, tests)
    except _BudgetExpired:
        return None
    if satisfied is None:
        return False
    for prime, _e in _factor(R):
        if prime >= 3 and pow(n, prime - 1, prime * prime) != 1:
            satisfied.add(prime)
        elif prime not in satisfied:
            witness = _witness_prime(n, prime, satisfied)
            if witness is False:
                return False
            if witness is None:
                return None
    # Every prime divisor p ≤ √n equals n^k mod s for some k = 1..R-1.
    base = n % s
    if _residues_divide(n, s, root, base, R - 1):
        return False
    return True
