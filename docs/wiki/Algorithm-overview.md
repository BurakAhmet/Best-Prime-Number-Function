# Algorithm overview

## Fast path — $n \lt 2^{64}$

CLI **`TIME` is end-to-end** (import → answer). Engines are tiered to minimize that total:

1. $n \lt 10^4$: tiny pure-Python loop (no NumPy/Numba).
2. If `is_prime_data/wheel_core.so` is present: **OpenMP C** small-prime precheck, then a **deterministic Miller test** with witnesses $2,3,5,7,11,13,23$ (complete for every 64-bit $n$).
3. Else if $n \le 4\cdot10^{12}$: **embedded 30030-wheel** (stdlib only, zlib-compressed steps in `best_prime/is_prime.py`).
4. Else: stdlib fixed-witness test (same complete set). The **9699690**-wheel / Numba path remains as a legacy table for tests.

Legacy `W30030` / `RES_TO_WI` load lazily for tests. Build the C core with `bash scripts/compile_wheel_core.sh` (regenerate sources via `python scripts/generate_wheel_core_c.py`). Regenerate tables with `python scripts/generate_wheel_data.py`. E2E bench: `python benchmarks/compare_e2e.py`.

## Large path — $n \ge 2^{64}$

1. If $n \le 3\,317\,044\,064\,679\,887\,385\,961\,981$: deterministic Miller test with witnesses $2,3,5,7,11,13,17,19,23,29,31,37$ (Sorenson–Webster). Prefer OpenMP C **`is_prime_u128_core`**.
2. For still-larger $n$: **30030-wheel** trial up to $\min(10^8,\lfloor\sqrt{n}\rfloor)$, then **AKS** if needed (Kronecker poly mul; correct, still slow for huge primes).

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
| `prime_factors` / `factorint` | 30-wheel trial, Fermat, deterministic Brent–Pollard, then `is_prime` |
| `is_perfect_power` / `is_prime_power` | Newton $k$-th roots; prime exponents only |

Console scripts: `next-prime 100` · `totient 10` · `primorial 7`.

## Related

- [**Algorithm history**](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md) — every engine era, benchmarks, advantages/disadvantages, **failures not to repeat**
- [Benchmarks](Benchmarks) — in-process vs end-to-end CLI `TIME`
- [Project restrictions](Project-restrictions)
- Source: [`best_prime/is_prime.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/best_prime/is_prime.py) · [`best_prime/prime_sieve.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/best_prime/prime_sieve.py)
