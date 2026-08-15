# n−1 / n+1 / combined BLS

A deterministic primality proof that is **not** a search up to $\sqrt{n}$ or $n^{1/3}$. When enough of $n\pm 1$ factors, a few modular exponentiations (and, on the $n+1$ side, a Lucas $U$-sequence) settle the predicate — often **orders of magnitude** faster than cubic search.

!!! tip "Hard path and still-larger $n$"
    Mid-size 64-bit $n$ ($\lfloor\sqrt{n}\rfloor < 10^{7}$) stay on wheel trial. Combined BLS runs where complete cubic search would (hard 64-bit $n$, cubic-budget multi-limb) **and** on still-larger $n$ before [ECPP](ecpp-proof.md) / AKS. If $n\pm 1$ is hostile, cubic search remains the complete fallback *in budget*; past that budget, ECPP then AKS.

## Why this beats cubic search

Cubic search (Lehman) is complete for every $n$ in budget: cost $\Theta(n^{1/3})$ in the worst case (including primes). The n−1 line of work (Pocklington 1914; Brillhart–Lehmer–Selfridge 1975) costs:

1. **Factor** $n-1$ (or enough of it that $F \mid (n-1)$ and $F > \sqrt{n}$).
2. For each prime $q \mid F$, find a fixed small base $a$ with
   $a^{n-1}\equiv 1\pmod n$ and $\gcd(a^{(n-1)/q}-1,\,n)=1$.

Then every prime divisor of $n$ is $\equiv 1\pmod F$. With $F>\sqrt{n}$, $n$ is prime.

When $n-1$ is smooth (e.g. $600000000000000000001$, where $n-1=2^{21}\cdot 3\cdot 5^{20}$), step 1 is microseconds and step 2 is a handful of modular exponentiations. The current CLI default $100000000000000000000000000000000000000000031$ (147-bit) settles via **partial Pocklington** after trial/Brent/p−1 splits of $n-1$ — even past the C cubic wall ($4kn$ no longer fits in 128 bits). `DEFAULT_N` is **not** moved to a 100-digit prime. Same machine class:

| Case | Cubic C (prior hard path) | n−1 proof |
|------|--------------------------:|----------:|
| Smooth 70-bit specimen | ~150 ms | **~0.2 ms** check / **~3 ms** e2e CLI |
| M61 | ~33 ms | **~0.3 ms** |
| near $2^{63}$ | ~37 ms | **~10 ms** |
| largest prime $<2^{64}$ | ~55 ms | **~27 ms** |
| CLI default (147-bit) | cubic incomplete ($4kn>128$ bits) | **~7–40 ms** n−1 (prove the 140-bit cofactor; no 5e6 $n+1$ scan) |

Hostile $n-1$ (large prime cofactor that will not split in budget) returns *inconclusive*; cubic search remains the complete fallback in budget. No RNG. No Miller–Rabin as the engine: a failed Fermat check **proves composite**; a passed Fermat check is only a filter, not a primality claim.

## n+1 (Lucas) — $G>\sqrt{n}$ or complete only

Write $n+1 = G\cdot S$ with $\gcd(G,S)=1$ and $G$ completely prime-factored. Selfridge’s discriminant sequence picks a Lucas witness ($P=1$, $Q=(1-D)/4$). Condition (II): $U_{n+1}\equiv 0\pmod n$ and $\gcd(U_{(n+1)/q},\,n)=1$ for every prime $q\mid G$. Then $n$ is prime if **$G>\sqrt{n}$**, or if $G=n+1$ (complete factorization). There is **no** n+1 cubic extra in this tree (BLS 1975 Theorem 11 is an n−1 result). Selfridge’s sequence is **not** used as a Lucas-PRP / BPSW filter.

## Combined Theorem 1 — not $FG>\sqrt{n}$

$FG>\sqrt{n}$ is **not a theorem** and must not be coded. Counter-scale: $F\approx G\approx n^{1/4}$ gives $FG\approx\sqrt{n}$ but $F^2G/2\approx n^{3/4}/2\ll n$. Every prime factor $q$ of $n$ satisfies $q\equiv 1\pmod F$ **and** $q\equiv\pm 1\pmod G$, so a composite cofactor is $m\equiv 1\pmod{FG/2}$. The resulting lower bound is **cubic** in the factored parts.

Let $n-1=F\cdot R$ and $n+1=G\cdot S$ with $\gcd(F,R)=\gcd(G,S)=1$, $F$ and $G$ completely factored, and **$\gcd(F,G)=2$** (both sides are even for odd $n$). Combined Theorem 1 (PrimePages, citing BLS 1975):

> If conditions (I) and (II) hold and
> $$n < \max\bigl(F^{2}G/2,\; FG^{2}/2\bigr),$$
> then $n$ is prime.

A composite with $FG>\sqrt{n}$ but $n\ge\max(F^{2}G/2,\,FG^{2}/2)$ must **not** be reported prime. Combined Theorem 2 is optional; Pomerance’s $3/10$ reduction is not shipped.

Evaluation order (canonical): n−1 ($F>\sqrt{n}$), n−1 cubic extra (BLS Theorem 5), n+1 ($G>\sqrt{n}$), n+1 complete, Combined Theorem 1. First success wins. `lab` path stays `u64_nm1` / `u128_nm1` when n−1 settles (including the 147-bit CLI default); n+1 or combined (and n−1 did not) is `bigint_bls`.

## C-less cubic wall

Cofactor proofs (`_prove_strictly_smaller`) never enter AKS. A leftover is proved only by a **complete** engine, recursive BLS, or ECPP. Completeness uses `cubic_complete_ready(c)`:

- **With** `wheel_core.so`: $4\cdot k\cdot c$ fits in 128 bits for every $k\le\lceil c^{1/3}\rceil$ — about **28 decimal digits**.
- **Without** `.so`: only $\lceil c^{1/3}\rceil\le 8\cdot 10^{6}$ — about **21 digits**. A 22–28 digit cofactor is **not** cubic-ready and goes to BLS, not `is_prime` (which would fall into AKS).

An unproven SIQS hit (this tree peels ~25–30 digit factors) stays an unproven split candidate and is never inserted into $F$ or $G$.

## Relation to recent literature

| Year | Result | Role here |
|------|--------|-----------|
| 1914 / 1975 | Pocklington; BLS $n\pm 1$; Combined Theorem 1 | **This engine** |
| 1974 | Lehman $O(n^{1/3})$ | Cubic **fallback** |
| 2020–21 | Harvey / Harvey–Hittmeir $n^{1/5}$ | Theoretical search; not shipped |
| 2024 | Hales–Hiary (Lehman for power divisors) | Confirms cubic search line |
| 2025 | Oznovich–Volk, Umans–Wang, … | Special-form / conjectural |

The synthesis is: use the classical **proof** line when $n-1$ cooperates; keep the modern **search** line when it does not. Both stay inside the repository restrictions.

## Dispatch

```text
hard path (cubic_complete_ready)
  → bls_primality(n)          # n−1, then n+1, then Combined Theorem 1
       True  → prime
       False → composite (then optional cubic for a FACTOR print)
       None  → lehman_factor_u128 (complete cubic)

still-larger n
  → same BLS first; if None → ECPP → AKS
```

`lab(n)["path"]` is `u64_nm1` / `u128_nm1` when n−1 settles, `bigint_bls` when n+1 or combined settles, else `u64_lehman_c` / `u128_lehman_c` in cubic budget.

BLS certificates (`kind='bls'`) record which side fired and, for combined, the two cubic products $F^{2}G/2$ and $FG^{2}/2$ — never $FG>\sqrt{n}$. At $\ge 256$ bits `primality_certificate` uses FastECPP, not BLS. Hostile Pratt $n-1$ still returns `n-1_unfactored` rather than hanging.

## Related

- [ECPP](ecpp-proof.md) — deterministic Atkin–Morain after BLS
- [Cubic search](cubic-search.md) — fallback / `factorint` splitter
- [Engines](engines.md) — full ladder
- [Restrictions](restrictions.md)
- [`docs/ALGORITHM_HISTORY.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md)
