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
| Hard 64-bit primes | n−1 `u64_nm1` (else cubic) | ~0.3–30 ms check (was ~30–55 ms cubic) |
| Up to about $10^{20}$ in cubic budget | n−1 `u128_nm1` (else cubic) | ~3 ms e2e CLI default (was ~0.15 s cubic) |
| Else practical $\sqrt{n}$ (≤128-bit) | OpenMP `u128_wheel_c` | Seconds, not AKS |
| Huge primes, no small factors | FastECPP (`bigint_fastecpp`) | 100 digits in seconds, 200 digits ~1 min here; 10k-digit / 10 s not claimed |

Without `wheel_core.so`, the library still works via stdlib wheels and/or Numba; only the slowest 64-bit / multi-limb cases suffer most.

## Snapshot (indicative)

End-to-end CLI `TIME` on a dev machine (`compare_e2e.py`, best of several runs; wall times vary by CPU and whether `wheel_core.so` is present):

| Case | $n$ | Typical e2e CLI `TIME` |
|------|----:|-----------------------:|
| Small prime | 97 | ~0.4 ms |
| $10^9+7$ | 1000000007 | ~2–3 ms |
| 12-digit prime | 999999999989 | ~2–4 ms |
| Near $2^{63}$ | 9223372036854775783 | ~0.19–0.22 s |
| CLI default (147-bit n−1) | 100000000000000000000000000000000000000000031 | ~0.3 s e2e |
| Largest prime $<2^{64}$ | 18446744073709551557 | ~0.21–0.23 s |
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

## Published FastECPP timings

[`benchmarks/timing_table.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/benchmarks/timing_table.py) records `is_prime` (and a certificate check on the cheap rows) on a fixed list. PR CI runs the `pr` band (P40, `DEFAULT_N`, the 123-digit Fermat composite, $P_{100}$). Main adds $P_{150}$. Nightly adds $P_{200}$. The job **fails only on a wrong verdict**, never because 200 digits were slow.

```bash
python3 benchmarks/timing_table.py --band pr
```

Times are machine-specific. 10k-digit / 10 s is the north-star and is not a row in that table.

Notable 64-bit primes and the automated prime-of-the-day log: [Hall of fame](https://burakahmet.github.io/Best-Prime-Number-Function/Hall-of-fame.html).
