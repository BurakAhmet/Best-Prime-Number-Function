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


def _ecm_phases(bits: int) -> list[tuple[int, int, int]]:
    """(B1, B2, curves) for a cofactor of this width. Stage 2 is B2.

    The first rows are sized for the factor ECM actually meets on a
    30-to-90-digit composite (about 12–20 digits), not for a balanced
    half-size factor. The continuation after these rows keeps going.
    """
    if bits <= 80:
        return [(2_000, 100_000, 12)]
    if bits <= 120:
        return [(8_000, 700_000, 12), (20_000, 1_000_000, 8)]
    if bits <= 180:
        return [(11_000, 900_000, 10), (50_000, 2_000_000, 16)]
    if bits <= 240:
        return [(15_000, 1_200_000, 8), (50_000, 2_000_000, 12), (200_000, 4_000_000, 8)]
    if bits <= 340:
        return [(15_000, 1_200_000, 8), (50_000, 2_000_000, 12), (250_000, 5_000_000, 8)]
    return [(50_000, 2_000_000, 8), (250_000, 5_000_000, 8), (1_000_000, 12_000_000, 6)]


def _classify_cofactor(n: int, *, parallel: bool) -> str:
    """'prime', 'composite', or 'unsettled'.

    Below 256 bits a BLS miss is not a composite. The cyclotomic proof
    has no such floor, so a Fermat survivor still gets a finished proof.
    """
    try:
        return "prime" if is_prime(n, parallel=parallel) else "composite"
    except UnsettledPrimalityError:
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
    g = _pollard_p1(n, 100_000 if bits > 90 else 20_000)
    if g is not None:
        return g
    sigma = 6
    for b1, b2, curves in _ecm_phases(bits):
        for _ in range(curves):
            if budget is not None:
                budget.check(n)
            g = ecm_one_curve(n, sigma, b1, b2)
            sigma += 1
            if g is not None and 1 < g < n:
                return g
    if bits > 160:
        # The planned curves missed. One deeper p−1 / p+1 pass, then the sieve.
        if budget is not None:
            budget.check(n)
        g = _pollard_p1(n, 2_000_000)
        if g is not None:
            return g
        for param in (1, 3, 5):
            if budget is not None:
                budget.check(n)
            g = _williams_pp1(n, 60_000, param)
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
    # No digit ceiling. Each new sigma is the next fixed curve.
    b1 = 100_000
    curves = 12
    while True:
        b2 = b1 * 40
        if b2 > 30_000_000:
            b2 = 30_000_000
        for _ in range(curves):
            if budget is not None:
                budget.check(n)
            g = ecm_one_curve(n, sigma, b1, b2)
            sigma += 1
            if g is not None and 1 < g < n:
                return g
        if b1 < 8_000_000:
            b1 *= 2
        else:
            curves = min(curves + 4, 80)


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
    if bits > 120:
        brent_curves, brent_r = 3, 1 << 16
    elif bits > 60:
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
