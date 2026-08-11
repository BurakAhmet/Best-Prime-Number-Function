# Project restrictions

These rules apply to **all** contributors and **automated agents**.

## Non-negotiable

1. **Deterministic** — no randomness; same input ⇒ same output, always.
2. **No stochastic Miller–Rabin** — no random bases, no “probably prime” engines as the core. A **deterministic Miller test** with a published *complete* witness set on a stated bound is allowed; above that bound we still use trial / AKS.
3. **No prime libraries** as the implementation (e.g. primesieve, sympy.isprime as the engine).
4. **Allowed:** NumPy / Numba, and our own compiled OpenMP helper (`wheel_core.so`), for speeding up *our* trial division.
5. **Correctness model**
   - $n \lt 2^{64}$: deterministic Miller test with witnesses $2,3,5,7,11,13,23$ (complete on this range), after a tiny prime precheck
   - $2^{64} \le n \le 3\,317\,044\,064\,679\,887\,385\,961\,981$: deterministic Miller test with witnesses $2,3,5,7,11,13,17,19,23,29,31,37$ (Sorenson–Webster)
   - still larger $n$: **30030**-wheel / **9699690**-wheel partial trial, then **AKS** (may be slow for huge primes)

## Why not random-base MR?

A random-base Miller–Rabin test is only *probably* prime. This project still forbids that. Fixed witness sets are a **theorem** on a finite interval: if those tests pass, $n$ is prime. Above the largest published bound we do not pretend a short witness list is a proof — we fall back to trial / AKS.

## Agent files in the main repo

- [`.github/copilot-instructions.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/.github/copilot-instructions.md)
- [`.github/AGENT_BRIEFING.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/.github/AGENT_BRIEFING.md)
- [CONTRIBUTING.md](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/CONTRIBUTING.md)
