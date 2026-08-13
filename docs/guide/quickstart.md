# Quick start

```python
from best_prime import (
    divisor_count, factorint, is_perfect_power, is_prime, is_prime_power,
    lab, next_prime, nth_prime, prev_prime, prime_count, prime_factors,
    primerange, primes, primorial, totient,
)

is_prime(17)                     # True
is_prime(100)                    # False
is_prime("00017")                # True
next_prime(14)                   # 17
next_prime(14, 3)                # 23
prev_prime(14)                   # 13
nth_prime(5)                     # 11
prime_count(10)                  # 4
primes(10)                       # [2, 3, 5, 7]
list(primerange(10, 20))         # [11, 13, 17, 19]
prime_factors(360)               # [2, 2, 2, 3, 3, 5]
factorint(360)                   # {2: 3, 3: 2, 5: 1}
totient(10)                      # 4
primorial(7)                     # 210
divisor_count(12)                # 6
is_perfect_power(36)             # True
is_prime_power(36)               # False

info = lab(10**9 + 7)
# info["is_prime"], info["path"], info["isqrt"],
# info["elapsed_ms"] (check only), info["e2e_ms"] (since process start)
```

Hard 64-bit specimens (want `wheel_core.so`):

```python
is_prime(1000000000000000000000000000000000000003)       # True  — CLI default (73-bit)
is_prime(18446744073709551557)        # True  — largest prime < 2^64
is_prime(9223372036854775783)         # True  — near 2^63
is_prime("100000000000000000039")     # True  — ~10^20, u128 path
is_prime(10**9 + 7, parallel=False)   # True  — still deterministic
```

## Input contract

`n` is a non-negative `int` or a decimal `str` (whitespace / leading zeros OK). `bool` is rejected — cast with `int` explicitly if you must.

`parallel=True` only affects OpenMP / Numba on large $\sqrt{n}$. Serial and parallel **always agree**.

## Runnable tours

From a clone:

```bash
python3 examples/basic_usage.py
python3 examples/library_tour.py
```

[`examples/library_tour.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/examples/library_tour.py) prints every public export. [`examples/basic_usage.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/examples/basic_usage.py) is the short smoke.

## Console scripts

After `pip install`:

```bash
is-prime 97
next-prime 14 3
prime-count 10
totient 10
```

See [Command line](cli.md) for the full set and exit codes. Full signatures live in the [API reference](api.md).
