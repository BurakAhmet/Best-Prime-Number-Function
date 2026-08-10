---
name: optimize-primes
description: >
  Run one deterministic speed-optimization round on Best-Prime-Number-Function.
  Use when the user says optimize, make it faster, another optimization round,
  or /optimize-primes.
---

# Optimize primes (one round)

You are continuing the Best-Prime-Number-Function engine. Treat this exactly
like the user said **"optimize this"**.

## Non-negotiable

1. Fully **deterministic**. No RNG. Serial == parallel.
2. **No** stochastic Miller–Rabin / “probably prime” as the engine.
3. **No** external prime libs (`primesieve`, `sympy.isprime`) as the engine.
4. Allowed: NumPy/Numba, in-tree OpenMP `wheel_core.so`, stdlib.
5. Primary metric: **end-to-end CLI `TIME`** (`python -m best_prime`, `benchmarks/compare_e2e.py`).
6. Secondary: in-process `lab(n)["elapsed_ms"]` / ctypes on `is_prime_u64_core`.
7. Read `docs/ALGORITHM_HISTORY.md` **Failures & anti-patterns (F1–F13)** before trying ideas. Do not repeat them.
8. One implementation of each module: only under `best_prime/`. No root shims.
9. CLI is `python -m best_prime` and `python -m best_prime.next_prime`.

## Setup

```bash
cd /home/ahmet/Best-Prime-Number-Function
git fetch origin
git checkout main
git pull --ff-only origin main
git checkout -b feat/opt-$(date -u +%Y%m%d-%H%M)
bash scripts/compile_wheel_core.sh
cp is_prime_data/wheel_core.so /tmp/orig_wheel_core.so
```

Record a same-machine baseline (12 threads if available) for:

- `(10**9+7)*(10**9+9)`
- M61 `(1<<61)-1`
- `9223372036854775783`
- `DEFAULT_N` (largest prime `< 2**64`)
- default e2e suite (`compare_e2e.py`, no `--include-hard` unless you also time hard)

Use **interleaved** orig vs candidate `.so` (or orig vs new binary) for hard cases. Do not ship on a single noisy run.

## Hunt

Pick **one** untried idea that does not violate F1–F13. Prefer:

- Hard-path OpenMP sieve/trial (`scripts/generate_wheel_core_c.py` BODY)
- Import / e2e of mid-size CLI (default suite)
- `prime_count` / `next_prime` only if `is_prime` is saturated

Edit the **generator**, then `python3 scripts/generate_wheel_core_c.py && bash scripts/compile_wheel_core.sh`. Do not hand-edit `wheel_core.c` as source of truth.

If an idea loses, is noise, or breaks correctness: revert it and record it under Failures if it is a new anti-pattern.

## Ship only a real win

A win means:

- Answers unchanged (primes still prime; `test_c_core` / determinism green)
- Interleaved A/B shows a clear improvement on at least one hard case **and** no e2e default-suite regression (`check_e2e_regression.py` vs `benchmarks/e2e_results.json`, 25% gate)
- Mid-size path not sacrificed for a hard-only micro-opt (F5, F10, F13)

Then:

1. Update `docs/ALGORITHM_HISTORY.md` (new era or append to current; list rejected ideas).
2. Update `CHANGELOG.md` (Unreleased or version bump if you cut a release).
3. Sync README / `docs/wiki/Algorithm-overview.md` / `docs/guide/engines.md` if dispatch or thresholds changed.
4. `python3 scripts/check_restrictions.py` and `check_wiki_sync.py`.
5. `pytest -q -m "not slow"` (include `tests/test_c_core.py` if you touched C).
6. Commit on the feature branch, push, open a PR against `main`.
7. Do **not** merge, tag, or create a GitHub release unless the user asked in that run.

## GitHub Optimize workflow

`.github/workflows/optimize.yml` now does more than log timings:

1. Baseline comment on the standing Optimization log issue.
2. `python3 scripts/optimize_hunt.py hunt` over the compile-time catalog.
3. On a catalog win: apply knobs, open `optimize/auto-*` PR (`optimize/candidate`).
4. Open `[Optimize] daily YYYY-MM-DD` and assign **Copilot** (secret
   `COPILOT_ASSIGN_TOKEN`) for a *real* engine idea beyond the catalog.
5. `optimize-examine.yml` A/B’s `optimize/candidate` PRs (catalog or Copilot)
   and squash-merges **only** if still faster. Generic Auto-merge skips them.

When you hunt locally, skip catalog knobs and skip whatever Copilot already
tried on the open `optimize/round` issue. Prefer ideas that are **not**
TILE_BYTES / TILE_P_MAX / PARALLEL_SEG_MIN unless you have a reason the
GHA 2-thread catalog would miss (e.g. 12-thread-only).

## No win

If nothing beats baseline after a few serious attempts:

- Leave `main` clean (delete the local branch or leave it unpushed).
- Write a short report: what you tried, numbers, why it lost.
- Do not open an empty or “docs only” PR.

## Report

Always end with: baseline vs candidate numbers, what shipped or why not, and the PR URL if any.
