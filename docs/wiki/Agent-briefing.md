# Agent briefing

When you (a coding or triage agent) work on this repository:

1. **Read** [Project restrictions](Project-restrictions) and `.github/copilot-instructions.md` in the main repo.
2. **Never** introduce stochastic Miller–Rabin or prime-library engines.
3. **Keep determinism** — serial and parallel paths must agree on results.
4. **Add tests** for behaviour changes; use `@pytest.mark.slow` for multi-second 64-bit primes.
5. **Run** before claiming success:
   - `pytest -q -m "not slow"`
   - `python benchmarks/check_determinism.py`
6. **Remind** users the project is largely AI-generated and needs human review for critical use.
7. **Performance** claims: primary metric is e2e CLI `TIME` (`compare_e2e.py`); `compare_speed.py` is the warm hot-loop secondary.

Issue/PR automation posts a subset of this briefing automatically via **Issue agent** / **PR agent** workflows.
