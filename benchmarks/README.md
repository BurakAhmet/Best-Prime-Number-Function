# Speed comparison: primitive vs optimized / end-to-end CLI

CLI `TIME` from `python -m best_prime` is **end-to-end** (module `t0` → result). Use `compare_e2e.py` for that metric.

`compare_speed.py` still times in-process `is_prime()` calls only (warm JIT), useful for hot-loop regressions.

This directory measures **wall-clock time** for deterministic algorithms on the same inputs:

| Method | What it does |
|--------|----------------|
| **Primitive** | Pure Python: reject evens, then trial-divide by every odd `i` with `3 ≤ i ≤ isqrt(n)` |
| **Optimized** | This repo’s `is_prime`: OpenMP precomputed-prime / segmented trial, or 9699690-wheel + Numba JIT fallback |

Both are **deterministic** (no Miller–Rabin / randomness). The gap is engineering (wheel + JIT + threads), not a weaker correctness model on the 64-bit path.

## Run the benchmark

From the repository root:

```bash
pip install -e ".[fast]"

# Default suite (up to ~12-digit primes; both methods timed)
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py

# Also time optimized on near-2^63 / M61 primes (primitive skipped by default)
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py --include-hard

# Force primitive on hard primes too (can take many minutes per number)
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py --include-hard --primitive-hard

# JSON output
python benchmarks/compare_speed.py --json /tmp/speed.json
```

## Sample results

Machine-dependent. Example run (**12 threads**, best of 3, Linux / Numba):

### End-to-end CLI `TIME` (`compare_e2e.py`, best of 3)

Indicative sample (OpenMP `.so`, multi-core; see `e2e_results.json` for last committed numbers):

| Case | `n` | E2E ms |
|------|-----:|-------:|
| small prime | 97 | ~0.4 |
| 4-digit prime | 7919 | ~0.4 |
| 10⁹+7 | 1000000007 | ~2–3 |
| Mersenne M31 | 2147483647 | ~2–3 |
| 12-digit prime | 999999999989 | ~2–4 (precomputed primes) |
| near 2⁶³ prime | 9223372036854775783 | ~190–220 (OpenMP `.so`) |
| CLI default (73-bit cubic) | 1000000000000000000000000000000000000003 | ~300 |
| largest prime < 2⁶⁴ | 18446744073709551557 | ~210–230 |
| Mersenne M61 | 2⁶¹−1 | ~150–200 |

Example CLI lines (same metric as `TIME:` on stdout):

```text
TEST:    999999999989 (12 chars)
THREADS: 12
RESULT:  prime
TIME:    4467572 ns  (4.467572 ms)
```

```text
TEST:    9223372036854775783 (19 chars)
THREADS: 12
RESULT:  prime
TIME:    569402248 ns  (569.402248 ms)
```

### In-process hot loop (`compare_speed.py`, warm engines)

| Case | `n` | Prime? | Primitive (ms) | Optimized (ms) | Speedup |
|------|-----|:------:|---------------:|---------------:|--------:|
| 10⁹+7 | 1000000007 | yes | ~0.7 | ~0.03 | **~23×** |
| 12-digit prime | 999999999989 | yes | ~19 | ~0.3–0.5 (C seg-primes) | **~40×+** |
| near 2⁶³ prime | 9223372036854775783 | yes | *(skipped)* | ~550–580 | — |

On **tiny** inputs, Python call overhead and Numba dispatch can make the optimized path look similar or slightly slower; the win grows as $\sqrt{n}$ grows.

On **hard** 64-bit primes, the primitive loop would perform on the order of $10^9$ Python iterations (minutes+); the optimized path finishes in well under a second with multi-threading.

## Files

| File | Role |
|------|------|
| `compare_e2e.py` | Primary metric: end-to-end CLI `TIME` |
| `compare_speed.py` | Warm in-process hot loop (secondary) |
| `check_determinism.py` | Serial == parallel, repeatable answers |
| `e2e_results.json` | Committed e2e snapshot (CI baseline) |
| `README.md` | This page |

Regenerate tables after meaningful code changes and paste updates here if you publish numbers.
