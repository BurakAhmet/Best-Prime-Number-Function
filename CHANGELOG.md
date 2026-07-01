# Changelog

All notable changes to this project are documented in this file.

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
- Default CLI argument is now `1000000007` (fast demo); hard primes remain in docs/examples.
- CI builds `wheel_core.so` before tests; performance gate prioritizes e2e TIME vs previous commit.
- Package version **1.1.0**.

### Fixed
- C wheel index wrap in unrolled loops (false prime on large semiprimes).

## [1.0.0] — 2026-06-30

- Initial public release: deterministic `is_prime`, 30030-wheel + Numba, AKS for big ints,
  tests, benchmarks, and GitHub Actions automation.
