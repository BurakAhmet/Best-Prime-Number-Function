# Project restrictions

These rules apply to **all** contributors and **automated agents**.

## Non-negotiable

1. **Deterministic** — no randomness; same input ⇒ same output, always.
2. **No stochastic Miller–Rabin** — no random bases, no “probably prime” engines as the core.
3. **No prime libraries** as the implementation (e.g. primesieve, sympy.isprime as the engine).
4. **Allowed:** NumPy / Numba, and our own compiled OpenMP helper (`wheel_core.so`), for speeding up *our* trial division.
5. **Correctness model**
   - $n \lt 2^{64}$: exact trial division up to $\lfloor\sqrt{n}\rfloor$ when $\lfloor\sqrt{n}\rfloor < 10^{7}$ (OpenMP **precomputed primes** / segmented primes, or primorial-wheel **30030** / **9699690**). Harder 64-bit $n$ ($\lfloor\sqrt{n}\rfloor \ge 10^{7}$): **n−1 Pocklington** when $n-1$ factors, else complete OpenMP cubic search when `lehman_factor_u128` is present.
   - $2^{64} \le n$ in cubic budget ($4kn$ fits in 128 bits): same n−1 then cubic ladder. Else $\lfloor\sqrt{n}\rfloor \le 2.5\cdot10^{10}$ (≤128-bit): full trial via OpenMP **u128** core or stdlib wheel
   - still larger $n$: **ECPP** first when $n$ is $\ge 256$ bits (deterministic Montgomery ECM), else combined BLS then ECPP (class-number-1, then small-$h$ CM — the general 100-digit layer), then **AKS**. `DEFAULT_N` is the 147-bit CLI default (`u128_nm1`, past the cubic wall).

## Why not “just use MR”?

Fixed witness Miller–Rabin is deterministic only on **proven finite ranges** (e.g. 64-bit with a known base set). That does **not** give a uniform finite-base proof for **every** natural number. This project optimizes under the stricter goal: deterministic for all $n$ in theory, with engineered fast paths for 64-bit inputs.

## Agent files in the main repo

- [`.github/copilot-instructions.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/.github/copilot-instructions.md)
- [`.github/AGENT_BRIEFING.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/.github/AGENT_BRIEFING.md)
- [CONTRIBUTING.md](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/CONTRIBUTING.md)
