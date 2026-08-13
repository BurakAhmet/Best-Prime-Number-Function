# Briefing for automated agents (issues & PRs)

Copy or attach this context when triaging **Best-Prime-Number-Function**.

**Repo:** deterministic `is_prime` / `next_prime` (OpenMP C precomputed-prime + segmented sieve; stdlib/Numba wheels as fallback; complete cubic C for $n\ge 2^{64}$ when it can finish, else u128/stdlib trial; AKS only for huge ints).  
**Forbidden:** stochastic Miller–Rabin, prime sieving libraries as engine, non-deterministic results.  
**Required:** respect CONTRIBUTING.md and README “Design restrictions” / “Supported platforms”.  
**CI gates:** build `wheel_core.so`, restriction linter, wiki sync, pytest not slow, Linux `lab(10**9+7)["path"]=="u64_wheel_c"` and hard 64-bit `u64_nm1`/`u64_lehman_c`, **e2e** perf vs base, Determinism.  
**Paths:** `u64_wheel_c` / `u64_nm1` / `u64_lehman_c` / `u128_nm1` / `u128_lehman_c` / `u128_wheel_c` (OpenMP), `python_wheel`, `bigint_wheel`, `bigint_trial_or_aks`.  
**Primary speed metric:** end-to-end CLI `TIME` (`benchmarks/compare_e2e.py`), not in-process hot loop alone.  
**Optimize workflow:** daily catalog hunt of compile-time knobs **and** a Copilot `[Optimize]` issue for a real engine idea. `optimize/candidate` PRs merge only after a same-machine A/B win. Do not rely on generic Auto-merge for those PRs. Secret `COPILOT_ASSIGN_TOKEN` is required to auto-assign Copilot.  
**Algorithm history:** before changing engines/thresholds, read [`docs/ALGORITHM_HISTORY.md`](../docs/ALGORITHM_HISTORY.md) (past eras, tradeoffs, **failures not to repeat**). Update that file when you ship a meaningful engine change.  
**Library docs:** public API / install / CLI live in [`docs/guide/`](../docs/guide/) (MkDocs → Pages `/guide/`). The exhibit lab stays at the Pages root.  
**Authorship:** repository largely designed by an AI agent; encourage human review.

When implementing fixes: add tests (include `tests/test_c_core.py` if touching native code), keep determinism, run the developer loop in README/CONTRIBUTING.
