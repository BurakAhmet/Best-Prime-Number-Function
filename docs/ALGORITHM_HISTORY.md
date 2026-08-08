# Algorithm & performance history

**Purpose.** Keep a durable record of every primality *engine* this project has used, why it was chosen, what it cost, and what went wrong — so future contributors (humans and agents) improve without replaying past mistakes.

| | |
|--|--|
| **Current package version** | **1.5.0** (`pyproject.toml`) |
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
2026-08-04  v1.3.2   Earlier segmented path (√n ≥ 2·10⁵), bit sieve, 8-way ILP, LTO
2026-08-07  v1.4.0   Precomputed primes ≤ 2²⁰ + 2-adic mul trial; drop C wheel table
2026-08-07  v1.4.1   Wheel-30 segmented sieve for hard √n (skip 2/3/5 marking)
2026-08-08  v1.4.2   8-way 2-adic wrap-mul trial of sieved primes (no DIV)
2026-08-08  v1.4.3   memcpy presieve 7·11·13·17 + 32-bit mark starts; CLI default = max 64-bit prime
2026-08-08  v1.4.4   uint64 ctzll extract of wheel-30 bits
2026-08-08  v1.5.0   Huge-n: wheel pre-AKS + Kronecker AKS  ← current
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
| 1.4.0 | this tree — precomputed-prime 2-adic trial + deferred OpenMP |
| 1.4.1 | this tree — wheel-30 segmented sieve on the hard path |
| 1.4.2 | this tree — 2-adic wrap-mul trial on sieved primes |

---

## Era 0 — Baseline (not shipped as product, still used in benches)

### Primitive odd trial division

**Design.** Reject even $n \gt 2$; trial-divide by every odd $i$ with $3 \le i \le \lfloor\sqrt{n}\rfloor$.

| | |
|--|--|
| **Where** | `benchmarks/compare_speed.py` “Primitive” column |
| **Complexity** | $\Theta(\sqrt{n})$ divisions in pure Python |
| **Advantages** | Trivially correct; good lower-bound baseline; no tables or compilers |
| **Disadvantages** | Unusable for hard 64-bit primes ($\sim 10^9$ Python iterations → minutes+) |
| **Keep?** | Yes, as a **benchmark reference only** |

---

## Era 1 — v1.0.0 (2026-06-30): Numba 30030-wheel + AKS

**Design.**

- **$n \lt 2^{64}$**: Hardcoded **30030-wheel** (candidates coprime to $2\cdot3\cdot5\cdot7\cdot11\cdot13$), Numba JIT, optional multi-threaded `prange` for large $\sqrt{n}$. Hardware `sqrt` + integer correction for `isqrt`.
- **$n \ge 2^{64}$**: Small-factor trial, then **AKS** if not finished to $\sqrt{n}$.

**Performance (order of magnitude, warm Numba).**

- vs primitive on $10^9+7$: tens of× faster (see early `benchmarks/README` samples).
- Hard 64-bit primes: feasible with threads, but **import + JIT** cost was large for one-shot CLI.

| | |
|--|--|
| **Advantages** | Fully deterministic; simple mental model; one fast path for all 64-bit; pure Python install (Numba wheels) |
| **Disadvantages** | E2E CLI dominated by NumPy/Numba import/JIT; wheel denser than prime-only trial for huge $\sqrt{n}$; AKS after tiny factor scan for any multi-limb $n$ (too eager); 30030 denser than larger primorial wheels |
| **Failures / lessons** | Measuring only warm loops misled “is it fast?” for CLI users → drove v1.1.0 E2E focus |

---

## Era 2 — v1.1.0 (2026-07-01): Tiered engines for **end-to-end** TIME

**Design.** Explicit size tiers to minimize **import → answer**:

| Band | Engine | Rationale |
|------|--------|-----------|
| $n \lt 10^4$ | Pure-Python small loop | Avoid tables/JIT entirely |
| $n \le 4\cdot10^{12}$ without C core | **Embedded zlib 30030-wheel** (stdlib) | ~µs decompress; no NumPy |
| Hard 64-bit with `.so` | **OpenMP C** `9699690`-wheel | Skip Numba JIT for CLI |
| Hard 64-bit without `.so` | Lazy **Numba 9699690-wheel** | Fallback when no compiler |
| Big int | Partial trial → **AKS** | Still the huge path |

Also: precomputed assets under `is_prime_data/`, `compare_e2e.py`, CI e2e regression gate, C-path tests.

**Performance.**

- Small/moderate CLI cases: sub-ms to few ms without waiting on Numba.
- Hard 64-bit (with `.so`): sub-second multi-core class on laptop-class machines (see Hall of fame).

| | |
|--|--|
| **Advantages** | E2E-aware; works without Numba for many moderate $n$; OpenMP path is stable and parallel; CI enforces no silent E2E regressions |
| **Disadvantages** | More code paths ⇒ more testing surface; needs `gcc`+OpenMP for best hard 64-bit; large wheel tables on disk |
| **Failures / lessons** | **C wheel index wrap** in unrolled loops → false prime on large **semiprimes** (fixed in 1.1.0). Always test composites that survive small-prime precheck. Unrolled wheel code must wrap the step index correctly. |

---

## Era 3 — v1.1.1 (2026-07-01): Micro-opts on OpenMP wheel

**Design changes.**

- **4-way independent trial mods** on the 9699690-wheel hot path (hide `DIV` latency on OoO CPUs).
- Integer `isqrt` in C (no libm in hot path).
- Small-prime precheck through 97; OpenMP shared `found` early abort; `-march=native` / `-funroll-loops`.

**Performance (same machine class as prior snapshot).**

- Near $2^{63}$ prime E2E: ~**7%** faster  
- 12-digit prime: ~**9%** faster  
- Default e2e suite: ~**6%** faster  

| | |
|--|--|
| **Advantages** | Pure engineering win; same correctness model; composites abort earlier |
| **Disadvantages** | More fragile C; still $\Theta(\sqrt{n}/w)$ wheel work — asymptotic limit unchanged |
| **Failures / lessons** | Micro-opts help but do not replace better **candidate density** (primes vs wheel) for hard primes |

---

## Era 4 — v1.2.0 (2026-07-01): Segmented primes for hard 64-bit

**Design.** When $\lfloor\sqrt{n}\rfloor \ge 2\cdot10^8$ (hard 64-bit class):

1. Parallel **segmented sieve** of odds up to $\sqrt{n}$ (in-tree; not primesieve).
2. **Prime-only** trial division of $n$ by those primes.

Moderate path kept the 9699690-wheel (4-way ILP). Precheck extended through 113.

**Performance.**

- Near $2^{63}$ and M61: roughly **12–20%** faster E2E / in-process vs 1.1.1 wheel-only parallel trial.
- Moderate suite (through 12-digit): no regression (within noise).

| | |
|--|--|
| **Advantages** | Fewer mods than a dense wheel when $\sqrt{n}$ is huge; still fully deterministic; sieve is ours (restriction-safe) |
| **Disadvantages** | Sieve memory/time overhead; threshold $2\cdot10^8$ left mid-size primes (e.g. 12-digit) on denser wheel longer than necessary (addressed in 1.3.2) |
| **Failures / lessons** | Hybrid thresholds must be **measured** across the suite, not only at the hardest primes |

---

## Era 5 — v1.3.0 (2026-07-01): Practical multi-limb full trial (u128)

**Design.**

- New OpenMP entry **`is_prime_u128_core(lo, hi)`** for $2^{64} \le n \lt 2^{128}$ with $\lfloor\sqrt{n}\rfloor \le 2.5\cdot10^{10}$ (e.g. primes near $10^{20}$): same wheel / segmented engines as u64, **no AKS**.
- Stdlib **`bigint_wheel`** fallback without `.so`.
- AKS only when full trial is no longer practical.

| | |
|--|--|
| **Advantages** | Huge correctness + UX win: multi-limb primes no longer fall into slow AKS after a token factor scan; reuses proven 64-bit engines |
| **Disadvantages** | Limb arithmetic complexity; still trial-division asymptotics (not poly-time like AKS in theory, but AKS constants are worse in practice here) |
| **Failures / lessons** | **Too-early AKS** for moderate big ints was a design failure of the 1.0 large path — never jump to AKS while $\sqrt{n}$ is still in “seconds, not hours” trial range |

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

## Era 7 — v1.3.2 (2026-08-04): earlier segmented path + denser ILP

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
| $10^9+7$, M31 | ~2–3 ms |
| 12-digit prime `999999999989` | ~4–10 ms (**~4×–7×** faster than 1.3.1) |
| M61 | ~0.27–0.35 s |
| near $2^{63}$ prime | ~0.55–0.65 s |

Committed default e2e suite snapshot (`benchmarks/e2e_results.json`): 12-digit ~**4.43 ms** on the machine that last refreshed the file.

| | |
|--|--|
| **Advantages** | Mid-size primes finally use prime-only trial; bit sieve wins measured tradeoff for moderate $\sqrt{n}$; 8-way ILP extracts more wheel ILP; LTO free win at link |
| **Disadvantages** | Thresholds and sieve layout are empirical — new CPUs may want retuning; more branches in C; hard primes still $\sim\sqrt{n}$ work (not MR-fast) |
| **Still true** | Deterministic fixed-base MR would crush hard 64-bit **latency** but is only proven on bounded ranges — out of product policy unless an explicit range-limited mode is added |

---

## Era 8 — v1.4.0 (2026-08-07): precomputed primes + 2-adic trial

**Design (current production stack).**

```text
is_prime(n)
  n < 10⁴              → pure-Python small loop
  10⁴ ≤ n < 2⁶⁴
       ├─ wheel_core.so → OpenMP C:
       │     small-prime precheck (through 271)
       │     if isqrt(n) ≤ 2²⁰ → precomputed odd primes + 2-adic wrap-mul trial
       │     else → trial that table, then segmented primes from 2²⁰
       │        (odds sieve in 1.4.0; **wheel-30** from 1.4.1)
       │        OpenMP only if isqrt(n) ≥ 10⁷
       ├─ else n ≤ 4·10¹² → embedded 30030-wheel (stdlib)
       └─ else → Numba 9699690-wheel
  n ≥ 2⁶⁴
       ├─ isqrt(n) ≤ 2.5·10¹⁰ and ≤128-bit → u128 OpenMP full trial / stdlib wheel
       └─ larger → partial trial → AKS if needed
```

The C 9699690-wheel **table is gone** (it lost to prime-only trial once a modest prime list exists, and it bloated `dlopen`). Fallback engines still use on-disk **30030** / **9699690** wheels.

**Performance (indicative, same machine class as 1.3.2).**

| Case | Order of E2E CLI `TIME` (OpenMP `.so`) |
|------|------------------------------------------|
| Tiny primes (97, 7919) | ~0.4 ms |
| $10^9+7$, M31 | ~2–3 ms |
| 12-digit prime `999999999989` | ~2.4 ms (**~45%** faster e2e vs 1.3.2 snapshot; in-process ~10×) |
| M61 / near $2^{63}$ | 1.4.0: same class as 1.3.2 (~0.27–0.65 s); **1.4.1 wheel-30 ~0.15 / ~0.30 s** |

Committed default e2e suite snapshot (`benchmarks/e2e_results.json`): 12-digit ~**2.42 ms**.

| | |
|--|--|
| **Advantages** | Exact cheaper test than `DIV` on the common mid-size band; no OpenMP tax on 12-digit; smaller conceptual C engine (no unrolled wheel wrap class); still fully deterministic |
| **Disadvantages** | ~1.6 MB of prime/`inv`/`thresh` rodata; hard 64-bit still $\Theta(\sqrt{n}/\log n)$ trial; thresholds remain empirical |
| **Still true** | Stochastic / range-limited MR is out of product policy as the engine |

---

## Era 9 — v1.4.1 (2026-08-07): wheel-30 hard sieve

**Design change (hard path only).** Mid-size $\sqrt{n}\le 2^{20}$ is unchanged (precomputed 2-adic trial). For larger $\sqrt{n}$:

- Sieve **numbers coprime to 30** packed as **1 byte / 30 integers** (bit $i$ = residue $1,7,11,13,17,19,23,29$).
- Marking prime $p\ge 7$: eight arithmetic progressions with byte-stride $p$ (step $30p$ in value space). $2,3,5$ never mark.
- Scan unset bits → 8-way `DIV` trial. Same exact prime-only model.
- Segment 64–256 KiB; 256 KiB when $\sqrt{n}\ge 5\cdot10^8$ (L2-sized on the measured laptop).
- Wheel-210 (48 residues) was prototyped and **lost** (marking 48 streams cost more than the extra density saved).

**Performance vs 1.4.0 (same machine, 12 OpenMP threads, in-process unless noted).**

| Case | 1.4.0 | 1.4.1 | Δ |
|------|------:|------:|--:|
| 18-digit prime | ~0.18 s | ~0.10 s | ~40% |
| M61 | ~0.27 s | ~0.15 s (e2e ~0.17 s) | ~44% |
| near $2^{63}$ | ~0.56 s | ~0.30 s (e2e ~0.32 s) | ~45% |
| largest prime $<2^{64}$ | ~1 s class | ~0.50 s | ~2× |
| Default e2e suite | — | unchanged | — |

| | |
|--|--|
| **Advantages** | Same correctness; big constant-factor cut on the sieve that dominated hard primes; no extra `.so` size |
| **Disadvantages** | More delicate marking math (must keep $m\equiv r\pmod{30}$ and $p\mid m$); unrolled marking is a footgun (F11) |
| **Tried and rejected** | Wheel-210 drop-in; Fermat filter (hurts primes); raising PRE_MAX (e2e `.so` bloat) |

---

## Era 10 — v1.4.2 (2026-08-08): 2-adic trial of sieved primes

**Design change (64-bit hard path trial only).** Sieve is still wheel-30. Mid-size $\sqrt{n}\le 2^{20}$ still uses precomputed `PRE_INV`/`PRE_TH`. For primes produced by the segmented sieve:

- Exact identity: odd $p$ divides $n&lt;2^{64}$ iff $(n\cdot p^{-1}\bmod 2^{64})\cdot p &lt; 2^{64}$ (equivalently $n\cdot p^{-1}\le\lfloor(2^{64}-1)/p\rfloor$, without storing the threshold).
- $p^{-1}\bmod 2^{64}$ from a 128-byte `INV8` table (inverse mod 256) + three Newton lift steps.
- Eight independent inverses/tests hide MUL latency. Replaces 8-way `DIV`.
- u128 full trial still uses 128-bit `%` (the wrap-mul identity is 64-bit).

**Tried and not taken (same session):** wheel-210 retry; presieve $7\cdot11\cdot13\cdot17$; precomputed $m_0$ mark starts; 8-way mark unroll; 16-way `DIV`. None beat inv64 ILP reliably after setup / noise, and several hurt M61 or semiprimes.

**Performance vs 1.4.1 (same machine, 12 OpenMP threads).**

| Case | 1.4.1 | 1.4.2 | Δ |
|------|------:|------:|--:|
| M61 in-process | ~0.17 s | ~0.14 s | ~15% |
| near $2^{63}$ in-process | ~0.34 s | ~0.28 s | ~17% |
| near $2^{63}$ e2e | ~0.32 s | ~0.29 s | ~8–15% |
| largest prime $<2^{64}$ | ~0.50 s class | ~0.41 s | ~18% |
| Default e2e suite | — | unchanged class | — |

| | |
|--|--|
| **Advantages** | Same exact prime-only trial model; no extra `.so` bulk; fewer DIV-port stalls on Zen 2 / similar |
| **Disadvantages** | Newton inv is more MUL work per prime than a precomputed inverse (still wins vs DIV when $p$ is seen once) |
| **Still true** | Stochastic / range-limited MR is out of product policy as the engine |

---

## Era 11 — v1.4.3 (2026-08-08): memcpy presieve + 32-bit mark starts

**Design.** After inv64 trial, sieve marking was the remaining hard-path cost (especially the new CLI default, $\lfloor\sqrt{n}\rfloor=2^{32}-1$).

- Build a 17017-byte ($7\cdot11\cdot13\cdot17$) wheel-30 bitmap **once**, marking *all* multiples (including $<p^2$) so wrapping onto large bases stays exact.
- Each segment is **memcpy**-tiled from that pattern (not `memset` + four hottest mark streams).
- Remaining primes $p\ge 19$: **32-bit** start arithmetic (`r % p` with $r<30$, single ceil onto $\max(p^2,\mathrm{base})$).
- CLI / `DEFAULT_N` = `18446744073709551557`. Pages in-browser demo stays near $2^{63}$ (JS wheel is much slower).

**Tried same session:** 512 KiB / 128 KiB segments on the max-64-bit prime — 256 KiB still won.

**Performance vs 1.4.2 (12 threads, same machine).**

| Case | 1.4.2 | 1.4.3 | Δ |
|------|------:|------:|--:|
| largest $<2^{64}$ | ~425 ms | ~397 ms | ~7% |
| near $2^{63}$ | ~308 ms | ~281 ms | ~9% |
| M61 | ~150 ms | ~142 ms | ~5% |
| $10^9+7\times10^9+9$ | ~83 ms | ~76 ms | ~8% |

| | |
|--|--|
| **Advantages** | Sequential fill beats strided ORs for $p=7,11,13,17$; cheaper mark starts; no `.so` bloat |
| **Disadvantages** | 17 KiB BSS + first-call pattern build; wrapping memcpy must keep $\mathrm{base}/30 \bmod 17017$ exact |
| **F6 note** | Default CLI $n$ is now *harder*, not faster; README / wiki / `DEFAULT_N` / e2e hard list all agree |

---

## Era 12 — v1.4.4 (2026-08-08): uint64 bit extract

**Design.** After inv64 trial + presieve, the remaining cost on $\lfloor\sqrt{n}\rfloor=2^{32}-1$ was **walking the sieve**: one Python-style byte loop × $\sim n/30$ bytes. Unset wheel-30 bits are packed 8-to-a-byte; loading `uint64_t`, inverting, skipping zeros, and `__builtin_ctzll` pulls the next prime in one bit-scan.

Tried same session and **rejected**: 8/16/32 KiB cache tiles (mark-all-primes per tile thrashed small-$p$ streams, **+8–55%**); `found` check removal (noise); presieve through 19 (323 KiB pattern lost on the default $n$); 8-way mark unroll (noise / slight loss).

**Performance vs 1.4.3 (12 threads).**

| Case | 1.4.3 | 1.4.4 | Δ |
|------|------:|------:|--:|
| largest $<2^{64}$ | ~380 ms | ~281–303 ms | **~20–26%** |
| near $2^{63}$ | ~265 ms | ~193–213 ms | ~20% |
| M61 | ~134 ms | ~100–106 ms | ~21% |
| $10^9+7\times10^9+9$ | ~80 ms | ~57–60 ms | ~25–29% |

| | |
|--|--|
| **Advantages** | Same primes, far fewer loop trips; no extra `.so` data |
| **Disadvantages** | Must keep last $<8$ bytes as a scalar tail; `memcpy` of `uint64_t` for aliasing safety |

---

## Era 13 — v1.5.0 (2026-08-08): **Current** — huge-n wheel pre-AKS + Kronecker AKS

**Problem.** Naive AKS used $O(r^2)$ Python nested loops for $(\mathbb{Z}/n\mathbb{Z})[X]/(X^r-1)$ multiplication. Direct `_aks_is_prime(10^9+7)` did not finish in minutes. Pre-AKS scan was an odd loop to $5\cdot10^7$ (~25 M mods).

**Design.**

- Pre-AKS: embedded **30030-wheel** to $\min(10^8,\lfloor\sqrt{n}\rfloor)$; small-prime list through 271.
- Perfect power: `isqrt` then **odd** exponents only (even powers are squares).
- Find prime $r$ with $\mathrm{ord}_r(n)>(\log_2 n)^2$; skip when $r-1$ is too small.
- Poly mul via **Kronecker substitution** + CPython long multiplication; optional threaded $a$-loop.
- Still exact AKS; no Miller–Rabin.

**Indicative (this machine).**

| Case | Notes |
|------|--------|
| `_aks_is_prime(97)` | ~8 ms |
| `_aks_is_prime(7919)` | ~0.45 s |
| `_aks_is_prime(10007)` | ~0.79 s |
| $100003\times10^{40}$ | ~0.01 ms (wheel factor, no AKS) |
| $7\times10^{50}$, $3^{80}$ | instant small factor / precheck |
| Huge **primes** past full-trial | Still AKS — seconds to very long; Kronecker is $10^{2+}$× vs schoolbook, not MR-fast |

| | |
|--|--|
| **Advantages** | Composites with a factor $\le10^8$ leave quickly; AKS usable on 4-digit primes in CI; same correctness |
| **Disadvantages** | Huge primes remain poly$(\log n)$ with large constants; threads help only the witness loop |
| **Not taken** | ECPP / APR-CL (different engine, large project); raising u128 full-trial $\sqrt{n}$ enough to cover 80-bit primes (infeasible) |

---

## Summary comparison

| Era | 64-bit engine (best case) | Big-int practical | Big-int huge | E2E focus | Main win | Main cost / risk |
|-----|---------------------------|-------------------|--------------|-----------|----------|------------------|
| Primitive (bench) | Odd trial Python | — | — | No | Simplicity | Too slow |
| **1.0** | Numba 30030-wheel | Tiny trial → AKS | AKS | Weak | One Numba path | JIT/import; eager AKS |
| **1.1.0** | OpenMP 9699690 + tiers | (same large path) | AKS | **Yes** | E2E tiers + C | Path complexity; wheel-wrap bug class |
| **1.1.1** | + 4-way ILP | | | Yes | ~6–9% E2E | Micro only |
| **1.2.0** | + seg-primes if $\sqrt{n}\ge 2\cdot10^8$ | | | Yes | 12–20% hard primes | Threshold too high for mid-size |
| **1.3.0** | same | **u128 full trial** | AKS | Yes | Avoid AKS for $\sim10^{20}$ | Limb code |
| **1.3.1** | same (build at install) | same | AKS | Yes | Portable packaging | No compiler ⇒ slower |
| **1.3.2** | seg-primes if $\sqrt{n}\ge 2\cdot10^5$; 8-way; bit sieve | same | AKS | Yes | Mid-size 4–7× | Empirical knobs |
| **1.4.0** | precomputed primes $\le 2^{20}$ (2-adic mul); seg-primes after | same | AKS | Yes | 12-digit e2e ~45%; no many-core mid-size tax | Extra rodata; still $\sim\sqrt{n}$ hard primes |
| **1.4.1** | + **wheel-30** sieve (byte/30) on hard path | same | AKS | Yes | Hard primes ~40–45% (M61 / $2^{63}$) | Wheel-210 marking overhead lost |
| **1.4.2** | + **2-adic wrap-mul** trial of sieved primes | same | AKS | Yes | Hard 64-bit ~15–17% more (M61 / $2^{63}$) | Newton cost if inverse not reused |
| **1.4.3** | + **memcpy presieve** $7{..}17$ + 32-bit mark starts | same | AKS | Yes | Hard 64-bit ~5–9% more (max $<2^{64}$ ~7%) | Pattern wrap must stay exact |
| **1.4.4** | + **uint64 ctzll** sieve extract | same | AKS | Yes | Hard 64-bit ~20–26% more (default $n$ ~280 ms) | Word tail + aliasing |
| **1.5.0 (now)** | same 64-bit | same u128 | **wheel→Kronecker AKS** | Yes | Huge composites with $p\le10^8$ instant; AKS usable on 4-digit $n$ | Huge primes still AKS-slow |

---

## Failures & anti-patterns (do not repeat)

Recorded so agents and humans do not “rediscover” them:

| ID | What happened | Why it hurt | Mitigation / policy |
|----|---------------|-------------|---------------------|
| **F1** | Optimize **warm Numba** only | CLI felt slow (import/JIT) | Optimize and gate on **E2E `TIME`** (`compare_e2e.py`) |
| **F2** | **Wheel index wrap** bug in unrolled C loops | **False primes** on large semiprimes | Matrix of semiprimes in `tests/test_c_core.py`; treat unrolled wheel code as high risk |
| **F3** | **AKS too early** for multi-limb with practical $\sqrt{n}$ | Correct but unusable latency | Full trial up to `_MAX_FULL_TRIAL_ISQRT`; AKS only beyond |
| **F4** | Prebuilt **Linux `.so` in pure wheel** | Broken/ misleading installs on other platforms | Build at install or ship **platform wheels** |
| **F5** | Segmented-prime **threshold only tuned on hardest primes** | 12-digit path left on dense wheel | Retune with full e2e suite (1.3.2: $2\cdot10^5$) |
| **F6** | Flip default CLI demo to a “fast” $n$ without updating all docs/agents | Confusion about what CI/demo measures | Default is the **hardest** 64-bit prime (`DEFAULT_N`, v1.4.3+); keep README / wiki / e2e hard list in sync. Pages JS demo may stay near $2^{63}$. |
| **F7** | Using **external prime sieve libs** or **stochastic MR** for speed | Violates project identity / correctness story | Forbidden as engine; optional bench-only scripts OK if labeled |
| **F8** | Skipping **serial vs parallel** determinism checks | Racey OpenMP bugs | `benchmarks/check_determinism.py` + Determinism workflow |
| **F9** | Changing wheel/sieve without regenerating **committed C / tables** | Drift between generators and shipped artifacts | `generate_wheel_core_c.py` / `generate_wheel_data.py` + compile script |
| **F10** | Parallel OpenMP segmented sieve on **mid-size** $\sqrt{n}$ (e.g. 12-digit) | More threads *slower* (fork + tiny segments); e2e 12-digit ~2–3× worse at 12 vs 2 threads | Serial precomputed trial for $\sqrt{n}\le 2^{20}$; OpenMP only if $\sqrt{n}\ge 10^7$ |
| **F11** | Unrolled sieve marking with `s += 4*step` and `(size_t)(e-s) > 3*step` | When `s` passes `e`, `e-s` wraps; **heap overflow / SEGV** | Index form `for (bi = …; bi < nbytes; bi += st)` or require `e-s >= 4*st` **and** `s < e` |
| **F12** | Wheel-210 (48 residues) as a drop-in denser sieve | 48 mark streams overtook the ~14% fewer candidates; slower than wheel-30 here | Prefer wheel-30 (8 bits / 30) unless marking is heavily optimized |

---

## Decision guide (when changing algorithms)

1. **Does it stay deterministic for all $n$?** If only for a range, document the range and keep the full path available.
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

*Last updated for package **1.5.0** (huge-n Kronecker AKS + wheel pretrial). Extend forward; do not delete past eras.*
