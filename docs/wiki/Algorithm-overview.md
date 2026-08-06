# Algorithm overview

## Fast path — $n < 2^{64}$

CLI **`TIME` is end-to-end** (import → answer). Engines are tiered to minimize that total:

1. $n < 10^4$: tiny pure-Python loop (no NumPy/Numba).
2. If `is_prime_data/wheel_core.so` is present: **OpenMP C** (preferred on Linux CI), with:
   - small-prime precheck (through a few hundred),
   - **8-way independent-mod** `9699690`-wheel when $\lfloor\sqrt{n}\rfloor$ is moderate (exact trial division; hides `DIV` latency on OoO CPUs),
   - **segmented prime sieve + prime-only trial** when $\lfloor\sqrt{n}\rfloor \ge 2\cdot10^5$ (fewer mods than the wheel; bit-packed sieve for moderate $\sqrt{n}$, byte sieve for hard 64-bit primes),
   - integer `isqrt` and early abort when a factor is found.
3. Else if $n \le 4\cdot10^{12}$: **embedded 30030-wheel** (stdlib only, zlib-compressed steps in `is_prime.py`).
4. Else: lazy **Numba** `9699690`-wheel with optional `prange` when $\lfloor\sqrt{n}\rfloor \ge 50\,000$.

Legacy `W30030` / `RES_TO_WI` load lazily for tests. Build the C core with `bash scripts/compile_wheel_core.sh` (regenerate sources via `python scripts/generate_wheel_core_c.py`). Regenerate tables with `python scripts/generate_wheel_data.py`. E2E bench: `python benchmarks/compare_e2e.py`.

## Large path — $n \ge 2^{64}$

1. If $\lfloor\sqrt{n}\rfloor \le 2.5\cdot10^{10}$ and $n$ fits in 128 bits (covers e.g. primes near $10^{20}$):
   - Prefer OpenMP C **`is_prime_u128_core`** (same wheel / segmented-prime full trial as the 64-bit engine; limbs `lo`/`hi`).
   - Else stdlib **9699690-wheel** full trial in Python.
2. For still-larger $n$: partial trial up to a practical bound, then **AKS** if needed (correct but can be very slow).

## Related

- [**Algorithm history**](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md) — every engine era, benchmarks, advantages/disadvantages, **failures not to repeat**
- [Benchmarks](Benchmarks) — in-process vs end-to-end CLI `TIME`
- [Project restrictions](Project-restrictions)
- Source: [`is_prime.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/is_prime.py)
