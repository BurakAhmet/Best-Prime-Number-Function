# Contributing

Thanks for your interest in improving **Best-Prime-Number-Function**. Contributions of all kinds are welcome—bug reports, tests, docs, benchmarks, and carefully reviewed code changes.

## Before you start

Please read the [README](README.md), especially **Design restrictions**. This project optimizes under hard constraints:

- Results must stay **fully deterministic** (no randomness).
- **No stochastic Miller–Rabin** or “probably prime” shortcuts.
- **No** external prime libraries (e.g. primesieve) as the engine.
- NumPy / Numba are allowed for speed of *our* algorithms only.

PRs that violate those rules will not be merged, even if they look faster on paper.

> This repository was **created and designed by an AI agent**. Human review of contributions (and of the existing code) is encouraged.

## Ways to contribute

| Area | Ideas |
|------|--------|
| **Correctness** | Edge cases, big integers, property tests, more known primes/composites |
| **Performance** | Wheel tweaks, Numba improvements, fairer benchmarks—without changing the math model |
| **Docs** | Clearer explanations, translations, examples |
| **CI / tooling** | Workflows, packaging, typing |
| **Issues** | Repros for bugs, ideas that respect the restrictions above |

## Development setup

```bash
git clone https://github.com/BurakAhmet/Best-Prime-Number-Function.git
cd Best-Prime-Number-Function
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt pytest
```

### Tests

```bash
# Default CI suite (skip multi-second 64-bit primes)
pytest -q -m "not slow"

# Full suite
pytest -q
```

### Benchmarks (optional)

```bash
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py
NUMBA_NUM_THREADS=2 python benchmarks/compare_speed.py --json /tmp/cand.json
python benchmarks/check_regression.py \
  --baseline benchmarks/baseline.json \
  --candidate /tmp/cand.json
```

### Determinism check (same idea as CI)

```bash
NUMBA_NUM_THREADS=2 python benchmarks/check_determinism.py
```

## Pull request checklist

1. **Restrictions** — change stays deterministic; no MR / prime libs.
2. **Tests** — add or update tests for new behaviour; `pytest -m "not slow"` passes.
3. **Speed** — if you touch the hot path, run benchmarks; avoid regressions CI would flag.
4. **Docs** — update README / benchmarks notes if behaviour or flags change.
5. **Scope** — prefer small, reviewable PRs.

## Code of conduct (short)

Be respectful and constructive. Assume good faith. Focus on technical merits and the project’s constraints.

## Questions?

Open an issue describing your idea or bug. If you are unsure whether an approach fits the restrictions, ask before investing in a large PR—we would rather discuss early.
