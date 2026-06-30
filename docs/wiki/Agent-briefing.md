# Agent briefing

When an automated agent handles issues or PRs in this repository:

1. Load restrictions from **Project restrictions** and `.github/copilot-instructions.md`.
2. Do not introduce stochastic primality tests.
3. Prefer adding tests for any behaviour change.
4. Run `pytest -q -m "not slow"` and `python benchmarks/check_determinism.py` before claiming success.
5. Remind users the repo is largely AI-generated and needs human review for critical use.
