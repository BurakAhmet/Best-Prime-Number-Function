# Comparison

How `best_prime` sits next to common primality tools. No stochastic
Miller–Rabin here; that is the point, not a missing feature.

| Library | Engine | Deterministic for every $n$? | Notes |
|---------|--------|------------------------------|-------|
| **best_prime** | Wheel / OpenMP trial, then AKS | **Yes** | Slower on hard 64-bit primes; Pratt certificates |
| `sympy.isprime` | BPSW + extra tests | No above proven bounds | Fine CAS default; `mr()` can lie |
| `gmpy2.is_prime` | Miller–Rabin | No | Fast probable-prime |
| `primesieve` | Highly optimized sieve | N/A (lists primes) | **Forbidden** as this repo’s engine |
| PARI/GP `ispseudoprime` | BPSW | No | Name says so |

End-to-end CLI `TIME` (`compare_e2e.py`) is this project’s primary speed
metric; `compare_speed.py` is the warm hot-loop. See
[performance](performance.md).
