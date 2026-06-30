# Contributing

We welcome contributions—bugs, tests, docs, benchmarks, and features that respect **determinism restrictions**.

Full guide in the repo: [CONTRIBUTING.md](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/CONTRIBUTING.md)

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
