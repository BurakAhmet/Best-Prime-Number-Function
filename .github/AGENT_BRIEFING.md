# Briefing for automated agents (issues & PRs)

Copy or attach this context when triaging **Best-Prime-Number-Function**.

**Repo:** deterministic `is_prime` (tiered wheels; OpenMP C when built; Numba fallback; AKS for big ints).  
**Forbidden:** stochastic Miller–Rabin, prime sieving libraries as engine, non-deterministic results.  
**Required:** respect CONTRIBUTING.md and README “Design restrictions” / “Supported platforms”.  
**CI gates:** build `wheel_core.so`, restriction linter, wiki sync, pytest not slow, Linux `lab(n)["path"]=="u64_wheel_c"`, **e2e** perf vs base, Determinism.  
**Primary speed metric:** end-to-end CLI `TIME` (`benchmarks/compare_e2e.py`), not in-process hot loop alone.  
**Authorship:** repository largely designed by an AI agent; encourage human review.

When implementing fixes: add tests (include `tests/test_c_core.py` if touching native code), keep determinism, run the developer loop in README/CONTRIBUTING.
