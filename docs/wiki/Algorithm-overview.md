# Algorithm overview

Canonical write-up: **[Engines](https://burakahmet.github.io/Best-Prime-Number-Function/guide/engines/)** (dispatch tree, mermaid, path table). This page is the exhibit summary.

CLI **`TIME` is end-to-end** (import → answer).

- $n \lt 10^4$: tiny Python loop.
- Mid-size 64-bit: **OpenMP** `wheel_core.so` when present; else **30030** / **9699690** wheel (stdlib / **Numba**).
- Hard 64-bit / cubic-budget multi-limb: combined BLS, else cubic C.
- Still larger: **BLS only** when $n$ has fewer than 256 bits (147-bit CLI default). **FastECPP only** when $n$ has $\ge 256$ bits (class-number-1 lives inside that walk). A miss raises `UnsettledPrimalityError`. AKS is not a product-path fallback.

History and failures not to repeat: [`docs/ALGORITHM_HISTORY.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md). Bench scripts: [Benchmarks](Benchmarks). Rules: [Project restrictions](Project-restrictions).
