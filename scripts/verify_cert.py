#!/usr/bin/env python3
"""Stdlib-only verifier for a ``primality-certificate --json`` file.

Does not import ``best_prime``. Arithmetic only: ``pow``, ``gcd``,
integer Lucas / Weierstrass mul. No discriminant search, no factoring.

    python3 scripts/verify_cert.py cert.json
    primality-certificate --json 17 | python3 scripts/verify_cert.py -
"""

from __future__ import annotations

import json
import math
import sys
from typing import Any

_PRIME_KINDS = frozenset({"axiom", "pratt", "bls", "ecpp"})


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


def gk_min_q(n: int) -> int:
    r = math.isqrt(math.isqrt(n))
    return (r + 2) ** 2


def jacobi(a: int, n: int) -> int:
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


def _add(p1, p2, a: int, n: int):
    if p1 is None:
        return p2, 1
    if p2 is None:
        return p1, 1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2:
        if (y1 + y2) % n == 0:
            return None, 1
        num = (3 * x1 * x1 + a) % n
        den = (2 * y1) % n
    else:
        num = (y2 - y1) % n
        den = (x2 - x1) % n
    g = math.gcd(den, n)
    if g > 1:
        return None, g
    if den == 0:
        return None, 1
    inv = pow(den, -1, n)
    m = (num * inv) % n
    x3 = (m * m - x1 - x2) % n
    y3 = (m * (x1 - x3) - y1) % n
    return (x3, y3), 1


def _mul(k: int, p, a: int, n: int):
    acc = None
    base = p
    kk = k
    while kk:
        if kk & 1:
            acc, g = _add(acc, base, a, n)
            if g > 1:
                return None, g
        base, g = _add(base, base, a, n)
        if g > 1:
            return None, g
        kk >>= 1
    return acc, 1


def _lucas_uv(k: int, P: int, Q: int, n: int):
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


def _bls_cubic_ok(n: int, F: int) -> bool:
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


def _prime_proof_ok(child: dict[str, Any]) -> bool:
    if child.get("prime") is not True:
        return False
    if child.get("kind") not in _PRIME_KINDS:
        return False
    if "error" in child:
        return False
    return verify(child)


def verify(cert: dict[str, Any]) -> bool:
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


def _load(path: str) -> dict[str, Any]:
    if path == "-":
        raw = json.load(sys.stdin)
    else:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    if not isinstance(raw, dict):
        raise SystemExit("certificate JSON must be an object")
    return raw


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(__doc__.strip(), file=sys.stderr if args and args[0] in {"-h", "--help"} else sys.stdout)
        return 0 if args and args[0] in {"-h", "--help"} else 2
    cert = _load(args[0])
    ok = verify(cert)
    n = cert.get("n", "?")
    kind = cert.get("kind") or cert.get("reason") or "?"
    print(f"n={n} kind={kind} verified={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
