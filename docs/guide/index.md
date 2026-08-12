# best_prime

**Fully deterministic** primality, $\pi(n)$, factoring, and arithmetic for every natural number. Exact trial through practical $\sqrt{n}$, then **AKS** only when walking to the root is no longer realistic.

Import the public API from **`best_prime`**. No stochastic Miller–Rabin. No prime libraries as the engine.

!!! warning "AI-designed repository"
    Code, tests, docs, and this site were created by an AI agent. Review before production or research-critical use.

```python
from best_prime import is_prime, next_prime, prime_count, totient

is_prime(17)          # True
next_prime(14, 3)     # 23
prime_count(10)       # 4
totient(10)           # 4
```

```bash
pip install "git+https://github.com/BurakAhmet/Best-Prime-Number-Function.git"
is-prime 97
```

## Why it exists

Most “is this prime?” libraries are **stochastic Miller–Rabin** or a wrapper around someone else’s sieve. Those are excellent *filters*. They are not a uniform proof for every natural number.

This library keeps a stricter contract: same $n$, any machine, serial or parallel → the same boolean. Speed is engineered **after** that promise, not instead of it. The primary performance metric is end-to-end CLI `TIME` (import → answer).

| You get | You do not get |
|---------|----------------|
| Exact `is_prime` for every natural number | Random-base Miller–Rabin |
| $\pi(n)$ through $2^{64}-1$ (Lucy then Meissel–Lehmer) | `primesieve` / `sympy.isprime` as the engine |
| Factoring, totient, primorial, CRT, Jacobi | A “probably prime” type |
| Optional OpenMP C + Numba **of our trial** | A result that depends on thread schedule |

## Where to go

- [Install](install.md) — PyPI / GitHub pip, `[fast]`, OpenMP `wheel_core`
- [Quick start](quickstart.md) — first calls and the runnable tours
- [Cubic search](cubic-search.md) — two-band $O(n^{1/3})$ factor search (not the 64-bit `is_prime` engine)
- [API reference](api.md) — every public function, with examples
- [Command line](cli.md) — `is-prime`, `prime-count`, `totient`, …
- [Restrictions](restrictions.md) — non-negotiable rules
- [Engines](engines.md) — which path runs for your $n$
- [Performance](performance.md) — e2e numbers and how we measure

The **interactive lab** (30-wheel orrery, daily specimen, downloadable trial certificate) stays at the [Pages root](https://burakahmet.github.io/Best-Prime-Number-Function/). This guide is the library documentation.

**Source:** [BurakAhmet/Best-Prime-Number-Function](https://github.com/BurakAhmet/Best-Prime-Number-Function) · package `best-prime-number-function` · import `best_prime`
