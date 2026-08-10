## Summary

<!-- What changed and why. Link issues with Fixes #N when applicable. -->

## Restrictions

This project’s engine must stay **fully deterministic** for every natural number.

- [ ] No RNG / non-deterministic APIs on the product path
- [ ] No stochastic Miller–Rabin or “probably prime” engine
- [ ] No external prime libraries (`primesieve`, `sympy.isprime`, …) as the implementation
- [ ] Serial and parallel still agree on results

If this PR changes engines, thresholds, or dispatch, I updated
`docs/ALGORITHM_HISTORY.md` (and did not repeat a listed failure).

## How I verified

- [ ] `python3 scripts/check_restrictions.py`
- [ ] `python3 scripts/check_wiki_sync.py` (if README / wiki facts changed)
- [ ] `pytest -q -m "not slow"`
- [ ] C-path tests if I touched `wheel_core.c` / the generator
- [ ] E2E: `OMP_NUM_THREADS=2 python3 benchmarks/compare_e2e.py --json /tmp/e2e.json`
      then `check_e2e_regression.py` vs `benchmarks/e2e_results.json` (or CI will)

Primary metric is **end-to-end CLI `TIME`**, not warm hot-loop alone.

## Docs

- [ ] README and `docs/wiki/` still agree (`check_wiki_sync.py`)
- [ ] `docs/guide/` (MkDocs `/guide/`) updated if the public API or install story changed
- [ ] Changelog / version bump if this is a user-visible engine or API change

## Notes for reviewers

<!-- Risk, remaining work, machine-specific bench numbers. -->

> This repository is largely AI-designed. Human review of this PR is encouraged.
