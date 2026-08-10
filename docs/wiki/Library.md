# Library reference

Import the public API from **`best_prime`**. Every result is **exact and deterministic**. No stochastic Miller–Rabin, no prime libraries as the engine.

**Canonical docs (MkDocs):** [burakahmet.github.io/Best-Prime-Number-Function/guide/](https://burakahmet.github.io/Best-Prime-Number-Function/guide/) — install, quick start, **full API**, CLI, engines.

This page is `docs/wiki/Library.md` in the repository (exhibit wiki copy). Keep it as a map; the function-by-function catalogue lives in the [guide API](https://burakahmet.github.io/Best-Prime-Number-Function/guide/api/).

```python
from best_prime import is_prime, next_prime, totient, primorial, primerange
```

Runnable tours: [`examples/basic_usage.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/examples/basic_usage.py) · [`examples/library_tour.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/examples/library_tour.py).

**Input contract (shared).** `n` is a non-negative `int` or a decimal `str`. `bool` is rejected. `parallel=True` only affects OpenMP / Numba on large $\sqrt{n}$; serial and parallel **always agree**.

> [!WARNING]
> This repository is AI-designed. Review before production or research-critical use.

## What is exported

| Area | Symbols |
|------|---------|
| Primality | `is_prime` (also list/array), `lab`, `primality_certificate`, `verify_certificate` |
| Neighbours | `next_prime`, `prev_prime`, `next_primes`, `prev_primes`, `nth_prime` |
| Count / list | `prime_count` (hard ceiling $2^{64}-1$), `primes`, `primerange` (generator) |
| Factors / powers | `prime_factors`, `factorint` (ECM + SIQS), `is_perfect_power`, `is_prime_power` |
| Multiplicative | `totient` / `euler_phi`, `totient_range`, `carmichael_lambda`, `primorial`, `divisors`, `divisor_count`, `divisor_sum`, `omega`, `bigomega`, `radical`, `is_squarefree`, `is_semiprime`, `is_carmichael` |
| Modular | `gcd`, `egcd`, `modinv`, `crt`, `jacobi` |
| Constants | `__version__`, `DEFAULT_N`, `PRIME_COUNT_MAX_N`, `TOTIENT_RANGE_MAX` |

Examples for every function: [guide / API](https://burakahmet.github.io/Best-Prime-Number-Function/guide/api/).

```bash
is-prime 97
next-prime 14 3
prime-count 10
totient 10
primorial 7
```

## Related

- [Library guide](https://burakahmet.github.io/Best-Prime-Number-Function/guide/)
- [Algorithm overview](Algorithm-overview)
- [Project restrictions](Project-restrictions)
- [Contributing](Contributing)
