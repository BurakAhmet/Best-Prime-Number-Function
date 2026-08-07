#!/usr/bin/env python3
"""Search for large composites where SymPy disagrees with exact trial.

Builds n ourselves (Chernick Carmichael, primes ≡ 1 mod M paired into
semiprimes / triples). No downloaded tables.

Default target: n < 9223372036854775783, then n > that bound.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from best_prime import is_prime  # noqa: E402
from sympy.ntheory.primetest import isprime as sympy_isprime  # noqa: E402
from sympy.ntheory.primetest import mr as sympy_mr  # noqa: E402

NEAR = 9_223_372_036_854_775_783
BASE_CHAIN = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]


def mr_depth(n: int) -> int:
    used: list[int] = []
    for b in BASE_CHAIN:
        if b >= n:
            break
        trial = used + [b]
        if sympy_mr(n, trial):
            used = trial
        else:
            break
    return len(used)


def report(kind: str, n: int, factors: tuple[int, ...], k: int) -> None:
    sy = sympy_isprime(n)
    print(
        f"{kind} n={n} bits={n.bit_length()} factors={'*'.join(map(str, factors))} "
        f"factor={factors[0]} mr_depth={k} sympy.isprime={sy} "
        f"below_near={n < NEAR}",
        flush=True,
    )


def primes_1_mod(mod: int, lo: int, hi: int, cap: int) -> list[int]:
    """Primes p with lo <= p < hi, p ≡ 1 (mod mod)."""
    out: list[int] = []
    p = lo - (lo % mod) + 1
    if p < lo:
        p += mod
    if p % 2 == 0:
        p += mod  # mod even ⇒ still odd
    while p < hi and len(out) < cap:
        if is_prime(p):
            out.append(p)
        p += mod
    return out


def scan_pairs(primes: list[int], *, max_n: int | None, min_n: int, min_k: int) -> int:
    hits = 0
    for i, p in enumerate(primes):
        for q in primes[i + 1 :]:
            n = p * q
            if n < min_n:
                continue
            if max_n is not None and n >= max_n:
                continue
            k = mr_depth(n)
            if k < min_k:
                continue
            report("SEMI", n, (p, q), k)
            hits += 1
    return hits


def scan_triples(primes: list[int], *, max_n: int | None, min_n: int, min_k: int) -> int:
    hits = 0
    m = len(primes)
    for i in range(m):
        for j in range(i + 1, m):
            pq = primes[i] * primes[j]
            for r in primes[j + 1 :]:
                n = pq * r
                if n < min_n:
                    continue
                if max_n is not None and n >= max_n:
                    continue
                k = mr_depth(n)
                if k < min_k:
                    continue
                report("TRIPLE", n, (primes[i], primes[j], r), k)
                hits += 1
    return hits


def chernick(m_lo: int, m_hi: int, *, min_k: int) -> int:
    hits = 0
    for m in range(m_lo, m_hi + 1):
        a, b, c = 6 * m + 1, 12 * m + 1, 18 * m + 1
        if not (is_prime(a) and is_prime(b) and is_prime(c)):
            continue
        n = a * b * c
        k = mr_depth(n)
        if k < min_k and not sympy_isprime(n):
            continue
        report("CHERNICK", n, (a, b, c), k)
        hits += 1
    return hits


def korselt_filter(primes: list[int], *, max_n: int | None, min_n: int, min_k: int) -> int:
    hits = 0
    m = len(primes)
    for i in range(m):
        p = primes[i]
        for j in range(i + 1, m):
            q = primes[j]
            pq = p * q
            for r in primes[j + 1 :]:
                n = pq * r
                if n < min_n:
                    continue
                if max_n is not None and n >= max_n:
                    continue
                nm1 = n - 1
                if nm1 % (p - 1) or nm1 % (q - 1) or nm1 % (r - 1):
                    continue
                k = mr_depth(n)
                report("CARM", n, (p, q, r), k)
                hits += 1
                if k >= min_k:
                    pass
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("below", "above", "both"), default="both")
    args = ap.parse_args()
    t0 = time.perf_counter()

    if args.phase in ("below", "both"):
        print(f"=== phase below {NEAR} ===", flush=True)
        print("Chernick m=1..200000 (~2^63)", flush=True)
        chernick(1, 200_000, min_k=2)
        print("primes 1 mod 2310 near 2e6 (3-prime ~2^63)", flush=True)
        p2e6 = primes_1_mod(2310, 1_500_000, 3_500_000, 80)
        print(f"  got {len(p2e6)} primes", flush=True)
        scan_triples(p2e6, max_n=NEAR, min_n=10**15, min_k=2)
        korselt_filter(p2e6[:50], max_n=NEAR, min_n=10**15, min_k=0)
        print("primes 1 mod 30030 near 2.5e9 (semiprime ~2^63)", flush=True)
        p3e9 = primes_1_mod(30_030, 2_200_000_000, 3_100_000_000, 120)
        print(f"  got {len(p3e9)} primes", flush=True)
        scan_pairs(p3e9, max_n=NEAR, min_n=10**17, min_k=2)
        print("primes 1 mod 510510 near 2.5e9", flush=True)
        pbig = primes_1_mod(510_510, 2_000_000_000, 3_200_000_000, 80)
        print(f"  got {len(pbig)} primes", flush=True)
        scan_pairs(pbig, max_n=NEAR, min_n=10**17, min_k=1)

    if args.phase in ("above", "both"):
        print(f"=== phase above {NEAR} ===", flush=True)
        print("Chernick m=190000..280000 (n > near-2^63)", flush=True)
        chernick(190_000, 280_000, min_k=2)
        print("primes 1 mod 30030 near 5e9 (semiprime >2^64)", flush=True)
        p5e9 = primes_1_mod(30_030, 4_500_000_000, 6_500_000_000, 100)
        print(f"  got {len(p5e9)} primes", flush=True)
        scan_pairs(p5e9, max_n=None, min_n=NEAR, min_k=2)
        print("primes 1 mod 2310 near 8e6 (3-prime >2^64)", flush=True)
        p8e6 = primes_1_mod(2310, 6_000_000, 12_000_000, 70)
        print(f"  got {len(p8e6)} primes", flush=True)
        scan_triples(p8e6, max_n=None, min_n=NEAR, min_k=2)
        korselt_filter(p8e6[:40], max_n=None, min_n=NEAR, min_k=0)

    print(f"elapsed {time.perf_counter() - t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
