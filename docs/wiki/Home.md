# Best-Prime-Number-Function Wiki

**Fully deterministic** primality testing for natural numbers — one engine per size band (stdlib / OpenMP C / Numba / **BLS** below 256 bits / **FastECPP** at 256+ bits). AKS is not a product-path fallback.

> [!WARNING]
> **This entire project (code, tests, docs, and wiki) was created and designed by an AI agent**. Treat it as AI-generated work: review code and results before production or research-critical use. Human oversight is recommended.

## Interactive lab

Today’s CI specimen sits above the bench. Type any $n$ for a **deterministic** check in this tab (not the OpenMP C core). **One engine per band**, matching the Python library: **class-number-1 ECPP, then in-tab FastECPP $H_D$** when $n$ has $256+$ bits (Montgomery ECM; Jacobian mul; no BLS after a miss), else **combined BLS only** (n−1 Pocklington, Lucas n+1, Combined Theorem 1 — $n < \max(F^{2}G/2,\,FG^{2}/2)$). Then exact 30-wheel trial if practical. The input shows its **digit count** as you type. Below the checker, **next / previous prime** walks candidates with the same engines (optional $k$-th neighbor; Stop to abort). Factoring uses trial / Brent / $p-1$ / **Montgomery ECM**. Composites print a **factor**. The 131-digit CM-friendly prime $10^{130}+1113$ proves in-tab via $D=-19$. General **132–150 digit** primes (for example $10^{131}+63$ and $10^{149}+183$) prove via in-tab computed-$H_D$ FastECPP. Wider misses are **inconclusive** here; Python may still prove them, else `UnsettledPrimalityError` (AKS is not a product-path fallback). Results are downloadable certificates.

<!-- acta-specimen -->

<div id="prime-lab-root"></div>

---

## What this project is

| | |
|--|--|
| **Library** | `is_prime`, `next_prime` / `prev_prime`, `nth_prime`, `prime_count`, `primes` / `primerange`, `prime_factors` / `factorint`, `totient` / `primorial` / `divisors`, `is_prime_power` / `is_perfect_power` |
| **Fast path** | $n \lt 2^{64}$: OpenMP C precomputed-prime / segmented trial when `wheel_core.so` is built; else tiered **30030** / **9699690** wheel (stdlib / Numba) |
| **Mid-large path** | $n \ge 2^{64}$ in cubic budget: **combined BLS** then cubic C; else OpenMP **u128** full trial / stdlib wheel |
| **Huge path** | bits $<256$: **BLS only** (147-bit CLI default `u128_nm1`). bits $\ge 256$: **FastECPP only** (class-number-1 inside that walk). A miss raises `UnsettledPrimalityError`. AKS is not a product-path fallback. |
| **Not used** | Stochastic Miller–Rabin, prime sieving libraries as the engine |

**Repository:** [BurakAhmet/Best-Prime-Number-Function](https://github.com/BurakAhmet/Best-Prime-Number-Function)

Keep this wiki aligned with the root [README](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/README.md) (`scripts/check_wiki_sync.py` in CI).

---

## Wiki map

| Page | Description |
|------|-------------|
| **[Home](Home)** | This overview |
| **[Library guide](https://burakahmet.github.io/Best-Prime-Number-Function/guide/)** | Standalone MkDocs site (install, API, CLI, engines) at `/guide/` |
| **[Library reference](Library)** | Every public function, with examples (wiki copy) |
| **[Project restrictions](Project-restrictions)** | Non-negotiable rules for humans **and agents** |
| **[Algorithm overview](Algorithm-overview)** | Wheel trial (u64/u128); BLS below 256 bits; FastECPP at 256+ bits |
| **[n−1 / BLS](https://burakahmet.github.io/Best-Prime-Number-Function/guide/nm1-proof/)** | Combined Theorem 1 when $n\pm 1$ factors (beats cubic) |
| **[ECPP](https://burakahmet.github.io/Best-Prime-Number-Function/guide/ecpp-proof/)** | Deterministic Atkin–Morain; general 100-digit = FastECPP (computed $H_D$) |
| **[Cubic search](https://burakahmet.github.io/Best-Prime-Number-Function/guide/cubic-search/)** | Two-band $O(n^{1/3})$ fallback / `factorint` splitter |
| **[Algorithm history](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md)** | Performance eras, opts, tradeoffs, failures to avoid |
| **[CI and automation](CI-and-automation)** | Tests, determinism, e2e performance, issue/PR agents |
| **[Agent briefing](Agent-briefing)** | Instructions for coding / triage agents |
| **[Contributing](Contributing)** | How to contribute safely |
| **[Benchmarks](Benchmarks)** | E2E CLI `TIME` vs in-process hot loop |
| **[Hall of fame](Hall-of-fame)** | Notable 64-bit primes + prime-of-the-day log |

**Source of truth in git:** [`docs/wiki/`](https://github.com/BurakAhmet/Best-Prime-Number-Function/tree/main/docs/wiki).

**Also published as Pages:** [burakahmet.github.io/Best-Prime-Number-Function](https://burakahmet.github.io/Best-Prime-Number-Function/) (exhibit) · [library guide](https://burakahmet.github.io/Best-Prime-Number-Function/guide/)

---

## Quick start

Install and first calls live in the [README](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/README.md) and the [library guide](https://burakahmet.github.io/Best-Prime-Number-Function/guide/).

```bash
pip install best-prime-number-function
is-prime 1000000007
```

Dispatch: [Algorithm overview](Algorithm-overview) · [engines](https://burakahmet.github.io/Best-Prime-Number-Function/guide/engines/).

---

## Status checks you should care about

| Workflow | Role |
|----------|------|
| **CI** | Build `.so`, tests, wiki sync, **e2e** perf vs previous commit, C-path assert on Linux |
| **Determinism** | Gate after repeated serial/parallel trials (PR: 3.12 only; main: multi-version) |
| **Issue agent** | Auto-answers + briefs restrictions |
| **PR agent** | Briefs agents; auto-approves *same-repo* PRs only |
| **Prime of the day** | Daily challenge + hall-of-fame log (`path` + e2e ms) |

Fork PRs are **not** auto-approved. Prefer requiring green **CI** + **Determinism** before merge.
