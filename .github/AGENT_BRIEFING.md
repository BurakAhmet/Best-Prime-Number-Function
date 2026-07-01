# Briefing for automated agents (issues & PRs)

Copy or attach this context when triaging **Best-Prime-Number-Function**.

**Repo:** deterministic `is_prime` (9699690-wheel + Numba; AKS for big ints).  
**Forbidden:** stochastic Miller–Rabin, prime sieving libraries as engine, non-deterministic results.  
**Required:** respect CONTRIBUTING.md and README “Design restrictions”.  
**CI gates:** `CI` (pytest not slow + performance vs base), `Determinism` (repeated trials).  
**Authorship:** repository largely designed by an AI agent; encourage human review.

When implementing fixes: add tests, keep determinism, run `pytest -m "not slow"`.
