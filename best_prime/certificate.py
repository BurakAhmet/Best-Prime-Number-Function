"""Primality certificates: Pratt, BLS, and Atkin–GKM (ECPP).

``primality_certificate(n, kind=None)`` follows the same ladder as
``is_prime`` and emits the theorem that settled. ``is_prime`` stays
boolean-only.

Verifier is arithmetic only — no discriminant search, no factoring.
"""

from __future__ import annotations

import math
from typing import Any

from .is_prime import _ECPP_MAX_H, _SMALL_LIMIT, _parse_n, _is_prime_small

_PRIME_KINDS = frozenset({"axiom", "pratt", "bls", "ecpp"})


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


def _pratt_unfactored(p: int) -> dict[str, Any]:
    return {"n": p, "kind": "pratt", "error": "n-1_unfactored"}


def _pratt_allowed(p: int) -> bool:
    """Complete n−1 factoring is safe only on complete-engine sizes."""
    if p < (1 << 64):
        return True
    from .factor_lehman import cubic_complete_ready

    return cubic_complete_ready(p)


def _pratt(
    p: int, memo: dict[int, dict[str, Any]], *, parallel: bool
) -> dict[str, Any] | None:
    if p in memo:
        return memo[p]
    if p == 2:
        cert: dict[str, Any] = {"n": 2, "prime": True, "kind": "axiom"}
        memo[p] = cert
        return cert
    if not _pratt_allowed(p):
        return _pratt_unfactored(p)
    qs = _factor_p_minus_1(p)
    g = _witness(p, qs)
    if g is None:
        return None
    factors = [_child_cert(q, parallel=parallel, memo=memo) for q in qs]
    if any(
        c.get("prime") is not True
        or c.get("kind") not in _PRIME_KINDS
        or "error" in c
        for c in factors
    ):
        return _pratt_unfactored(p)
    cert = {"n": p, "prime": True, "kind": "pratt", "witness": g, "factors": factors}
    memo[p] = cert
    return cert


def _composite_record(n: int, *, parallel: bool) -> dict[str, Any]:
    r = math.isqrt(n)
    if r * r == n and n > 1:
        return {"n": n, "prime": False, "factor": r}
    if n < (1 << 64) or _pratt_allowed(n):
        from .prime_factors import prime_factors

        facs = prime_factors(n, parallel=parallel)
        factor = facs[0] if facs and facs[0] != n else None
        if factor is not None and 1 < factor < n:
            return {"n": n, "prime": False, "factor": factor}
        return {"n": n, "prime": False, "reason": "composite"}
    # Do not block a composite verdict on a complete factorization.
    from .is_prime import _one_factor

    f = _one_factor(n, parallel=parallel)
    if f is not None and 1 < f < n:
        return {"n": n, "prime": False, "factor": f}
    from .primality_nm1 import _try_split_cofactor

    f = _try_split_cofactor(n, parallel=parallel)
    if f is not None and 1 < f < n:
        return {"n": n, "prime": False, "factor": f}
    return {"n": n, "prime": False, "reason": "composite"}


def _as_map(raw: Any) -> dict[int, int] | None:
    if not isinstance(raw, dict):
        return None
    out: dict[int, int] = {}
    for k, e in raw.items():
        q, ee = int(k), int(e)
        if q < 2 or ee < 1:
            return None
        out[q] = ee
    return out


def _prod_map(fac: dict[int, int]) -> int:
    prod = 1
    for q, e in fac.items():
        prod *= pow(q, e)
    return prod


def _child_cert(
    q: int, *, parallel: bool, memo: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    if q in memo:
        return memo[q]
    cert = _certificate(q, kind=None, parallel=parallel, memo=memo)
    if cert.get("prime") is True and "error" not in cert:
        memo[q] = cert
    return cert


def _build_bls_cert(
    n: int, data: dict, *, parallel: bool, memo: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    side = data["side"]
    cert: dict[str, Any] = {
        "n": n,
        "prime": True,
        "kind": "bls",
        "side": side,
        "inequality": data["inequality"],
        "witnesses": list(data.get("witnesses") or []),
    }
    primes: list[int] = []
    if side in ("nm1", "combined"):
        cert["F"] = dict(data["F"])
        primes.extend(sorted(int(q) for q in data["F"]))
    if side in ("np1", "combined"):
        cert["G"] = dict(data["G"])
        primes.extend(sorted(int(q) for q in data["G"]))
    if side == "combined":
        cert["F2G_over_2"] = int(data["F2G_over_2"])
        cert["FG2_over_2"] = int(data["FG2_over_2"])
    if side != "nm1" and data.get("lucas") is not None:
        cert["lucas"] = dict(data["lucas"])
    seen: set[int] = set()
    factors: list[dict[str, Any]] = []
    for q in primes:
        if q in seen:
            continue
        seen.add(q)
        factors.append(_child_cert(q, parallel=parallel, memo=memo))
    cert["factors"] = factors
    return cert


def _ecpp_rec_complete(data: dict[str, Any]) -> bool:
    return all(k in data for k in ("D", "t", "v", "a", "b", "m", "c", "q", "x", "y"))


def _rec_to_prime_cert(
    n: int, data: dict[str, Any], *, parallel: bool, memo: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    """Turn a search witness into a certificate without re-walking D."""
    if data.get("side") in ("nm1", "np1", "combined") and _bls_settled(data):
        return _build_bls_cert(n, data, parallel=parallel, memo=memo)
    if _ecpp_rec_complete(data):
        return _build_ecpp_cert(n, data, parallel=parallel, memo=memo)
    return _child_cert(n, parallel=parallel, memo=memo)


def _build_ecpp_cert(
    n: int, data: dict[str, Any], *, parallel: bool, memo: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    q = int(data["q"])
    q_src = data.get("q_rec")
    if isinstance(q_src, dict):
        q_cert = _rec_to_prime_cert(q, q_src, parallel=parallel, memo=memo)
    else:
        q_cert = _child_cert(q, parallel=parallel, memo=memo)
    cert: dict[str, Any] = {
        "n": n,
        "prime": True,
        "kind": "ecpp",
        "D": int(data["D"]),
        "t": int(data["t"]),
        "v": int(data["v"]),
        "curve": {"a": int(data["a"]), "b": int(data["b"])},
        "m": int(data["m"]),
        "c": int(data["c"]),
        "point": {"x": int(data["x"]), "y": int(data["y"])},
        "q_cert": q_cert,
    }
    if "j" in data:
        cert["j"] = int(data["j"])
    return cert


def _failure(n: int, kind: str, error: str) -> dict[str, Any]:
    return {"n": n, "prime": True, "kind": kind, "error": error}


def _bls_settled(data: dict[str, Any] | None) -> bool:
    if not data or data.get("side") not in ("nm1", "np1", "combined"):
        return False
    if data["side"] == "nm1":
        return "F" in data
    if data["side"] == "np1":
        return "G" in data
    return "F" in data and "G" in data


def _certificate(
    n: int, *, kind: str | None, parallel: bool, memo: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    if n < 2:
        return {"n": n, "prime": False, "reason": "non-prime-by-definition"}

    if kind == "pratt":
        if n < _SMALL_LIMIT and not _is_prime_small(n):
            return _composite_record(n, parallel=parallel)
        if not _pratt_allowed(n):
            return _pratt_unfactored(n)
        cert = _pratt(n, memo, parallel=parallel)
        if cert is None:
            return _composite_record(n, parallel=parallel)
        return cert

    if kind == "bls":
        from .primality_nm1 import _bls_proof

        decided, data = _bls_proof(n, parallel=parallel)
        if decided is True and data is not None and _bls_settled(data):
            return _build_bls_cert(n, data, parallel=parallel, memo=memo)
        if decided is False:
            return _composite_record(n, parallel=parallel)
        return _failure(n, "bls", "unsettled")

    if kind == "ecpp":
        if n.bit_length() >= 256:
            from .primality_fastecpp import fastecpp_search, is_prime_fastecpp_max_ms

            decided, data = fastecpp_search(
                n,
                parallel=parallel,
                skip_small_h=True,
                max_ms=is_prime_fastecpp_max_ms(n.bit_length()),
            )
        else:
            from .primality_ecpp import _ecpp_search

            decided, data = _ecpp_search(n, parallel=parallel, max_h=_ECPP_MAX_H)
        if decided is True and data and _ecpp_rec_complete(data):
            return _build_ecpp_cert(n, data, parallel=parallel, memo=memo)
        if decided is False:
            return _composite_record(n, parallel=parallel)
        return _failure(n, "ecpp", "unsettled")

    # kind=None: same dispatch as is_prime / _is_prime_one.
    if n < _SMALL_LIMIT:
        if _is_prime_small(n):
            cert = _pratt(n, memo, parallel=parallel)
            return cert if cert is not None else _composite_record(n, parallel=parallel)
        return _composite_record(n, parallel=parallel)

    from .factor_lehman import cubic_complete_ready
    from .primality_nm1 import _bls_proof

    if cubic_complete_ready(n):
        decided, data = _bls_proof(n, parallel=parallel)
        if decided is True and data is not None and _bls_settled(data):
            return _build_bls_cert(n, data, parallel=parallel, memo=memo)
        if decided is False:
            return _composite_record(n, parallel=parallel)
        from .factor_lehman import lehman_factor

        f = lehman_factor(n, parallel=parallel)
        if f is not None and 1 < f < n:
            return {"n": n, "prime": False, "factor": f}
        cert = _pratt(n, memo, parallel=parallel)
        return cert if cert is not None else _pratt_unfactored(n)

    if n < (1 << 64):
        from .is_prime import is_prime

        if is_prime(n, parallel=parallel):
            cert = _pratt(n, memo, parallel=parallel)
            return cert if cert is not None else _composite_record(n, parallel=parallel)
        return _composite_record(n, parallel=parallel)

    # Huge n: same dispatch as is_prime. FastECPP at ≥256 bits; BLS then
    # transcribed ECPP below that. No complete n−1 factoring, no AKS.
    bits = n.bit_length()
    if bits >= 256:
        from .huge_arith import powmod as _powmod
        from .primality_ecpp import fermat_bases_for_bits
        from .primality_fastecpp import (
            FASTECPP_MAX_BITS,
            FASTECPP_MIN_BITS,
            fastecpp_search,
            is_prime_fastecpp_max_ms,
        )
        from .progress import deadline_hit, emit

        emit("fermat", digits=len(str(n)), bits=bits)
        for a in fermat_bases_for_bits(bits):
            if a % n == 0:
                return {"n": n, "prime": True, "kind": "axiom"} if n == a else _composite_record(
                    n, parallel=parallel
                )
            if _powmod(a, n - 1, n) != 1:
                return _composite_record(n, parallel=parallel)
        if deadline_hit():
            return {"n": n, "kind": "unsupported"}
        if FASTECPP_MIN_BITS <= bits <= FASTECPP_MAX_BITS:
            decided, data = fastecpp_search(
                n,
                parallel=parallel,
                skip_small_h=True,
                max_ms=is_prime_fastecpp_max_ms(bits),
            )
            if decided is True and data and _ecpp_rec_complete(data):
                return _build_ecpp_cert(n, data, parallel=parallel, memo=memo)
            if decided is False:
                return _composite_record(n, parallel=parallel)
        return {"n": n, "kind": "unsupported"}

    decided, data = _bls_proof(n, parallel=parallel)
    if decided is True and data is not None and _bls_settled(data):
        return _build_bls_cert(n, data, parallel=parallel, memo=memo)
    if decided is False:
        return _composite_record(n, parallel=parallel)

    from .primality_nm1 import _try_split_cofactor

    f = _try_split_cofactor(n, parallel=parallel)
    if f is not None and 1 < f < n:
        return {"n": n, "prime": False, "factor": f}

    from .primality_ecpp import _ecpp_search

    decided, data = _ecpp_search(n, parallel=parallel, max_h=_ECPP_MAX_H)
    if decided is True and data and _ecpp_rec_complete(data):
        return _build_ecpp_cert(n, data, parallel=parallel, memo=memo)
    if decided is False:
        return _composite_record(n, parallel=parallel)
    return {"n": n, "kind": "unsupported"}


def primality_certificate(
    n: int | str, kind: str | None = None, *, parallel: bool = True
) -> dict[str, Any]:
    """Return a checkable primality (or compositeness) certificate for ``n``.

    ``kind=None`` walks the same ladder as ``is_prime`` and emits
    ``bls`` / ``ecpp`` / ``pratt`` / ``axiom`` (or a composite factor).
    At ``bits ≥ 256`` that is Fermat then FastECPP (nested ``q_cert``
    from the proof, not a second search). ``kind='pratt'`` on hostile
    huge ``n`` returns
    ``{"prime": True, "kind": "pratt", "error": "n-1_unfactored"}``
    instead of hanging in ``prime_factors(n-1)``.
    """
    n_int = _parse_n(n)
    if kind is not None:
        kind = str(kind).lower()
        if kind not in {"pratt", "bls", "ecpp"}:
            return {"n": n_int, "kind": "unsupported"}
    return _certificate(n_int, kind=kind, parallel=parallel, memo={})


def _prime_proof_ok(child: dict[str, Any]) -> bool:
    """True iff ``child`` is a prime proof, not a compositeness record."""
    if child.get("prime") is not True:
        return False
    if child.get("kind") not in _PRIME_KINDS:
        return False
    if "error" in child:
        return False
    return verify_certificate(child)


def _verify_condition_I(n: int, fmap: dict[int, int], witnesses: Any) -> bool:
    if not isinstance(witnesses, list):
        return False
    need = set(fmap)
    got: set[int] = set()
    for w in witnesses:
        if not isinstance(w, dict):
            return False
        q = int(w.get("q", 0))
        a = int(w.get("a", 0))
        if q not in need or a < 2:
            return False
        if not (1 < a < n) or math.gcd(a, n) != 1:
            return False
        if (n - 1) % q != 0:
            return False
        if pow(a, n - 1, n) != 1:
            return False
        if math.gcd(pow(a, (n - 1) // q, n) - 1, n) != 1:
            return False
        got.add(q)
    return got == need


def _verify_condition_II(n: int, gmap: dict[int, int], luc: Any) -> bool:
    if not isinstance(luc, dict):
        return False
    from .ntheory import jacobi
    from .primality_nm1 import _lucas_uv

    D = int(luc["D"])
    P = int(luc.get("P", 1))
    Q = int(luc["Q"])
    if P * P - 4 * Q != D:
        return False
    try:
        if jacobi(D, n) != -1:
            return False
    except ValueError:
        return False
    uv = _lucas_uv(n + 1, P, Q, n)
    if isinstance(uv, int) or uv[0] % n != 0:
        return False
    raw_qs = luc.get("qs")
    if raw_qs is None:
        qs = list(gmap)
    elif not isinstance(raw_qs, list):
        return False
    else:
        qs = [int(q) for q in raw_qs]
    if set(qs) != set(gmap):
        return False
    for q in qs:
        if q <= 1 or (n + 1) % q != 0:
            return False
        uvq = _lucas_uv((n + 1) // q, P, Q, n)
        if isinstance(uvq, int):
            return False
        if math.gcd(uvq[0], n) != 1:
            return False
    return True


def _verify_bls(cert: dict[str, Any], n: int) -> bool:
    from .primality_nm1 import _bls_cubic_ok

    if cert.get("error"):
        return False
    side = cert.get("side")
    if side not in {"nm1", "np1", "combined"}:
        return False
    fmap = _as_map(cert["F"]) if "F" in cert else {}
    gmap = _as_map(cert["G"]) if "G" in cert else {}
    if fmap is None or gmap is None:
        return False
    if side == "nm1" and ("G" in cert or not fmap):
        return False
    if side == "np1" and ("F" in cert or not gmap):
        return False
    if side == "combined" and (not fmap or not gmap):
        return False
    F = _prod_map(fmap) if fmap else 1
    G = _prod_map(gmap) if gmap else 1
    if side in {"nm1", "combined"}:
        if F <= 1 or (n - 1) % F != 0:
            return False
    if side in {"np1", "combined"}:
        if G <= 1 or (n + 1) % G != 0:
            return False
    ineq = cert.get("inequality")
    sqrt_n = math.isqrt(n)
    if side == "combined":
        if ineq != "combined_thm1":
            return False
        if math.gcd(F, G) != 2:
            return False
        f2g = int(cert.get("F2G_over_2", -1))
        fg2 = int(cert.get("FG2_over_2", -1))
        if f2g != F * F * G // 2 or fg2 != F * G * G // 2:
            return False
        if not (n < max(f2g, fg2)):
            return False
    elif side == "nm1":
        if ineq != "F>sqrt":
            return False
        if F <= sqrt_n and not (n < 2 * F * F * F and _bls_cubic_ok(n, F)):
            return False
    else:
        if ineq != "G>sqrt" or G <= sqrt_n:
            return False
    if side in {"nm1", "combined"}:
        if not _verify_condition_I(n, fmap, cert.get("witnesses")):
            return False
    if side in {"np1", "combined"}:
        if not _verify_condition_II(n, gmap, cert.get("lucas")):
            return False
    factors = cert.get("factors")
    if not isinstance(factors, list):
        return False
    need = set(fmap) | set(gmap)
    got = set()
    for child in factors:
        if not isinstance(child, dict):
            return False
        q = int(child["n"])
        if q in got or q not in need:
            return False
        got.add(q)
        if not _prime_proof_ok(child):
            return False
    return got == need


def _verify_ecpp(cert: dict[str, Any], n: int) -> bool:
    from .factor_ecm import _mul
    from .primality_ecpp import gk_min_q

    if cert.get("error"):
        return False
    D = int(cert["D"])
    t = int(cert["t"])
    v = int(cert["v"])
    if t <= 0 or t * t + abs(D) * v * v != 4 * n:
        return False
    curve = cert.get("curve")
    point = cert.get("point")
    q_cert = cert.get("q_cert")
    if not isinstance(curve, dict) or not isinstance(point, dict):
        return False
    if not isinstance(q_cert, dict):
        return False
    a = int(curve["a"])
    b = int(curve["b"])
    x = int(point["x"])
    y = int(point["y"])
    m = int(cert["m"])
    c = int(cert["c"])
    q = int(q_cert["n"])
    if m not in {n + 1 - t, n + 1 + t}:
        return False
    if c < 2 or q < 2 or m != c * q:
        return False
    if q < gk_min_q(n):
        return False
    if (y * y - (pow(x, 3, n) + a * x + b)) % n != 0:
        return False
    disc = (4 * pow(a, 3, n) + 27 * ((b * b) % n)) % n
    if math.gcd(disc, n) != 1:
        return False
    pnt = (x % n, y % n)
    cp, g = _mul(c, pnt, a, n)
    if g > 1 or cp is None:
        return False
    mp, g = _mul(m, pnt, a, n)
    if g > 1 or mp is not None:
        return False
    return _prime_proof_ok(q_cert)


def verify_certificate(cert: dict[str, Any]) -> bool:
    """True iff ``cert`` is a valid Pratt / BLS / ECPP / factor witness."""
    try:
        n = int(cert["n"])
    except (KeyError, TypeError, ValueError):
        return False
    if n < 2:
        return cert.get("prime") is False
    if cert.get("error"):
        return False
    if cert.get("prime") is False:
        if "factor" in cert:
            d = int(cert["factor"])
            return 1 < d < n and n % d == 0
        return cert.get("reason") in {"composite", "non-prime-by-definition"}
    kind = cert.get("kind")
    if kind == "unsupported":
        return False
    if kind == "axiom":
        return n == 2
    if kind == "bls":
        try:
            return _verify_bls(cert, n)
        except (KeyError, TypeError, ValueError):
            return False
    if kind == "ecpp":
        try:
            return _verify_ecpp(cert, n)
        except (KeyError, TypeError, ValueError):
            return False
    if kind != "pratt":
        return False
    g = int(cert.get("witness", 0))
    factors = cert.get("factors")
    if not isinstance(factors, list) or g < 2:
        return False
    qs = [int(c["n"]) for c in factors]
    if not qs:
        return False
    tmp = n - 1
    for q in qs:
        if tmp % q:
            return False
    if pow(g, n - 1, n) != 1:
        return False
    if any(pow(g, (n - 1) // q, n) == 1 for q in qs):
        return False
    return all(_prime_proof_ok(c) for c in factors)
