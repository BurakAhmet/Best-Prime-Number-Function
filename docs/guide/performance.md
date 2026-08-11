# Performance

Two complementary metrics — do not mix them up.

| Script | What it measures | Role |
|--------|------------------|------|
| [`benchmarks/compare_e2e.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/benchmarks/compare_e2e.py) | **End-to-end CLI `TIME`** (import → answer) | Primary optimization target and CI perf gate |
| [`benchmarks/compare_speed.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/benchmarks/compare_speed.py) | In-process `is_prime()` after engines are warm | Secondary, non-gating hot-loop snapshot |

Both in-process baselines are **deterministic** (no Miller–Rabin).

## What to expect

| Input size | Typical engine (with `.so`) | Notes |
|------------|----------------------------|--------|
| Tiny / moderate | Python loop or stdlib wheel | Sub-ms to tens of ms |
| Hard 64-bit primes | OpenMP `u64_wheel_c` | Sub-second multi-core on a laptop |
| Up to about $10^{20}$ with practical $\sqrt{n}$ | OpenMP `u128_wheel_c` | Seconds, not AKS |
| Huge primes, no small factors | Partial trial → **AKS** | Correct but can be very slow |

Without `wheel_core.so`, the library still works via stdlib wheels and/or Numba; only the slowest 64-bit / multi-limb cases suffer most.

## Snapshot (indicative)

End-to-end CLI `TIME` on a dev machine (`compare_e2e.py`, best of several runs; wall times vary by CPU and whether `wheel_core.so` is present):

| Case | $n$ | Typical e2e CLI `TIME` |
|------|----:|-----------------------:|
| Small prime | 97 | ~0.4 ms |
| $10^9+7$ | 1000000007 | ~2–3 ms |
| 12-digit prime | 999999999989 | ~2–4 ms |
| Near $2^{63}$ | 9223372036854775783 | ~0.19–0.22 s |
| Largest prime $<2^{64}$ | 18446744073709551557 | ~0.28–0.31 s |
| Mersenne M61 | $2^{61}-1$ | ~0.10–0.12 s |

Recent engine work (INV16, persist uint32 marks, `DELTA[64]`, L1-tiled marking in v1.10.0, then **tiles to $p<4096$ + 4+4 wrap-mul**) moved the hard 64-bit class roughly **20–30%** in-process versus the v1.7 engine. Mid-size e2e stays on the precomputed-prime path and is unchanged in class.

## Reproduce

```bash
bash scripts/compile_wheel_core.sh
OMP_NUM_THREADS=2 python benchmarks/compare_e2e.py --include-hard
OMP_NUM_THREADS=2 python benchmarks/compare_speed.py --include-hard
python scripts/check_e2e_regression.py \
  --baseline benchmarks/e2e_results.json --candidate /tmp/e2e.json
```

CI fails a PR if candidate e2e `TIME` regresses **>25%** on measurable cases versus the base commit (`min-ms` 1.0). Primary metric is still wall-clock CLI `TIME`, not a warm hot-loop.

Notable 64-bit primes and the automated prime-of-the-day log: [Hall of fame](https://burakahmet.github.io/Best-Prime-Number-Function/Hall-of-fame.html).
