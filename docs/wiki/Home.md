# Best-Prime-Number-Function Wiki

**Fully deterministic** primality testing for natural numbers — tiered engines (stdlib / OpenMP C / Numba) optimizing end-to-end CLI `TIME`, with full trial through practical multi-limb sizes and **AKS** only for huge inputs.

> [!WARNING]
> **This entire project (code, tests, docs, and wiki) was created and designed by an AI agent**. Treat it as AI-generated work: review code and results before production or research-critical use. Human oversight is recommended.

---

## What this project is

| | |
|--|--|
| **Library** | `is_prime(n)` in Python (`int` or decimal `str`) |
| **Fast path** | $n < 2^{64}$: tiered **30030** / **9699690** wheel (OpenMP C when `wheel_core.so` is built; else stdlib / Numba) |
| **Mid-large path** | $n \ge 2^{64}$ with practical $\sqrt{n}$ (e.g. ~$10^{20}$): OpenMP **u128** full trial (or stdlib wheel) |
| **Huge path** | Partial trial, then **AKS** if needed (deterministic, can be slow) |
| **Not used** | Stochastic Miller–Rabin, prime sieving libraries as the engine |

**Repository:** [BurakAhmet/Best-Prime-Number-Function](https://github.com/BurakAhmet/Best-Prime-Number-Function)

Keep this wiki aligned with the root [README](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/README.md) (`scripts/check_wiki_sync.py` in CI).

---

## Wiki map

| Page | Description |
|------|-------------|
| **[Home](Home)** | This overview |
| **[Project restrictions](Project-restrictions)** | Non-negotiable rules for humans **and agents** |
| **[Algorithm overview](Algorithm-overview)** | Tiered wheel trial (u64/u128) + AKS for huge n |
| **[CI and automation](CI-and-automation)** | Tests, determinism, e2e performance, issue/PR agents |
| **[Agent briefing](Agent-briefing)** | Instructions for coding / triage agents |
| **[Contributing](Contributing)** | How to contribute safely |
| **[Benchmarks](Benchmarks)** | E2E CLI `TIME` vs in-process hot loop |
| **[Hall of fame](Hall-of-fame)** | Notable 64-bit primes + prime-of-the-day log |

**Source of truth in git:** [`docs/wiki/`](https://github.com/BurakAhmet/Best-Prime-Number-Function/tree/main/docs/wiki).

**Also published as Pages:** [burakahmet.github.io/Best-Prime-Number-Function](https://burakahmet.github.io/Best-Prime-Number-Function/)

---

## Quick start

```bash
git clone https://github.com/BurakAhmet/Best-Prime-Number-Function.git
cd Best-Prime-Number-Function
pip install -r requirements.txt
bash scripts/compile_wheel_core.sh
python -c "from is_prime import is_prime; print(is_prime(17))"
python is_prime.py 1000000007          # fast demo
python is_prime.py                     # default: near-2^63 prime
python is_prime.py 100000000000000000039  # ~10^20 prime (u128_wheel_c)
pytest -q -m "not slow"
```

---

## Design at a glance

```text
is_prime(n)
    ├─ n < 10⁴         → pure-Python small loop
    ├─ n < 2⁶⁴
    │    ├─ wheel_core.so → OpenMP C 9699690-wheel
    │    ├─ n ≤ 4·10¹²    → embedded 30030-wheel (stdlib)
    │    └─ else          → Numba 9699690-wheel
    └─ n ≥ 2⁶⁴
         ├─ practical √n (≤128-bit) → OpenMP u128 full trial / stdlib wheel
         └─ larger still            → partial trial → AKS if needed
```

---

## Status checks you should care about

| Workflow | Role |
|----------|------|
| **CI** | Build `.so`, tests, wiki sync, **e2e** perf vs previous commit, C-path assert on Linux |
| **Determinism** | Repeated serial/parallel trials must agree |
| **Issue agent** | Auto-answers + briefs restrictions |
| **PR agent** | Briefs agents; auto-approves *same-repo* PRs only |
| **Prime of the day** | Daily challenge + hall-of-fame log (`path` + e2e ms) |

Fork PRs are **not** auto-approved. Prefer requiring green **CI** + **Determinism** before merge.
