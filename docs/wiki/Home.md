# Best-Prime-Number-Function Wiki

**Fully deterministic** primality testing for natural numbers — tiered engines (stdlib / OpenMP C / Numba) optimizing end-to-end CLI `TIME`, with full trial through practical multi-limb sizes and **AKS** only for huge inputs.

> [!WARNING]
> **This entire project (code, tests, docs, and wiki) was created and designed by an AI agent**. Treat it as AI-generated work: review code and results before production or research-critical use. Human oversight is recommended.

## Interactive lab

Today’s CI specimen sits above the bench. Type any $n$ for a **deterministic** check in this tab (not the OpenMP C core): **n−1 Pocklington** when $n-1$ factors (trial / Brent / $p-1$ / **Montgomery ECM**), else exact 30-wheel trial. Composites print a **factor**. The stage panel mirrors the live engine (precheck, Fermat, cofactor split, Brent, $p-1$, ECM, Pocklington $F$ vs $\sqrt{n}$, 30-wheel). No digit-length limit: smooth $n-1$ is typically sub-second; hostile $n-1$ (e.g. $10^{54}+31$) can take a minute or two of ECM. If a proof is still impractical, the lab reports **inconclusive** rather than spinning forever. Results are downloadable certificates.

<!-- acta-specimen -->

<div id="prime-lab-root"></div>

---

## Mission

Most “is this prime?” code is **stochastic Miller–Rabin** or a wrapper around someone else’s sieve. Those are excellent *filters*. They are not a uniform proof for every natural number.

This project refuses that bargain: same $n$, any machine, serial or parallel → the same boolean. Speed is engineered **after** that promise. $\pi(n)$, factoring, and Pratt certificates sit on the same contract.

## What this project is

| | |
|--|--|
| **Library** | `is_prime`, `next_prime` / `prev_prime`, `nth_prime`, `prime_count`, `primes` / `primerange`, `prime_factors` / `factorint`, `totient` / `primorial` / `divisors`, `is_prime_power` / `is_perfect_power` |
| **Fast path** | $n \lt 2^{64}$: OpenMP C precomputed-prime / segmented trial when `wheel_core.so` is built; else tiered **30030** / **9699690** wheel (stdlib / Numba) |
| **Mid-large path** | $n \ge 2^{64}$: n−1 Pocklington then cubic C (CLI default); else OpenMP **u128** full trial / stdlib wheel |
| **Huge path** | Partial trial, then **AKS** if needed (deterministic, can be slow) |
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
| **[Algorithm overview](Algorithm-overview)** | Tiered wheel trial (u64/u128) + AKS for huge n |
| **[n−1 Pocklington](https://burakahmet.github.io/Best-Prime-Number-Function/guide/nm1-proof/)** | Hard-path proof when $n-1$ factors (beats cubic) |
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

```bash
git clone https://github.com/BurakAhmet/Best-Prime-Number-Function.git
cd Best-Prime-Number-Function

# library install (preferred)
pip install -e .
# optional if OpenMP core was not built at install time:
bash scripts/compile_wheel_core.sh

python -c "from best_prime import is_prime, next_prime; print(is_prime(17), next_prime(14, 3))"
is-prime 1000000007                    # console script
next-prime 100                         # 101
next-prime 14 3                        # 23
prev-prime 14                          # 13
nth-prime 5                            # 11
prime-count 10                         # 4
prime-factors 360                      # 2 2 2 3 3 5
python -m best_prime                     # default: largest prime < 2^64
python -m best_prime 100000000000000000039  # ~10^20 prime (u128_wheel_c)
pytest -q -m "not slow"
```

As a dependency from GitHub:

```bash
pip install "git+https://github.com/BurakAhmet/Best-Prime-Number-Function.git"
```

---

## Design at a glance

```text
is_prime(n)
    ├─ n < 10⁴         → pure-Python small loop
    ├─ n < 2⁶⁴
    │    ├─ isqrt ≥ 10⁷ → n−1 Pocklington, else cubic C
    │    ├─ wheel_core.so → OpenMP C precomputed primes / seg-primes
    │    ├─ n ≤ 4·10¹²    → embedded 30030-wheel (stdlib)
    │    └─ else          → Numba 9699690-wheel
    └─ n ≥ 2⁶⁴
         ├─ cubic budget → BLS n±1, else cubic C (CLI default)
         ├─ practical √n (≤128-bit) → OpenMP u128 full trial / stdlib wheel
         └─ larger still            → combined BLS → ECPP (h=1 then small-h) → AKS
```

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
