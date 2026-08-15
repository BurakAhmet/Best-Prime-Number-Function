# Command line

After `pip install`, the same programs as `python -m best_prime` / `python -m best_prime.next_prime` are on `PATH`.

```bash
is-prime 97
is-prime 100000000000000000000000000000000000000000031
best-prime --lab 1000000007    # alias of is-prime
is-prime --serial 10**9+7      # force single-threaded engines
is-prime --progress --max-ms 15000 10**99+289
prime-factors --max-ms 30000 $n
primality-certificate --json 17 | python3 scripts/verify_cert.py -
primality-certificate --write /tmp/p40.json 100000000000000001000000000000000003029
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

`is-prime` with no argument defaults to the 147-bit prime `100000000000000000000000000000000000000000031` (n−1 Pocklington when $n-1$ factors; OpenMP cubic only if n−1 is hostile and `4kn` fits in 128 bits). The largest prime $<2^{64}$ (`18446744073709551557`) remains a documented 64-bit specimen. `next-prime` **requires** `n`.

On a TTY (or `BEST_PRIME_PROGRESS=1`) long proofs print stages on stderr: Fermat, usable $D$, prove $q$, factor hunt. A successful FastECPP / ECPP proof also prints `CM_TREE:` (`digits/D/h` for each downrun). That is why two similar-size primes can invert on wall-clock. `--max-ms` / `BEST_PRIME_MAX_MS` aborts as `RESULT: unsettled` (exit 3). A composite verdict is printed as soon as Fermat / FastECPP rejects; factoring is a bounded extra and does not block it. `prime-factors --max-ms` (default 30 s when $n$ has more than 512 bits) is the same idea for complete factorization.

`primality-certificate --json` writes only the certificate object (pipe it to `scripts/verify_cert.py`). `--write PATH` stores the same JSON and still prints the `TEST` / `RESULT` summary. `scripts/verify_cert.py` is stdlib-only — it does not import `best_prime`.

## Exit codes (`is-prime` / power predicates)

| Exit code | Meaning |
|-----------|---------|
| `0` | prime / yes |
| `1` | not prime / no |
| `2` | invalid input |
| `3` | unsettled (proof or factorization hit a time cap / engine wall) |

## What `TIME` means

`TIME` on the CLI is **end-to-end** (import + tables/native load + check), not a warm hot-loop. That is the [primary performance metric](performance.md).

```text
TEST:    100000000000000000000000000000000000000000031 (45 chars)
THREADS: 12
RESULT:  prime
TIME:    309392974 ns  (309.392974 ms)
```

A composite prints one proper factor:

```text
TEST:    6000000000000000000043 (22 chars)
THREADS: 1
RESULT:  not prime
FACTOR:  1017077
TIME:    4881644 ns  (4.881644 ms)
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
| `primality-certificate` | `primality_certificate` (`--json` / `--write`) |
