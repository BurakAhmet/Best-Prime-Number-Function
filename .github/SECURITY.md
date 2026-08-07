# Security Policy

## Supported Versions

Security updates are applied on the default branch (`main`) of this repository.
There is no long-term support train; please reproduce against current `main`
before reporting.

| Version | Supported |
| ------- | --------- |
| `main` (latest) | :white_check_mark: |
| Older tagged releases | :x: (best-effort only) |

This project is a deterministic primality library plus CLI. Treat it as
**AI-generated research/engineering work** and review it before production use.

## Reporting a Vulnerability

**Do not** open a public GitHub issue for exploitable flaws.

Please report privately using one of:

1. **GitHub private vulnerability reporting** (preferred):
   [Report a vulnerability](https://github.com/BurakAhmet/Best-Prime-Number-Function/security/advisories/new)
2. Email **ahmetburakbicer@gmail.com**

Include:

- A short description and impact
- Affected commit SHA or release tag
- Reproduction steps (input `n`, command, OS / Python / whether `wheel_core.so` is built)
- Whether the result is a **wrong primality answer**, a crash, or a trust / supply-chain issue

You should receive an acknowledgement when the report is seen. We aim to assess
reports promptly and will say whether the issue is accepted, declined, or needs
more detail. Coordinated disclosure is welcome; please allow a reasonable window
before publishing.

### In scope

- Remote code execution, path traversal, or unsafe deserialization in the CLI,
  packaging, or native `wheel_core` build path
- Secret leakage in the repo, Actions, or published packages
- Supply-chain issues (malicious install hooks, compromised workflow tokens)
- Integrity bugs that could silently return the **wrong primality** for a
  specific `n` (false prime / false composite)

### Out of scope

- Requests to switch the engine to Miller–Rabin or another probable-prime API
  (that contradicts the [project restrictions](../docs/wiki/Project-restrictions.md),
  not a security hole)
- Slow hard 64-bit primes (expected: full deterministic trial / sieve)
- Missing Numba or a locally unbuilt `wheel_core.so` (documented fallback paths)

Fixes must stay deterministic: no stochastic Miller–Rabin as the engine, no
external prime libraries as the implementation. See [CONTRIBUTING.md](../CONTRIBUTING.md).
