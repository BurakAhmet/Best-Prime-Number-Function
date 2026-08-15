"""
Exact integer factorization.

Small factors by 8-way 30-wheel trial (updates √n as it shrinks). Composite
remainders split with Fermat (close factors), two-band cubic search
(Lehman + rising-product wheel), deterministic Brent–Pollard
(fixed c = 1,2,3,… — no RNG), then deterministic ECM and SIQS for larger
balanced composites. Each prime factor is confirmed with is_prime.
"""

from __future__ import annotations

import math
import time
from collections import Counter
from dataclasses import dataclass, field

from .errors import UnsettledFactorError
from .is_prime import _parse_n, is_prime

# 30-wheel steps starting at 7 (residues 1,7,11,13,17,19,23,29).
_W30 = (4, 2, 4, 2, 4, 6, 2, 6)


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


@dataclass
class _FactorBudget:
    n: int
    found: list[int] = field(default_factory=list)
    deadline: float | None = None

    def check(self, leftover: int) -> None:
        if self.deadline is not None and time.perf_counter() >= self.deadline:
            raise UnsettledFactorError(self.n, leftover=leftover, found=list(self.found))


def _split(n: int, budget: _FactorBudget | None = None) -> int:
    """A proper factor of composite n > 1."""
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
    if n.bit_length() <= 64:
        f = lehman_factor(n)
    else:
        f = lehman_factor(n, k_max=100_000)
    if f is not None and 1 < f < n:
        return f
    # Fixed c sequence: 1,2,3,… (c=0 is x^2, often degenerate).
    for c in range(1, 64):
        if budget is not None:
            budget.check(n)
        g = _brent(n, c)
        if 1 < g < n:
            return g
    # Medium / large balanced composites: ECM then SIQS (deterministic schedules).
    bits = n.bit_length()
    if bits >= 28:
        if budget is not None:
            budget.check(n)
        from .factor_ecm import ecm_factor

        g = ecm_factor(n)
        if g is not None and 1 < g < n:
            return g
    if bits >= 28:
        if budget is not None:
            budget.check(n)
        from .factor_siqs import siqs_factor

        g = siqs_factor(n)
        if g is not None and 1 < g < n:
            return g
    # Last resort: full 30-wheel trial (always finds a factor of a composite).
    if budget is not None:
        budget.check(n)
    out: list[int] = []
    rem = _trial_30(n, out)
    if out:
        return out[0]
    if rem != n and rem > 1:
        return rem
    raise RuntimeError(f"failed to split composite {n}")


def _factor_rec(n: int, out: list[int], *, parallel: bool, budget: _FactorBudget) -> None:
    if n == 1:
        return
    budget.check(n)
    if n < 4 or is_prime(n, parallel=parallel):
        out.append(n)
        return
    f = _split(n, budget)
    _factor_rec(f, out, parallel=parallel, budget=budget)
    _factor_rec(n // f, out, parallel=parallel, budget=budget)


def prime_factors(
    n: int | str, *, parallel: bool = True, max_ms: int | None = None
) -> list[int]:
    """Prime factors of n with multiplicity, ascending. ``[]`` for n < 2.

    ``max_ms`` is a wall-clock cap. When it expires and a composite
    remainder is still unsplit, raise ``UnsettledFactorError`` (the
    isolated primes are on ``.found``). ``None`` is the historical
    complete search — hostile 100-digit balanced composites can take
    a long time. The CLI default-caps huge ``n``; this function does not.
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
