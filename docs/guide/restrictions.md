# Restrictions

These rules apply to **all** contributors and **automated agents**. They are the product contract, not a style preference.

## Non-negotiable

1. **Deterministic** — no randomness; same input ⇒ same output, always.
2. **No stochastic Miller–Rabin** — no random bases, no “probably prime” engines as the core.
3. **No prime libraries** as the implementation (e.g. `primesieve`, `sympy.isprime` as the engine).
4. **Allowed:** NumPy / Numba, and our own compiled OpenMP helper (`wheel_core.so`), for speeding up *our* trial division.
5. **Correctness model**
    - $n \lt 2^{64}$: exact trial division up to $\lfloor\sqrt{n}\rfloor$ when $\lfloor\sqrt{n}\rfloor < 10^{7}$ (OpenMP **precomputed primes** / segmented primes, or primorial-wheel **30030** / **9699690**). Harder 64-bit $n$ ($\lfloor\sqrt{n}\rfloor \ge 10^{7}$): **n−1 Pocklington** when $n-1$ factors in budget, else complete OpenMP cubic search when `lehman_factor_u128` is present.
    - $2^{64} \le n$ in cubic budget ($4kn$ fits in 128 bits (no artificial cub cap), $4kn$ fits in 128 bits): same n−1 then cubic ladder (covers every $n$ with $4kn$ in 128 bits). Else $\lfloor\sqrt{n}\rfloor \le 2.5\cdot10^{10}$ (≤128-bit): full trial via OpenMP **u128** core or stdlib wheel
    - still larger $n$: **combined BLS**, then deterministic Atkin–Morain **ECPP** (class-number-1, then small-$h$ CM — the general 100-digit layer), then **AKS** (may be slow for huge primes). `DEFAULT_N` is the 147-bit CLI default (`u128_nm1`, past the cubic wall).

Enforced in CI by `scripts/check_restrictions.py`. Serial and parallel must agree on every result.

## Why not “just use MR”?

Fixed witness Miller–Rabin is deterministic only on **proven finite ranges** (e.g. 64-bit with a known base set). That does **not** give a uniform finite-base proof for **every** natural number. This project optimizes under the stricter goal: deterministic for all $n$ in theory, with engineered fast paths for 64-bit inputs.

A random-base quiz can also be *wrong*. SymPy’s stochastic helper `sympy.ntheory.primetest.mr` said the Chernick Carmichael number below was prime for bases $\{2,3,5\}$; exact trial found a factor.

```python
from sympy.ntheory.primetest import mr, isprime
from best_prime import is_prime

n = 3943673813084040361            # 869461 × 1738921 × 2608381
mr(n, [2, 3, 5])                   # True   ← “prime”
isprime(n)                         # False  ← SymPy’s full predicate
is_prime(n)                        # False  ← exact trial
```

`sympy.isprime` itself is **not** used here, even when it happens to agree — the restriction is about the engine, not the boolean on a lucky sample.

## What “allowed accelerators” means

NumPy, Numba, and `wheel_core.so` exist to run **our** wheel / sieve / wrap-mul faster. They are not a licence to call a third-party primality oracle. If a patch makes a hard 64-bit prime faster by asking someone else “is this prime?”, it will not be merged, even if the e2e numbers look great.

## Related

- [n−1 / BLS](nm1-proof.md) — Combined Theorem 1; C-less cubic wall
- [ECPP](ecpp-proof.md) — deterministic Atkin–Morain; $h=1$ is not a random-100-digit engine
- [Cubic search](cubic-search.md) — $O(n^{1/3})$ fallback / `factorint` splitter
- [Engines](engines.md)
- [Algorithm history](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md) — eras, tradeoffs, **failures not to repeat**
- [CONTRIBUTING.md](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/CONTRIBUTING.md)
