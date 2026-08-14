"""n−1 / n+1 / combined BLS primality — complete deterministic proofs.

Brillhart–Lehmer–Selfridge:

* Fermat filter with fixed bases (composite if a^{n−1} ≢ 1 mod n).
* Pocklington on a fully factored F | (n−1) (condition I).
* Lucas U-sequence on a fully factored G | (n+1) (condition II).
* n−1: F > √n, or BLS Theorem 5 when n < 2F³.
* n+1: G > √n, or G = n+1 (complete factorization). No n+1 cubic extra.
* Combined Theorem 1: gcd(F, G) = 2 and n < max(F²G/2, FG²/2).

Deterministic. No RNG. Not Miller–Rabin as the engine.
"""

from __future__ import annotations

import math
from typing import Optional

_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)

_TRIAL_BOUND = 100_000
_TRIAL_PRIME_CACHE_MAX = 5_000_000
# Pollard p−1 stage-1 bound (smooth factors of n±1 cofactors).
_P1_B1 = 100_000
P1_B1_SMALL = 100_000
SIQS_MIN_BITS = 80
SIQS_MAX_BITS = 200
_SELFRIDGE_D_LIMIT = 256

Result = Optional[bool]

_primes_cache: tuple[int, ...] | None = None
_primes_cache_limit = 0


def _primes_upto(limit: int) -> tuple[int, ...]:
    global _primes_cache, _primes_cache_limit
    need = min(int(limit), _TRIAL_PRIME_CACHE_MAX)
    if _primes_cache is None or _primes_cache_limit < need:
        from .prime_sieve import _sieve_primes_upto

        _primes_cache = tuple(_sieve_primes_upto(need))
        _primes_cache_limit = need
    return _primes_cache


def _adaptive_trial_bound(m: int) -> int:
    bits = m.bit_length()
    if bits <= 40:
        return _TRIAL_BOUND
    if bits <= 80:
        return 1_000_000
    return _TRIAL_PRIME_CACHE_MAX


def _max_splits(bits: int) -> int:
    if bits <= 64:
        return 48
    if bits <= 160:
        return 48
    if bits <= 250:
        return 64
    return 80


def _ecm_max_ms(bits: int) -> int:
    if bits <= 40:
        return 50
    if bits <= 64:
        return 200
    if bits <= 80:
        return 500
    if bits <= 100:
        return 2000
    if bits <= 160:
        return 8000
    return 15000


def _siqs_max_ms(bits: int) -> int:
    if bits <= 100:
        return 5000
    return 20000


def _trial_split(m: int, bound: int) -> tuple[dict[int, int], int]:
    """Peel prime powers ≤ bound. Returns (factors, remaining)."""
    fac: dict[int, int] = {}
    if m <= 1:
        return fac, m
    bound = min(int(bound), _TRIAL_PRIME_CACHE_MAX)
    for p in _primes_upto(bound):
        if p > bound or p * p > m:
            break
        if m % p == 0:
            e = 0
            while m % p == 0:
                m //= p
                e += 1
            fac[p] = fac.get(p, 0) + e
            if m == 1:
                break
    return fac, m


def _F_value(fac: dict[int, int]) -> int:
    prod = 1
    for q, e in fac.items():
        prod *= pow(q, e)
    return prod


def _primes_for_bound(fac: dict[int, int], target: int) -> list[int]:
    """Largest-first primes of ``fac`` whose product exceeds ``target``."""
    primes = sorted(fac.keys(), reverse=True)
    used: list[int] = []
    prod = 1
    for q in primes:
        e = fac[q]
        for _ in range(e):
            if prod > target:
                break
            prod *= q
        used.append(q)
        if prod > target:
            break
    return used


def _prove_strictly_smaller(
    c: int, parent: int, *, parallel: bool, allow_ecpp: bool = False
) -> Result:
    """True / False / None. ``c`` must be < ``parent``. Never AKS."""
    assert 1 < c < parent
    if c < 10_000:
        from .is_prime import _is_prime_small

        return _is_prime_small(c)
    from .factor_lehman import cubic_complete_ready
    from .is_prime import _MAX_FULL_TRIAL_ISQRT, is_prime

    if cubic_complete_ready(c) or c < (1 << 64) or (
        math.isqrt(c) <= _MAX_FULL_TRIAL_ISQRT and c.bit_length() <= 128
    ):
        return bool(is_prime(c, parallel=parallel))
    decided = bls_primality(c, parallel=parallel)
    if decided is not None:
        return decided
    if allow_ecpp:
        return None
    return None


def _pollard_p1(n: int, B1: int = _P1_B1) -> int | None:
    """Pollard p−1 stage 1 (fixed B1). Returns a proper factor or None."""
    if n < 4 or n % 2 == 0:
        return 2 if n % 2 == 0 and n > 2 else None
    a = 2
    for p in _primes_upto(B1):
        if p > B1:
            break
        # a := a^{p^e} mod n with p^e ≤ B1 maximal
        pe = p
        while pe <= B1 // p:
            pe *= p
        a = pow(a, pe, n)
        if a == 0:
            return None
    g = math.gcd(a - 1, n)
    if 1 < g < n:
        return g
    return None


def _try_split_cofactor(c: int, *, parallel: bool) -> int | None:
    """Proper factor of composite c, or None.

    Order: trial → Fermat → Brent → p−1 → short cubic → ECM → SIQS.
    Brent before long cubic: ~1e9 factors often fall in tens of ms.
    SIQS only for SIQS_MIN_BITS ≤ bits ≤ SIQS_MAX_BITS; budgets abort with None.
    """
    from .factor_ecm import ecm_factor
    from .factor_lehman import _c_lehman_ready, _ceil_icbrt, lehman_factor
    from .prime_factors import _brent, _fermat_split

    fac, rem = _trial_split(c, _adaptive_trial_bound(c))
    if fac:
        if rem == 1:
            return min(fac)
        if rem > 1 and rem < c:
            return min(fac)

    f = _fermat_split(c)
    if f is not None and 1 < f < c:
        return f

    for cv in range(1, 64):
        g = _brent(c, cv)
        if 1 < g < c:
            return g

    f = _pollard_p1(c, B1=P1_B1_SMALL)
    if f is not None:
        return f

    cub = _ceil_icbrt(c)
    if _c_lehman_ready() and c.bit_length() <= 128 and c > 1:
        max_k = ((1 << 128) - 1) // (4 * c)
        budget = min(max_k, cub, 100_000)
        if budget >= 16:
            f = lehman_factor(c, k_max=int(budget), parallel=parallel)
            if f is not None and 1 < f < c:
                return f
    else:
        budget = min(cub, 50_000)
        if budget >= 16:
            f = lehman_factor(c, k_max=int(budget), parallel=parallel)
            if f is not None and 1 < f < c:
                return f

    bits = c.bit_length()
    f = ecm_factor(c, max_ms=_ecm_max_ms(bits))
    if f is not None and 1 < f < c:
        return f
    if SIQS_MIN_BITS <= bits <= SIQS_MAX_BITS:
        from .factor_siqs import siqs_factor

        f = siqs_factor(c, max_ms=_siqs_max_ms(bits))
        if f is not None and 1 < f < c:
            return f
    return None


def _peel_leftover(
    c: int,
    fac: dict[int, int],
    stack: list[int],
    unproven: set[int],
    parent: int,
    *,
    parallel: bool,
    allow_split: bool,
) -> bool:
    """Absorb ``c`` into ``fac`` / ``stack``. True if a splitter call was made."""
    if c <= 1 or c in unproven:
        return False
    cb = _adaptive_trial_bound(c)
    sub, r2 = _trial_split(c, cb)
    for p, e in sub.items():
        fac[p] = fac.get(p, 0) + e
    if r2 == 1:
        return False
    c = r2
    proved = _prove_strictly_smaller(c, parent, parallel=parallel, allow_ecpp=False)
    if proved is True:
        fac[c] = fac.get(c, 0) + 1
        return False
    if not allow_split:
        unproven.add(c)
        return False
    f = _try_split_cofactor(c, parallel=parallel)
    if f is None or f <= 1 or f >= c:
        unproven.add(c)
        return True
    stack.append(f)
    stack.append(c // f)
    return True


def _factor_enough(n: int, *, parallel: bool) -> dict[int, int] | None:
    """Factor n−1 until product of proven prime powers F > √n.

    Does **not** require factoring the full cofactor R = (n−1)/F.
    Returns the prime→exponent map for F, or None if F cannot be built.
    Unproven leftovers are never inserted into F and are not re-split.
    """
    target = math.isqrt(n)
    m = n - 1
    fac: dict[int, int] = {}
    bound = _adaptive_trial_bound(m)
    peeled, rem = _trial_split(m, bound)
    fac.update(peeled)
    stack: list[int] = [rem] if rem > 1 else []
    unproven: set[int] = set()
    splits = 0
    max_splits = _max_splits(n.bit_length())

    def done() -> bool:
        F = _F_value(fac)
        return F > target or n < 2 * F * F * F

    if done():
        return fac

    while stack and not done():
        c = stack.pop()
        if c <= 1 or c in unproven:
            continue
        cb = _adaptive_trial_bound(c)
        sub, r2 = _trial_split(c, cb)
        for p, e in sub.items():
            fac[p] = fac.get(p, 0) + e
        if r2 == 1:
            if done():
                return fac
            continue
        c = r2
        proved = _prove_strictly_smaller(c, n, parallel=parallel, allow_ecpp=False)
        if proved is True:
            fac[c] = fac.get(c, 0) + 1
            if done():
                return fac
            continue
        if splits >= max_splits:
            return None
        splits += 1
        f = _try_split_cofactor(c, parallel=parallel)
        if f is None or f <= 1 or f >= c:
            unproven.add(c)
            continue
        stack.append(f)
        stack.append(c // f)

    return fac if done() else None


def _factor_done(n: int, F: int, G: int) -> bool:
    """Stop peeling n±1 when any BLS theorem's size predicate holds."""
    target = math.isqrt(n)
    if F > target:
        return True
    if n < 2 * F * F * F and _bls_cubic_ok(n, F):
        return True
    if G > target:
        return True
    if G == n + 1:
        return True
    if math.gcd(F, G) == 2 and n < max(F * F * G // 2, F * G * G // 2):
        return True
    return False


def _factor_nm1_np1(
    n: int, *, parallel: bool
) -> tuple[dict[int, int], dict[int, int]]:
    """Peel n−1 and n+1 until a BLS size predicate holds or the abort table fires.

    Returns proven prime-power maps (F, G). Unproven leftovers never enter them.
    """
    fac_f: dict[int, int] = {}
    fac_g: dict[int, int] = {}
    unproven: set[int] = set()

    peeled_f, rem_f = _trial_split(n - 1, _adaptive_trial_bound(n - 1))
    fac_f.update(peeled_f)
    peeled_g, rem_g = _trial_split(n + 1, _adaptive_trial_bound(n + 1))
    fac_g.update(peeled_g)
    stack_f: list[int] = [rem_f] if rem_f > 1 else []
    stack_g: list[int] = [rem_g] if rem_g > 1 else []
    splits = 0
    max_splits = _max_splits(n.bit_length())

    if _factor_done(n, _F_value(fac_f), _F_value(fac_g)):
        return fac_f, fac_g

    while stack_f or stack_g:
        if _factor_done(n, _F_value(fac_f), _F_value(fac_g)):
            break
        F = _F_value(fac_f)
        G = _F_value(fac_g)
        # Prefer the short side; ties go to n−1 so existing Pocklington cases stay fast.
        allow = splits < max_splits
        if stack_f and (not stack_g or F <= G):
            c = stack_f.pop()
            if _peel_leftover(
                c, fac_f, stack_f, unproven, n, parallel=parallel, allow_split=allow
            ):
                splits += 1
        else:
            c = stack_g.pop()
            if _peel_leftover(
                c, fac_g, stack_g, unproven, n, parallel=parallel, allow_split=allow
            ):
                splits += 1

    return fac_f, fac_g


def _pocklington(n: int, primes_of_F: list[int]) -> Result:
    """Pocklington: each q | F needs some fixed base a (bases may differ)."""
    # Cache a^{n-1} mod n so we do not recompute per q.
    fermat_ok: dict[int, bool] = {}
    for q in primes_of_F:
        found = False
        for a in _BASES:
            if a % n == 0:
                return n == a
            ok = fermat_ok.get(a)
            if ok is None:
                ok = pow(a, n - 1, n) == 1
                fermat_ok[a] = ok
            if not ok:
                return False  # exact composite
            if math.gcd(pow(a, (n - 1) // q, n) - 1, n) == 1:
                found = True
                break
        if not found:
            return None
    return True


def _lucas_uv(k: int, P: int, Q: int, n: int) -> tuple[int, int, int] | int:
    """Binary Lucas ladder: ``(U_k, V_k, Q^k mod n)``, or a proper factor of ``n``."""
    if n <= 2:
        return n if n > 1 else 1
    D = P * P - 4 * Q
    try:
        inv2 = pow(2, -1, n)
    except ValueError:
        g = math.gcd(2, n)
        return g if g > 1 else 1
    U, V, Qk = 0, 2, 1
    if k == 0:
        return U, V, Qk % n
    for bit in range(k.bit_length() - 1, -1, -1):
        U = (U * V) % n
        V = (V * V - 2 * Qk) % n
        Qk = (Qk * Qk) % n
        if (k >> bit) & 1:
            Up = ((P * U + V) * inv2) % n
            Vp = ((D * U + P * V) * inv2) % n
            Qk = (Qk * Q) % n
            U, V = Up, Vp
    return U, V, Qk


def _selfridge_D():
    d = 5
    sign = 1
    for _ in range(_SELFRIDGE_D_LIMIT):
        yield sign * d
        d += 2
        sign = -sign


def _condition_II(n: int, primes_of_G: list[int]) -> Result:
    """Lucas condition (II) for every prime ``q | G``. False is a composite proof."""
    if not primes_of_G:
        return None
    from .ntheory import jacobi

    for D in _selfridge_D():
        j = jacobi(D, n)
        if j == 0:
            g = math.gcd(abs(D), n)
            if 1 < g < n:
                return False
            continue
        if j != -1:
            continue
        P = 1
        Q = (1 - D) // 4
        uv = _lucas_uv(n + 1, P, Q, n)
        if isinstance(uv, int):
            if 1 < uv < n:
                return False
            continue
        if uv[0] % n != 0:
            continue
        ok = True
        for q in primes_of_G:
            if q <= 1 or (n + 1) % q != 0:
                ok = False
                break
            uvq = _lucas_uv((n + 1) // q, P, Q, n)
            if isinstance(uvq, int):
                if 1 < uvq < n:
                    return False
                ok = False
                break
            g = math.gcd(uvq[0], n)
            if 1 < g < n:
                return False
            if g != 1:
                ok = False
                break
        if ok:
            return True
    return None


def _combined_theorem1_ok(n: int, F: int, G: int) -> bool:
    """Combined Theorem 1 size predicate (not ``FG > √n``)."""
    if F <= 1 or G <= 1 or n <= 1:
        return False
    if math.gcd(F, G) != 2:
        return False
    return n < max(F * F * G // 2, F * G * G // 2)


def _early_reject(n: int) -> Result:
    """Shared tiny / Fermat filter. None means keep going."""
    if n < 2:
        return False
    if n in (2, 3, 5, 7):
        return True
    if n % 2 == 0 or n % 3 == 0 or n % 5 == 0:
        return False
    if n > 1 and math.isqrt(n) ** 2 == n:
        return False
    for a in _BASES[:6]:  # 2..13 enough for almost all composites
        if a % n == 0:
            return n == a
        if pow(a, n - 1, n) != 1:
            return False
    return None


def nm1_primality(n: int, *, parallel: bool = True) -> Result:
    """Try to settle primality of ``n`` via n−1 (Pocklington / Theorem 5).

    True / False / None (inconclusive).
    """
    early = _early_reject(n)
    if early is not None:
        return early

    fac = _factor_enough(n, parallel=parallel)
    if fac is None:
        return None

    # Sanity: F divides n−1
    F = _F_value(fac)
    if F <= 1 or (n - 1) % F != 0:
        return None
    sqrt_n = math.isqrt(n)
    cubic = n < 2 * F * F * F
    if F <= sqrt_n and not cubic:
        return None

    primes = sorted(fac.keys(), reverse=True)
    target = sqrt_n if F > sqrt_n else _icbrt(n)
    used: list[int] = []
    prod = 1
    for q in primes:
        e = fac[q]
        for _ in range(e):
            if prod > target:
                break
            prod *= q
        used.append(q)
        if prod > target:
            break

    decided = _pocklington(n, used)
    if decided is True and prod <= sqrt_n and not _bls_cubic_ok(n, prod):
        return None
    return decided


def _bls_decide(n: int, *, parallel: bool = True) -> tuple[Result, str | None]:
    """n−1, then n+1, then Combined Theorem 1. Side is nm1 / np1 / combined."""
    early = _early_reject(n)
    if early is not None:
        return early, "nm1"

    fac_f, fac_g = _factor_nm1_np1(n, parallel=parallel)
    F = _F_value(fac_f)
    G = _F_value(fac_g)
    sqrt_n = math.isqrt(n)

    if F > 1 and (n - 1) % F == 0 and F > sqrt_n:
        decided = _pocklington(n, _primes_for_bound(fac_f, sqrt_n))
        if decided is not None:
            return decided, "nm1"

    if F > 1 and (n - 1) % F == 0 and n < 2 * F * F * F and _bls_cubic_ok(n, F):
        decided = _pocklington(n, _primes_for_bound(fac_f, _icbrt(n)))
        if decided is not None:
            return decided, "nm1"

    if G > 1 and (n + 1) % G == 0 and G > sqrt_n:
        decided = _condition_II(n, _primes_for_bound(fac_g, sqrt_n))
        if decided is not None:
            return decided, "np1"

    if G == n + 1 and G > 1:
        decided = _condition_II(n, list(fac_g.keys()))
        if decided is not None:
            return decided, "np1"

    if _combined_theorem1_ok(n, F, G):
        dec_i = _pocklington(n, list(fac_f.keys()))
        if dec_i is False:
            return False, "combined"
        if dec_i is True:
            dec_ii = _condition_II(n, list(fac_g.keys()))
            if dec_ii is not None:
                return dec_ii, "combined"

    return None, None


def bls_primality(n: int, *, parallel: bool = True) -> Result:
    """n−1, then n+1, then Combined Theorem 1, sharing one factoring effort."""
    decided, _side = _bls_decide(n, parallel=parallel)
    return decided


def bls_side(n: int, *, parallel: bool = True) -> str | None:
    """Which theorem proved primality: ``nm1``, ``np1``, ``combined``, or None."""
    decided, side = _bls_decide(n, parallel=parallel)
    return side if decided is True else None


def _icbrt(n: int) -> int:
    if n < 8:
        return 0 if n < 1 else 1
    x = 1 << ((n.bit_length() + 2) // 3)
    while True:
        y = (2 * x + n // (x * x)) // 3
        if y >= x:
            return x
        x = y


def _bls_cubic_ok(n: int, F: int) -> bool:
    """BLS n^{1/3} extra: n < 2F³, R = rF+s, r odd or s²−4r not square."""
    if F <= 1 or (n - 1) % F != 0:
        return False
    if n >= 2 * F * F * F:
        return False
    R = (n - 1) // F
    if R <= 0 or math.gcd(F, R) != 1:
        return False
    r, s = divmod(R, F)
    if not (0 < s < F):
        return False
    if r & 1:
        return True
    disc = s * s - 4 * r
    if disc < 0:
        return True
    root = math.isqrt(disc)
    return root * root != disc


def nm1_ready(n: int) -> bool:
    """Whether multi-limb / hard paths should try n−1."""
    if n >= (1 << 64):
        return True
    from .factor_lehman import cubic_complete_ready

    return cubic_complete_ready(n)
