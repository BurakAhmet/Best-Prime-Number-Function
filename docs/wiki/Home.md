# Best-Prime-Number-Function Wiki

**Fully deterministic** primality testing for natural numbers — optimized 64-bit path with Numba, big integers supported under strict correctness rules.

> [!WARNING]
> **This entire project (code, tests, docs, and wiki) was created and designed by an AI agent** (Grok / xAI). Treat it as AI-generated work: review code and results before production or research-critical use. Human oversight is recommended.

---

## What this project is

| | |
|--|--|
| **Library** | `is_prime(n)` in Python (`int` or decimal `str`) |
| **Fast path** | $n < 2^{64}$: **30030-wheel** trial division + **Numba** (optional multi-thread) |
| **Large path** | Small-factor trial, then **AKS** if needed (deterministic, can be slow) |
| **Not used** | Stochastic Miller–Rabin, prime sieving libraries as the engine |

**Repository:** [BurakAhmet/Best-Prime-Number-Function](https://github.com/BurakAhmet/Best-Prime-Number-Function) (private)

---

## Wiki map

| Page | Description |
|------|-------------|
| **[Home](Home)** | This overview |
| **[Project restrictions](Project-restrictions)** | Non-negotiable rules for humans **and agents** |
| **[Algorithm overview](Algorithm-overview)** | Wheel trial division + AKS |
| **[CI and automation](CI-and-automation)** | Tests, determinism, performance, issue/PR agents |
| **[Agent briefing](Agent-briefing)** | Instructions for coding / triage agents |
| **[Contributing](Contributing)** | How to contribute safely |
| **[Benchmarks](Benchmarks)** | Primitive vs optimized speed |
| **[Hall of fame](Hall-of-fame)** | Slow 64-bit primes + indicative timings |

**Source of truth in git:** [`docs/wiki/`](https://github.com/BurakAhmet/Best-Prime-Number-Function/tree/main/docs/wiki) — keep this Wiki in sync when those files change.

**Also published as Pages:** [burakahmet.github.io/Best-Prime-Number-Function](https://burakahmet.github.io/Best-Prime-Number-Function/)

---

## Quick start

```bash
git clone https://github.com/BurakAhmet/Best-Prime-Number-Function.git
cd Best-Prime-Number-Function
pip install -r requirements.txt
python -c "from is_prime import is_prime; print(is_prime(17))"
NUMBA_NUM_THREADS=$(nproc) python is_prime.py 9223372036854775783
pytest -q -m "not slow"
```

---

## Design at a glance

```text
is_prime(n)
    │
    ├─ n < 2          → False
    ├─ n < 2⁶⁴        → 30030-wheel trial division to √n  (Numba / threads)
    └─ n ≥ 2⁶⁴        → small factors → AKS if still undecided
```

---

## Status checks you should care about

| Workflow | Role |
|----------|------|
| **CI** | Fast tests + performance vs previous commit |
| **Determinism** | Repeated serial/parallel trials must agree |
| **Issue agent** | Auto-answers + briefs restrictions |
| **PR agent** | Briefs agents; auto-approves *same-repo* PRs only |

Fork PRs are **not** auto-approved. Prefer requiring green **CI** + **Determinism** before merge.
