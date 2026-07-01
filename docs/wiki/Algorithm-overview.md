# Algorithm overview

## Fast path — $n < 2^{64}$

CLI **`TIME` is end-to-end** (import → answer). Engines are tiered to minimize that total:

1. $n < 10^4$: tiny pure-Python loop (no NumPy/Numba).
2. If `is_prime_data/wheel_core.so` is present: **OpenMP C** `9699690`-wheel (preferred on Linux CI). The hot loop uses **4-way independent mods** (exact trial division; hides `DIV` latency on OoO CPUs), integer `isqrt`, and optional early abort when a factor is found.
3. Else if $n \le 4\cdot10^{12}$: **embedded 30030-wheel** (stdlib only, zlib-compressed steps in `is_prime.py`).
4. Else: lazy **Numba** `9699690`-wheel with optional `prange` when $\lfloor\sqrt{n}\rfloor \ge 50\,000$.

Legacy `W30030` / `RES_TO_WI` load lazily for tests. Build the C core with `bash scripts/compile_wheel_core.sh` (regenerate sources via `python scripts/generate_wheel_core_c.py`). Regenerate tables with `python scripts/generate_wheel_data.py`. E2E bench: `python benchmarks/compare_e2e.py`.

## Large path — $n \ge 2^{64}$

1. Trial division by small primes and odds up to a practical bound (or $\sqrt{n}$).
2. If the bound reaches $\sqrt{n}$, answer is exact.
3. Otherwise **AKS** — unconditional and deterministic, but potentially very slow for large primes with no small factors.

## Related

- [Benchmarks](Benchmarks) — in-process vs end-to-end CLI `TIME`
- [Project restrictions](Project-restrictions)
- Source: [`is_prime.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/is_prime.py)
