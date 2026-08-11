# Security Policy

Security updates are applied on the default branch (`main`). There is no
long-term support train; please reproduce against current `main` before
reporting.

| Version | Supported |
| ------- | --------- |
| `main` (latest) | :white_check_mark: |
| Older tagged releases | :x: (best-effort only) |

This project is a deterministic primality library plus CLI. Treat it as
**AI-generated research/engineering work** and review it before production use.

## Reporting a Vulnerability

**Do not** open a public GitHub issue for exploitable flaws.

1. **Preferred:** [Report a vulnerability](https://github.com/BurakAhmet/Best-Prime-Number-Function/security/advisories/new)
   (private vulnerability reporting)
2. Or email **ahmetburakbicer@gmail.com**

Include a short description and impact, the commit SHA or tag, reproduction
steps (input `n`, command, OS / Python / whether `wheel_core` is built), and
whether the result is a **wrong primality answer**, a crash, or a
supply-chain issue.

You should receive an acknowledgement when the report is seen. Coordinated
disclosure is welcome.

### In scope

- RCE, path traversal, or unsafe deserialization in the CLI, packaging, or
  native `wheel_core` build path
- Secret leakage in the repo, Actions, or published packages
- Supply-chain issues (malicious install hooks, compromised workflow tokens)
- Integrity bugs that silently return the **wrong primality** for a specific `n`

### Out of scope

- Requests to switch the engine to Miller–Rabin (that contradicts the
  [project restrictions](../docs/wiki/Project-restrictions.md), not a security hole)
- Slow hard 64-bit primes (expected: full deterministic trial / sieve)
- Missing Numba or a locally unbuilt `wheel_core` (documented fallback)

Fixes must stay deterministic: no stochastic Miller–Rabin as the engine, no
external prime libraries as the implementation. See [CONTRIBUTING.md](../CONTRIBUTING.md).
