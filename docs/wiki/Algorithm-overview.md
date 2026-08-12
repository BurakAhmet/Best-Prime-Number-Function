# Algorithm overview

## Fast path — $n \lt 2^{64}$

CLI **`TIME` is end-to-end** (import → answer). Engines are tiered to minimize that total:

1. $n \lt 10^4$: tiny pure-Python loop (no NumPy/Numba).
2. If `is_prime_data/wheel_core.so` is present: **OpenMP C** (preferred on Linux CI), with:
   - small-prime precheck (through a few hundred),
   - **precomputed odd primes** $\le 2^{20}$ and exact **2-adic inverse** trial when $\lfloor\sqrt{n}\rfloor \le 1\,048\,576$ (wrap-mul divisibility; no wheel `DIV`),
   - **complete cubic search** (`u64_lehman_c`) when $\lfloor\sqrt{n}\rfloor \ge 10^{7}$ and `lehman_factor_u128` is present,
   - otherwise **wheel-30 segmented sieve + memcpy presieve** ($7\cdot11\cdot13\cdot17$) **+ OR presieve** ($19\cdot23\cdot29$) **+ persisted uint32 byte-index marks + L1 tiles for $p<4096$ (16 KiB) + `DELTA[64]`/`ctzll` extract + 4+4 2-adic** (INV16, two Newton steps) when $\lfloor\sqrt{n}\rfloor$ is larger (1 byte / 30 numbers; wrap-mul, no `DIV`; OpenMP only when $\lfloor\sqrt{n}\rfloor \ge 10^7$; 128 KiB segments),
   - integer `isqrt` and early abort when a factor is found.
3. Else if $n \le 4\cdot10^{12}$: **embedded 30030-wheel** (stdlib only, zlib-compressed steps in `best_prime/is_prime.py`).
4. Else: lazy **Numba** `9699690`-wheel with optional `prange` when $\lfloor\sqrt{n}\rfloor \ge 50\,000$.

Legacy `W30030` / `RES_TO_WI` load lazily for tests. Build the C core with `bash scripts/compile_wheel_core.sh` (regenerate sources via `python scripts/generate_wheel_core_c.py`). Regenerate tables with `python scripts/generate_wheel_data.py`. E2E bench: `python benchmarks/compare_e2e.py`.

## Large path — $n \ge 2^{64}$

1. If OpenMP **`lehman_factor_u128`** can finish a complete cubic proof (cube root $\le 2\cdot10^{7}$, $4kn$ fits in 128 bits): that is the **CLI default** path (`u128_lehman_c`).
2. Else if $\lfloor\sqrt{n}\rfloor \le 2.5\cdot10^{10}$ and $n$ fits in 128 bits:
   - Prefer OpenMP C **`is_prime_u128_core`** (same wheel / segmented-prime full trial as the 64-bit engine; limbs `lo`/`hi`).
   - Else stdlib **9699690-wheel** full trial in Python.
3. For still-larger $n$: **30030-wheel** trial up to $\min(10^8,\lfloor\sqrt{n}\rfloor)$, then **AKS** if needed (Kronecker poly mul; correct, still slow for huge primes).

## Enumeration, factors, powers

All of these reuse **our** sieves / `is_prime`. No external prime engine.

| API | How |
|-----|-----|
| `next_prime(n, k=1)` | Table / interval sieve / forward 30030-wheel + `is_prime` |
| `prev_prime(n, k=1)` | Same, walking backward |
| `nth_prime(k)` | Sieve while $p_k$ is moderate; else $\log p_k$ `prime_count` probes |
| `prime_count(n)` | Sieve for $n\le 2\cdot10^7$; Lucy–Hedgehog (Numba when $n\ge10^7$) up to $n\le 2.5\cdot10^{15}$; **Meissel–Lehmer** through $2^{64}-1$ |
| `primes(n)` / `primerange(a,b)` | Cached odds-only Eratosthenes; **`primerange` yields** (segmented windows, no full list) |
| `totient` / `primorial` / `divisors` | From `factorint`; `totient_range` is a linear sieve; primorial uses a product tree |
| `prime_factors` / `factorint` | 30-wheel trial, Fermat, two-band cubic search (Lehman + rising-product wheel), deterministic Brent–Pollard, ECM, SIQS; each prime confirmed with `is_prime` |
| `lehman_factor` | Complete $O(n^{1/3})$ split while $\lceil n^{1/3}\rceil\le 3\cdot 10^6$; not the 64-bit `is_prime` engine |
| `is_perfect_power` / `is_prime_power` | Newton $k$-th roots; prime exponents only |

Console scripts: `next-prime 100` · `totient 10` · `primorial 7`.

## Related

- [**Algorithm history**](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md) — every engine era, benchmarks, advantages/disadvantages, **failures not to repeat**
- [Benchmarks](Benchmarks) — in-process vs end-to-end CLI `TIME`
- [Project restrictions](Project-restrictions)
- Source: [`best_prime/is_prime.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/best_prime/is_prime.py) · [`best_prime/prime_sieve.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/best_prime/prime_sieve.py)
