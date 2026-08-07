# Security policy

## Supported versions

Security fixes are applied on the default branch (`main`) of
[Best-Prime-Number-Function](https://github.com/BurakAhmet/Best-Prime-Number-Function).
There is no long-term support train; please test against current `main` before
reporting.

| Version | Supported |
|---------|-----------|
| `main` (latest) | Yes |
| Older tagged releases | Best-effort only |

This project is a deterministic primality library plus CLI. Treat it as
**AI-generated research/engineering work**: review before production use.

## What to report here

Please report privately if you discover:

- Remote code execution, path traversal, or unsafe deserialization in the CLI,
  packaging, or native `wheel_core` build path
- Secret leakage in the repo, Actions, or published packages
- Supply-chain issues (malicious install hooks, compromised workflow tokens)
- Integrity bugs that could silently return **wrong primality** for a specific
  `n` (false prime / false composite) in a released engine

Performance complaints, feature ideas, and algorithm discussion belong in
**GitHub Issues**, not this policy.

## What not to report as a vulnerability

- “Please switch the engine to Miller–Rabin / a probable-prime API” — that
  contradicts the project’s correctness model, not a security hole
- Slow hard 64-bit primes (expected; full trial / sieve, not MR)
- Missing Numba or a locally unbuilt `wheel_core.so` (fallback paths)

## How to report

**Do not** open a public issue for exploitable flaws.

Email **ahmetburakbicer@gmail.com** with:

1. A short description and impact
2. Affected commit SHA or release tag
3. Reproduction steps (input `n`, command, platform)
4. Whether the result is wrong, a crash, or a trust/supply-chain issue

You should receive an acknowledgement when the report is seen. Coordinated
disclosure is welcome; please give a reasonable window before publishing.

GitHub’s private
[vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
may also be used if enabled on the repository.

## Preferred fix path

Fixes should stay within project restrictions: deterministic results, no
stochastic Miller–Rabin as the engine, no external prime libraries as the
implementation. See [CONTRIBUTING.md](CONTRIBUTING.md) and
[docs/wiki/Project-restrictions.md](docs/wiki/Project-restrictions.md).
