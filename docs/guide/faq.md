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

## Is AKS practical?

Only as the last engine for huge $n$ with no small factor. Hard 64-bit
primes stay on OpenMP trial. Huge primes can take a very long time; that
is the cost of refusing probable-prime shortcuts.
