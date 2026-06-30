# Project restrictions

These rules apply to all contributors and automated agents.

1. **Deterministic** — no randomness; same input ⇒ same output.
2. **No stochastic Miller–Rabin** or other probabilistic primality engines.
3. **No prime libraries** (primesieve, sympy.isprime, …) as the core implementation.
4. **Allowed:** NumPy / Numba for performance of *our* algorithms.
5. **Correctness:**
   - $n < 2^{64}$: exact 30030-wheel trial division up to $\lfloor\sqrt{n}\rfloor$
   - larger $n$: small-factor trial, then AKS if needed (may be slow)

See also `.github/copilot-instructions.md` in the main repo.
