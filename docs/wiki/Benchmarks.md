# Benchmarks — primitive vs optimized

Both methods are **deterministic**. The gap is engineering (wheel + Numba + threads), not weaker math on the 64-bit path.

| Method | Description |
|--------|-------------|
| **Primitive** | Pure Python: odds only up to `isqrt(n)` |
| **Optimized** | `is_prime()` — 9699690-wheel + Numba (+ threads) |

## Run

```bash
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py --include-hard
```

## Sample speedups (indicative, 12 threads)

| Case | Speedup (optimized vs primitive) |
|------|----------------------------------:|
| $10^9+7$ / $10^9+9$ | ~20× |
| Mersenne $2^{31}-1$ | ~17× |
| 12-digit prime | ~90–100× |
| Near $2^{63}$ prime | Optimized ~0.7s; primitive usually skipped (too slow) |

Details: [benchmarks/README.md](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/benchmarks/README.md)
