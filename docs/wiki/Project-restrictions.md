# Project restrictions

These rules apply to **all** contributors and **automated agents**.

## Non-negotiable

1. **Deterministic** — no randomness; same input ⇒ same output, always.
2. **No stochastic Miller–Rabin** — no random bases, no “probably prime” engines as the core.
3. **No prime libraries** as the implementation (e.g. primesieve, sympy.isprime as the engine).
4. **Allowed:** NumPy / Numba, and our own compiled OpenMP helper (`wheel_core.so`), for speeding up *our* trial division.
5. **Correctness model**
   - $n \lt 2^{64}$: exact trial division up to $\lfloor\sqrt{n}\rfloor$ — OpenMP **precomputed primes** / segmented primes when `wheel_core.so` is built; otherwise primorial-wheel (embedded **30030** and/or modulus **9699690**)
   - $2^{64} \le n$ with $\lfloor\sqrt{n}\rfloor \le 2.5\cdot10^{10}$ (≤128-bit): same full trial model via OpenMP **u128** core or stdlib wheel
   - still larger $n$: partial trial, then **AKS** (may be slow for huge primes)

## Why not “just use MR”?

Fixed witness Miller–Rabin is deterministic only on **proven finite ranges** (e.g. 64-bit with a known base set). That does **not** give a uniform finite-base proof for **every** natural number. This project optimizes under the stricter goal: deterministic for all $n$ in theory, with engineered fast paths for 64-bit inputs.

## Agent files in the main repo

- [`.github/copilot-instructions.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/.github/copilot-instructions.md)
- [`.github/AGENT_BRIEFING.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/.github/AGENT_BRIEFING.md)
- [CONTRIBUTING.md](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/CONTRIBUTING.md)
