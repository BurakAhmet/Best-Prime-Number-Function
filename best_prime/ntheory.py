"""
Deterministic arithmetic on top of our primes / factoring.

Totient, divisors, primorial, Jacobi, CRT. No RNG, no Miller–Rabin,
no prime libraries. Single-n functions factor once; range totient is a
linear sieve (O(n)).
"""

from __future__ import annotations

import math
from array import array
from typing import Sequence

from .is_prime import _parse_n
from .prime_factors import factorint
from .prime_sieve import _nth_prime_upper, _parse_k, _primes_upto_cached, primerange

# Linear-sieve totient_range: uint32 table, 4 bytes × (n+1). 20e6 → ~80 MiB.
TOTIENT_RANGE_MAX = 20_000_000


def _prod_tree(vals: list[int]) -> int:
    """Product of ints via a balanced tree (much faster than left-fold for big ints)."""
    if not vals:
        return 1
    while len(vals) > 1:
        nxt: list[int] = []
        n = len(vals)
        i = 0
        lim = n - 1
        while i < lim:
            nxt.append(vals[i] * vals[i + 1])
            i += 2
        if n & 1:
            nxt.append(vals[-1])
        vals = nxt
    return vals[0]


def gcd(*args: int) -> int:
    """Greatest common divisor. ``gcd()`` is 0; negatives allowed."""
    if not args:
        return 0
    g = abs(int(args[0]))
    for x in args[1:]:
        g = math.gcd(g, int(x))
        if g == 1:
            return 1
    return g


def egcd(a: int, b: int) -> tuple[int, int, int]:
    """Return ``(g, x, y)`` with ``a*x + b*y = g = gcd(a, b)``."""
    a = int(a)
    b = int(b)
    x0, x1 = 1, 0
    y0, y1 = 0, 1
    while b:
        q = a // b
        a, b = b, a - q * b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    if a < 0:
        return -a, -x0, -y0
    return a, x0, y0


def modinv(a: int, m: int) -> int:
    """Inverse of ``a`` modulo ``m`` (``m > 1``). Raises ``ValueError`` if none."""
    m = int(m)
    if m <= 1:
        raise ValueError("modulus must be > 1")
    try:
        return pow(int(a), -1, m)
    except ValueError as exc:
        raise ValueError(f"{a} is not invertible modulo {m}") from exc


def crt(remainders: Sequence[int], moduli: Sequence[int]) -> int:
    """Solve ``x ≡ remainders[i] (mod moduli[i])``.

    Moduli need not be pairwise coprime; inconsistent systems raise
    ``ValueError``. Result is in ``[0, lcm(moduli))``.
    """
    if len(remainders) != len(moduli):
        raise ValueError("remainders and moduli must have the same length")
    if not remainders:
        raise ValueError("empty CRT system")
    x = int(remainders[0])
    m = int(moduli[0])
    if m <= 0:
        raise ValueError("moduli must be positive")
    x %= m
    for ai, mi in zip(remainders[1:], moduli[1:]):
        ai = int(ai)
        mi = int(mi)
        if mi <= 0:
            raise ValueError("moduli must be positive")
        g, p, _ = egcd(m, mi)
        if (ai - x) % g:
            raise ValueError("CRT system has no solution")
        # x + m * t ≡ ai (mod mi)  ⇒  t ≡ (ai-x)/g * (m/g)^{-1}  (mod mi/g)
        t = ((ai - x) // g) * modinv(m // g, mi // g)
        x += m * (t % (mi // g))
        m = m // g * mi
        x %= m
    return x


def jacobi(a: int, n: int) -> int:
    """Jacobi symbol ``(a/n)`` ∈ {-1, 0, 1}. ``n`` must be odd and positive."""
    a = int(a)
    n = int(n)
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


def totient(n: int | str, *, parallel: bool = True) -> int:
    """Euler's φ(n): count of ``k`` in ``1..n`` coprime to ``n``. ``φ(0)=0``."""
    n_int = _parse_n(n)
    if n_int == 0:
        return 0
    if n_int == 1:
        return 1
    fac = factorint(n_int, parallel=parallel)
    r = n_int
    for p in fac:
        r -= r // p
    return r


euler_phi = totient


def totient_range(limit: int | str) -> list[int]:
    """``[φ(0), φ(1), …, φ(limit)]`` via a linear sieve. ``limit ≤ TOTIENT_RANGE_MAX``."""
    n = _parse_n(limit)
    if n > TOTIENT_RANGE_MAX:
        raise ValueError(
            f"totient_range supports limit <= {TOTIENT_RANGE_MAX} (got {n})"
        )
    if n == 0:
        return [0]
    phi = array("I", range(n + 1))
    # phi[k] starts as k; for each prime p, φ(j) -= φ(j)/p on multiples j.
    for i in range(2, n + 1):
        if phi[i] == i:
            for j in range(i, n + 1, i):
                phi[j] -= phi[j] // i
    return phi.tolist()


def carmichael_lambda(n: int | str, *, parallel: bool = True) -> int:
    """Carmichael λ(n): exponent of ``(Z/nZ)*``. ``λ(0)=0``, ``λ(1)=1``."""
    n_int = _parse_n(n)
    if n_int == 0:
        return 0
    if n_int == 1:
        return 1
    fac = factorint(n_int, parallel=parallel)
    r = 1
    for p, e in fac.items():
        if p == 2 and e >= 3:
            lam = 1 << (e - 2)
        else:
            lam = p ** (e - 1) * (p - 1)
        r = math.lcm(r, lam)
    return r


def divisor_count(n: int | str, *, parallel: bool = True) -> int:
    """``d(n)``: number of positive divisors. ``d(0)`` is undefined → error."""
    n_int = _parse_n(n)
    if n_int == 0:
        raise ValueError("divisor_count(0) is undefined")
    if n_int == 1:
        return 1
    d = 1
    for e in factorint(n_int, parallel=parallel).values():
        d *= e + 1
    return d


def divisor_sum(n: int | str, k: int = 1, *, parallel: bool = True) -> int:
    """``σ_k(n)``: sum of ``d^k`` over positive divisors ``d`` of ``n``."""
    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("k must be an int")
    if k < 0:
        raise ValueError("k must be >= 0")
    n_int = _parse_n(n)
    if n_int == 0:
        raise ValueError("divisor_sum(0) is undefined")
    if k == 0:
        return divisor_count(n_int, parallel=parallel)
    if n_int == 1:
        return 1
    s = 1
    for p, e in factorint(n_int, parallel=parallel).items():
        pk = p**k
        s *= (pk ** (e + 1) - 1) // (pk - 1)
    return s


def divisors(n: int | str, *, parallel: bool = True) -> list[int]:
    """Positive divisors of ``n``, ascending. ``divisors(1) == [1]``."""
    n_int = _parse_n(n)
    if n_int == 0:
        raise ValueError("divisors(0) is undefined")
    if n_int == 1:
        return [1]
    fac = factorint(n_int, parallel=parallel)
    divs = [1]
    for p, e in fac.items():
        mul = 1
        extra: list[int] = []
        for _ in range(e):
            mul *= p
            extra.extend(d * mul for d in divs)
        divs.extend(extra)
    divs.sort()
    return divs


def omega(n: int | str, *, parallel: bool = True) -> int:
    """``ω(n)``: number of distinct prime factors. ``ω(0)=ω(1)=0``."""
    n_int = _parse_n(n)
    if n_int < 2:
        return 0
    return len(factorint(n_int, parallel=parallel))


def bigomega(n: int | str, *, parallel: bool = True) -> int:
    """``Ω(n)``: prime factors counted with multiplicity. ``Ω(0)=Ω(1)=0``."""
    n_int = _parse_n(n)
    if n_int < 2:
        return 0
    return sum(factorint(n_int, parallel=parallel).values())


def radical(n: int | str, *, parallel: bool = True) -> int:
    """Square-free kernel: product of distinct primes dividing ``n``. ``rad(0)=0``, ``rad(1)=1``."""
    n_int = _parse_n(n)
    if n_int == 0:
        return 0
    if n_int == 1:
        return 1
    r = 1
    for p in factorint(n_int, parallel=parallel):
        r *= p
    return r


def is_squarefree(n: int | str, *, parallel: bool = True) -> bool:
    """True iff no square other than 1 divides ``n``. ``1`` is square-free; ``0`` is not."""
    n_int = _parse_n(n)
    if n_int == 0:
        return False
    if n_int == 1:
        return True
    # Fast reject: 4|n, 9|n, …
    if (n_int & 3) == 0:
        return False
    return all(e == 1 for e in factorint(n_int, parallel=parallel).values())


def is_semiprime(n: int | str, *, parallel: bool = True) -> bool:
    """True iff ``n = p*q`` for primes ``p, q`` (not necessarily distinct)."""
    n_int = _parse_n(n)
    if n_int < 4:
        return False
    return bigomega(n_int, parallel=parallel) == 2


def is_carmichael(n: int | str, *, parallel: bool = True) -> bool:
    """True iff ``n`` is a Carmichael number (square-free composite, ``p-1 | n-1`` for all ``p|n``)."""
    n_int = _parse_n(n)
    if n_int < 561:
        return False
    fac = factorint(n_int, parallel=parallel)
    if len(fac) < 3:
        return False
    nm1 = n_int - 1
    for p, e in fac.items():
        if e != 1 or nm1 % (p - 1):
            return False
    return True


def primorial(n: int | str, *, nth: bool = False) -> int:
    """Primorial.

    * ``nth=False`` (default): product of primes ``≤ n``. ``primorial(1) == 1``.
    * ``nth=True``: product of the first ``n`` primes (``n ≥ 1``).
      ``primorial(4, nth=True) == 210``.
    """
    if nth:
        k = _parse_k(n if isinstance(n, int) else int(_parse_n(n)))
        bound = _nth_prime_upper(k)
        ps = _primes_upto_cached(bound)
        if len(ps) < k:
            # Bound was shy; stream until we have k primes.
            more = list(primerange(ps[-1] + 1 if ps else 2, bound * 2 + 32))
            ps = list(ps) + more
            while len(ps) < k:
                lo = ps[-1] + 1
                ps.extend(primerange(lo, lo + 1_000_000))
        return _prod_tree(list(ps[:k]))
    n_int = _parse_n(n)
    if n_int < 2:
        return 1
    return _prod_tree(list(primerange(2, n_int + 1)))


__all__ = [
    "TOTIENT_RANGE_MAX",
    "bigomega",
    "carmichael_lambda",
    "crt",
    "divisor_count",
    "divisor_sum",
    "divisors",
    "egcd",
    "euler_phi",
    "gcd",
    "is_carmichael",
    "is_semiprime",
    "is_squarefree",
    "jacobi",
    "modinv",
    "omega",
    "primorial",
    "radical",
    "totient",
    "totient_range",
]
