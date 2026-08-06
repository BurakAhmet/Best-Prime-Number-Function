# Algorithm & performance history

**Purpose.** Keep a durable record of every primality *engine* this project has used, why it was chosen, what it cost, and what went wrong — so future contributors (humans and agents) improve without replaying past mistakes.

| | |
|--|--|
| **Current package version** | **1.3.2** (`pyproject.toml`) |
| **Primary metric** | End-to-end CLI **`TIME`** (import → answer), not warm hot-loop only |
| **Secondary metric** | In-process `is_prime()` after engines are warm (`benchmarks/compare_speed.py`) |
| **Correctness model** | Fully **deterministic** for all natural numbers (see restrictions) |
| **Living code map** | [`docs/wiki/Algorithm-overview.md`](wiki/Algorithm-overview.md) |
| **Changelog** | [`CHANGELOG.md`](../CHANGELOG.md) (release notes; this file is the design narrative) |

**How to extend this file.** On any meaningful engine or threshold change: add a new **era** section (version + date + key commit), fill advantages/disadvantages, paste indicative numbers from `benchmarks/compare_e2e.py` / Hall of fame, and append a row to the summary table. If something regressed or was reverted, add it under **Failures & anti-patterns**.

---

## Non-negotiable constraints (every era)

These bound every algorithm below; “faster” ideas that violate them are out of scope for the library engine:

1. **Deterministic** — same input ⇒ same output; no RNG.
2. **No stochastic Miller–Rabin** — no random-base “probably prime” as the engine.
3. **No external prime libraries** as the implementation (e.g. primesieve, `sympy.isprime` as the engine).
4. **Allowed accelerators** — NumPy / Numba; in-tree OpenMP C (`wheel_core.so`); pure Python fallbacks.
5. **All natural numbers** — `int` or decimal `str`; big integers included.

*Benchmark-only* comparisons to fixed-base Miller–Rabin (e.g. optional scripts) are fine for education; they must not become the product path without an explicit, documented correctness contract.

---

## Metrics glossary

| Metric | Script / surface | Includes |
|--------|------------------|----------|
| **E2E CLI `TIME`** | `python is_prime.py …` / `benchmarks/compare_e2e.py` | Import, table load, native load/JIT, check |
| **Hot-loop ms** | `lab(n)["elapsed_ms"]`, `compare_speed.py` | Check only, after warm-up |
| **`lab(n)["path"]`** | API | Which engine ran (`python_small`, `python_wheel`, `u64_wheel_c`, …) |

**Rule of thumb learned in v1.1.0:** optimizing only warm Numba loops can *hurt* end-to-end CLI time (import + JIT dominate). Prefer the tier that wins **E2E** for each size class.

Indicative numbers below are **machine-dependent** (CPU, core count, `OMP_NUM_THREADS`, whether `.so` built). Treat them as order-of-magnitude and relative rankings, not absolute SLAs. Authoritative artifacts for a given commit: CI performance gate + `benchmarks/e2e_results.json` + Hall of fame.

---

## Timeline (high level)

```text
2026-06-30  v1.0.0   Numba 30030-wheel (64-bit) + AKS for big ints
2026-07-01  v1.1.0   Tiered E2E engines: embedded 30030 + OpenMP C 9699690 + Numba fallback
2026-07-01  v1.1.1   4-way mod ILP, integer isqrt, early abort (OpenMP wheel)
2026-07-01  v1.2.0   Segmented sieve + prime-only trial for hard 64-bit (√n ≥ 2·10⁸)
2026-07-01  v1.3.0   OpenMP u128 full trial for practical multi-limb (≤ ~10²⁰); AKS only for huge
2026-07-01  v1.3.1   Installable library; compile .so at install (no prebuilt Linux .so in pure wheel)
2026-08-04  v1.3.2   Earlier segmented path (√n ≥ 2·10⁵), bit sieve, 8-way ILP, LTO  ← current
```

Key commits (algorithm/perf only):

| Version | Representative commit |
|---------|------------------------|
| 1.0.0 | `fb7e59f` Initial release: deterministic is_prime with Numba wheel trial division |
| 1.1.0 | `e376602` / `813abf0` Tiered engines + e2e gate + C tests |
| 1.1.1 | `94d73df` 4-way independent trial mods |
| 1.2.0 | `bc0867c` Hybrid segmented-prime trial for hard 64-bit n |
| 1.3.0 | `d1c700b` OpenMP u128 full trial |
| 1.3.1 | `57d855e` Installable `best_prime` package |
| 1.3.2 | `22ba10d` Earlier segmented path + bit sieve + 8-way ILP |

---

## Era 0 — Baseline (not shipped as product, still used in benches)

### Primitive odd trial division

**Design.** Reject even \(n > 2\); trial-divide by every odd \(i\) with \(3 \le i \le \lfloor\sqrt{n}\rfloor\).

| | |
|--|--|
| **Where** | `benchmarks/compare_speed.py` “Primitive” column |
| **Complexity** | \(\Theta(\sqrt{n})\) divisions in pure Python |
| **Advantages** | Trivially correct; good lower-bound baseline; no tables or compilers |
| **Disadvantages** | Unusable for hard 64-bit primes (\(\sim 10^9\) Python iterations → minutes+) |
| **Keep?** | Yes, as a **benchmark reference only** |

---

## Era 1 — v1.0.0 (2026-06-30): Numba 30030-wheel + AKS

**Design.**

- **\(n < 2^{64}\):** Hardcoded **30030-wheel** (candidates coprime to \(2\cdot3\cdot5\cdot7\cdot11\cdot13\)), Numba JIT, optional multi-threaded `prange` for large \(\sqrt{n}\). Hardware `sqrt` + integer correction for `isqrt`.
- **\(n \ge 2^{64}\):** Small-factor trial, then **AKS** if not finished to \(\sqrt{n}\).

**Performance (order of magnitude, warm Numba).**

- vs primitive on \(10^9+7\): tens of× faster (see early `benchmarks/README` samples).
- Hard 64-bit primes: feasible with threads, but **import + JIT** cost was large for one-shot CLI.

| | |
|--|--|
| **Advantages** | Fully deterministic; simple mental model; one fast path for all 64-bit; pure Python install (Numba wheels) |
| **Disadvantages** | E2E CLI dominated by NumPy/Numba import/JIT; wheel denser than prime-only trial for huge \(\sqrt{n}\); AKS after tiny factor scan for any multi-limb \(n\) (too eager); 30030 denser than larger primorial wheels |
| **Failures / lessons** | Measuring only warm loops misled “is it fast?” for CLI users → drove v1.1.0 E2E focus |

---

## Era 2 — v1.1.0 (2026-07-01): Tiered engines for **end-to-end** TIME

**Design.** Explicit size tiers to minimize **import → answer**:

| Band | Engine | Rationale |
|------|--------|-----------|
| \(n < 10^4\) | Pure-Python small loop | Avoid tables/JIT entirely |
| \(n \le 4\cdot10^{12}\) without C core | **Embedded zlib 30030-wheel** (stdlib) | ~µs decompress; no NumPy |
| Hard 64-bit with `.so` | **OpenMP C** `9699690`-wheel | Skip Numba JIT for CLI |
| Hard 64-bit without `.so` | Lazy **Numba 9699690-wheel** | Fallback when no compiler |
| Big int | Partial trial → **AKS** | Still the huge path |

Also: precomputed assets under `is_prime_data/`, `compare_e2e.py`, CI e2e regression gate, C-path tests.

**Performance.**

- Small/moderate CLI cases: sub-ms to few ms without waiting on Numba.
- Hard 64-bit (with `.so`): sub-second multi-core class on laptop-class machines (see Hall of fame).

| | |
|--|--|
| **Advantages** | E2E-aware; works without Numba for many moderate \(n\); OpenMP path is stable and parallel; CI enforces no silent E2E regressions |
| **Disadvantages** | More code paths ⇒ more testing surface; needs `gcc`+OpenMP for best hard 64-bit; large wheel tables on disk |
| **Failures / lessons** | **C wheel index wrap** in unrolled loops → false prime on large **semiprimes** (fixed in 1.1.0). Always test composites that survive small-prime precheck. Unrolled wheel code must wrap the step index correctly. |

---

## Era 3 — v1.1.1 (2026-07-01): Micro-opts on OpenMP wheel

**Design changes.**

- **4-way independent trial mods** on the 9699690-wheel hot path (hide `DIV` latency on OoO CPUs).
- Integer `isqrt` in C (no libm in hot path).
- Small-prime precheck through 97; OpenMP shared `found` early abort; `-march=native` / `-funroll-loops`.

**Performance (same machine class as prior snapshot).**

- Near-\(2^{63}\) prime E2E: ~**7%** faster  
- 12-digit prime: ~**9%** faster  
- Default e2e suite: ~**6%** faster  

| | |
|--|--|
| **Advantages** | Pure engineering win; same correctness model; composites abort earlier |
| **Disadvantages** | More fragile C; still \(\Theta(\sqrt{n}/w)\) wheel work — asymptotic limit unchanged |
| **Failures / lessons** | Micro-opts help but do not replace better **candidate density** (primes vs wheel) for hard primes |

---

## Era 4 — v1.2.0 (2026-07-01): Segmented primes for hard 64-bit

**Design.** When \(\lfloor\sqrt{n}\rfloor \ge 2\cdot10^8\) (hard 64-bit class):

1. Parallel **segmented sieve** of odds up to \(\sqrt{n}\) (in-tree; not primesieve).
2. **Prime-only** trial division of \(n\) by those primes.

Moderate path kept the 9699690-wheel (4-way ILP). Precheck extended through 113.

**Performance.**

- Near-\(2^{63}\) and M61: roughly **12–20%** faster E2E / in-process vs 1.1.1 wheel-only parallel trial.
- Moderate suite (through 12-digit): no regression (within noise).

| | |
|--|--|
| **Advantages** | Fewer mods than a dense wheel when \(\sqrt{n}\) is huge; still fully deterministic; sieve is ours (restriction-safe) |
| **Disadvantages** | Sieve memory/time overhead; threshold \(2\cdot10^8\) left mid-size primes (e.g. 12-digit) on denser wheel longer than necessary (addressed in 1.3.2) |
| **Failures / lessons** | Hybrid thresholds must be **measured** across the suite, not only at the hardest primes |

---

## Era 5 — v1.3.0 (2026-07-01): Practical multi-limb full trial (u128)

**Design.**

- New OpenMP entry **`is_prime_u128_core(lo, hi)`** for \(2^{64} \le n < 2^{128}\) with \(\lfloor\sqrt{n}\rfloor \le 2.5\cdot10^{10}\) (e.g. primes near \(10^{20}\)): same wheel / segmented engines as u64, **no AKS**.
- Stdlib **`bigint_wheel`** fallback without `.so`.
- AKS only when full trial is no longer practical.

| | |
|--|--|
| **Advantages** | Huge correctness + UX win: multi-limb primes no longer fall into slow AKS after a token factor scan; reuses proven 64-bit engines |
| **Disadvantages** | Limb arithmetic complexity; still trial-division asymptotics (not poly-time like AKS in theory, but AKS constants are worse in practice here) |
| **Failures / lessons** | **Too-early AKS** for moderate big ints was a design failure of the 1.0 large path — never jump to AKS while \(\sqrt{n}\) is still in “seconds, not hours” trial range |

---

## Era 6 — v1.3.1 (2026-07-01): Packaging (performance-adjacent)

Not a new math engine, but it changed what users actually run:

- `pip install` / `best_prime` import; console scripts `is-prime` / `best-prime`.
- Build `wheel_core.so` **at install** when a compiler exists; **do not** ship a Linux-only `.so` inside a pure `py3-none-any` wheel.

| | |
|--|--|
| **Advantages** | Portable wheels; honest platform story |
| **Disadvantages** | Users without a compiler fall back to Numba/stdlib (slower hard 64-bit) |
| **Failures / lessons** | Shipping a prebuilt `.so` in a pure wheel **looked** convenient and **broke** portability / packaging honesty — regenerate/build native code on the target, or use platform wheels |

---

## Era 7 — v1.3.2 (2026-08-04): **Current** — earlier segmented path + denser ILP

**Design (current production stack).**

```text
is_prime(n)
  n < 10⁴              → pure-Python small loop
  10⁴ ≤ n < 2⁶⁴
       ├─ wheel_core.so → OpenMP C:
       │     small-prime precheck (through 271)
       │     if isqrt(n) ≥ 2·10⁵ → segmented primes + prime-only trial
       │        (bit-packed odd sieve for moderate √n; byte sieve for hard 64-bit)
       │     else → 9699690-wheel with 8-way independent-mod ILP
       ├─ else n ≤ 4·10¹² → embedded 30030-wheel (stdlib)
       └─ else → Numba 9699690-wheel
  n ≥ 2⁶⁴
       ├─ isqrt(n) ≤ 2.5·10¹⁰ and ≤128-bit → u128 OpenMP full trial / stdlib wheel
       └─ larger → partial trial → AKS if needed
```

**Also:** adaptive segment size; LTO (`-flto`) in `scripts/compile_wheel_core.sh`.

**Performance (indicative, same machine class as 1.3.1).**

| Case | Order of E2E CLI `TIME` (OpenMP `.so`, multi-core) |
|------|------------------------------------------------------|
| Tiny primes (97, 7919) | ~0.4 ms |
| \(10^9+7\), M31 | ~2–3 ms |
| 12-digit prime `999999999989` | ~4–10 ms (**~4×–7×** faster than 1.3.1) |
| M61 | ~0.27–0.35 s |
| near \(2^{63}\) prime | ~0.55–0.65 s |

Committed default e2e suite snapshot (`benchmarks/e2e_results.json`): 12-digit ~**4.43 ms** on the machine that last refreshed the file.

| | |
|--|--|
| **Advantages** | Mid-size primes finally use prime-only trial; bit sieve wins measured tradeoff for moderate \(\sqrt{n}\); 8-way ILP extracts more wheel ILP; LTO free win at link |
| **Disadvantages** | Thresholds and sieve layout are empirical — new CPUs may want retuning; more branches in C; hard primes still \(\sim\sqrt{n}\) work (not MR-fast) |
| **Still true** | Deterministic fixed-base MR would crush hard 64-bit **latency** but is only proven on bounded ranges — out of product policy unless an explicit range-limited mode is added |

---

## Summary comparison

| Era | 64-bit engine (best case) | Big-int practical | Big-int huge | E2E focus | Main win | Main cost / risk |
|-----|---------------------------|-------------------|--------------|-----------|----------|------------------|
| Primitive (bench) | Odd trial Python | — | — | No | Simplicity | Too slow |
| **1.0** | Numba 30030-wheel | Tiny trial → AKS | AKS | Weak | One Numba path | JIT/import; eager AKS |
| **1.1.0** | OpenMP 9699690 + tiers | (same large path) | AKS | **Yes** | E2E tiers + C | Path complexity; wheel-wrap bug class |
| **1.1.1** | + 4-way ILP | | | Yes | ~6–9% E2E | Micro only |
| **1.2.0** | + seg-primes if \(\sqrt{n}\ge 2\cdot10^8\) | | | Yes | 12–20% hard primes | Threshold too high for mid-size |
| **1.3.0** | same | **u128 full trial** | AKS | Yes | Avoid AKS for \(\sim10^{20}\) | Limb code |
| **1.3.1** | same (build at install) | same | AKS | Yes | Portable packaging | No compiler ⇒ slower |
| **1.3.2 (now)** | seg-primes if \(\sqrt{n}\ge 2\cdot10^5\); 8-way; bit sieve | same | AKS | Yes | Mid-size 4–7× | Empirical knobs |

---

## Failures & anti-patterns (do not repeat)

Recorded so agents and humans do not “rediscover” them:

| ID | What happened | Why it hurt | Mitigation / policy |
|----|---------------|-------------|---------------------|
| **F1** | Optimize **warm Numba** only | CLI felt slow (import/JIT) | Optimize and gate on **E2E `TIME`** (`compare_e2e.py`) |
| **F2** | **Wheel index wrap** bug in unrolled C loops | **False primes** on large semiprimes | Matrix of semiprimes in `tests/test_c_core.py`; treat unrolled wheel code as high risk |
| **F3** | **AKS too early** for multi-limb with practical \(\sqrt{n}\) | Correct but unusable latency | Full trial up to `_MAX_FULL_TRIAL_ISQRT`; AKS only beyond |
| **F4** | Prebuilt **Linux `.so` in pure wheel** | Broken/ misleading installs on other platforms | Build at install or ship **platform wheels** |
| **F5** | Segmented-prime **threshold only tuned on hardest primes** | 12-digit path left on dense wheel | Retune with full e2e suite (1.3.2: \(2\cdot10^5\)) |
| **F6** | Flip default CLI demo to a “fast” \(n\) without updating all docs/agents | Confusion about what CI/demo measures | Prefer documenting both fast demos **and** hard primes; default restored near \(2^{63}\) (`77242d6`) |
| **F7** | Using **external prime sieve libs** or **stochastic MR** for speed | Violates project identity / correctness story | Forbidden as engine; optional bench-only scripts OK if labeled |
| **F8** | Skipping **serial vs parallel** determinism checks | Racey OpenMP bugs | `benchmarks/check_determinism.py` + Determinism workflow |
| **F9** | Changing wheel/sieve without regenerating **committed C / tables** | Drift between generators and shipped artifacts | `generate_wheel_core_c.py` / `generate_wheel_data.py` + compile script |

---

## Decision guide (when changing algorithms)

1. **Does it stay deterministic for all \(n\)?** If only for a range, document the range and keep the full path available.
2. **Does E2E improve** for the size class you care about without regressing the default suite? Run:
   ```bash
   bash scripts/compile_wheel_core.sh
   OMP_NUM_THREADS=2 python benchmarks/compare_e2e.py --json /tmp/e2e.json
   python scripts/check_e2e_regression.py \
     --baseline benchmarks/e2e_results.json --candidate /tmp/e2e.json
   ```
3. **Composites:** especially semiprimes with large factors (not just primes).
4. **Serial == parallel** on C/Numba paths.
5. **Update this file** + `CHANGELOG.md` + wiki Algorithm overview if the dispatch diagram changes.

---

## Related files

| Path | Role |
|------|------|
| `is_prime.py` | Dispatch + Python/Numba/AKS engines |
| `is_prime_data/wheel_core.c` | OpenMP u64/u128 engines (generated + hand-tuned sections) |
| `scripts/generate_wheel_core_c.py` | C generator |
| `scripts/generate_wheel_data.py` | Wheel tables |
| `scripts/compile_wheel_core.sh` | Build `.so` (LTO in 1.3.2+) |
| `benchmarks/compare_e2e.py` | Primary perf metric |
| `benchmarks/compare_speed.py` | Warm in-process + primitive baseline |
| `benchmarks/e2e_results.json` | Committed e2e snapshot |
| `docs/wiki/Hall-of-fame.md` | Notable primes + prime-of-the-day timings |
| `docs/wiki/Project-restrictions.md` | Hard rules |

---

*Last updated for package **1.3.2** (segmented threshold \(2\cdot10^5\), 8-way ILP, bit sieve, u128 full trial, AKS for huge ints). Extend forward; do not delete past eras.*
