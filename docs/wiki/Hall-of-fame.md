# Slow prime hall of fame

Large **64-bit** primes exercised by this project (exact wheel trial division).  
Times are **indicative** (depend on runner CPU and `NUMBA_NUM_THREADS`).

| Prime | Formula / note | Typical optimized time (12 threads, order of magnitude) |
|------:|----------------|--------------------------------------------------------|
| 1000000007 | $10^9+7$ | ~0.03 ms |
| 1000000009 | $10^9+9$ | ~0.03 ms |
| 2147483647 | $2^{31}-1$ (M31) | ~0.05 ms |
| 999999999989 | 12-digit prime | ~0.2–0.6 ms |
| 2305843009213693951 | $2^{61}-1$ (M61) | ~0.3–0.5 s |
| 9223372036854775783 | near $2^{63}$ | ~0.7–0.8 s |
| 18446744073709551557 | largest prime $< 2^{64}$ | ~1 s class |

Update this table when benchmark workflows or hardware change. Reproduce:

```bash
NUMBA_NUM_THREADS=$(nproc) python is_prime.py --lab 9223372036854775783
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py --include-hard
```

Artifacts from CI **Certificate of correctness** and **benchmark-json** are authoritative for a given commit.
