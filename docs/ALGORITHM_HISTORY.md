# Algorithm & performance history

**Purpose.** Keep a durable record of every primality *engine* this project has used, why it was chosen, what it cost, and what went wrong — so future contributors (humans and agents) improve without replaying past mistakes.

| | |
|--|--|
| **Current package version** | **1.12.0** + unreleased huge-n BLS / ECPP ladder |
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
| **E2E CLI `TIME`** | `python -m best_prime …` / `benchmarks/compare_e2e.py` | Import, table load, native load/JIT, check |
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
2026-08-08  v1.5.0   Huge-n: wheel pre-AKS + Kronecker AKS
2026-08-10  v1.6.0   API: next_prime (30030-wheel candidates + existing is_prime)
2026-08-10  v1.7.0   API: prev/nth/π/range/factor/prime-power
2026-08-10  v1.8.0   INV16 + 19·23·29 OR presieve + persisted contiguous marks
2026-08-10  v1.8.1   uint32 nextg persist + DELTA[64] extract
2026-08-10  v1.8.2   prime_count Meissel–Lehmer through 2^64−1
2026-08-10  v1.9.0   totient / primorial / divisors; primerange generator
2026-08-10  v1.10.0  L1-tiled marking for p<256 on the hard path
2026-08-11  unreleased  L1 tiles to p<4096 + 4+4 wrap-mul trial
2026-08-12  unreleased  Complete cubic C for hard 64-bit + CLI default
2026-08-13  unreleased  n−1 Pocklington before cubic on hard path
2026-08-14  unreleased  huge-n combined BLS + deterministic ECPP  ← current
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

## Era 13 — v1.5.0 (2026-08-08): huge-n wheel pre-AKS + Kronecker AKS

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

## API addition — v1.6.0 (2026-08-10): `next_prime`

**Not an engine change.** New module [`next_prime.py`](../next_prime.py) returns the `k`-th prime $> n$ (`k=1` default) under the same restrictions: tiny table, interval sieve for large `k`, or **30030-wheel** candidates + a 17…1021 prefilter, then the existing `is_prime` dispatch (OpenMP / wheel / AKS). No new `lab()` path.

## API addition — v1.7.0 (2026-08-10): enumeration, factors, powers

Still not an `is_prime` engine change. Shared [`prime_sieve.py`](../prime_sieve.py) (odds-only Eratosthenes, segmented ranges, Lucy–Hedgehog $\pi(n)$) plus:

- `prev_prime` — backward wheel / sieve
- `nth_prime` — sieve to a Dusart bound
- `primes` / `primerange` / `prime_count`
- `prime_factors` / `factorint` — 30-wheel + Fermat + **deterministic** Brent–Pollard (fixed $c$, no RNG), then `is_prime`
- `is_perfect_power` / `is_prime_power` — Newton $k$-th roots

Lucy–Hedgehog allows $n\le 2.5\cdot10^{15}$ ($\sqrt{n}\le 5\cdot10^7$, compact int64 tables). **v1.8.2:** larger $n$ (every 64-bit integer) uses memoized Meissel–Lehmer; leftover cofactors in `factorint` are still proved with `is_prime`. Brent is **not** a primality test.

---

## Era 14 — v1.8.0 (2026-08-10): INV16 + extra presieve + persisted marks

**Design (64-bit / practical u128 hard path).** Mid-size $\sqrt{n}\le 2^{20}$ is unchanged (precomputed 2-adic trial). For larger $\sqrt{n}$:

- **INV16** (64 KiB, built once): $p^{-1}\bmod 2^{16}$ from `INV8` + one lift; two Newton steps to 64-bit. Same wrap-mul identity; ~1/3 fewer inverse muls than INV8+3 steps.
- **Second presieve** $19\cdot23\cdot29$ (12673 bytes), AVX2/scalar word OR after the $7\cdot11\cdot13\cdot17$ memcpy tile. Sequential fill replaces three hottest remaining mark streams. Factors $\le 29$ remain covered by `trial_pre` / start skip.
- **Contiguous thread partitions** of the segment list + **persisted next-$m$** per (prime, residue). First-mark uses 32-bit DIV when it fits; later segments only add $30p$. Interleaved `tid` stride is gone (it forced a DIV every segment).
- Hard-path segment size **128 KiB** (persist made 256 KiB unnecessary).
- `inv30` cached once in BSS. u128 full trial uses the same sieve/persist layout (still 128-bit `%` for trial).

**Tried same session and rejected:** 16-way wrap-mul (hurt the default $n$); $31\cdot37\cdot41$ third OR pattern (helped M61, slightly slower on $\lfloor\sqrt{n}\rfloor=2^{32}-1$); 512 KiB segments; raising `PRE_MAX`.

**Performance vs 1.4.4 / 1.7.0 engine (same machine, 12 OpenMP threads, LTO).**

| Case | 1.7.0 LTO | 1.8.0 LTO | Δ |
|------|------:|------:|--:|
| 12-digit (warm) | ~0.021 ms | ~0.021 ms | — |
| $10^9+7\times10^9+9$ | ~62 ms | ~55 ms | ~12% |
| M61 | ~115 ms | ~105 ms | ~9% |
| near $2^{63}$ | ~233 ms | ~202 ms | ~13% |
| largest $<2^{64}$ | ~336 ms | ~287–292 ms | ~13% |
| Default e2e suite | — | unchanged class | — |

| | |
|--|--|
| **Advantages** | Same exact prime-only model; less Newton work; fewer strided marks; no per-segment DIV |
| **Disadvantages** | ~400 KiB extra BSS (INV16 + `inv30` cache + PS2); contiguous ranges do slightly more work on *tiny* sieved factors (all $p\le 2^{20}$ already caught by `trial_pre`) |
| **Still true** | Stochastic / range-limited MR is out of product policy as the engine |

---

## Era 15 — v1.8.1 (2026-08-10): uint32 nextg + DELTA extract

**Design (hard path only).** Mid-size $\sqrt{n}\le 2^{20}$ unchanged.

- Persist **global wheel-30 byte indexes** (`uint32 nextg`, $m/30$) instead of 64-bit values. Mark start is `bi = nextg - base/30` (subtract, no DIV). Half the persist RAM (fits better next to a 128 KiB segment).
- Extract: `DELTA[tz] = (tz>>3)\cdot 30 + \mathrm{WR30}[tz\&7]` so each `ctzll` is one table add, not a shift/mask/two-lookup.
- Index-form marking (F11-safe). Same wheel-30 + INV16 trial.

**Tried same session and rejected:** 31/37/41 tiny OR presieves (hurt default $n$); 64 KiB segments; 8-way mark unroll for $p<256$; 16-way trial (still).

**Performance vs 1.8.0 (same machine, 12 threads, LTO).**

| Case | 1.8.0 | 1.8.1 | Δ |
|------|------:|------:|--:|
| $10^9+7\times10^9+9$ | ~64 ms | ~52 ms | ~15% |
| M61 | ~117 ms | ~108 ms | ~7% |
| near $2^{63}$ | ~219 ms | ~207 ms | ~6% |
| largest $<2^{64}$ | ~323 ms | ~285 ms | ~12% |

| | |
|--|--|
| **Advantages** | Same primes; fewer DIVs; cheaper extract; smaller persist working set |
| **Disadvantages** | `nextg` assumes $\mathrm{limit}/30 < 2^{32}$ (true for u64 and for u128 full-trial $\sqrt{n}\le 2.5\cdot10^{10}$) |

---

## Era 16 — v1.10.0 (2026-08-10): L1-tiled small-prime marking

**Design (hard path only).** Mid-size $\sqrt{n}\le 2^{20}$ unchanged.

Marking a 128 KiB wheel-30 segment with every $p\le\sqrt{\mathrm{limit}}$ walks the segment once per prime. For $p<256$ that is a dense store stream that falls out of L1 when mixed with thousands of large-$p$ streams.

- Split `mark_segment`: primes $31\le p<256$ mark **16 KiB tiles** (L1-resident); $p\ge 256$ still one pass over the full segment (few stores per prime — tile restart costs more than it saves).
- Persist `nextg` is unchanged (global byte index; each tile is just a smaller `nbytes`/`g0`).
- Same wheel-30 + INV16 trial; same F11-safe index form.

**Tried same session and rejected:** 8-way mark unroll (noise); `__builtin_umul_overflow` (that builtin is 32-bit — would miscompile the 64-bit wrap-mul); PGO / `-mprefer-vector-width=128` (noise / mid-size only); tiling *all* primes (already lost in 1.8.x).

**Performance vs 1.8.1 / 1.9.0 `.so` (interleaved A/B, 12 threads, Zen 2).**

| Case | Δ best-of |
|------|----------:|
| $10^9+7\times10^9+9$ | ~**10%** |
| M61 | ~**8–14%** |
| near $2^{63}$ | ~**6–10%** |
| largest $<2^{64}$ | ~**6–7%** |

| | |
|--|--|
| **Advantages** | Same exact primes; marking-bound hard path hits L1 on the dense streams |
| **Disadvantages** | Extra loop nest for ~40 small primes; tile size / cutoff are CPU-tuned (16 KiB / 256 on Zen 2 L1D) |

---

## Era 17 — unreleased (2026-08-11): **Current** — tiles to $p<4096$ + 4+4 trial

**Design (hard path only).** Mid-size $\sqrt{n}\le 2^{20}$ unchanged.

Profile on Zen 2 (12 threads): fill ~1 ms, **mark ≈ trial ≈ 100 ms** each on DEFAULT_N. Two complementary changes:

- Raise **`TILE_P_MAX` 256 → 4096** so medium primes (the bulk of remaining mark stores) also walk 16 KiB L1 tiles. Catalog only tried $\le 512$; $p\ge 8192$ restarts too often (tiling *all* primes still loses).
- Split 8-way wrap-mul into **two groups of 4** with an early exit between them. Four independent Newton chains fit in GPRs (no spill). A forced 8-wide bitwise `|` (no short-circuit) spilled and was **~2–3% slower**; full 4-wide replacement was already slower in 1.10.x.

**Tried same session and rejected:** Newton mixed into extract (lost 8-wide ILP, +2–8%); fill-presieve inside each tile (~1%); two-band 64 KiB tiles for $p\in[256,2048)$ (wash); long presieve memcpy / `aligned_alloc` / extract prefetch / TLS segment buffers (noise); `orb` asm (GCC already emits it); 8-wide `|` instead of `||` (register spills); TILE_P_MAX $\ge 8192$ (10–25% slower).

**Performance vs 1.10.0 `.so` (interleaved mean A/B, 12 threads, Zen 2; two runs + order-swap).**

| Case | mean ratio (cand/orig) |
|------|-----------------------:|
| $10^9+7\times10^9+9$ | ~0.95–1.00 |
| M61 | ~0.96–1.00 |
| near $2^{63}$ | ~**0.94–0.97** |
| largest $<2^{64}$ | ~**0.94–0.96** (11/12 pair wins) |
| geomean | ~**0.96** |

| | |
|--|--|
| **Advantages** | Same exact primes; more of the mark stream in L1; 4-wide trial hides Newton latency without spilling |
| **Disadvantages** | Tile cutoff 4096 is CPU-tuned (Zen 2 L1D 32 KiB); composites lose a bit of 8-way early-exit |

**Default $n$ (same day).** CLI / `DEFAULT_N` moved from the largest prime $<2^{64}$ to **`10000000000000000000000000000000000000121`** (70-bit, `u128_wheel_c`, $\lfloor\sqrt{n}\rfloor\approx 2.45\cdot 10^{10}$, ~2.3 s on 12 threads). Tried inlined x86-64 `divq` for $n/2^{64}<p$ on the u128 path: geomean 1.005 vs `__umodti3` (wash; reverted). The 64-bit prime stays a documented specimen.

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
| **1.5.0** | same 64-bit | same u128 | **wheel→Kronecker AKS** | Yes | Huge composites with $p\le10^8$ instant; AKS usable on 4-digit $n$ | Huge primes still AKS-slow |
| **1.6.0** | same | same | same | Yes | **`next_prime` API** (wheel candidates + `is_prime`) | Successor search still $\sim$gap $\times$ one prime check |
| **1.7.0** | same | same | same | Yes | prev / $p_k$ / $\pi(n)$ / factor / prime-power | Lucy $n\le 2.5\cdot10^{15}$; Pollard only after trial, never as primality |
| **1.8.0** | + **INV16**, **19·23·29 OR presieve**, **persist + contiguous segs**, 128 KiB | same persist u128 | same | Yes | Hard 64-bit ~10–15% (max $<2^{64}$ ~287 ms in-process) | Extra BSS (~INV16/inv30 cache); 16-way / PS3 rejected |
| **1.8.1** | + **uint32 nextg**, **DELTA extract** | same | same | Yes | Hard 64-bit another ~6–15% | `limit/30` must fit `uint32` |
| **1.8.2** | same | same | same | Yes | **`prime_count` to $2^{64}-1$** (Lucy then Meissel–Lehmer) | Hardest 64-bit $\pi(n)$ needs primes $\le 2^{32}$ once |
| **1.9.0** | same | same | same | Yes | **`primerange` generator**; totient / primorial / divisors / Jacobi / CRT | Product-tree primorial; linear-sieve `totient_range` |
| **1.10.0** | + **L1 tiles for $p<256$** (16 KiB) | same tiles on u128 | same | Yes | Hard 64-bit ~6–14% (marking-bound) | Tile only the dense streams; tiling *all* primes still loses |
| **unreleased** | + **L1 tiles $p<4096$** + **4+4 wrap-mul** | same | same | Yes | Hard 64-bit ~4% geomean (DEFAULT_N ~4–6%) | Tiling $p\ge 8192$ restarts too often; forced 8-wide `\|` spills |
| **unreleased** | same 64-bit (BLS then cubic on hard path) | same cubic / u128 | **BLS → ECPP (h=1 then small-$h$) → AKS** | Yes | Special-form BLS; general 100-digit = small-$h$; `DEFAULT_N` unchanged | $FG>\sqrt{n}$ is not a theorem; h=1 is not completeness; F7 still holds |

---

## API addition — cubic factor search (unreleased)

**Not an `is_prime` engine change.** New module [`best_prime/factor_lehman.py`](../best_prime/factor_lehman.py):

- **Band 1.** 30-wheel rising-product gcd (batches of 128) through the cube-root budget. One gcd proves a block has no factor — Pollard–Strassen / product-tree idea, no FFT, no RNG.
- **Band 2.** Integer-safe Lehman windows on $4kn$ for $k=1,\ldots,\lceil n^{1/3}\rceil$. Overestimated extra so the Crandall–Pomerance interval is never short. $O(n^{1/3})$ instead of walking $(n^{1/3},\sqrt{n}]$.
- **`factorint` / `_split`.** After Fermat, before Brent. Complete on every 64-bit composite; `k_max=100_000` probe for larger $n`.
- **`is_prime`.** Complete cubic C for $n\ge 2^{64}$ (`u128_lehman_c`) and hard 64-bit $n$ with $\lfloor\sqrt{n}\rfloor\ge 10^{7}$ (`u64_lehman_c`). Mid-size 64-bit stays trial (`u64_wheel_c`). Completeness cap `LEHMAN_COMPLETE_CUB_MAX = 3·10^6` (Python) / `LEHMAN_COMPLETE_CUB_MAX_C = 2^{63}-1 (engine max; not a product clamp)` (C; covers $n$ up to $\sim 8\cdot10^{27}$).

Indicative (pure Python, this machine class): $101\times 103$ instant; $(10^9+7)(10^9+9)$ tens of ms; $(2^{31}-1)\times$ next odd $\sim 80\,\mathrm{ms}$.

**C follow-up / CLI default.** `lehman_factor_u128` in `wheel_core.so` (source `is_prime_data/lehman_core.c`) completes through `LEHMAN_COMPLETE_CUB_MAX_C = 2\cdot10^7`. **`is_prime` uses it for every $n\ge 2^{64}$** that fits that budget (`lab` path `u128_lehman_c`), including the CLI default. Same machine: `is_prime(DEFAULT_N)` ~**0.19 s** (was ~**2.1 s** u128 trial). Hard 64-bit: M61 ~**19 ms**, near $2^{63}$ ~**31 ms** (after C micro-opts: 64-bit `%`, parallel wheel, faster `isqrt`). Mid-size 64-bit stays `u64_wheel_c`. CLI default ~**118 ms**.

Recent papers surveyed and **not** taken as the sole engine: Harvey $n^{1/5}$ (2020), Harvey–Hittmeir (2021), Hales–Hiary power-divisor Lehman (2024), Oznovich–Volk high-order elements (2025). Those are either theoretical or special-form. Guide: [`docs/guide/cubic-search.md`](guide/cubic-search.md).

---

## Era — unreleased (2026-08-13): n−1 Pocklington before cubic

**Design.** On the same size class as complete cubic (`cubic_complete_ready`):

1. **Fermat filter** with fixed bases $\{2,3,5,\ldots,37\}$ — composite if $a^{n-1}\not\equiv 1\pmod n$.
2. **Factor $n-1$** with trial + cubic Lehman + cofactor trial (no RNG; cofactor primality reuses wheel/cubic, not the n−1 prover).
3. **Pocklington**: for each prime $q\mid F$ with $F\mid(n-1)$ and $F>\sqrt{n}$, a fixed base $a$ with $a^{n-1}\equiv 1$ and $\gcd(a^{(n-1)/q}-1,n)=1$.
4. If inconclusive (hostile $n-1$), **unchanged cubic** `lehman_factor_u128`.

Module: [`best_prime/primality_nm1.py`](../best_prime/primality_nm1.py). CLI hard path uses the same ladder (not cubic-only). `lab` paths: `u64_nm1` / `u128_nm1` when settled.

**Why this beats cubic.** Cubic is $\Theta(n^{1/3})$ even for primes. n−1 is $O\sim(\log n)$ exponentiations once enough of $n-1$ is factored ($F>\sqrt{n}$). Smooth specimen $600\ldots001$ has $n-1=2^{21}\cdot 3\cdot 5^{20}$; the 147-bit CLI default uses partial Pocklington after Brent/p−1 splits.

**Indicative (this machine, 12 threads where relevant).**

| Case | Prior cubic | n−1 hard path |
|------|------------:|--------------:|
| Smooth 70-bit specimen e2e | ~130–150 ms | **~3 ms** |
| M61 check | ~33 ms | **~0.3 ms** |
| near $2^{63}$ | ~37 ms | **~10 ms** |
| max prime $<2^{64}$ | ~55 ms | **~27 ms** |
| $(10^9+7)(10^9+9)$ | ~20 ms cubic | **~0.01 ms** Fermat reject |
| CLI default **133-bit** (earlier same day) | cubic ~0.3 s | n−1 / cubic depending on factors |
| CLI default **147-bit** `…00031` | cubic incomplete ($4kn>128$b) | **~0.3 s** n−1 |

Default e2e suite (mid-size) unchanged in class (still wheel trial).
**CLI default (2026-08-13):** `100000000000000000000000000000000000000000031` (147-bit, `u128_nm1`).

| | |
|--|--|
| **Advantages** | Asymptotically better when $n-1$ factors; huge CLI-default win; still fully deterministic; cubic completeness preserved |
| **Disadvantages** | Hostile $n-1$ pays factoring attempt then cubic; recursive cofactor primes need care (no re-entrant n−1) |
| **Failures / lessons** | CLI `_main_simple` had a **cubic-only** shortcut that bypassed `is_prime` — fixed so e2e TIME reflects the new engine (F14 risk: “optimize API, forget CLI”) |

Guide: [`docs/guide/nm1-proof.md`](guide/nm1-proof.md).

---

## Era — unreleased (2026-08-14): huge-n BLS / ECPP ladder

**Design.** Still-larger $n$ (past complete cubic and practical u128 trial) is no longer “partial trial then AKS.” The proving ladder is:

1. **Combined BLS** (`primality_nm1`): n−1 Pocklington / Theorem 5, Lucas n+1 ($G>\sqrt{n}$ or $G=n+1$), Combined Theorem 1
   $$n < \max(F^{2}G/2,\; FG^{2}/2)\quad(\gcd(F,G)=2).$$
   $FG>\sqrt{n}$ is **not** a theorem. No n+1 cubic extra (BLS Theorem 11 is n−1). SIQS is wired into `_try_split_cofactor` after ECM (`80\le` bits $\le 200$), hard abort, no raise. Cofactor proofs never enter AKS.
2. **Deterministic Atkin–Morain ECPP** (`primality_ecpp`): class-number-1 skeleton (13 discriminants, canonical Cornacchia, $C_4$/$C_6$ twists, `gk_min_q`), then small-$h$ CM ($h(D)\le 16$, transcribed $H_D$). Search is a prefix barrier on increasing $|D|$.
3. **AKS** — unchanged last resort so every natural number still has a complete algorithm.

**General 100-digit completeness is the small-$h$ layer.** $h=1$ is a curve-construction convenience: a single-step Goldwasser–Kilian downrun to a complete-engine $q$ cannot reach 100 digits (`gk_min_q` forces $q\gtrsim 10^{49.5}$; cubic C proves $\lesssim 28$ digits). Combined BLS is special-form / smooth $n\pm 1$ only.

**`DEFAULT_N` stays** the 147-bit CLI default `100…00031` (`u128_nm1`). Not moved to a 100-digit prime (F6).

**F7 still holds.** This is an in-tree reimplementation. Do not call Primo, PARI `primecert`, FLINT APRCL, Enge’s `cm`, or `gmpy2.is_prime`. No stochastic MR, BPSW, or Lucas-PRP filter. A failed Fermat/Lucas is a composite proof; an unsettled cofactor is `None`.

`lab` paths: `bigint_bls` (n+1 or combined; n−1 did not settle), `bigint_ecpp`. Both stay **out** of the `lab` `parallel` set (D-order barrier). Certificates: `is_prime` is boolean-only; designed `kind='bls'|'ecpp'` follows the same ladder (until that API ships, $n\ge 2^{64}$ outside cubic is `kind='unsupported'` — no Pratt hang).

Guides: [`docs/guide/nm1-proof.md`](guide/nm1-proof.md) · [`docs/guide/ecpp-proof.md`](guide/ecpp-proof.md). Design: [`docs/design-100-digit-engine.md`](design-100-digit-engine.md).

| | |
|--|--|
| **Advantages** | Special-form 100-digit primes via BLS; general 100-digit gate on small-$h$ CM; AKS contract preserved; mid-size paths unchanged |
| **Disadvantages** | This tree’s ECM/SIQS peels ≤25–30 digit factors of $m$; $h=1$ alone is not a random-100-digit engine; FastECPP is out of this program |
| **Failures / lessons** | Do not code $FG>\sqrt{n}$; do not treat h=1 as completeness; do not flip `DEFAULT_N` (F6); F7 still forbids PRP / external oracles |

---

## Era — unreleased (2026-08-14): Montgomery ECM + huge-n ECPP first

**Design.** `ecm_factor` is deterministic Suyama/Montgomery ($\sigma=6,7,\ldots$), not affine Weierstrass. ECPP point search uses Jacobian `_mul` (same Weierstrass curve). For $n$ with `bit_length≥256`, `is_prime` tries ECPP before a deep BLS peel. Curve-order peels are cached; the smallest Goldwasser–Kilian $q$ is proved first. Multi-limb leftovers skip 63-curve Brent and 5e6 trial (those hung 131-digit $m$).

**Specimen.** $n=10^{130}+1113$ (131-digit) is ECPP-true via $D=-19$ (in-tree). Not a 2-second proof yet: the downrun is several CM steps and failed $D$ still pay a short ECM. `DEFAULT_N` stays 147-bit `u128_nm1`.

| | |
|--|--|
| **Advantages** | p8-class factors of $m$ in ~0.15 s; 131-digit $n$ now has a proof path; no RNG; F6/F7 hold |
| **Disadvantages** | Python Montgomery is not FastECPP; 131-digit e2e is tens of seconds, not 2 s |
| **Failures / lessons** | Do not trial-split 300-bit leftovers to $5\cdot10^6$; do not 63×Brent on 400-bit $n$; the Pages lab must not treat a $g=n$ inversion as $[q]Q=O$, nor run the hard55 700-curve ECM on ECPP peels (both hung $10^{130}+1113$ in-tab); do not 5e6-scan $n+1$ when $n-1=2\cdot5\cdot13\cdot q$ already proves `DEFAULT_N` |

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
| **F6** | Flip default CLI demo to a “fast” $n$ without updating all docs/agents | Confusion about what CI/demo measures | Default is the **147-bit** hard-path prime `100000000000000000000000000000000000000000031` (`DEFAULT_N`); keep README / wiki / `DEFAULT_N` in sync. Largest prime $<2^{64}$ stays a documented 64-bit specimen. Pages JS demo may stay near $2^{63}$. |
| **F7** | Using **external prime sieve libs** or **stochastic MR** for speed | Violates project identity / correctness story | Forbidden as engine; optional bench-only scripts OK if labeled. **Still holds** after the ECPP ladder: no Primo / PARI `primecert` / FLINT APRCL / Enge `cm` / BPSW / Lucas-PRP |
| **F8** | Skipping **serial vs parallel** determinism checks | Racey OpenMP bugs | `benchmarks/check_determinism.py` + Determinism workflow |
| **F9** | Changing wheel/sieve without regenerating **committed C / tables** | Drift between generators and shipped artifacts | `generate_wheel_core_c.py` / `generate_wheel_data.py` + compile script |
| **F10** | Parallel OpenMP segmented sieve on **mid-size** $\sqrt{n}$ (e.g. 12-digit) | More threads *slower* (fork + tiny segments); e2e 12-digit ~2–3× worse at 12 vs 2 threads | Serial precomputed trial for $\sqrt{n}\le 2^{20}$; OpenMP only if $\sqrt{n}\ge 10^7$ |
| **F11** | Unrolled sieve marking with `s += 4*step` and `(size_t)(e-s) > 3*step` | When `s` passes `e`, `e-s` wraps; **heap overflow / SEGV** | Index form `for (bi = …; bi < nbytes; bi += st)` or require `e-s >= 4*st` **and** `s < e` |
| **F12** | Wheel-210 (48 residues) as a drop-in denser sieve | 48 mark streams overtook the ~14% fewer candidates; slower than wheel-30 here | Prefer wheel-30 (8 bits / 30) unless marking is heavily optimized |
| **F13** | 16-way wrap-mul trial / extra $31\cdot37\cdot41$ OR presieve | Helped M61; **hurt** the default $\lfloor\sqrt{n}\rfloor=2^{32}-1$ yardstick | Keep 8-way INV16; second presieve stops at $19\cdot23\cdot29$ |
| **F14** | CLI hard path called `lehman_factor` directly, bypassing `is_prime` | New engine invisible in e2e `TIME` | Keep CLI and library on the same hard-path ladder |

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
| `best_prime/is_prime.py` | Dispatch + Python/Numba/AKS engines |
| `best_prime/next_prime.py` | Successor prime (wheel candidates + `is_prime`) |
| `best_prime/prev_prime.py` | Predecessor prime |
| `best_prime/prime_sieve.py` | Odds-only / segmented sieve, $\pi(n)$, $p_k$, generator `primerange` |
| `best_prime/ntheory.py` | totient, primorial, divisors, Jacobi, CRT |
| `best_prime/prime_factors.py` | Trial + Fermat + cubic search + deterministic Brent |
| `best_prime/factor_lehman.py` | Two-band cubic split (rising-product + Lehman) |
| `best_prime/primality_nm1.py` | Combined BLS n±1 (Pocklington, Lucas, Combined Theorem 1) |
| `best_prime/primality_ecpp.py` | Deterministic Atkin–Morain ECPP (`gk_min_q`, h=1 then small-$h$) |
| `best_prime/_classpoly_h16.py` | Transcribed Hilbert class polynomials ($h(D)\le 16$) |
| `best_prime/factor_ecm.py` | Deterministic ECM |
| `best_prime/factor_siqs.py` | Deterministic SIQS |
| `best_prime/prime_power.py` | Perfect powers / prime powers |
| `is_prime_data/wheel_core.c` | OpenMP u64/u128 engines (generated + hand-tuned sections) |
| `scripts/generate_wheel_core_c.py` | C generator |
| `scripts/generate_wheel_data.py` | Wheel tables |
| `scripts/compile_wheel_core.sh` | Build `.so` (LTO in 1.3.2+; `WHEEL_CORE_CFLAGS` for hunt overrides) |
| `scripts/optimize_hunt.py` | Catalog hunt + examine verdict for the Optimize workflow |
| `benchmarks/compare_e2e.py` | Primary perf metric |
| `benchmarks/compare_speed.py` | Warm in-process + primitive baseline |
| `benchmarks/e2e_results.json` | Committed e2e snapshot |
| `docs/wiki/Hall-of-fame.md` | Notable primes + prime-of-the-day timings |
| `docs/wiki/Project-restrictions.md` | Hard rules |

---

*Last updated for package **1.12.0** + unreleased huge-n BLS / ECPP ladder (147-bit `DEFAULT_N` unchanged). Extend forward; do not delete past eras.*
