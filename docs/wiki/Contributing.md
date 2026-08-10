# Contributing

We welcome contributions—bugs, tests, docs, benchmarks, and features that respect **determinism restrictions**.

Full guide in the repo: [CONTRIBUTING.md](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/CONTRIBUTING.md). Public API: [Library guide](https://burakahmet.github.io/Best-Prime-Number-Function/guide/) · [Library reference](Library).

Community standards: [Code of Conduct](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/CODE_OF_CONDUCT.md) · [Security policy](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/SECURITY.md) · [Issue templates](https://github.com/BurakAhmet/Best-Prime-Number-Function/tree/main/.github/ISSUE_TEMPLATE) · [PR template](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/.github/PULL_REQUEST_TEMPLATE.md)

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q -m "not slow"
```

## PR checklist

1. Restrictions still hold (deterministic, no MR, no prime libs).
2. Tests updated; fast suite green.
3. No major performance regression (CI checks vs base).
4. Docs updated if behaviour changes.

Open an issue before large designs if you’re unsure about the restrictions.
