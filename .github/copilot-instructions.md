# Agent instructions — Best-Prime-Number-Function

You are assisting with this repository. Follow these rules strictly.

## Mission

Provide **fully deterministic** primality testing. Optimize for speed only within these constraints.

## Non-negotiable restrictions

1. **Deterministic** — same input ⇒ same output always. No RNG, no randomized algorithms.
2. **No stochastic Miller–Rabin** — no random bases, no “probably prime” APIs as the engine.
3. **No prime libraries** — do not depend on primesieve, sympy.isprime, etc. for the implementation.
4. **Allowed** — NumPy, Numba (JIT / parallel) for *our* trial division / helpers.
5. **Correctness model** — for `n < 2^64`: exact trial division on a 30030-wheel up to `isqrt(n)`. For larger `n`: small-factor trial then AKS if needed (may be slow).

## When answering issues

- Restate whether the request fits the restrictions; refuse or redesign if it asks for probabilistic MR.
- Point to README, CONTRIBUTING.md, and benchmarks for performance claims.
- Prefer concrete repro steps and test ideas over vague advice.
- Reminder: much of this repo was AI-generated; recommend review before production use.

## When changing code or reviewing PRs

- Keep or extend unit tests; do not remove edge-case coverage without replacement.
- Do not break determinism (serial vs parallel must agree on results).
- Do not regress the hot path without measurement (`benchmarks/compare_speed.py`).
- Mark multi-second 64-bit primes with `@pytest.mark.slow` if added to tests.

## Project layout

- `is_prime.py` — library + CLI
- `tests/` — pytest suite
- `benchmarks/` — primitive vs optimized speed, regression, determinism checks
- `.github/workflows/` — CI, determinism, issue/PR agents
