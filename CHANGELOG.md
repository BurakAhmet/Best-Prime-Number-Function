# Changelog

All notable changes to this project are documented in this file.

## [1.6.0] — 2026-08-10

### Added
- **`next_prime(n, k=1, *, parallel=True) -> int`** in a new module [`next_prime.py`](next_prime.py): the `k`-th prime *strictly greater than* `n` (`k=1` is the successor).
  - Same input contract as `is_prime` (`int` or decimal `str`; rejects `bool` / negatives). `k` is a positive `int`.
  - Tiny \(n\): one Eratosthenes table through \(10\,007\) and a bisect (no NumPy/Numba).
  - Large `k` with practical \(\sqrt{\text{bound}}\): our own interval sieve.
  - Otherwise: **30030-wheel** candidates, a 17…1021 prefilter, then the existing `is_prime` engines (OpenMP C / stdlib wheel / Numba / AKS).
  - Fully deterministic; no Miller–Rabin; no prime libraries as the engine.
- Console script **`next-prime`**. Also importable as `best_prime.next_prime` and lazily as `is_prime.next_prime`.

### Tests
- New `tests/test_next_prime.py`: exhaustive naive match on \(0\ldots4999\), `k`-th successor, API contract, wheel alignment, mid-size twins / 12-digit minimality, Hypothesis (derandomized), CLI.

## [1.5.0] — 2026-08-08

### Changed
- **Huge \(n\)** (beyond practical full trial): 30030-wheel factor scan to \(10^8\) (was an odd loop to \(5\cdot10^7\)), then a faster exact **AKS**:
  - Kronecker substitution (Python long-int) instead of \(O(r^2)\) schoolbook poly mul
  - prime \(r\) only; skip when \(r-1\le(\log_2 n)^2\)
  - perfect-power: squares + odd exponents only
  - optional threaded witness loop (`parallel=True`)
- Still fully deterministic; AKS remains the final engine (no Miller–Rabin). Huge **primes** can still take a long time; huge **composites** with a factor \(\le 10^8\) return quickly.

### Tests
- New `tests/test_aks.py`: perfect powers, Kronecker mul vs schoolbook, AKS vs `is_prime` on \(0\ldots399\), Carmichael/Poulet, huge pre-AKS composites.

## [1.4.4] — 2026-08-08

### Changed
- Hard-path prime extract: scan **8 wheel-30 bytes per `ctzll`** instead of one byte per loop. Same exact prime-only trial; u64 wrap-mul and u128 `%` unchanged.

### Performance (indicative vs 1.4.3, 12 OpenMP threads)
- Largest prime $<2^{64}$ (CLI default): ~**381 ms → ~303 ms** (~**20%**).
- Near $2^{63}$ / M61 / large semiprime: ~**20–29%** faster in-process.
- Default mid-size e2e suite: unchanged class.

## [1.4.3] — 2026-08-08

### Changed
- CLI default $n$ is now **`18446744073709551557`** (largest prime $<2^{64}$), the hardest 64-bit yardstick. `DEFAULT_N` is exported from `is_prime` / `best_prime`.
- Hard-path sieve: **memcpy presieve** of $7\cdot11\cdot13\cdot17$ (17017-byte repeating wheel-30 bitmap) plus **32-bit mark starts**. Same exact prime-only trial.

### Tests
- Shared `tests/numbers.py` + `conftest.py`; new `test_cli.py`, `test_lab.py`, `test_determinism.py`.
- Exhaustive naive match extended through $9999$; more Carmichael / Poulet / Fermat specimens; Hypothesis products/squares/evens/string parity; threaded small-n determinism; `lab()` contract.
- Hard 64-bit serial==parallel moved under `@pytest.mark.slow`. CI determinism script covers more mid-size / composite / MR-liar cases without evaluating the 64-bit default (too slow).

### Performance (indicative vs 1.4.2, 12 OpenMP threads)
- Largest prime $<2^{64}$: ~**425 ms → ~397 ms** (~**7%**).
- Near $2^{63}$ / M61 / large semiprime: ~**5–9%** faster in-process.
- Default mid-size e2e suite: unchanged class.

## [1.4.2] — 2026-08-08

### Changed
- Hard 64-bit OpenMP path: **8-way 2-adic wrap-mul trial** of sieved primes instead of `DIV`. Odd $p$ divides $n&lt;2^{64}$ iff $(n\cdot p^{-1}\bmod 2^{64})\cdot p&lt;2^{64}$. Inverse lifted from a 128-byte table (`INV8`) by three Newton steps. Mid-size precomputed `PRE_INV`/`PRE_TH` path unchanged. u128 trial still uses limb `DIV`.

### Performance (indicative, same machine as 1.4.1, 12 OpenMP threads)
- Near $2^{63}$ prime in-process ~**340 ms → ~281 ms** (~**17%**); e2e ~**0.29 s**.
- M61 in-process ~**168 ms → ~143 ms** (~**15%**); e2e ~**0.16 s**.
- Largest prime $<2^{64}$ in-process ~**0.41 s** (was ~0.50 s class).
- Default mid-size e2e suite: unchanged class (still precomputed-prime path).

## [1.4.1] — 2026-08-07

### Changed
- Hard 64-bit / u128 OpenMP path: **wheel-30 segmented sieve** (1 byte per 30 numbers; residues $1,7,11,13,17,19,23,29$) instead of an odds-only byte/bit sieve. Marks only numbers coprime to $2\cdot3\cdot5$; 8-way prime trial unchanged. 4-way stride unroll on small-prime marking is bounds-checked.
- Adaptive wheel-30 segment: 64–256 KiB (256 KiB when $\lfloor\sqrt{n}\rfloor \ge 5\cdot10^8$).

### Performance (indicative, same machine as 1.4.0)
- **M61** in-process ~**0.27 s → ~0.15 s**; e2e 12-thread ~**0.17 s**.
- **Near $2^{63}$ prime** in-process ~**0.56 s → ~0.30 s**; e2e 12-thread ~**0.32 s** (~**45%** faster).
- 2-thread e2e: M61 ~1.0 s → ~0.60 s; near $2^{63}$ ~1.9 s → ~1.16 s.
- Default mid-size e2e suite: unchanged (still precomputed-prime path).

## [1.4.0] — 2026-08-07

### Changed
- OpenMP C core: **precomputed odd primes ≤ 2²⁰** with exact **2-adic inverse / threshold** trial (wrap-mul, no `DIV`) for `isqrt(n) ≤ 1 048 576`. Mid-size primes no longer sieve or walk the dense 9699690-wheel.
- Drop the 1.6 MB 9699690-wheel table from `wheel_core.c` (stdlib / Numba fallbacks still use on-disk wheel assets).
- Harder 64-bit / u128 path: trial the precomputed table first, then **segmented prime sieve** from 2²⁰ with **8-way DIV** ILP. Parallel OpenMP only when `isqrt(n) ≥ 10⁷` (avoids thread overhead that previously *slowed* 12-digit checks on many cores).
- Restriction linter: allow `docs/ALGORITHM_HISTORY.md` to mention banned engines in prose.

### Performance (indicative, same machine class as 1.3.2)
- **12-digit prime** e2e CLI `TIME`: ~**45%** faster vs committed 1.3.2 snapshot (~4.4 ms → ~2.4 ms); in-process check ~**10×** faster.
- Default e2e suite (`10⁹+7`, `10⁹+9`, M31): slightly faster (import-bound; no regression).
- 12-digit e2e no longer blows up with `OMP_NUM_THREADS=12` (was ~2–3× slower than 2 threads).
- Hard primes (M61 / near 2⁶³): same performance class.

## [1.3.2] — 2026-08-04

### Changed
- OpenMP C core: **lower segmented-prime threshold** (`isqrt(n) ≥ 2·10⁵` instead of `2·10⁸`) so mid-size primes (e.g. 12-digit) use prime-only trial instead of the denser 9699690-wheel.
- **Bit-packed** odd segmented sieve for moderate $\sqrt{n}$; **byte sieve** retained for hard 64-bit primes (best measured tradeoff).
- Adaptive segment size; **8-way** independent-mod ILP on the wheel hot path (was 4-way).
- Expanded deterministic small-prime precheck (through 271).
- Build: enable **LTO** (`-flto`) in `scripts/compile_wheel_core.sh`.

### Performance (indicative, same machine class)
- **12-digit prime** e2e CLI `TIME`: ~**4×–7×** faster vs 1.3.1 (segmented primes + bit sieve).
- Hard primes (M61 / near $2^{63}$): roughly **unchanged to slightly faster** in-process; e2e within noise.
- Default e2e suite: large win on the 12-digit case; no regressions on smaller cases.

## [1.3.1] — 2026-07-01

### Added
- **Installable library packaging**: `pip install -e .` / `pip install git+https://…` with console scripts `is-prime` and `best-prime`.
- Friendly import package `best_prime` (re-exports `is_prime`, `lab`, `__version__`).
- Optional **native OpenMP build during install** via `setup.py` (skips cleanly if no compiler).
- `examples/basic_usage.py` and README **Install as a Python library** section.

### Changed
- Wheels no longer embed a prebuilt Linux-only `wheel_core.so` as `py3-none-any`; the core is compiled at install when possible.

## [1.3.0] — 2026-07-01

### Added
- **65–128-bit full trial** via OpenMP C `is_prime_u128_core` (limbs `lo`/`hi`): same deterministic wheel / segmented-prime engines as the 64-bit path, no AKS for practical sizes (`isqrt(n) ≤ 2.5·10¹⁰`, e.g. primes near $10^{20}$).
- `lab()` paths `u128_wheel_c` and `bigint_wheel` (stdlib wheel fallback without the `.so` symbol).

### Changed
- Big-int path no longer jumps to AKS after a tiny factor scan when full trial is practical; AKS remains only for huge inputs.

## [1.2.0] — 2026-07-01

### Changed
- Hard 64-bit path (`isqrt(n) ≥ 2·10⁸`): **parallel segmented sieve + prime-only trial division** in OpenMP C (still fully deterministic; sieve implemented in-tree — no external prime engines, no stochastic tests).
- Moderate 64-bit path unchanged in spirit (9699690-wheel with 4-way mod ILP); small-prime precheck extended through 113.
- Regenerated `is_prime_data/wheel_core.c` / `wheel_core.so` via `scripts/generate_wheel_core_c.py`.

### Performance (indicative, same class of machine)
- Near $2^{63}$ prime and Mersenne M61: roughly **12–20%** faster end-to-end / in-process vs 1.1.1 wheel-only parallel trial.
- Moderate e2e suite (`compare_e2e.py` cases through 12-digit): no regression vs prior baseline (within noise / slightly faster on several cases).

## [1.1.1] — 2026-07-01

### Changed
- Faster OpenMP C `9699690`-wheel hot path: **4-way independent trial mods** so out-of-order CPUs can overlap `DIV` latency (still exact wheel trial division to $\lfloor\sqrt{n}\rfloor$).
- Integer `isqrt` in `wheel_core` (no libm in the hot path); slightly extended deterministic small-prime precheck (through 97).
- OpenMP early-abort via shared `found` for composites; compile with `-march=native` (fallback `x86-64-v2`), `-funroll-loops`, and correct `-lm` link order.
- Regenerated `is_prime_data/wheel_core.c` / `wheel_core.so`; refreshed `benchmarks/e2e_results.json` and performance docs.

### Performance (indicative e2e CLI `TIME`, same machine as prior snapshot)
- Near $2^{63}$ prime: ~7% faster; 12-digit prime: ~9% faster; overall default e2e suite ~6% faster. Still fully deterministic; no MR / prime-lib engines.

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
