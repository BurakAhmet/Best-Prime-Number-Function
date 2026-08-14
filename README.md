# Best-Prime-Number-Function

> [!WARNING]
> **This repository was created and designed by an AI agent**, including code, tests, docs, benchmarks, and automation. Treat it as **AI-generated work**: review, test, and validate before production or research-critical use.

**Exact `is_prime(n)` for every natural number** — wheel / OpenMP trial, then **combined BLS**, then **ECPP**, then **AKS** only as last resort. No stochastic Miller–Rabin. No prime libraries as the engine.

[Open the exhibit →](https://burakahmet.github.io/Best-Prime-Number-Function/) · [Library guide →](https://burakahmet.github.io/Best-Prime-Number-Function/guide/) · [API](https://burakahmet.github.io/Best-Prime-Number-Function/guide/api/) · [FAQ](https://burakahmet.github.io/Best-Prime-Number-Function/guide/faq/)

<p align="center">
  <a href="https://burakahmet.github.io/Best-Prime-Number-Function/">
    <img src="docs/wiki/assets/og.png" alt="Best Prime — deterministic primality; 9223372036854775783 near 2^63" width="640"/>
  </a>
</p>

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Deterministic](https://img.shields.io/badge/primality-deterministic-success.svg)](#design-restrictions)
[![OpenMP](https://img.shields.io/badge/hard%2064--bit-OpenMP%20C-blue.svg)](scripts/compile_wheel_core.sh)
[![Numba](https://img.shields.io/badge/fallback-Numba-orange.svg)](https://numba.pydata.org/)
[![CI](https://github.com/BurakAhmet/Best-Prime-Number-Function/actions/workflows/ci.yml/badge.svg)](https://github.com/BurakAhmet/Best-Prime-Number-Function/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-library%20guide-teal.svg)](https://burakahmet.github.io/Best-Prime-Number-Function/guide/)
[![PyPI](https://img.shields.io/pypi/v/best-prime-number-function.svg)](https://pypi.org/project/best-prime-number-function/)
[![Packages GHCR](https://img.shields.io/badge/Packages-GHCR%20container-blue?logo=github)](https://github.com/BurakAhmet/Best-Prime-Number-Function/pkgs/container/best-prime-number-function)

---

## Install

```bash
pip install best-prime-number-function          # PyPI (Trusted Publisher on first upload)
pip install "git+https://github.com/BurakAhmet/Best-Prime-Number-Function.git"
pip install -e ".[dev]"                         # clone + tests, ruff, mypy, Numba
bash scripts/compile_wheel_core.sh              # gcc+OpenMP (Linux) or clang+libomp (macOS)
```

Package name: **`best-prime-number-function`**. Import: **`best_prime`**. Extra `[fast]` adds NumPy / Numba. See [install](https://burakahmet.github.io/Best-Prime-Number-Function/guide/install/).

Native core: Linux CI builds `wheel_core.so`. macOS wants `brew install libomp`. Windows uses the stdlib / Numba fallback unless MinGW is present. A no-compiler install still covers $n \le 4\cdot10^{12}$ exactly.

---

## API

| Symbol | Role |
|--------|------|
| `is_prime(n, *, parallel=True)` | `True` iff prime. Also accepts a `list` / NumPy array. |
| `primality_certificate(n)` / `verify_certificate(c)` | Pratt certificate, or a factor if composite. |
| `next_prime` / `prev_prime` / `next_primes` / `prev_primes` | Neighbours; generators stream. Interval sieve while $\sqrt{\text{bound}}\le$ `NEXT_PRIME_SIEVE_ISQRT_MAX` ($2\cdot10^6$). |
| `nth_prime(k)` / `prime_count(n)` / `primes` / `primerange` | $p_k$, $\pi(n)$ (**hard ceiling** `PRIME_COUNT_MAX_N = 2⁶⁴−1`), lists. |
| `prime_factors` / `factorint` / `lehman_factor` | Trial + Fermat + **two-band cubic search** + deterministic Brent + **ECM** + **SIQS**. Hard `is_prime` also uses **combined BLS** before cubic; still-larger $n$ then **ECPP**. |
| `totient` / `primorial` / `divisors` / `gcd` / `jacobi` / … | Exact arithmetic. Catalogue: [`docs/wiki/Library.md`](docs/wiki/Library.md). |
| `lab(n)` | Diagnostics (`path`, timings). |

```python
from best_prime import is_prime, next_prime, prime_count, primality_certificate

is_prime(17)                              # True
is_prime([17, 18, 19])                    # [True, False, True]
next_prime(14, 3)                         # 23
prime_count(10)                           # 4   — n > 2**64-1 raises ValueError
primality_certificate(17)["kind"]         # 'pratt'
is_prime(100000000000000000000000000000000000000000031)           # CLI default — 147-bit n−1 Pocklington
is_prime(18446744073709551557)            # largest prime < 2^64
is_prime(9223372036854775783)             # near 2^63
is_prime(2305843009213693951)             # M61 = 2^{61}-1
```

CLI after install: `is-prime`, `next-prime`, `next-primes`, `prime-count`, `primality-certificate`, … Exit 0 = prime, 1 = not prime, 2 = bad input. Default `is-prime` yardstick is `100000000000000000000000000000000000000000031` (147-bit; n−1 Pocklington; cubic only if n−1 is hostile). Printed `TIME` is **end-to-end** (import + check).

---

## vs other libraries

| | Engine | Deterministic for every $n$? | Typical use |
|--|--------|------------------------------|-------------|
| **best_prime** | Wheel / OpenMP trial, combined BLS, cubic, ECPP, **AKS** | **Yes** | Proof-grade boolean |
| `sympy.isprime` | BPSW + extras | No above proven bounds | CAS default |
| `gmpy2.is_prime` | Miller–Rabin | No | Fast probable-prime |
| `primesieve` | Sieve | N/A (enumeration) | **Forbidden** here as the engine |

A 3-base Miller–Rabin can lie: $n = 3943673813084040361$ is `mr([2,3,5])` “prime” and `is_prime` composite. Worked example: [restrictions](https://burakahmet.github.io/Best-Prime-Number-Function/guide/restrictions/) · [FAQ](https://burakahmet.github.io/Best-Prime-Number-Function/guide/faq/).

---

## Why

`is_prime(n)` is true **if and only if** `n` is prime. The boolean must not depend on a random number generator, a runtime witness, a thread schedule, or a “probably prime” threshold. Same `n`, any machine, serial or parallel → same answer.

Most libraries stop at stochastic Miller–Rabin (a filter, not a proof). This one does not outsource the answer to primesieve, `sympy.isprime`, or a dice roll. Speed is end-to-end CLI `TIME`. The same contract covers $\pi(n)$, deterministic factoring, and certificates.

## Design restrictions

| Rule | Meaning |
|------|---------|
| **Deterministic** | Same input → same answer; no RNG |
| **No stochastic Miller–Rabin** | No “probably prime” engines |
| **No prime libraries as the engine** | No primesieve, `sympy.isprime`, … |
| **All natural numbers** | `int` or decimal `str`, including $>64$ bits |
| **Allowed accelerators** | NumPy / Numba, plus our OpenMP `wheel_core` |

## How the checker chooses a path

Linux/macOS **wheels** (v1.12.0+) ship `wheel_core.so`. A no-compiler or Windows install still falls back to stdlib / Numba. Same dispatch either way:

```text
is_prime(n)
  n < 10⁴              →  tiny pure-Python loop
  10⁴ ≤ n < 2⁶⁴
       ├─ isqrt(n) ≥ 10⁷ and cubic budget
       │     →  BLS n±1, else OpenMP cubic (hard 64-bit)
       ├─ wheel_core.so present  →  OpenMP C (precomputed primes / seg-primes + 2-adic trial)
       ├─ else n ≤ 4·10¹²        →  embedded 30030-wheel (stdlib only)
       └─ else                   →  lazy NumPy/Numba 9699690-wheel
  n ≥ 2⁶⁴
       ├─ cubic budget (4·k·n fits in 128 bits (no artificial cub cap))
       │     →  BLS n±1, else OpenMP cubic
       ├─ isqrt(n) ≤ 2.5·10¹⁰ (e.g. ~10²⁰) and wheel_core.so
       │                      →  OpenMP C full trial (u128 limbs; no AKS)
       ├─ same size, no .so  →  stdlib 9699690-wheel full trial
       └─ larger still       →  ECPP first if ≥256-bit (Montgomery ECM); else BLS → ECPP → AKS

  ✗  stochastic Miller–Rabin · prime sieving libraries
  ✓  deterministic for every natural number
```

Diagram and path notes: [engines](https://burakahmet.github.io/Best-Prime-Number-Function/guide/engines/). Mid-size 64-bit is exact trial to $\lfloor\sqrt{n}\rfloor$. Hard 64-bit and cubic-budget multi-limb try **combined BLS** first; cubic search is the fallback when $n\pm 1$ is hostile and in budget. Still-larger $n$ with $256+$ bits tries **ECPP** first (deterministic Montgomery ECM). The **147-bit CLI default** stays `u128_nm1`. `DEFAULT_N` is unchanged.

`primality_certificate` / `factorint` sit on top of this predicate (Pratt; trial + Fermat + deterministic Brent + ECM + SIQS). They do not change the boolean contract.

Primary perf metric: e2e CLI `TIME` (`benchmarks/compare_e2e.py`). Secondary: warm hot-loop (`benchmarks/compare_speed.py`).

---

## Platforms and C bindings

| Platform | Native OpenMP core | Fallback |
|----------|--------------------|----------|
| **Linux x86_64** (CI, Docker) | Built in CI; `lab(n)["path"] == "u64_wheel_c"` | — |
| **macOS** | `brew install libomp` then `compile_wheel_core.sh` | 30030-wheel / Numba |
| **Windows** | MinGW `gcc` if present | 30030-wheel / Numba |
| **Pure Python** | Unavailable | Stdlib through $4\cdot10^{12}$ |

C API: [`include/best_prime.h`](include/best_prime.h) + [`native/Makefile`](native/Makefile) (`pkg-config best_prime`). Rust/Go notes: [bindings](https://burakahmet.github.io/Best-Prime-Number-Function/guide/bindings/).

---

## Develop

```bash
pip install -e ".[dev]"
bash scripts/compile_wheel_core.sh
python3 scripts/check_restrictions.py
python3 scripts/check_wiki_sync.py
ruff check best_prime tests
mypy
pytest -q -m "not slow"
OMP_NUM_THREADS=2 python3 benchmarks/check_determinism.py
```

Nightly Actions runs `@pytest.mark.slow`. Releases attach sdist/wheels and a GHCR image. Cite via [`CITATION.cff`](CITATION.cff).

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md). Conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Security: [SECURITY.md](SECURITY.md).
