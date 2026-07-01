# Changelog

All notable changes to this project are documented in this file.

## [1.2.0] — 2026-07-01

### Changed
- Hard 64-bit path (`isqrt(n) ≥ 2·10⁸`): **parallel segmented sieve + prime-only trial division** in OpenMP C (still fully deterministic; sieve implemented in-tree — no external prime engines, no stochastic tests).
- Moderate 64-bit path unchanged in spirit (9699690-wheel with 4-way mod ILP); small-prime precheck extended through 113.
- Regenerated `is_prime_data/wheel_core.c` / `wheel_core.so` via `scripts/generate_wheel_core_c.py`.

### Performance (indicative, same class of machine)
- Near-\(2^{63}\) prime and Mersenne M61: roughly **12–20%** faster end-to-end / in-process vs 1.1.1 wheel-only parallel trial.
- Moderate e2e suite (`compare_e2e.py` cases through 12-digit): no regression vs prior baseline (within noise / slightly faster on several cases).

## [1.1.1] — 2026-07-01

### Changed
- Faster OpenMP C `9699690`-wheel hot path: **4-way independent trial mods** so out-of-order CPUs can overlap `DIV` latency (still exact wheel trial division to \(\lfloor\sqrt{n}\rfloor\)).
- Integer `isqrt` in `wheel_core` (no libm in the hot path); slightly extended deterministic small-prime precheck (through 97).
- OpenMP early-abort via shared `found` for composites; compile with `-march=native` (fallback `x86-64-v2`), `-funroll-loops`, and correct `-lm` link order.
- Regenerated `is_prime_data/wheel_core.c` / `wheel_core.so`; refreshed `benchmarks/e2e_results.json` and performance docs.

### Performance (indicative e2e CLI `TIME`, same machine as prior snapshot)
- Near-\(2^{63}\) prime: ~7% faster; 12-digit prime: ~9% faster; overall default e2e suite ~6% faster. Still fully deterministic; no MR / prime-lib engines.

## [1.1.0] — 2026-07-01

### Added
- Tiered engines optimizing **end-to-end CLI `TIME`** (import → answer).
- Embedded zlib-compressed **30030-wheel** for stdlib-only moderate inputs.
- Optional **OpenMP C extension** (`is_prime_data/wheel_core.so`) for hard 64-bit primes.
- Precomputed wheel assets under `is_prime_data/` and `scripts/generate_wheel_data.py`.
- `benchmarks/compare_e2e.py` and `scripts/check_e2e_regression.py` for CLI latency gates.
- `scripts/check_wiki_sync.py` to keep `docs/wiki` aligned with README facts.
- C-path tests (`tests/test_c_core.py`): engine path assertion, serial==parallel, semiprime matrix.
- Prime-of-the-day appends `path` + e2e timings to `docs/wiki/Hall-of-fame.md`.
- Supported-platforms note and Linux CI assertion that `lab(n)["path"] == "u64_wheel_c"`.

### Changed
- CI builds `wheel_core.so` before tests; performance gate prioritizes e2e TIME vs previous commit.
- Package version **1.1.0**.
- README/docs examples highlight both fast demos (`1000000007`) and the default hard 64-bit CLI prime.

### Fixed
- C wheel index wrap in unrolled loops (false prime on large semiprimes).

## [1.0.0] — 2026-06-30

- Initial public release: deterministic `is_prime`, 30030-wheel + Numba, AKS for big ints,
  tests, benchmarks, and GitHub Actions automation.
