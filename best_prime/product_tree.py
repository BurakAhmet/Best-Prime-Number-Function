"""Product / remainder trees for FastECPP batch trial.

Given many curve orders ``m_i`` and one integer ``A`` (a primorial of
primes ≤ B), the remainder tree computes ``A mod m_i`` for every i, so
``gcd(m_i, A)`` is the B-smooth kernel of ``m_i``. Deterministic. No RNG.
"""

from __future__ import annotations

import math


def product_tree(vals: list[int]) -> list[list[int]]:
    """Levels of pairwise products. ``levels[0]`` is ``vals``; the last is the root."""
    if not vals:
        return []
    levels: list[list[int]] = [list(vals)]
    cur = vals
    while len(cur) > 1:
        nxt: list[int] = []
        for i in range(0, len(cur), 2):
            if i + 1 < len(cur):
                nxt.append(cur[i] * cur[i + 1])
            else:
                nxt.append(cur[i])
        levels.append(nxt)
        cur = nxt
    return levels


def remainder_tree(a: int, tree: list[list[int]]) -> list[int]:
    """``a mod tree[0][i]`` for every leaf, via the product tree."""
    if not tree:
        return []
    top = [a % tree[-1][0]]
    for level in range(len(tree) - 2, -1, -1):
        kids = tree[level]
        nxt: list[int] = []
        for i, parent in enumerate(top):
            left = 2 * i
            nxt.append(parent % kids[left])
            if left + 1 < len(kids):
                nxt.append(parent % kids[left + 1])
        top = nxt
    return top


def _primorial(bound: int) -> int:
    """Product of primes ≤ bound. Bound is modest (≤ 2e6)."""
    bound = int(bound)
    if bound < 2:
        return 1
    sieve = bytearray(b"\x01") * (bound + 1)
    sieve[0:2] = b"\x00\x00"
    r = math.isqrt(bound)
    for p in range(2, r + 1):
        if sieve[p]:
            sieve[p * p : bound + 1 : p] = b"\x00" * (((bound - p * p) // p) + 1)
    acc = 1
    for p in range(2, bound + 1):
        if sieve[p]:
            acc *= p
    return acc


_PRIMORIAL_CACHE: dict[int, int] = {}


def primorial(bound: int) -> int:
    bound = int(bound)
    hit = _PRIMORIAL_CACHE.get(bound)
    if hit is not None:
        return hit
    val = _primorial(bound)
    _PRIMORIAL_CACHE[bound] = val
    return val


def batch_smooth_kernel(ms: list[int], prime_bound: int) -> list[int]:
    """``gcd(m_i, primorial(prime_bound))`` for each ``m_i``.

    Empty ``ms`` returns ``[]``. A single ``m`` uses a direct gcd.
    """
    if not ms:
        return []
    a = primorial(prime_bound)
    if len(ms) == 1:
        return [math.gcd(ms[0], a)]
    tree = product_tree(ms)
    rems = remainder_tree(a, tree)
    return [math.gcd(m, r) for m, r in zip(ms, rems)]


def peel_kernel(m: int, kernel: int) -> tuple[int, int]:
    """Return ``(smooth_part, leftover)`` where ``smooth_part = gcd(m, kernel)^∞``."""
    if m <= 1 or kernel <= 1:
        return 1, m
    g = math.gcd(m, kernel)
    if g <= 1:
        return 1, m
    smooth = 1
    rem = m
    while g > 1:
        smooth *= g
        rem //= g
        g = math.gcd(rem, g)
    return smooth, rem
