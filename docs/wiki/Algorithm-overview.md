# Algorithm overview

Canonical write-up: **[Engines](https://burakahmet.github.io/Best-Prime-Number-Function/guide/engines/)** (dispatch tree, mermaid, path table). This page is the exhibit summary.

CLI **`TIME` is end-to-end** (import → answer).

- $n \lt 10^4$: tiny Python loop.
- Mid-size 64-bit: **OpenMP** `wheel_core.so` when present; else **30030** / **9699690** wheel (stdlib / **Numba**).
- Hard 64-bit / cubic-budget multi-limb: combined BLS, else cubic C. Odd prime powers of $n\pm 1$ are peeled from the OpenMP prime table ($\le 2^{20}$), so a fresh CLI check of the near-$2^{63}$ prime is about **3 ms** and the 147-bit default about **5 ms**.
- Still larger: **BLS only** when $n$ has fewer than 256 bits. **Cyclotomic APR-CL** from 256 bits while its modulus exceeds $\sqrt{n}$ (the CLI default $10^{149}+183$ is in this band). The modulus is a ladder of smooth exponents and clears $\sqrt{n}$ through 5000 digits. **FastECPP** only when that modulus does not cover $n$. A 1000-digit prime ($10^{999}+7$) is the cyclotomic proof: about **50 s** in the library on 12 cores, and about **three minutes** in the in-tab checker on the same machine. $10^{1099}+73$ is the same proof in about **158 s**. A miss raises `UnsettledPrimalityError`. AKS is not in the library.

History and failures not to repeat: [`docs/ALGORITHM_HISTORY.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md). Bench scripts: [Benchmarks](Benchmarks). Rules: [Project restrictions](Project-restrictions).
