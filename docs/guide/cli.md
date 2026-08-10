# Command line

After `pip install`, the same programs as `python is_prime.py` / the library modules are on `PATH`.

```bash
is-prime 97
is-prime 18446744073709551557
best-prime --lab 1000000007    # alias of is-prime
is-prime --serial 10**9+7      # force single-threaded engines
next-prime 100                 # 101 (smallest prime > 100)
next-prime 14 3                # 23
prev-prime 14                  # 13
prev-prime 10 3                # 3
nth-prime 5                    # 11
prime-count 10                 # 4
primes 10                      # 2 3 5 7
primerange 10 20               # 11 13 17 19
prime-factors 360              # 2 2 2 3 3 5
totient 10                     # 4
primorial 7                    # 210
divisors 12                    # 1 2 3 4 6 12
is-prime-power 8               # yes (exit 0)
is-perfect-power 36            # yes (exit 0)
```

`is-prime` with no argument defaults to the largest prime $<2^{64}$: `18446744073709551557` (hardest 64-bit yardstick). Near $2^{63}$ (`9223372036854775783`) is a documented mid-hard specimen. `next-prime` **requires** `n` — it does not default to that 64-bit prime (the successor is 65-bit).

## Exit codes (`is-prime` / power predicates)

| Exit code | Meaning |
|-----------|---------|
| `0` | prime / yes |
| `1` | not prime / no |
| `2` | invalid input |

## What `TIME` means

`TIME` on the CLI is **end-to-end** (import + tables/native load + check), not a warm hot-loop. That is the [primary performance metric](performance.md).

```text
TEST:    18446744073709551557 (20 chars)
THREADS: 12
RESULT:  prime
TIME:    289827924 ns  (289.827924 ms)
```

Example for the mid-size 12-digit prime (precomputed-prime C path):

```text
TEST:    999999999989 (12 chars)
THREADS: 12
RESULT:  prime
TIME:    2806562 ns  (2.806562 ms)
```

## Mapping to Python

| Script | Function |
|--------|----------|
| `is-prime` / `best-prime` | `is_prime` / `lab` |
| `next-prime` | `next_prime` |
| `prev-prime` | `prev_prime` |
| `nth-prime` | `nth_prime` |
| `prime-count` | `prime_count` |
| `primes` | `primes` |
| `primerange` | `primerange` |
| `prime-factors` | `prime_factors` |
| `totient` | `totient` |
| `primorial` | `primorial` |
| `divisors` | `divisors` |
| `is-prime-power` | `is_prime_power` |
| `is-perfect-power` | `is_perfect_power` |
