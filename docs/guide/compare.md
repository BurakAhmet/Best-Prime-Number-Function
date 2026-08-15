# Comparison

How `best_prime` sits next to common primality tools — especially **Miller–Rabin**.

## Miller–Rabin vs this library

| | Miller–Rabin (typical libraries) | **best_prime** (this project) |
|--|----------------------------------|-------------------------------|
| **Correctness model** | Probable prime (or deterministic only inside proven witness tables) | **Exact** boolean for every natural $n$ |
| **Randomness** | Often random bases (stochastic) | **None** — same $n$ → same answer |
| **What “yes” means** | “Passes $k$ bases” (composite MR-pseudoprimes exist) | Proven prime (or proven composite with a factor / AKS) |
| **Failure mode** | False prime (rare but real above fixed-witness bounds) | Timeout / slow AKS on huge hard primes — **never** a silent false prime |
| **Typical engine** | Modular exponentiations with $k$ bases | Wheel / OpenMP trial → **n−1 Pocklington** → complete cubic ($O(n^{1/3})$) → AKS |
| **Certificates** | Usually none | Pratt / BLS / FastECPP; arithmetic-only verifier |
| **Speed class** | Microseconds–milliseconds even for huge $n$ | Competitive on smooth $n-1$; slower on hostile hard primes by design |
| **CLI default (147-bit)** | Instant probable-prime | ~0.3 s e2e via **n−1 Pocklington** (`u128_nm1`) |
| **Allowed here?** | **Forbidden as the engine** | Required contract |

Miller–Rabin is an excellent *filter*. It is not this repository’s primality engine. Project restrictions ban stochastic MR and prime sieving libraries as the source of truth.

## Library table

| Library | Engine | Deterministic for every $n$? | Notes |
|---------|--------|------------------------------|-------|
| **best_prime** | Wheel / OpenMP trial, BLS below 256 bits, FastECPP at 256+ bits | **Yes** | Proof-grade; Pratt / BLS / FastECPP certificates |
| `sympy.isprime` | BPSW + extra tests | No above proven bounds | Fine CAS default; `mr()` can lie |
| `gmpy2.is_prime` | Miller–Rabin | No | Fast probable-prime |
| `primesieve` | Highly optimized sieve | N/A (lists primes) | **Forbidden** as this repo’s engine |
| PARI/GP `ispseudoprime` | BPSW | No | Name says so |

End-to-end CLI `TIME` (`compare_e2e.py`) is this project’s primary speed
metric; `compare_speed.py` is the warm hot-loop. See
[performance](performance.md).
