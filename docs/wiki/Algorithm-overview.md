# Algorithm overview

## Fast path — $n < 2^{64}$

CLI **`TIME` is end-to-end** (import → answer). Paths minimize that total:

1. $n < 10^4$: tiny pure-Python loop (no NumPy/Numba).
2. $n \le 4\cdot10^{12}$: **stdlib** `9699690`-wheel from `is_prime_data/w9699690_steps.u8` (no NumPy/Numba).
3. Harder 64-bit $n$: lazy NumPy/Numba + precomputed `w9699690_u64x2.npy` / `res9699690_u32.npy`; 16× unrolled trial division; `prange` when $\lfloor\sqrt{n}\rfloor \ge 50\,000$.

Legacy `W30030` / `RES_TO_WI` load lazily for tests. Regenerate with `python scripts/generate_wheel_data.py`. E2E bench: `python benchmarks/compare_e2e.py`.

## Large path — $n \ge 2^{64}$

1. Trial division by small primes and odds up to a practical bound (or $\sqrt{n}$).
2. If the bound reaches $\sqrt{n}$, answer is exact.
3. Otherwise **AKS** — unconditional and deterministic, but potentially very slow for large primes with no small factors.

## Related

- [Benchmarks](Benchmarks) — primitive vs optimized
- Source: [`is_prime.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/is_prime.py)
