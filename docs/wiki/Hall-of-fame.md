# Slow prime hall of fame

Large **64-bit** primes exercised by this project (exact wheel trial division).
Times are **indicative** and depend on CPU, `OMP_NUM_THREADS`, and whether `wheel_core.so` is loaded.

| Prime | Formula / note | Typical e2e CLI `TIME` (with OpenMP `.so`) |
|------:|----------------|---------------------------------------------|
| 1000000007 | $10^9+7$ | ~2–3 ms |
| 1000000009 | $10^9+9$ | ~2–3 ms |
| 2147483647 | $2^{31}-1$ (M31) | ~3 ms |
| 999999999989 | 12-digit prime | ~20–55 ms |
| 2305843009213693951 | $2^{61}-1$ (M61) | ~0.4 s |
| 9223372036854775783 | near $2^{63}$ | ~0.7–0.8 s |
| 18446744073709551557 | largest prime $< 2^{64}$ | ~1 s class |

Reproduce:

```bash
bash scripts/compile_wheel_core.sh
OMP_NUM_THREADS=$(nproc) python is_prime.py --lab 9223372036854775783
OMP_NUM_THREADS=$(nproc) python benchmarks/compare_e2e.py --include-hard
```

Artifacts from CI **Certificate of correctness** and **benchmark-json** are authoritative for a given commit.

## Prime-of-the-day log

Automated entries from the **Prime of the day** workflow (`path` + e2e `TIME`).

<!-- potd-log:start -->
| Date (UTC) | n | Prime? | Path | E2E ms | Check ms |
|------------|--:|:------:|------|-------:|---------:|
| 2026-07-01 | `1000000007` | yes | `u64_wheel_c` | 3.218 | 0.063 |
<!-- potd-log:end -->
