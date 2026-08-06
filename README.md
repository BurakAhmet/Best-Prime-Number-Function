# Best-Prime-Number-Function

> [!WARNING]
> **This repository was created and designed by an AI agent**, including code, tests, docs, benchmarks, and automation. Treat it as **AI-generated work**: review, test, and validate before production or research-critical use.

**Fully deterministic** primality testing as an installable **Python library** (and optional CLI) — for every natural number, under strict no-randomness rules.

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Deterministic](https://img.shields.io/badge/primality-deterministic-success.svg)](#design-restrictions)
[![OpenMP](https://img.shields.io/badge/hard%2064--bit-OpenMP%20C-blue.svg)](scripts/compile_wheel_core.sh)
[![Numba](https://img.shields.io/badge/fallback-Numba-orange.svg)](https://numba.pydata.org/)
[![CI](https://github.com/BurakAhmet/Best-Prime-Number-Function/actions/workflows/ci.yml/badge.svg)](https://github.com/BurakAhmet/Best-Prime-Number-Function/actions/workflows/ci.yml)
[![Packages GHCR](https://img.shields.io/badge/Packages-GHCR%20container-blue?logo=github)](https://github.com/BurakAhmet/Best-Prime-Number-Function/pkgs/container/best-prime-number-function)

---

## Python library

### Install

```bash
# dependency from GitHub (no clone required)
pip install "git+https://github.com/BurakAhmet/Best-Prime-Number-Function.git"

# or editable install while hacking on this repo
git clone https://github.com/BurakAhmet/Best-Prime-Number-Function.git
cd Best-Prime-Number-Function
pip install -e .
```

Package name on disk: **`best-prime-number-function`**. Import the API as **`best_prime`** (or the implementation module `is_prime` — same functions).

If hard primes feel slow, ensure the OpenMP core built successfully (`gcc` + OpenMP). Re-run from a clone:

```bash
bash scripts/compile_wheel_core.sh
```

Then set threads for the heavy paths (optional; defaults to all CPUs when unset):

```bash
export OMP_NUM_THREADS=$(nproc)   # also read as NUMBA_NUM_THREADS on the Numba path
```

### API

| Symbol | Role |
|--------|------|
| `is_prime(n, *, parallel=True) -> bool` | `True` iff `n` is prime. Fully deterministic. |
| `lab(n, *, parallel=True) -> dict` | Same check plus diagnostics (`path`, `isqrt`, timings, `note`). |
| `__version__` | Installed package version (`best_prime` only). |

**Accepted `n`:** non-negative `int`, or a decimal `str` (leading zeros / surrounding whitespace OK). Rejects negatives, non-decimal strings, and `bool` (use `int` explicitly if you must).

**`parallel`:** only affects multi-threaded OpenMP / Numba engines on large enough \(\sqrt{n}\). Result never depends on it — serial and parallel must agree.

```python
from best_prime import is_prime, lab

is_prime(17)                              # True
is_prime(100)                             # False
is_prime(9223372036854775783)             # True  (hard 64-bit; wants wheel_core.so)
is_prime("100000000000000000039")         # True  (~10^20; u128 OpenMP path)
is_prime("9" * 100)                       # False (tiny factor / big-int path)
is_prime(10**9 + 7, parallel=False)       # True  (still deterministic)

info = lab(10**9 + 7)
# info["is_prime"], info["path"], info["isqrt"],
# info["elapsed_ms"] (check only), info["e2e_ms"] (since process start), info["note"]
```

Runnable sample: [`examples/basic_usage.py`](examples/basic_usage.py).

### What to expect for performance

| Input size (order of magnitude) | Typical engine (with `.so`) | Notes |
|---------------------------------|----------------------------|--------|
| Tiny / moderate | Python loop or stdlib wheel | Sub-ms to tens of ms |
| Hard 64-bit primes | OpenMP `u64_wheel_c` | Sub-second multi-core on a laptop |
| Up to ~\(10^{20}\) with practical \(\sqrt{n}\) | OpenMP `u128_wheel_c` | Seconds, not AKS |
| Huge primes, no small factors | Partial trial → **AKS** | Correct but can be very slow |

Without `wheel_core.so`, the library still works via stdlib wheels and/or Numba; only the slowest 64-bit / multi-limb cases suffer most.

---

## CLI

After `pip install`, use the console scripts (same program as `python is_prime.py` from a clone):

```bash
is-prime 97
is-prime 9223372036854775783
best-prime --lab 1000000007    # alias of is-prime
is-prime --serial 10**9+7      # force single-threaded engines
```

No argument defaults to the near-\(2^{63}\) prime `9223372036854775783`.

| Exit code | Meaning |
|-----------|---------|
| `0` | prime |
| `1` | not prime |
| `2` | invalid input |

`TIME` on the CLI is **end-to-end** (import + tables/native load + check), not a warm hot-loop only.

```text
TEST:    9223372036854775783 (19 chars)
THREADS: 12
RESULT:  prime
TIME:    569402248 ns  (569.402248 ms)
```

Example for the mid-size 12-digit prime (segmented-prime C path):

```text
TEST:    999999999989 (12 chars)
THREADS: 12
RESULT:  prime
TIME:    4467572 ns  (4.467572 ms)
```

### Developer loop

From a clone, checks matching CI:

```bash
pip install -e ".[dev]"
bash scripts/compile_wheel_core.sh   # if install skipped the native core
python3 scripts/check_restrictions.py
python3 scripts/check_wiki_sync.py
pytest -q -m "not slow"
OMP_NUM_THREADS=2 python3 benchmarks/check_determinism.py
OMP_NUM_THREADS=2 python3 benchmarks/compare_e2e.py --json /tmp/e2e.json
python3 scripts/check_e2e_regression.py \
  --baseline benchmarks/e2e_results.json --candidate /tmp/e2e.json
```

### Supported platforms

| Platform | `wheel_core.so` (OpenMP C) | Fallback |
|----------|----------------------------|----------|
| **Linux x86_64** (CI, Docker) | Built in CI via `scripts/compile_wheel_core.sh`; `lab(n)["path"] == "u64_wheel_c"` is asserted | — |
| **macOS / Windows / other** | Build locally if `gcc`/`clang` + OpenMP are available | Embedded 30030-wheel (stdlib) and/or **Numba** 9699690-wheel |
| **Pure Python env** (no compiler, no Numba wheels) | Unavailable | Stdlib paths only (`n ≤ 4·10¹²` fully covered; harder 64-bit needs Numba or a local `.so`) |

The committed `.so` is a Linux convenience artifact; **source of truth** is `is_prime_data/wheel_core.c` rebuilt in CI.

---

## Why this exists

Many fast prime checks use **Miller–Rabin** with random witnesses. That is fine when a tiny error probability is acceptable. It is **not** a uniform deterministic predicate for **every** natural number unless you restrict to proven finite witness sets (for example 64-bit only).

This project optimizes under harder rules:

| Rule | Meaning |
|------|---------|
| **Deterministic** | Same input → same answer; no RNG |
| **No stochastic MR** | No random-base Miller–Rabin / “probably prime” engines |
| **No prime libraries as the engine** | No primesieve, `sympy.isprime`, etc. |
| **All natural numbers** | `int` or decimal `str`, including values beyond 64 bits |
| **Allowed accelerators** | NumPy / Numba, plus an optional OpenMP C extension we compile ourselves |

---

## How the checker chooses a path

```text
is_prime(n)
  n < 10⁴              →  tiny pure-Python loop
  10⁴ ≤ n < 2⁶⁴
       ├─ wheel_core.so present  →  OpenMP C (9699690-wheel)
       ├─ else n ≤ 4·10¹²        →  embedded 30030-wheel (stdlib only)
       └─ else                   →  lazy NumPy/Numba 9699690-wheel
  n ≥ 2⁶⁴
       ├─ isqrt(n) ≤ 2.5·10¹⁰ (e.g. ~10²⁰) and wheel_core.so
       │                      →  OpenMP C full trial (u128 limbs; no AKS)
       ├─ same size, no .so  →  stdlib 9699690-wheel full trial
       └─ larger still       →  partial trial → AKS if needed

  ✗  stochastic Miller–Rabin · prime sieving libraries
  ✓  deterministic for every natural number
```

```mermaid
flowchart TD
  A[Input n] --> B{n < 2}
  B -->|yes| Z1[False]
  B -->|no| C{n < 10⁴}
  C -->|yes| P1[Pure-Python small loop]
  C -->|no| D{n < 2⁶⁴}
  D -->|yes| E{wheel_core.so?}
  E -->|yes| P2[OpenMP C 9699690-wheel]
  E -->|no| F{n ≤ 4·10¹²}
  F -->|yes| P3[Embedded 30030-wheel stdlib]
  F -->|no| P4[Numba 9699690-wheel]
  P1 --> G{divisor ≤ √n?}
  P2 --> G
  P3 --> G
  P4 --> G
  G -->|yes| Z1
  G -->|no| Z2[True]
  D -->|no| H{practical √n and ≤128-bit?}
  H -->|yes| P5[OpenMP C u128 full trial / stdlib wheel]
  P5 --> G
  H -->|no| I[Partial trial then AKS if needed]
  I --> L{prime?}
  L -->|yes| Z2
  L -->|no| Z1
```

Exact **trial division** up to $\lfloor\sqrt{n}\rfloor$ on the 64-bit paths and on practical multi-limb sizes (candidates restricted by a primorial wheel / prime sieve segment). Only for still-larger inputs does unfinished trial fall through to **AKS** (correct, but can be very slow).

### Time complexity

Let $N = n$ when discussing bit size, and write $L = \lfloor\sqrt{n}\rfloor$. Arithmetic cost below is in **word operations** on $O(1)$- or $O(\log n)$-word integers as implemented (64-bit core; multi-limb mod for the u128 path).

| Path | Worst-case (prime / no small factor) | Notes |
|------|--------------------------------------|--------|
| Tiny loop / odd trial | $\Theta(L) = \Theta(\sqrt{n})$ | Constant-factor 6-wheel style steps |
| Primorial **wheel** trial (stdlib, Numba, OpenMP C) | $\Theta\!\left(\dfrac{\varphi(W)}{W}\,L\right) = \Theta(\sqrt{n})$ | $W \in \{30030,\,9699690\}$; density $\varphi(W)/W < 1$ cuts the constant, **not** the asymptotic class |
| OpenMP wheel / seg-primes ($t$ threads) | $\Theta(\sqrt{n}/t)$ wall-clock *ideally* | Same work, split across cores; prime case has little early exit |
| Segmented sieve + prime-only trial (large $L$) | $\tilde{O}(\sqrt{n})$ | Fewer mods ($\sim \pi(L)$) plus sieving; still $\Theta(\sqrt{n}/\log n)$ mods in the prime case |
| Partial trial then **AKS** (huge $n$) | Poly in $\log n$ for AKS *in theory* | Practical AKS here is far costlier than trial on moderate sizes; used only when full trial is abandoned |

**Composite early exit:** if the least prime factor is $p$, work is roughly $\Theta(p)$ (or $\Theta(\varphi(W)/W \cdot p)$ on a wheel), so smooth composites are much cheaper than the prime worst case.

**Contrast (not used in the library):** deterministic Miller–Rabin for a fixed 64-bit witness set is $\Theta(k \cdot M(\log n)\cdot\log n)$ for $k$ modular exponentiations — much faster for hard 64-bit primes, but that is a different correctness model than “full trial / AKS for every natural number.” See `benchmarks/compare_miller_rabin.py`.

### Build the optional C core

```bash
# requires gcc and OpenMP (libgomp)
bash scripts/compile_wheel_core.sh
```

CI builds this automatically on Linux. Without the `.so`, the library falls back to embedded stdlib wheels and/or Numba. Regenerate table assets with `python scripts/generate_wheel_data.py`.

---

## Performance snapshot

Indicative **end-to-end CLI `TIME`** on a dev machine (`benchmarks/compare_e2e.py`, best of several runs; wall times vary by CPU and whether `wheel_core.so` is present):

| Case | `n` | Typical e2e CLI `TIME` |
|------|-----:|-----------------------:|
| Small prime | 97 | ~0.4 ms |
| $10^9+7$ | 1000000007 | ~2–3 ms |
| 12-digit prime | 999999999989 | ~4–10 ms (sample: `4467572 ns` / `4.467572 ms`) |
| Near $2^{63}$ prime | 9223372036854775783 | ~0.55–0.65 s (sample: `569402248 ns` / `569.402248 ms`) |
| Mersenne M61 | $2^{61}-1$ | ~0.27–0.35 s |

In-process hot-loop comparisons (warm engines) live in [`benchmarks/compare_speed.py`](benchmarks/compare_speed.py). End-to-end CLI timing: [`benchmarks/compare_e2e.py`](benchmarks/compare_e2e.py). More context: [`benchmarks/README.md`](benchmarks/README.md), [Hall of fame](docs/wiki/Hall-of-fame.md).

| Regime | Behaviour |
|--------|-----------|
| Tiny / moderate $n$ | Sub-millisecond to tens of ms e2e; often no NumPy/Numba |
| Hard 64-bit primes | Sub-second multi-core with `wheel_core.so` |
| Huge composites with a small factor | Near-instant |
| Huge primes via AKS | May take a very long time |

---

## Repository map

Think of four layers. Only the first is the product.

```text
+--------------------------------------------------------------------------+
|  1. CORE                                                                 |
|     is_prime.py          is_prime() / lab() / CLI                        |
|     is_prime_data/       precomputed wheels + optional wheel_core.so     |
|     Rules: deterministic, no stochastic MR, no prime libs as engine      |
+--------------------------------------------------------------------------+
|  2. PROOF & SPEED                                                        |
|     tests/               pytest + Hypothesis (derandomized)              |
|     benchmarks/          in-process speed, e2e CLI TIME, determinism     |
|     scripts/             restriction linter, table/C generators, attest  |
+--------------------------------------------------------------------------+
|  3. GITHUB ACTIONS                                                       |
|     CI, Determinism, performance gate, auto-merge, agents, GHCR, wiki    |
+--------------------------------------------------------------------------+
|  4. DOCS & TRACKING                                                      |
|     README, CONTRIBUTING, docs/wiki, labels / optional Project board     |
+--------------------------------------------------------------------------+
```

| If you want to… | Go here |
|-----------------|--------|
| Use the checker | [Quick start](#quick-start) |
| Understand the math/engines | [How the checker chooses a path](#how-the-checker-chooses-a-path) · [restrictions](#design-restrictions) |
| Run tests / benchmarks | [Testing & quality gates](#testing--quality-gates) · [`benchmarks/`](benchmarks/README.md) |
| See automation | [Automation map](#automation-map) |
| Contribute | [Contributing](#contributing) · [CONTRIBUTING.md](CONTRIBUTING.md) |
| Install a release / container | [Releases & packages](#releases--packages) |
| Board / labels | [Project board & labels](#project-board--labels) · [docs/PROJECT_BOARD.md](docs/PROJECT_BOARD.md) |

```text
Best-Prime-Number-Function/
├── is_prime.py                 # API + CLI
├── is_prime_data/              # wheels, wheel_core.c / .so
├── tests/
├── benchmarks/                 # compare_speed, compare_e2e, determinism
├── scripts/
│   ├── check_restrictions.py
│   ├── compile_wheel_core.sh
│   ├── generate_wheel_data.py
│   ├── write_attestation.py
│   └── design_github_project.py
├── docs/wiki/
├── .github/workflows/
├── Dockerfile
├── pyproject.toml / requirements.txt
├── CONTRIBUTING.md
└── README.md
```

---

## Design restrictions

Enforced by review and `scripts/check_restrictions.py` in CI:

1. **Determinism for every natural number** — threads OK; randomness not OK.
2. **No stochastic Miller–Rabin** / “probably prime” engines.
3. **No dedicated prime libraries** as the implementation core (e.g. primesieve, `sympy.isprime`).
4. **Allowed:** NumPy / Numba, and our own compiled OpenMP helper, to accelerate *our* trial division.

Fixed-base MR is deterministic only on **proven finite ranges**. This repo uses **primorial-wheel trial division** (plus **AKS** for oversized integers) so the API stays correct for all naturals under the restriction set.

---

## Testing & quality gates

See the [Developer loop](#developer-loop) above. Full suite: `pytest -q` (includes `@pytest.mark.slow`).

**Two metrics (do not mix them up):**

| Metric | Script | CI role |
|--------|--------|---------|
| **E2E CLI `TIME`** (primary) | `compare_e2e.py` | Perf gate vs previous commit (`check_e2e_regression.py`, 25% threshold) |
| **In-process hot loop** (secondary) | `compare_speed.py` | Informational artifact only |

Coverage highlights: exhaustive checks on $0\ldots4999$; Hypothesis with `derandomize=True`; C-path serial==parallel and semiprime matrix (`tests/test_c_core.py`); Linux assertion `lab(n)["path"] == "u64_wheel_c"`; wiki sync (`scripts/check_wiki_sync.py`).

| Gate | Workflow | Role |
|------|----------|------|
| Restriction linter | **CI** | Bans MR / primesieve / random engines in implementation paths |
| Wiki sync | **CI** | Key README facts must appear in `docs/wiki/` |
| Fast tests | **CI** | `pytest -m "not slow"` on **3.9 / 3.11 / 3.12** (+ build `.so`, assert C path on Linux) |
| Performance | **CI** | **E2E** candidate vs previous commit / PR base; fail if `e2e_ms` regresses **>25%** on measurable cases |
| Attestation | **CI** | Re-runs lint + tests + determinism; uploads `attestation.json` |
| Determinism | **Determinism** | Repeated serial/parallel trials must agree |

---

## Automation map

Workflows under `.github/workflows/` are optional for *using* `is_prime`; they operate the repo for maintainers and agents.

### Quality & publish

| Workflow | Trigger | What it does |
|----------|---------|----------------|
| [**CI**](.github/workflows/ci.yml) | push / PR → `main` | Build C core, linter, pytest, performance, e2e smoke, attestation |
| [**Determinism**](.github/workflows/determinism.yml) | push / PR → `main` | Repeat trials + `check_determinism.py` |
| [**Auto-merge**](.github/workflows/auto-merge.yml) | PR / check_suite | Squash-merge **same-repo**, non-draft PRs when checks are green (not forks) |
| [**Publish package**](.github/workflows/publish-package.yml) | release / manual | Build & push **GHCR** container |
| [**Publish wiki**](.github/workflows/publish-wiki.yml) | `docs/wiki/**` changes | GitHub Pages from wiki markdown |

### Agents & board

| Workflow | Trigger | What it does |
|----------|---------|----------------|
| [**Issue agent**](.github/workflows/issue-agent.yml) | issue opened / reopened | Keyword answers + restrictions briefing + labels |
| [**PR agent**](.github/workflows/pr-agent.yml) | PR open / sync | Briefing, best-effort Copilot review request, **auto-approve** same-repo PRs |
| [**Project autonomy**](.github/workflows/project-autonomy.yml) | issues / PRs | Moves kanban / agent labels |
| [**Project sync**](.github/workflows/project-sync.yml) | manual / optional | Re-seed GitHub Project if `PROJECT_TOKEN` has `project` scopes |
| [**Prime of the day**](.github/workflows/prime-of-the-day.yml) | daily 12:00 UTC / manual | Deterministic date → `n` → `lab()`; upserts labeled issue |

Agent context: [`.github/copilot-instructions.md`](.github/copilot-instructions.md), [`.github/AGENT_BRIEFING.md`](.github/AGENT_BRIEFING.md).

**Policy:** same-repo PRs may be auto-approved and auto-merged after green **CI** + **Determinism**; **forks are never** auto-approved or auto-merged.

```text
Issue opened ──► Issue agent (answer + labels)
PR opened    ──► PR agent (brief + approve if same-repo)
                 Project autonomy (status/*, agent/*)
                      ▼
            CI + Determinism green
                      ▼
            Auto-merge (squash) ──► status/done
```

---

## Project board & labels

Work is tracked with **labels** so Actions can move items without a human-only column. A GitHub **Project** can mirror Status if configured in the UI (or via `scripts/design_github_project.py` with `project` scopes).

| Track | Labels |
|-------|--------|
| **Kanban** | `status/backlog` → `ready` → `in-progress` → `in-review` → `done` |
| **Agent ops** | `agent/triaged` → `implementing` → `waiting-ci` → `done` |
| **Quality** | `quality/checklist` + `todo` / `partial` / `done` |
| **Area / priority / size** | `area/*`, `priority/p0`…`p3`, `size/S|M|L` |
| **Restriction risk** | `restriction-risk/low` or `high` |

Details: [docs/PROJECT_BOARD.md](docs/PROJECT_BOARD.md).

---

## Wiki & docs site

| Location | Role |
|----------|------|
| [docs/wiki/](docs/wiki/) | Source in git |
| [GitHub Wiki](https://github.com/BurakAhmet/Best-Prime-Number-Function/wiki) | Browsable copy |
| [GitHub Pages](https://burakahmet.github.io/Best-Prime-Number-Function/) | HTML mirror |

Start here: [Project restrictions](docs/wiki/Project-restrictions.md) · [Algorithm overview](docs/wiki/Algorithm-overview.md) · [**Algorithm history**](docs/ALGORITHM_HISTORY.md) · [CI and automation](docs/wiki/CI-and-automation.md) · [Hall of fame](docs/wiki/Hall-of-fame.md) · [Agent briefing](docs/wiki/Agent-briefing.md).

---

## Releases & packages

| Channel | How |
|---------|-----|
| **GitHub Release** | Version tags (e.g. `v1.0.0`) |
| **pip library** | See [Python library](#python-library) (`pip install git+https://…` or `pip install -e .`) |
| **GHCR container** | Repo **Packages** tab; published by **Publish package** |

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
docker pull ghcr.io/burakahmet/best-prime-number-function:1.0.0
docker run --rm ghcr.io/burakahmet/best-prime-number-function:1.0.0 17
```

---

## Contributing

Contributions are welcome when they respect the [design restrictions](#design-restrictions). See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
pip install -r requirements.txt
bash scripts/compile_wheel_core.sh
python3 scripts/check_restrictions.py
pytest -q -m "not slow"
OMP_NUM_THREADS=2 python3 benchmarks/check_determinism.py
python3 is_prime.py --lab 97
```

Open an issue before large designs if you are unsure about the restrictions.

---

## AI authorship

Design, code, tests, benchmarks, docs, and automation in this repository were **generated by an AI agent**. This is not presented as independently human-authored work. Review and verify before production use.

---

## License

MIT — see [LICENSE](LICENSE).
