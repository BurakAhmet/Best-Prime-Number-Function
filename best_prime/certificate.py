"""Pratt primality certificates (and composite factor witnesses).

A Pratt certificate for prime ``p`` is a witness ``g`` such that
``g^{p-1} ≡ 1 (mod p)`` and ``g^{(p-1)/q} ≢ 1 (mod p)`` for every prime
factor ``q`` of ``p-1``, plus recursive certificates for those ``q``.
Composites return a proper factor. Fully deterministic; no Miller–Rabin.
"""

from __future__ import annotations

from typing import Any

from .is_prime import _parse_n, is_prime


def _factor_p_minus_1(p: int) -> list[int]:
    # Local import: prime_factors imports is_prime, not this module.
    from .prime_factors import prime_factors

    return sorted(set(prime_factors(p - 1)))


def _witness(p: int, qs: list[int]) -> int | None:
    """Smallest g ≥ 2 that proves p prime given the prime factors of p-1."""
    for g in range(2, min(p, 10_000)):
        if pow(g, p - 1, p) != 1:
            continue
        if all(pow(g, (p - 1) // q, p) != 1 for q in qs):
            return g
    return None


def _pratt(p: int, memo: dict[int, dict[str, Any]]) -> dict[str, Any]:
    if p in memo:
        return memo[p]
    if p == 2:
        cert: dict[str, Any] = {"n": 2, "prime": True, "kind": "axiom"}
        memo[p] = cert
        return cert
    qs = _factor_p_minus_1(p)
    g = _witness(p, qs)
    if g is None:
        raise RuntimeError(f"failed to build Pratt witness for {p}")
    factors = [_pratt(q, memo) for q in qs]
    cert = {"n": p, "prime": True, "kind": "pratt", "witness": g, "factors": factors}
    memo[p] = cert
    return cert


def primality_certificate(n: int | str, *, parallel: bool = True) -> dict[str, Any]:
    """Return a checkable primality (or compositeness) certificate for ``n``.

    Prime ``n``: Pratt tree (``kind='pratt'`` or ``'axiom'`` for 2).
    Composite ``n``: ``{"n", "prime": False, "factor": d}`` with ``1 < d < n``.
    ``n < 2``: ``{"n", "prime": False, "reason": "non-prime-by-definition"}``.
    """
    n_int = _parse_n(n)
    if n_int < 2:
        return {"n": n_int, "prime": False, "reason": "non-prime-by-definition"}
    # Between PR2 and PR3: refuse huge-n Pratt rather than hang in AKS / n−1.
    if n_int >= (1 << 64):
        from .factor_lehman import cubic_complete_ready

        if not cubic_complete_ready(n_int):
            return {"n": n_int, "kind": "unsupported"}
    if not is_prime(n_int, parallel=parallel):
        from .prime_factors import prime_factors

        facs = prime_factors(n_int, parallel=parallel)
        factor = facs[0] if facs and facs[0] != n_int else None
        if factor is None or factor == n_int:
            # Should not happen for a composite that factorint can split;
            # still return a verifiable "not prime" record.
            return {"n": n_int, "prime": False, "reason": "composite"}
        return {"n": n_int, "prime": False, "factor": factor}
    return _pratt(n_int, {})


def verify_certificate(cert: dict[str, Any]) -> bool:
    """True iff ``cert`` is a valid Pratt / factor witness for ``cert['n']``."""
    try:
        n = int(cert["n"])
    except (KeyError, TypeError, ValueError):
        return False
    if n < 2:
        return cert.get("prime") is False
    if cert.get("prime") is False:
        if "factor" in cert:
            d = int(cert["factor"])
            return 1 < d < n and n % d == 0
        return cert.get("reason") in {"composite", "non-prime-by-definition"}
    kind = cert.get("kind")
    if kind == "axiom":
        return n == 2
    if kind != "pratt":
        return False
    g = int(cert.get("witness", 0))
    factors = cert.get("factors")
    if not isinstance(factors, list) or g < 2:
        return False
    qs = [int(c["n"]) for c in factors]
    if not qs:
        return False
    prod = 1
    tmp = n - 1
    # Every q must divide n-1; the product of the q's (with multiplicity
    # ignored) need not reconstruct n-1 — Pratt only needs the distinct primes.
    for q in qs:
        if tmp % q:
            return False
        prod *= q
    if pow(g, n - 1, n) != 1:
        return False
    if any(pow(g, (n - 1) // q, n) == 1 for q in qs):
        return False
    return all(verify_certificate(c) for c in factors)
