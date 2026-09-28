"""
Exact integer factorization.

Small factors by 8-way 30-wheel trial (updates √n as it shrinks). Composite
remainders split with Fermat (close factors), two-band cubic search
(Lehman + rising-product wheel), deterministic Brent–Pollard
(fixed c = 1,2,3,… — no RNG), then p−1, p+1, stage-2 ECM, and SIQS.
No digit cap. Each prime factor is proved (cyclotomic, if BLS does not settle).
"""

from __future__ import annotations

import math
import time
from collections import Counter
from dataclasses import dataclass, field

from .errors import UnsettledFactorError, UnsettledPrimalityError
from .is_prime import _parse_n, is_prime

# 30-wheel steps starting at 7 (residues 1,7,11,13,17,19,23,29).
_W30 = (4, 2, 4, 2, 4, 6, 2, 6)
# Same Fermat screen as the primality filter. A pass is not a proof.
_FERMAT_BASES = (2, 3, 5, 7, 11, 13)


def _strip(n: int, p: int, out: list[int]) -> int:
    if n % p:
        return n
    while True:
        n //= p
        out.append(p)
        if n % p:
            return n


def _refresh_trial_cap(n: int, hard: int | None) -> int:
    cap = math.isqrt(n)
    if hard is not None and cap > hard:
        return hard
    return cap


def _trial_30(n: int, out: list[int], limit: int | None = None) -> int:
    """Divide n by 7,11,13,… up to limit (default isqrt(n), refreshed).

    ``limit`` is a hard ceiling. After a factor is stripped, the cap
    shrinks to ``isqrt(remainder)`` but must not jump back up to a
    60-digit root (that hung ``_one_factor(10^131+1113)`` after 193).
    """
    if n < 49:
        return n
    cap = _refresh_trial_cap(n, limit)
    p = 7
    wi = 0

    def hit() -> bool:
        nonlocal n, cap, p
        if n % p == 0:
            n = _strip(n, p, out)
            if n == 1:
                return True
            cap = _refresh_trial_cap(n, limit)
            if p > cap:
                return True
        return False

    # 8-way unroll matches one 30-wheel turn (7..31).
    while p + 28 <= cap:
        for _ in range(8):
            if hit():
                return 1 if n == 1 else n
            p += _W30[wi]
            wi += 1
            if wi == 8:
                wi = 0
    while p <= cap:
        if hit():
            return 1 if n == 1 else n
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


def _fermat_composite(n: int) -> bool:
    """True when a fixed base proves n composite."""
    if n < 2:
        return True
    for a in _FERMAT_BASES:
        if a % n == 0:
            return n != a
        if pow(a, n - 1, n) != 1:
            return True
    return False


def _power_base(n: int) -> int | None:
    """a > 1 with n = a^e, e > 1. None when n is not a perfect power."""
    if n < 4:
        return None
    root = math.isqrt(n)
    if root * root == n:
        return root
    from .prime_power import _iroot
    from .prime_sieve import _primes_upto_cached

    max_e = n.bit_length()
    for e in _primes_upto_cached(min(max_e, 4096)):
        if e < 3 or e >= max_e:
            continue
        base = _iroot(n, e)
        if base > 1 and pow(base, e) == n:
            return base
    return None


def _pollard_p1(n: int, b1: int) -> int | None:
    """Factor when some p | n has p−1 B1-smooth. Fixed base 2. No RNG."""
    from .factor_ecm import _primes_upto

    a = 2
    for p in _primes_upto(b1):
        if p > b1:
            break
        pe = p
        while pe <= b1 // p:
            pe *= p
        a = pow(a, pe, n)
        if a == 0:
            return None
    g = math.gcd(a - 1, n)
    return g if 1 < g < n else None


def _lucas_v(k: int, p: int, n: int) -> int:
    """V_k(P, 1) mod n. V_0 = 2, V_1 = P, V_{m+1} = P·V_m − V_{m−1}."""
    if k <= 0:
        return 2 % n
    p %= n
    # Leading 1 of k leaves the pair (V_1, V_2). Each later bit doubles.
    vm = p
    vmp = (p * p - 2) % n
    for i in range(k.bit_length() - 2, -1, -1):
        if (k >> i) & 1:
            vm, vmp = (vm * vmp - p) % n, (vmp * vmp - 2) % n
        else:
            vm, vmp = (vm * vm - 2) % n, (vm * vmp - p) % n
    return vm


def _williams_pp1(n: int, b1: int, p: int) -> int | None:
    """Factor when some prime factor q has q+1 B1-smooth. Parameter P is fixed."""
    from .factor_ecm import _primes_upto

    disc = (p * p - 4) % n
    g = math.gcd(disc, n)
    if 1 < g < n:
        return g
    if g == n or disc == 0:
        return None
    exponent = 1
    for prime in _primes_upto(b1):
        if prime > b1:
            break
        pe = prime
        while pe <= b1 // prime:
            pe *= prime
        exponent *= pe
    v = _lucas_v(exponent, p, n)
    g = math.gcd(v - 2, n)
    return g if 1 < g < n else None


def _ecm_ladder(bits: int) -> list[tuple[int, int, int]]:
    """(B1, B2, curves), small factors first, for every cofactor width.

    The rows follow the GMP-ECM expected-curve table (Zimmermann): a
    16-digit factor wants about B1=11e3, a 20-digit factor about B1=25e3,
    a 25-digit factor about B1=50e3. Curve counts are a fixed slice of
    that expectation, so a 91-digit cofactor gets the same early rows as
    a 40-digit one. How far the ladder climbs is half the cofactor's
    digits. B2 stays a small multiple of B1; this stage 2 is a product
    of X-differences, and a huge B2 costs more than it finds.
    """
    digits = max(2, int(bits * math.log10(2)) + 1)
    half = max(digits // 2, 12)
    # (target factor digits, B1, curves)
    # Each row starts again at σ=6. A σ that needs this B1 must not be
    # spent on a cheaper row: 10^90+9's 18-digit factor is σ=30 at
    # B1=50_000, and the same σ at B1=25_000 does not split it.
    rows = (
        (12, 2_000, 8),
        (16, 11_000, 16),
        (21, 50_000, 32),
        (26, 120_000, 16),
        (31, 250_000, 16),
        (36, 1_000_000, 8),
    )
    out: list[tuple[int, int, int]] = []
    for target, b1, curves in rows:
        if target > half + 3 and target > 20:
            break
        ratio = 40 if b1 <= 50_000 else 16
        b2 = b1 * ratio
        if b2 > 8_000_000:
            b2 = 8_000_000
        out.append((b1, b2, curves))
    if not out:
        out.append((2_000, 80_000, 8))
    return out


def _classify_cofactor(n: int, *, parallel: bool) -> str:
    """'prime', 'composite', or 'unsettled'.

    Up to 96 bits the n±1 / trial proof is the fast one. Wider than that,
    ``is_prime`` still spends its ECM budget on n±1 before it will say
    the cofactor is prime: about 13 s for the 186-bit prime factor of
    10^90+9, and minutes in the browser. The same prime is a cyclotomic
    proof in a fraction of a second, with no band edge at 200 bits.
    """
    if n.bit_length() <= 96:
        try:
            return "prime" if is_prime(n, parallel=parallel) else "composite"
        except UnsettledPrimalityError:
            pass
    from .primality_aprcl import aprcl_primality

    decided = aprcl_primality(n)
    if decided is True:
        return "prime"
    if decided is False:
        return "composite"
    return "unsettled"


def _deep_split(n: int, budget: "_FactorBudget") -> int | None:
    """Split a Fermat-composite cofactor. None only when a deadline stops it.

    With no deadline the elliptic-curve search does not stop on a digit
    cap. ``budget.check`` raises ``UnsettledFactorError`` when ``max_ms``
    expires.
    """
    from .factor_ecm import ecm_one_curve

    bits = n.bit_length()
    if budget is not None:
        budget.check(n)
    # p−1 is one modular exponentiation. One modest bound, then curves.
    # A second, larger bound runs only if those curves miss.
    if budget is not None:
        budget.check(n)
    g = _pollard_p1(n, 100_000 if bits > 64 else 20_000)
    if g is not None:
        return g
    # σ restarts at 6 for each B1. See _ecm_ladder.
    tried_at: dict[int, int] = {}
    tried_heavy_p1 = False

    def _curves(b1: int, b2: int, curves: int) -> int | None:
        start = 6 + tried_at.get(b1, 0)
        for i in range(curves):
            if budget is not None:
                budget.check(n)
            found = ecm_one_curve(n, start + i, b1, b2)
            if found is not None and 1 < found < n:
                tried_at[b1] = tried_at.get(b1, 0) + i + 1
                return found
        tried_at[b1] = tried_at.get(b1, 0) + curves
        return None

    for b1, b2, curves in _ecm_ladder(bits):
        # One larger p−1 / p+1 pass once the cheap curves have missed.
        # It is a single exponentiation, useful at every width.
        if b1 >= 50_000 and not tried_heavy_p1:
            tried_heavy_p1 = True
            if budget is not None:
                budget.check(n)
            g = _pollard_p1(n, 1_000_000)
            if g is not None:
                return g
            for param in (1, 3, 5):
                if budget is not None:
                    budget.check(n)
                g = _williams_pp1(n, 40_000, param)
                if g is not None:
                    return g
        g = _curves(b1, b2, curves)
        if g is not None:
            return g
    if not tried_heavy_p1 and bits > 80:
        if budget is not None:
            budget.check(n)
        g = _pollard_p1(n, 1_000_000)
        if g is not None:
            return g
    if 90 <= bits <= 140 and pow(2, n - 1, n) != 1:
        if budget is not None:
            budget.check(n)
        from .factor_siqs import siqs_factor

        ms: int | None
        if budget is not None and budget.deadline is not None:
            ms = int((budget.deadline - time.perf_counter()) * 1000)
            if ms <= 0:
                budget.check(n)
                return None
        else:
            ms = None
        g = siqs_factor(n, max_ms=ms)
        if g is not None and 1 < g < n:
            return g
    # The ladder missed. More curves at the B1 that fits a 20-to-30-digit
    # factor, then a slow step up. Jumping straight to B1=8e6 spends
    # minutes per curve on the wrong bound.
    for b1, b2, curves in (
        (50_000, 1_200_000, 40),
        (250_000, 4_000_000, 24),
    ):
        g = _curves(b1, b2, curves)
        if g is not None:
            return g
    b1 = 500_000
    curves = 16
    while True:
        b2 = b1 * 12
        if b2 > 8_000_000:
            b2 = 8_000_000
        g = _curves(b1, b2, curves)
        if g is not None:
            return g
        if b1 < 4_000_000:
            b1 = (b1 * 3) // 2
        else:
            curves = min(curves + 8, 48)


@dataclass
class _FactorBudget:
    n: int
    found: list[int] = field(default_factory=list)
    deadline: float | None = None

    def check(self, leftover: int) -> None:
        if self.deadline is not None and time.perf_counter() >= self.deadline:
            raise UnsettledFactorError(self.n, leftover=leftover, found=list(self.found))


def _split(n: int, budget: _FactorBudget | None = None) -> int | None:
    """A proper factor of composite n, or None when n still looks prime.

    A Fermat survivor returns None so the caller can prove it. A Fermat
    composite is split with Brent, then p−1 / p+1 / ECM / the sieve.
    There is no digit cap on that search. ``max_ms`` still aborts it.
    """
    if budget is not None:
        budget.check(n)
    f = _fermat_split(n)
    if f is not None:
        return f
    # Cubic search: complete through 64-bit (n^{1/3} ≤ 2.6e6); bounded
    # probe after that. Does not replace is_prime's trial-to-√n contract.
    from .factor_lehman import lehman_factor

    if budget is not None:
        budget.check(n)
    bits = n.bit_length()
    if bits <= 64:
        f = lehman_factor(n)
    else:
        # Full cube-root Lehman is tens of millions of steps past 40 digits.
        f = lehman_factor(n, k_max=16)
    if f is not None and 1 < f < n:
        return f
    # A wide Fermat survivor is proved before Brent or ECM. Those searches
    # cannot split a prime, and on a 60-digit prime they cost seconds.
    if bits > 96 and not _fermat_composite(n):
        return None
    # Primes up to 1e6. Doing this before Brent avoids a million modular
    # steps on a cofactor whose smallest factor is still small.
    if budget is not None:
        budget.check(n)
    peeled: list[int] = []
    rem = _trial_30(n, peeled, limit=1_000_000)
    if peeled:
        return peeled[0]
    if rem != n and rem > 1:
        return rem
    # Fixed c sequence. A miss at 2^20 is several seconds and still too
    # short for a 15-digit factor; stage-2 ECM is faster there. 2^22 is
    # the multi-minute hang, so the wide cofactor only gets a short probe.
    # 2^16 misses an 8-digit factor (10^90+9's 28511929). 2^18 with a
    # few curves catches that and still returns in about a second when
    # the factor is larger. 2^22 is the multi-minute hang.
    if bits > 60:
        brent_curves, brent_r = 4, 1 << 18
    else:
        brent_curves, brent_r = 64, 1 << 22
    for c in range(1, brent_curves + 1):
        if budget is not None:
            budget.check(n)
        g = _brent(n, c, max_r=brent_r)
        if 1 < g < n:
            return g
    if not _fermat_composite(n):
        return None
    return _deep_split(n, budget)


def _factor_rec(n: int, out: list[int], *, parallel: bool, budget: _FactorBudget) -> None:
    if n == 1:
        return
    budget.check(n)
    if n < 4:
        out.append(n)
        return
    base = _power_base(n)
    if base is not None and 1 < base < n and n % base == 0:
        exponent = 0
        reduced = n
        while reduced % base == 0:
            reduced //= base
            exponent += 1
        if reduced == 1 and exponent > 1:
            for _ in range(exponent):
                _factor_rec(base, out, parallel=parallel, budget=budget)
            return
    # Above 96 bits, BLS can spend minutes and still return unsettled.
    # Split first. A prime that nothing splits is proved afterwards.
    if n.bit_length() <= 96:
        if is_prime(n, parallel=parallel):
            out.append(n)
            return
    f = _split(n, budget)
    if f is None:
        kind = _classify_cofactor(n, parallel=parallel)
        if kind == "prime":
            out.append(n)
            return
        if kind == "composite":
            # Passed the Fermat screen and still composite (or the screen
            # was skipped). Keep splitting; a deadline raises inside.
            f = _deep_split(n, budget)
        else:
            raise UnsettledFactorError(budget.n, leftover=n, found=list(out))
    if f is None or f <= 1 or f >= n or n % f != 0:
        raise UnsettledFactorError(budget.n, leftover=n, found=list(out))
    _factor_rec(f, out, parallel=parallel, budget=budget)
    _factor_rec(n // f, out, parallel=parallel, budget=budget)


def prime_factors(
    n: int | str, *, parallel: bool = True, max_ms: int | None = None
) -> list[int]:
    """Prime factors of n with multiplicity, ascending. ``[]`` for n < 2.

    ``max_ms`` is a wall-clock cap. When it expires and a composite
    remainder is still unsplit, raise ``UnsettledFactorError`` (the
    isolated primes are on ``.found``). ``None`` runs until the
    factorization is finished: trial, Fermat, Lehman, fixed-c Brent,
    p−1, p+1, ECM with stage 2, then the quadratic sieve. A prime
    cofactor that BLS does not settle is proved with the cyclotomic
    test. A balanced semiprime whose factors are both large can take
    a long time. The CLI default-caps ``n`` wider than 512 bits; this
    function does not.
    """
    n_int = _parse_n(n)
    if n_int < 2:
        return []
    out: list[int] = []
    original = n_int
    n_int = _strip(n_int, 2, out)
    n_int = _strip(n_int, 3, out)
    n_int = _strip(n_int, 5, out)
    if n_int == 1:
        return out
    # Cheap small-prime pass (√n shrinks when factors appear).
    n_int = _trial_30(n_int, out, limit=1021 if n_int.bit_length() > 40 else None)
    if n_int == 1:
        return out
    deadline = None if max_ms is None else time.perf_counter() + max(0, int(max_ms)) / 1000.0
    budget = _FactorBudget(n=original, found=out, deadline=deadline)
    if deadline is not None and time.perf_counter() >= deadline:
        if is_prime(n_int, parallel=parallel):
            out.append(n_int)
            out.sort()
            return out
        raise UnsettledFactorError(original, leftover=n_int, found=out)
    _factor_rec(n_int, out, parallel=parallel, budget=budget)
    out.sort()
    return out


def factorint(
    n: int | str, *, parallel: bool = True, max_ms: int | None = None
) -> dict[int, int]:
    """Map prime → exponent. Empty for n < 2. See ``prime_factors`` for ``max_ms``."""
    facs = prime_factors(n, parallel=parallel, max_ms=max_ms)
    return dict(Counter(facs))
