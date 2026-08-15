# FAQ

## Why not Miller–Rabin?

This library’s contract is **exact** `is_prime(n)` for every natural number.
Stochastic Miller–Rabin (and “probably prime” APIs) can be wrong, are not a
uniform function of `n` alone, and hide failures as rarity. Fixed-base
“deterministic MR” is only proven on **finite** ranges — it is not a drop-in
for “all $n$”.

A concrete liar below the near-$2^{63}$ prime, using SymPy’s `mr` helper
(not `sympy.isprime`):

```python
from sympy.ntheory.primetest import mr, isprime
from best_prime import is_prime

n = 3943673813084040361            # 869461 × 1738921 × 2608381
mr(n, [2, 3, 5])                   # True   ← three ordinary bases: “prime”
isprime(n)                         # False  ← SymPy’s full predicate
is_prime(n)                        # False  ← exact trial
```

An optional `mode="probabilistic"` flag will **not** be accepted. See
[restrictions](restrictions.md) and issue
[#2](https://github.com/BurakAhmet/Best-Prime-Number-Function/issues/2).

## How far does `prime_count` go?

**Hard ceiling:** `PRIME_COUNT_MAX_N = 2**64 - 1`. Larger `n` raises
`ValueError`. This is not an approximation — Meissel–Lehmer here stores
primes as uint32 through $2^{32}$.

## When is the next/prev interval sieve used?

Only while $\sqrt{\text{bound}} \le$ `NEXT_PRIME_SIEVE_ISQRT_MAX`
($2\cdot 10^6$). Larger $k$ or $n$ walk a 30030-wheel and call `is_prime`.
Stream with `next_primes` / `prev_primes`.

## Did you replace “search up to $\sqrt{n}$”?

For mid-size $n < 2^{64}$ ($\lfloor\sqrt{n}\rfloor < 10^{7}$), `is_prime` is still exact trial through $\lfloor\sqrt{n}\rfloor$. Harder 64-bit $n$ and $n\ge 2^{64}$ in budget try an **n−1 Pocklington** proof first ([guide](nm1-proof.md)); complete cubic search is the fallback when $n-1$ is hostile.

`lehman_factor` is a **different schedule** of the trial interval: a rising-product wheel through $n^{1/3}$, then Lehman windows instead of walking $(n^{1/3},\sqrt{n}]$. Details: [cubic search](cubic-search.md).

## Is AKS practical?

No. AKS is **not** a product-path fallback. At $\ge 512$ bits a miss is
`UnsettledPrimalityError` (CLI `RESULT: unsettled`, exit 3). Hard 64-bit
primes stay on OpenMP / BLS. Huge primes use FastECPP or stay unsettled.

## What does 1.13.0 actually prove?

Exact `is_prime` on the documented bands: BLS below 256 bits, FastECPP
from 256 through 40 000 bits. Certificates match that ladder and
`verify_certificate` is arithmetic only. Measured sizes (one machine,
see [`benchmarks/timing_table.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/benchmarks/timing_table.py)):
about 100 digits in seconds, 150 digits in tens of seconds, 200 digits
around a minute. A *general* 10k-digit prime in 10 s is the north-star
and is **not** claimed.

## Is the GitHub Pages lab the library?

No. The Pages lab is an in-browser **exhibit** (JS worker, no OpenMP
core). It mirrors the same theorems but is not `best_prime`. A miss
in-tab can be inconclusive while Python `is_prime` still settles. The
library lives in this guide and on PyPI.

## How do I cap a long proof or factorization?

`is-prime --max-ms MS` (or `BEST_PRIME_MAX_MS`) stops the search as
unsettled — never as a false composite. `prime_factors(n, max_ms=MS)`
raises `UnsettledFactorError` with the isolated primes and leftover.
The `prime-factors` CLI default-caps $n$ wider than 512 bits at 30 s.

## Why is a smaller prime sometimes slower?

FastECPP time follows the CM tree, not the digit count. A 122-digit prime
with $D=-1316$ ($h=24$) can lose to a 132-digit prime with $D=-467$ ($h=7$).
`lab(n)["cm_tree"]` and the CLI `CM_TREE:` line print that path.

## How do I check a certificate without this library?

```bash
primality-certificate --json n > cert.json
python3 scripts/verify_cert.py cert.json
```

The script uses only the standard library (`pow`, `gcd`, integer Lucas and
curve arithmetic). It does not import `best_prime` and does not search for
a discriminant.
