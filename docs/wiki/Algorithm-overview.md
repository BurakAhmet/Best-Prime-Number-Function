# Algorithm overview

## Fast path — $n < 2^{64}$

Exact **trial division** up to $\lfloor\sqrt{n}\rfloor$:

1. Handle $n < 2$, $2$, $3$, other evens.
2. Reject multiples of $3,5,7,11,13$ (baked into wheel modulus $30030$).
3. $\lfloor\sqrt{n}\rfloor$ via hardware `sqrt` + integer correction.
4. Walk candidates **coprime to** $30030 = 2\cdot3\cdot5\cdot7\cdot11\cdot13$ using hardcoded wheel `W30030` (5760 steps), starting at $17$.
5. Optional multi-threading: split the candidate range with Numba `prange` (same idea as OpenMP chunks).

If no divisor appears by $\sqrt{n}$, $n$ is prime.

## Large path — $n \ge 2^{64}$

1. Trial division by small primes and odds up to a practical bound (or $\sqrt{n}$).
2. If the bound reaches $\sqrt{n}$, answer is exact.
3. Otherwise **AKS** — unconditional and deterministic, but potentially very slow for large primes with no small factors.

## Related

- [Benchmarks](Benchmarks) — primitive vs optimized
- Source: [`is_prime.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/is_prime.py)
