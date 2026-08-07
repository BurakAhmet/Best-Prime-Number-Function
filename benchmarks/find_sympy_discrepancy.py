#!/usr/bin/env python3
"""Search for n where SymPy's primality helpers disagree with exact trial.

Does not download lists. Builds composites as products of small primes found
by our own is_prime, then compares:

  * sympy.isprime(n)          — full SymPy predicate
  * sympy.ntheory.primetest.mr(n, bases) — SymPy's multi-base helper

Prints the first liars (SymPy says prime, we say composite) with a factor.
"""
from __future__ import annotations

import argparse
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from best_prime import is_prime  # noqa: E402
from sympy.ntheory.primetest import isprime as sympy_isprime  # noqa: E402
from sympy.ntheory.primetest import mr as sympy_mr  # noqa: E402

BASE_CHAIN = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]


def small_odd_primes(limit: int) -> list[int]:
    out = []
    for n in range(3, limit, 2):
        if is_prime(n):
            out.append(n)
    return out


def factor_hint(n: int, primes: list[int]) -> int | None:
    for p in primes:
        if p * p > n:
            break
        if n % p == 0:
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prime-limit", type=int, default=400)
    ap.add_argument("--max-n", type=int, default=10**12)
    ap.add_argument("--want", type=int, default=8, help="stop after this many mr-liars")
    args = ap.parse_args()

    primes = small_odd_primes(args.prime_limit)
    print(f"odd primes < {args.prime_limit}: {len(primes)}", flush=True)

    seen: set[int] = set()
    isprime_hits = 0
    mr_hits = 0

    def consider(n: int, built_from: tuple[int, ...]) -> None:
        nonlocal isprime_hits, mr_hits
        if n < 9 or n > args.max_n or n in seen:
            return
        seen.add(n)
        ours = is_prime(n)
        sy = sympy_isprime(n)
        if sy and not ours:
            fac = factor_hint(n, primes) or built_from[0]
            print(
                f"ISPRIME_LIAR n={n} factors={'*'.join(map(str, built_from))} "
                f"factor={fac} sympy.isprime=True is_prime=False",
                flush=True,
            )
            isprime_hits += 1
        if ours and not sy:
            print(
                f"OURS_SAYS_PRIME n={n} sympy.isprime=False is_prime=True "
                f"(investigate — should not happen)",
                flush=True,
            )
        if ours:
            return
        k = 0
        used: list[int] = []
        for b in BASE_CHAIN:
            if b >= n:
                break
            trial = used + [b]
            if sympy_mr(n, trial):
                used = trial
                k = len(used)
            else:
                break
        if k == 0:
            return
        fac = factor_hint(n, primes) or built_from[0]
        print(
            f"MR_LIAR k={k} bases={used} n={n} factors={'*'.join(map(str, built_from))} "
            f"factor={fac} sympy.mr=True is_prime=False sympy.isprime={sy}",
            flush=True,
        )
        mr_hits += 1

    # Exhaustive tiny n (sanity: sympy.isprime should match trial).
    for n in range(0, 20_000):
        ours = is_prime(n)
        sy = sympy_isprime(n)
        if ours != sy:
            print(f"TINY_MISMATCH n={n} is_prime={ours} sympy.isprime={sy}", flush=True)
            isprime_hits += 1

    # Semiprimes and 3-prime products from our prime table.
    for p, q in combinations(primes, 2):
        consider(p * q, (p, q))
        if mr_hits >= args.want and isprime_hits == 0:
            # keep going a bit for 3-prime / isprime, but bound work
            pass
    for p, q, r in combinations(primes, 3):
        n = p * q * r
        if n > args.max_n:
            continue
        consider(n, (p, q, r))
        if mr_hits >= args.want * 3:
            break

    print(
        f"done seen={len(seen)} sympy.isprime_liars={isprime_hits} sympy.mr_liars>={mr_hits}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
