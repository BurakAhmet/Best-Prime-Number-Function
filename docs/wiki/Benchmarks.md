# Benchmarks

Two complementary metrics:

| Script | What it measures |
|--------|------------------|
| [`benchmarks/compare_e2e.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/benchmarks/compare_e2e.py) | **End-to-end CLI `TIME`** (module import → answer). Primary optimization target and CI perf gate. |
| [`benchmarks/compare_speed.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/benchmarks/compare_speed.py) | In-process `is_prime()` after engines are warm. Useful for hot-loop regressions. |

Both methods compared in-process against a naive odd trial baseline are **deterministic** (no Miller–Rabin).

```bash
bash scripts/compile_wheel_core.sh
OMP_NUM_THREADS=2 python benchmarks/compare_e2e.py --include-hard
OMP_NUM_THREADS=2 python benchmarks/compare_speed.py --include-hard
python scripts/check_e2e_regression.py \
  --baseline benchmarks/e2e_results.json --candidate /tmp/e2e.json
```

See also [Hall of fame](Hall-of-fame) for notable primes and the automated prime-of-the-day log. A 1000-digit cyclotomic proof, $10^{999}+7$, is about 43 seconds in `is_prime` on 12 cores, and about three minutes in the in-tab checker on that machine. $10^{1099}+73$, past the old 1024-digit modulus, is the same proof in about 158 seconds in the library. The modulus ladder covers 5000-digit integers. That walk is one multiplication per exponent, about $4.7\times 10^{9}$ of them, so a 5000-digit proof is not a five-minute run.
