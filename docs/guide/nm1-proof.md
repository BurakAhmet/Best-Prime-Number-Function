# n−1 Pocklington proof

A deterministic primality proof that is **not** a search up to $\sqrt{n}$ or $n^{1/3}$. When $n-1$ factors, a few modular exponentiations settle the predicate — often **orders of magnitude** faster than cubic search.

!!! tip "Hard path only"
    Mid-size 64-bit $n$ ($\lfloor\sqrt{n}\rfloor < 10^{7}$) stay on wheel trial. The n−1 prover runs only where complete cubic search would: hard 64-bit $n$ and $n\ge 2^{64}$ in the C cubic budget. If $n-1$ is hostile, cubic search still finishes the proof.

## Why this beats cubic search

Cubic search (Lehman) is complete for every $n$ in budget: cost $\Theta(n^{1/3})$ in the worst case (including primes). The n−1 line of work (Pocklington 1914; Brillhart–Lehmer–Selfridge 1975) costs:

1. **Factor** $n-1$ (or enough of it that $F \mid (n-1)$ and $F > \sqrt{n}$).
2. For each prime $q \mid F$, find a fixed small base $a$ with
   $a^{n-1}\equiv 1\pmod n$ and $\gcd(a^{(n-1)/q}-1,\,n)=1$.

Then every prime divisor of $n$ is $\equiv 1\pmod F$. With $F>\sqrt{n}$, $n$ is prime.

When $n-1$ is smooth (e.g. $600000000000000000001$, where $n-1=2^{21}\cdot 3\cdot 5^{20}$), step 1 is microseconds and step 2 is a handful of modular exponentiations. The current CLI default $10000000000000000000000000000000000000121$ has a hostile $n-1$ and falls through to cubic. Same machine class:

| Case | Cubic C (prior hard path) | n−1 proof |
|------|--------------------------:|----------:|
| Smooth 70-bit specimen | ~150 ms | **~0.2 ms** check / **~3 ms** e2e CLI |
| M61 | ~33 ms | **~0.3 ms** |
| near $2^{63}$ | ~37 ms | **~10 ms** |
| largest prime $<2^{64}$ | ~55 ms | **~27 ms** |
| CLI default (133-bit, hostile $n-1$) | — | inconclusive → **cubic ~0.3 s** |

Hostile $n-1$ (large prime cofactor that will not split in budget) returns *inconclusive*; cubic search remains the complete fallback. No RNG. No Miller–Rabin as the engine: a failed Fermat check **proves composite**; a passed Fermat check is only a filter, not a primality claim.

## Relation to recent literature

| Year | Result | Role here |
|------|--------|-----------|
| 1914 / 1975 | Pocklington; BLS $n\pm 1$ tests | **This engine** |
| 1974 | Lehman $O(n^{1/3})$ | Cubic **fallback** |
| 2020–21 | Harvey / Harvey–Hittmeir $n^{1/5}$ | Theoretical search; not shipped |
| 2024 | Hales–Hiary (Lehman for power divisors) | Confirms cubic search line |
| 2025 | Oznovich–Volk, Umans–Wang, … | Special-form / conjectural |

The synthesis is: use the classical **proof** line when $n-1$ cooperates; keep the modern **search** line when it does not. Both stay inside the repository restrictions.

## Dispatch

```text
hard path (cubic_complete_ready)
  → nm1_primality(n)
       True  → prime
       False → composite (then optional cubic for a FACTOR print)
       None  → lehman_factor_u128 (complete cubic)
```

`lab(n)["path"]` is `u64_nm1` / `u128_nm1` when the prover settles, else `u64_lehman_c` / `u128_lehman_c`.

## Related

- [Cubic search](cubic-search.md) — fallback / `factorint` splitter
- [Engines](engines.md) — full ladder
- [Restrictions](restrictions.md)
- [`docs/ALGORITHM_HISTORY.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md)
