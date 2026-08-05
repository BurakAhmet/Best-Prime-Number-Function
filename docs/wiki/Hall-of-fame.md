# Slow prime hall of fame

Large **64-bit** primes exercised by this project (exact wheel trial division).
Times are **indicative** and depend on CPU, `OMP_NUM_THREADS`, and whether `wheel_core.so` is loaded.

| Prime | Formula / note | Typical e2e CLI `TIME` (with OpenMP `.so`) |
|------:|----------------|---------------------------------------------|
| 1000000007 | $10^9+7$ | ~2–3 ms |
| 1000000009 | $10^9+9$ | ~2–3 ms |
| 2147483647 | $2^{31}-1$ (M31) | ~2–3 ms |
| 999999999989 | 12-digit prime | ~5–10 ms |
| 2305843009213693951 | $2^{61}-1$ (M61) | ~0.27–0.35 s |
| 9223372036854775783 | near $2^{63}$ | ~0.55–0.65 s |
| 18446744073709551557 | largest prime $< 2^{64}$ | ~1 s class |

C core (v1.3.2+): 8-way independent trial mods on the OpenMP wheel loop; mid-size / hard 64-bit paths use segmented prime sieve + prime-only trial (bit-packed sieve when $\sqrt{n}$ is moderate).

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
| 2026-08-05 | `1354509` | no | `u64_wheel_c` | 4.371 | 0.004 |
| 2026-08-04 | `1344537` | no | `u64_wheel_c` | 4.912 | 0.004 |
| 2026-08-03 | `1334563` | yes | `u64_wheel_c` | 4.892 | 0.016 |
| 2026-08-02 | `1324591` | yes | `u64_wheel_c` | 5.091 | 0.017 |
| 2026-07-15 | `1145077` | yes | `u64_wheel_c` | 4.878 | 0.016 |
| 2026-07-14 | `1135103` | yes | `u64_wheel_c` | 4.808 | 0.015 |
| 2026-07-01 | `1000000007` | yes | `u64_wheel_c` | 3.218 | 0.063 |
<!-- potd-log:end -->
