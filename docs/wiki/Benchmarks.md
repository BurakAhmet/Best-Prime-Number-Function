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

See also [Hall of fame](Hall-of-fame) for notable 64-bit primes and the automated prime-of-the-day log.
