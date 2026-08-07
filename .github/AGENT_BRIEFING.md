# Briefing for automated agents (issues & PRs)

Copy or attach this context when triaging **Best-Prime-Number-Function**.

**Repo:** deterministic `is_prime` (OpenMP C precomputed-prime + segmented sieve; stdlib/Numba wheels as fallback; full trial for practical multi-limb sizes; AKS only for huge ints).  
**Forbidden:** stochastic Miller–Rabin, prime sieving libraries as engine, non-deterministic results.  
**Required:** respect CONTRIBUTING.md and README “Design restrictions” / “Supported platforms”.  
**CI gates:** build `wheel_core.so`, restriction linter, wiki sync, pytest not slow, Linux `lab(n)["path"]=="u64_wheel_c"` for 64-bit, **e2e** perf vs base, Determinism.  
**Paths:** `u64_wheel_c` / `u128_wheel_c` (OpenMP), `python_wheel`, `bigint_wheel`, `bigint_trial_or_aks`.  
**Primary speed metric:** end-to-end CLI `TIME` (`benchmarks/compare_e2e.py`), not in-process hot loop alone.  
**Algorithm history:** before changing engines/thresholds, read [`docs/ALGORITHM_HISTORY.md`](../docs/ALGORITHM_HISTORY.md) (past eras, tradeoffs, **failures not to repeat**). Update that file when you ship a meaningful engine change.  
**Authorship:** repository largely designed by an AI agent; encourage human review.

When implementing fixes: add tests (include `tests/test_c_core.py` if touching native code), keep determinism, run the developer loop in README/CONTRIBUTING.
