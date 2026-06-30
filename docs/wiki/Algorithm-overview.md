# Algorithm overview

## Fast path ($n < 2^{64}$)

Exact **trial division** on a hardcoded **30030-wheel** (skip multiples of $2\cdot3\cdot5\cdot7\cdot11\cdot13$), accelerated with **Numba** (JIT + optional multi-threaded `prange`).

## Large path ($n \ge 2^{64}$)

1. Trial division by small primes / odds up to a bound.
2. If the bound reaches $\sqrt{n}$, done.
3. Otherwise **AKS** (deterministic, can be slow for huge primes).

## Speed comparison

See [benchmarks/README.md](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/benchmarks/README.md) for **primitive vs optimized** timings.
