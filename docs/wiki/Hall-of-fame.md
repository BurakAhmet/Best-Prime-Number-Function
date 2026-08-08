# Slow prime hall of fame

Large **64-bit** primes exercised by this project (exact wheel trial division).
Times are **indicative** and depend on CPU, `OMP_NUM_THREADS`, and whether `wheel_core.so` is loaded.

| Prime | Formula / note | Typical e2e CLI `TIME` (with OpenMP `.so`) |
|------:|----------------|---------------------------------------------|
| 1000000007 | $10^9+7$ | ~2–3 ms |
| 1000000009 | $10^9+9$ | ~2–3 ms |
| 2147483647 | $2^{31}-1$ (M31) | ~2–3 ms |
| 999999999989 | 12-digit prime | ~2–4 ms |
| 2305843009213693951 | $2^{61}-1$ (M61) | ~0.10–0.12 s |
| 9223372036854775783 | near $2^{63}$ | ~0.19–0.22 s |
| 18446744073709551557 | largest prime $\lt 2^{64}$ (CLI default) | ~0.28–0.32 s |

C core (v1.4.4+): precomputed primes $\le 2^{20}$ with 2-adic inverse trial for mid-size $n$; harder 64-bit paths use a **wheel-30** segmented sieve, **memcpy presieve** of $7\cdot11\cdot13\cdot17$, **uint64 `ctzll` extract**, and **8-way 2-adic** prime-only trial. Stdlib / Numba still keep the **30030** / **9699690** wheels.

Reproduce:

```bash
bash scripts/compile_wheel_core.sh
OMP_NUM_THREADS=$(nproc) python is_prime.py --lab 18446744073709551557
OMP_NUM_THREADS=$(nproc) python benchmarks/compare_e2e.py --include-hard
```

Artifacts from CI **Certificate of correctness** and **benchmark-json** are authoritative for a given commit.

## Prime-of-the-day log

Automated entries from the **Prime of the day** workflow (`path` + e2e `TIME`). The Pages home exhibits the latest row as *Acta Primorum*.

<!-- potd-log:start -->
| Date (UTC) | n | Prime? | Path | E2E ms | Check ms |
|------------|--:|:------:|------|-------:|---------:|
| 2026-08-08 | `1384429` | no | `u64_wheel_c` | 5.154 | 0.005 |
| 2026-08-07 | `1374455` | no | `u64_wheel_c` | 4.74 | 0.005 |
| 2026-08-06 | `1364483` | yes | `u64_wheel_c` | 5.482 | 0.017 |
| 2026-08-05 | `1354509` | no | `u64_wheel_c` | 4.371 | 0.004 |
| 2026-08-04 | `1344537` | no | `u64_wheel_c` | 4.912 | 0.004 |
| 2026-08-03 | `1334563` | yes | `u64_wheel_c` | 4.892 | 0.016 |
| 2026-08-02 | `1324591` | yes | `u64_wheel_c` | 5.091 | 0.017 |
| 2026-07-15 | `1145077` | yes | `u64_wheel_c` | 4.878 | 0.016 |
| 2026-07-14 | `1135103` | yes | `u64_wheel_c` | 4.808 | 0.015 |
| 2026-07-01 | `1000000007` | yes | `u64_wheel_c` | 3.218 | 0.063 |
<!-- potd-log:end -->
