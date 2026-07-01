# Speed comparison: primitive vs optimized / end-to-end CLI

CLI `TIME` in `is_prime.py` is **end-to-end** (module `t0` → result). Use `compare_e2e.py` for that metric.

`compare_speed.py` still times in-process `is_prime()` calls only (warm JIT), useful for hot-loop regressions.

This directory measures **wall-clock time** for deterministic algorithms on the same inputs:

| Method | What it does |
|--------|----------------|
| **Primitive** | Pure Python: reject evens, then trial-divide by every odd `i` with `3 ≤ i ≤ isqrt(n)` |
| **Optimized** | This repo’s `is_prime`: 9699690-wheel + Numba JIT + multi-threaded `prange` for large 64-bit `n` |

Both are **deterministic** (no Miller–Rabin / randomness). The gap is engineering (wheel + JIT + threads), not a weaker correctness model on the 64-bit path.

## Run the benchmark

From the repository root:

```bash
pip install -r requirements.txt

# Default suite (up to ~12-digit primes; both methods timed)
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py

# Also time optimized on near-2^63 / M61 primes (primitive skipped by default)
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py --include-hard

# Force primitive on hard primes too (can take many minutes per number)
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py --include-hard --primitive-hard

# JSON output
python benchmarks/compare_speed.py --json benchmarks/results.json
```

## Sample results

Machine-dependent. Example run (**12 threads**, best of 3, Linux / Numba):

### End-to-end CLI `TIME` (`compare_e2e.py`, best of 3)

| Case | `n` | E2E ms |
|------|-----:|-------:|
| small prime | 97 | ~3 |
| 4-digit prime | 7919 | ~3 |
| 10⁹+7 | 1000000007 | ~6 |
| Mersenne M31 | 2147483647 | ~7 |
| 12-digit prime | 999999999989 | ~24 |
| near 2⁶³ prime | 9223372036854775783 | ~720 (OpenMP `.so`) |
| Mersenne M61 | 2⁶¹−1 | ~360 |

### In-process hot loop (`compare_speed.py`, warm JIT)

| Case | `n` | Prime? | Primitive (ms) | Optimized (ms) | Speedup |
|------|-----|:------:|---------------:|---------------:|--------:|
| 10⁹+7 | 1000000007 | yes | ~0.7 | ~0.03 | **~23×** |
| 12-digit prime | 999999999989 | yes | ~19 | ~0.02 | **stdlib path** |
| near 2⁶³ prime | 9223372036854775783 | yes | *(skipped)* | ~680 | — |

On **tiny** inputs, Python call overhead and Numba dispatch can make the optimized path look similar or slightly slower; the win grows as $\sqrt{n}$ grows.

On **hard** 64-bit primes, the primitive loop would perform on the order of $10^9$ Python iterations (minutes+); the optimized path finishes in well under a second with multi-threading.

## Files

| File | Role |
|------|------|
| `compare_speed.py` | Runnable benchmark |
| `results.json` | Optional last JSON dump (if generated) |
| `latest_run.txt` | Optional captured console output (if generated) |
| `README.md` | This page |

Regenerate tables after meaningful code changes and paste updates here if you publish numbers.
