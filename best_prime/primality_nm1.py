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
# First peel of n±1. Deepen to ``_TRIAL_PRIME_CACHE_MAX`` only when the
# leftover is Fermat-composite. DEFAULT_N is 2·5·13·q with q a 140-bit
# prime: a 5e6 scan never finds another factor and dominated CLI TIME.
_CHEAP_TRIAL_BOUND = 50_000
# Pollard p−1 stage-1 bound (smooth factors of n±1 cofactors).
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
    if bits <= 160:
        return _TRIAL_PRIME_CACHE_MAX
    if bits <= 280:
        return 200_000
    return 50_000


def _max_splits(bits: int) -> int:
    if bits <= 64:
        return 48
    if bits <= 160:
        return 48
    if bits <= 250:
        return 24
    if bits <= 512:
        return 8
    return 16


def _p1_b1(bits: int) -> int:
    if bits <= 80:
        return P1_B1_SMALL
    if bits <= 160:
        return 250_000
    return 200_000


def _brent_curve_count(bits: int) -> int:
    if bits <= 80:
        return 63
    if bits <= 160:
        return 16
    return 0


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
    if bits <= 220:
        return 600
    if bits <= 512:
        return 200
    if bits <= 1100:
        return 3_000
    if bits <= 1700:
        return 5_000
    return 500


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


def _looks_prime(c: int) -> bool:
    """Fermat bases 2…13: True means 'try a complete proof', not 'is prime'."""
    if c < 2:
        return False
    if c in (2, 3, 5, 7):
        return True
    if (c & 1) == 0:
        return False
    for a in _BASES[:6]:
        if a % c == 0:
            return c == a
        if pow(a, c - 1, c) != 1:
            return False
    return True


def _trial_split_staged(m: int) -> tuple[dict[int, int], int]:
    """Cheap trial, then deepen to the leftover's adaptive bound if composite.

    Bound follows the integer still being split, not the parent. A 140-bit
    prime leftover of DEFAULT_N must not trigger a 5e6 scan of that prime.
    """
    if m <= 1:
        return {}, m
    cheap = min(_CHEAP_TRIAL_BOUND, _adaptive_trial_bound(m))
    fac, rem = _trial_split(m, cheap)
    if rem <= 1 or _looks_prime(rem):
        return fac, rem
    full = _adaptive_trial_bound(rem)
    if full > cheap:
        extra, rem = _trial_split(rem, full)
        for p, e in extra.items():
            fac[p] = fac.get(p, 0) + e
    return fac, rem


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
    c: int,
    parent: int,
    *,
    parallel: bool,
    allow_ecpp: bool = False,
    max_h: int = 1,
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
    # 128+ bit cofactors: class-number-1 ECPP first (this is the P131
    # downrun). ≥256 bits: do *not* then run BLS / h≤16 — FastECPP
    # recurses if h=1 misses.
    if allow_ecpp and c.bit_length() >= 128:
        from .primality_ecpp import ecpp_primality

        decided = ecpp_primality(c, parallel=parallel, max_h=1)
        if decided is not None:
            return decided
        if c.bit_length() >= 256:
            return None
    decided = bls_primality(c, parallel=parallel)
    if decided is not None:
        return decided
    if allow_ecpp:
        from .primality_ecpp import ecpp_primality

        decided = ecpp_primality(c, parallel=parallel, max_h=max_h)
        if decided is not None:
            return decided
    return None


def _pollard_p1(n: int, B1: int = P1_B1_SMALL) -> int | None:
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

    Mid-size: trial → Fermat → Brent → p−1 → cubic → ECM → SIQS.
    Multi-limb (bits > 160): p−1 then Montgomery ECM; skip long Brent/cubic.
    """
    from .factor_ecm import ecm_factor
    from .factor_lehman import _c_lehman_ready, _ceil_icbrt, lehman_factor
    from .prime_factors import _brent, _fermat_split

    bits = c.bit_length()
    fac, rem = _trial_split(c, _adaptive_trial_bound(c))
    if fac:
        if rem == 1:
            return min(fac)
        if rem > 1 and rem < c:
            return min(fac)

    if bits <= 200:
        f = _fermat_split(c)
        if f is not None and 1 < f < c:
            return f

    # 10k-digit p−1 (B1=2e5) is tens of seconds of 33k-bit pow and
    # cannot prove primality. Trial already ran. FastECPP / Fermat own
    # this band. DEFAULT_N is 147-bit and never reaches here.
    if bits > 3_500:
        return None

    if bits > 160:
        f = _pollard_p1(c, B1=_p1_b1(bits))
        if f is not None:
            return f

    for cv in range(1, _brent_curve_count(bits) + 1):
        g = _brent(c, cv)
        if 1 < g < c:
            return g

    if bits <= 160:
        f = _pollard_p1(c, B1=_p1_b1(bits))
        if f is not None:
            return f

        cub = _ceil_icbrt(c)
        if _c_lehman_ready() and bits <= 128 and c > 1:
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

    f = ecm_factor(c, max_ms=_ecm_max_ms(bits))
    if f is not None and 1 < f < c:
        return f
    # bits > 160: ECPP peels need a cheap miss, not a multi-minute SIQS.
    # Mid-size BLS (DEFAULT_N / hard55 leftovers) stays ≤160 and may SIQS.
    if bits > 160:
        return None
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
    sub, r2 = _trial_split_staged(c)
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
    peeled, rem = _trial_split_staged(m)
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
        sub, r2 = _trial_split_staged(c)
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

    # DEFAULT_N shape: n−1 = tiny × one large prime. Prove that leftover
    # and skip n+1 (a 5e6 scan of hostile n+1 was most of CLI TIME).
    # Mid-size n+1 specimens (e.g. NP1_SMOOTH, 58-bit leftover) stay below
    # this cutoff so the existing short-side interleave still picks n+1.
    cheap = min(_CHEAP_TRIAL_BOUND, _adaptive_trial_bound(n - 1))
    peeled_fast, rem_fast = _trial_split(n - 1, cheap)
    if (
        rem_fast > 1
        and rem_fast.bit_length() >= 96
        and _looks_prime(rem_fast)
    ):
        proved = _prove_strictly_smaller(
            rem_fast, n, parallel=parallel, allow_ecpp=False
        )
        if proved is True:
            peeled_fast[rem_fast] = peeled_fast.get(rem_fast, 0) + 1
            if _factor_done(n, _F_value(peeled_fast), 1):
                return peeled_fast, fac_g

    peeled_f, rem_f = _trial_split_staged(n - 1)
    fac_f.update(peeled_f)
    peeled_g, rem_g = _trial_split(n + 1, cheap)
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


def _pocklington_witnesses(
    n: int, primes_of_F: list[int]
) -> tuple[Result, list[dict[str, int]] | None]:
    """Pocklington plus the (q, a) pairs. False is a composite proof."""
    fermat_ok: dict[int, bool] = {}
    witnesses: list[dict[str, int]] = []
    for q in primes_of_F:
        found: int | None = None
        for a in _BASES:
            if a % n == 0:
                return (n == a), None
            ok = fermat_ok.get(a)
            if ok is None:
                ok = pow(a, n - 1, n) == 1
                fermat_ok[a] = ok
            if not ok:
                return False, None
            if math.gcd(pow(a, (n - 1) // q, n) - 1, n) == 1:
                found = a
                break
        if found is None:
            return None, None
        witnesses.append({"q": int(q), "a": int(found)})
    return True, witnesses


def _pocklington(n: int, primes_of_F: list[int]) -> Result:
    """Pocklington: each q | F needs some fixed base a (bases may differ)."""
    decided, _wit = _pocklington_witnesses(n, primes_of_F)
    return decided


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


def _condition_II_record(
    n: int, primes_of_G: list[int]
) -> tuple[Result, dict | None]:
    """Lucas condition (II) plus the (D, P, Q) witness. False is composite."""
    if not primes_of_G:
        return None, None
    from .ntheory import jacobi

    qs = [int(q) for q in primes_of_G]
    for D in _selfridge_D():
        j = jacobi(D, n)
        if j == 0:
            g = math.gcd(abs(D), n)
            if 1 < g < n:
                return False, None
            continue
        if j != -1:
            continue
        P = 1
        Q = (1 - D) // 4
        uv = _lucas_uv(n + 1, P, Q, n)
        if isinstance(uv, int):
            if 1 < uv < n:
                return False, None
            continue
        if uv[0] % n != 0:
            continue
        ok = True
        for q in qs:
            if q <= 1 or (n + 1) % q != 0:
                ok = False
                break
            uvq = _lucas_uv((n + 1) // q, P, Q, n)
            if isinstance(uvq, int):
                if 1 < uvq < n:
                    return False, None
                ok = False
                break
            g = math.gcd(uvq[0], n)
            if 1 < g < n:
                return False, None
            if g != 1:
                ok = False
                break
        if ok:
            return True, {"D": int(D), "P": 1, "Q": int(Q), "qs": qs}
    return None, None


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


def _canon_fac(fac: dict[int, int]) -> dict[int, int]:
    return {int(q): int(fac[q]) for q in sorted(fac)}


def _nm1_record(
    n: int, fac_f: dict[int, int], primes: list[int], inequality: str
) -> tuple[Result, dict | None]:
    decided, wit = _pocklington_witnesses(n, primes)
    if decided is True and wit is not None:
        fmap = {int(q): int(fac_f[q]) for q in sorted(primes) if q in fac_f}
        return True, {
            "side": "nm1",
            "F": fmap,
            "inequality": inequality,
            "witnesses": wit,
        }
    if decided is not None:
        return decided, {"side": "nm1"}
    return None, None


def _np1_record(
    n: int, fac_g: dict[int, int], primes: list[int]
) -> tuple[Result, dict | None]:
    decided, luc = _condition_II_record(n, primes)
    if decided is True and luc is not None:
        gmap = {int(q): int(fac_g[q]) for q in sorted(primes) if q in fac_g}
        return True, {
            "side": "np1",
            "G": gmap,
            "inequality": "G>sqrt",
            "witnesses": [],
            "lucas": luc,
        }
    if decided is not None:
        return decided, {"side": "np1"}
    return None, None


def _bls_proof(n: int, *, parallel: bool = True) -> tuple[Result, dict | None]:
    """n−1, then n+1, then Combined Theorem 1. Payload is the cert witness."""
    early = _early_reject(n)
    if early is not None:
        return early, {"side": "nm1"}

    fac_f, fac_g = _factor_nm1_np1(n, parallel=parallel)
    F = _F_value(fac_f)
    G = _F_value(fac_g)
    sqrt_n = math.isqrt(n)

    if F > 1 and (n - 1) % F == 0 and F > sqrt_n:
        decided, rec = _nm1_record(
            n, fac_f, _primes_for_bound(fac_f, sqrt_n), "F>sqrt"
        )
        if decided is not None:
            return decided, rec

    if F > 1 and (n - 1) % F == 0 and n < 2 * F * F * F and _bls_cubic_ok(n, F):
        decided, rec = _nm1_record(
            n, fac_f, _primes_for_bound(fac_f, _icbrt(n)), "F>sqrt"
        )
        if decided is not None:
            return decided, rec

    if G > 1 and (n + 1) % G == 0 and G > sqrt_n:
        decided, rec = _np1_record(n, fac_g, _primes_for_bound(fac_g, sqrt_n))
        if decided is not None:
            return decided, rec

    if G == n + 1 and G > 1:
        decided, rec = _np1_record(n, fac_g, list(fac_g.keys()))
        if decided is not None:
            return decided, rec

    if _combined_theorem1_ok(n, F, G):
        dec_i, wit = _pocklington_witnesses(n, list(fac_f.keys()))
        if dec_i is False:
            return False, {"side": "combined"}
        if dec_i is True and wit is not None:
            dec_ii, luc = _condition_II_record(n, list(fac_g.keys()))
            if dec_ii is False:
                return False, {"side": "combined"}
            if dec_ii is True and luc is not None:
                return True, {
                    "side": "combined",
                    "F": _canon_fac(fac_f),
                    "G": _canon_fac(fac_g),
                    "inequality": "combined_thm1",
                    "F2G_over_2": F * F * G // 2,
                    "FG2_over_2": F * G * G // 2,
                    "witnesses": wit,
                    "lucas": luc,
                }
            if dec_ii is not None:
                return dec_ii, {"side": "combined"}

    return None, None


def _bls_decide(n: int, *, parallel: bool = True) -> tuple[Result, str | None]:
    """n−1, then n+1, then Combined Theorem 1. Side is nm1 / np1 / combined."""
    decided, rec = _bls_proof(n, parallel=parallel)
    if decided is None:
        return None, None
    side = rec.get("side") if rec else "nm1"
    return decided, side


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
