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


def _jacobi_sum(q: int, r: int) -> list[int]:
    """``j(χ,χ)`` in the power basis of ``ζ_r``, integer coefficients."""
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


def _in_cyclic_subgroup(elem: list[int], r: int, phi: list[int], n: int) -> bool:
    for m in range(r):
        if _zeta_power(m, phi, n) == elem:
            return True
    return False


def _product_test(n: int, r: int, base: list[int], idxs: list[int]) -> bool:
    phi = _phi_poly(r)
    base = _mod_phi(base, phi, n)
    # One square chain, then each Galois conjugate is an assembly.
    squares = []
    b = base
    bits = max(n.bit_length() + 1, 2)
    for _ in range(bits):
        squares.append(b)
        b = _ring_mul(b, b, phi, n)
    one = [0] * (len(phi) - 1)
    one[0] = 1
    acc = one
    for i in idxs:
        e = (n * i) // r
        t = one
        bit = 0
        while e:
            if e & 1:
                t = _ring_mul(t, squares[bit], phi, n)
            e >>= 1
            bit += 1
        t = _galois(t, pow(i, -1, r), phi, n)
        acc = _ring_mul(acc, t, phi, n)
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


def _one_test(n: int, q: int, r: int, packed: tuple[int, ...]) -> bool:
    j = [c % n for c in packed]
    if r >= 8 and _factor(r)[0][0] == 2 and n % 8 in (1, 3):
        both_raw = [0] * (2 * r)
        j2 = [c % n for c in _jacobi_sum_chi2(q, r)]
        for i, ca in enumerate(j):
            for k, cb in enumerate(j2):
                if ca and cb:
                    both_raw[i + k] = (both_raw[i + k] + ca * cb) % n
        base, idxs = both_raw, _two_idxs(r, n)
    else:
        base, idxs = j, _coprime_idxs(r)
    if n.bit_length() >= 512:
        reduced = _mod_phi(base, _phi_poly(r), n)
        got = _c_product(n, r, reduced, idxs)
        if got >= 0:
            return got == 1
    return _product_test(n, r, base, idxs)


def _tests_ok(n: int, tests: tuple[tuple[int, int, tuple[int, ...]], ...]) -> bool:
    if n.bit_length() < 1024 or len(tests) < 32:
        for q, r, packed in tests:
            if not _one_test(n, q, r, packed):
                return False
        return True
    import os
    from concurrent.futures import ProcessPoolExecutor

    workers = min(os.cpu_count() or 1, 12, len(tests))
    chunks: list[list[tuple[int, int, tuple[int, ...]]]] = [[] for _ in range(workers)]
    for i, test in enumerate(tests):
        chunks[i % workers].append(test)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_chunk_ok, n, tuple(ch)) for ch in chunks if ch]
        for fut in futs:
            if not fut.result():
                return False
    return True


def _chunk_ok(n: int, tests: tuple[tuple[int, int, tuple[int, ...]], ...]) -> bool:
    for q, r, packed in tests:
        if not _one_test(n, q, r, packed):
            return False
    return True


def _scan_chunk(n: int, s: int, root: int, base: int, start: int, count: int) -> bool:
    """True when some ``n^{start+j} mod s`` (``j = 1..count``) divides ``n``."""
    acc = pow(base, start, s)
    for _ in range(count):
        acc = (acc * base) % s
        if 1 < acc <= root and n % acc == 0:
            return True
    return False


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
    # The Jacobi identity is still required for every (q, r).
    if not _tests_ok(n, tests):
        return False
    # Every prime divisor p ≤ √n equals n^k mod s for some k = 1..R-1.
    base = n % s
    if n.bit_length() < 1024:
        acc = 1 % s
        for _k in range(1, R):
            acc = (acc * base) % s
            if 1 < acc <= root and n % acc == 0:
                return False
        return True
    import os
    from concurrent.futures import ProcessPoolExecutor

    workers = min(os.cpu_count() or 1, 12)
    span = R - 1
    chunk = (span + workers - 1) // workers
    jobs = []
    for i in range(workers):
        start = i * chunk
        if start >= span:
            break
        count = min(chunk, span - start)
        jobs.append((start, count))
    with ProcessPoolExecutor(max_workers=len(jobs)) as pool:
        futs = [
            pool.submit(_scan_chunk, n, s, root, base, start, count)
            for start, count in jobs
        ]
        for fut in futs:
            if fut.result():
                return False
    return True
