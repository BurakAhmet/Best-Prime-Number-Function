# Contributing

Thanks for your interest in improving **Best-Prime-Number-Function**. Contributions of all kinds are welcome—bug reports, tests, docs, benchmarks, and carefully reviewed code changes.

## Before you start

Please read the [README](README.md), especially **Design restrictions** and **Supported platforms**. This project optimizes under hard constraints:

- Results must stay **fully deterministic** (no randomness).
- **No stochastic Miller–Rabin** or “probably prime” shortcuts.
- **No** external prime libraries (e.g. primesieve) as the engine.
- NumPy / Numba and our own OpenMP `wheel_core.so` are allowed for speed of *our* algorithms only.

PRs that violate those rules will not be merged, even if they look faster on paper.

If you change engines, thresholds, or the dispatch ladder, read and update
[`docs/ALGORITHM_HISTORY.md`](docs/ALGORITHM_HISTORY.md) (past eras, tradeoffs, and failures not to repeat).

> This repository was **created and designed by an AI agent**. Human review of contributions (and of the existing code) is encouraged.

## Developer loop (matches CI)

```bash
git clone https://github.com/BurakAhmet/Best-Prime-Number-Function.git
cd Best-Prime-Number-Function
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# OpenMP core is built during install when gcc+OpenMP are available; else:
bash scripts/compile_wheel_core.sh
python3 scripts/check_restrictions.py
python3 scripts/check_wiki_sync.py
pytest -q -m "not slow"
OMP_NUM_THREADS=2 python3 benchmarks/check_determinism.py
OMP_NUM_THREADS=2 python3 benchmarks/compare_e2e.py --json /tmp/e2e.json
python3 scripts/check_e2e_regression.py \
  --baseline benchmarks/e2e_results.json --candidate /tmp/e2e.json
# library smoke:
python3 -c "from best_prime import is_prime, next_prime, nth_prime, prime_count; assert is_prime(17); assert next_prime(14, 3)==23; assert nth_prime(5)==11; assert prime_count(10)==4"
python3 examples/basic_usage.py
```

**Primary perf metric:** end-to-end CLI `TIME` (`compare_e2e.py`).  
**Secondary:** in-process hot loop (`compare_speed.py`) after engines are warm.

On Linux with a successful `compile_wheel_core.sh`, `lab(10**9+7)["path"]` must be `u64_wheel_c`.

### Full tests

```bash
pytest -q   # includes @pytest.mark.slow hard 64-bit primes
```

## Pull request checklist

1. **Restrictions** — deterministic; no MR / prime libs as engine.
2. **Tests** — `pytest -m "not slow"` passes; add C-path coverage if you touch `wheel_core.c`.
3. **Speed** — run `compare_e2e.py`; avoid e2e regressions CI would flag (>25% on measurable cases).
4. **Docs** — update README **and** `docs/wiki/` (`check_wiki_sync.py` must pass).
5. **Build path** — use `scripts/compile_wheel_core.sh` / `generate_wheel_data.py` / `generate_wheel_core_c.py` only (no ad-hoc AOT scripts).
6. **Scope** — prefer small, reviewable PRs.

## Code of conduct

Be respectful and constructive. Assume good faith. Focus on technical merits and the project’s constraints.

Full policy: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Reports: **ahmetburakbicer@gmail.com**.

Security reports (wrong primality that could be abused, RCE, leaked secrets): [SECURITY.md](SECURITY.md) — not a public issue.

## Questions?

Open an issue with the [issue templates](.github/ISSUE_TEMPLATE/) (bug, feature, or question). Pull requests should use [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md). If you are unsure whether an approach fits the restrictions, ask before investing in a large PR.
