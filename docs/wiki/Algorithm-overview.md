# Algorithm overview

Canonical write-up: **[Engines](https://burakahmet.github.io/Best-Prime-Number-Function/guide/engines/)** (dispatch tree, mermaid, path table). This page is the exhibit summary.

CLI **`TIME` is end-to-end** (import → answer).

- $n \lt 10^4$: tiny Python loop.
- Mid-size 64-bit: **OpenMP** `wheel_core.so` when present; else **30030** / **9699690** wheel (stdlib / **Numba**).
- Hard 64-bit / cubic-budget multi-limb: combined BLS, else cubic C.
- Still larger: combined BLS → ECPP → **AKS**.

History and failures not to repeat: [`docs/ALGORITHM_HISTORY.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md). Bench scripts: [Benchmarks](Benchmarks). Rules: [Project restrictions](Project-restrictions).
