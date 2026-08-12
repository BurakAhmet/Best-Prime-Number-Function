# Engines

CLI **`TIME` is end-to-end** (import → answer). Dispatch is tiered to minimize that total while keeping every answer exact.

## `is_prime`

```text
is_prime(n)
    ├─ n < 10⁴         → pure-Python small loop
    ├─ n < 2⁶⁴
    │    ├─ isqrt ≥ 10⁷ and cubic C → lehman_factor_u128
    │    ├─ wheel_core.so → OpenMP C precomputed primes / seg-primes
    │    │                 (Linux/macOS wheels ship this; else compile locally)
    │    ├─ n ≤ 4·10¹²    → embedded 30030-wheel (stdlib)
    │    └─ else          → Numba 9699690-wheel
    └─ n ≥ 2⁶⁴
         ├─ cubic C can finish (cube root ≤ 2·10⁷) → lehman_factor_u128 (CLI default)
         ├─ isqrt(n) ≤ 2.5·10¹⁰ (≤128-bit) → OpenMP u128 full trial / stdlib wheel
         └─ larger still            → 30030-wheel to 1e8 → AKS if needed
```

```mermaid
flowchart TD
  A[Input n] --> B{n < 2}
  B -->|yes| Z1[False]
  B -->|no| C{n < 10^4}
  C -->|yes| P1[Pure-Python small loop]
  C -->|no| D{n < 2^64}
  D -->|yes| E0{isqrt ≥ 10^7 and cubic C?}
  E0 -->|yes| P7[OpenMP C cubic search]
  P7 --> Z3
  E0 -->|no| E{wheel_core.so?}
  E -->|yes| P2[OpenMP C — precomputed / seg-primes<br/>Linux/macOS wheels ship this]
  E -->|no| F{n ≤ 4·10^12}
  F -->|yes| P3[Embedded 30030-wheel]
  F -->|no| P4[Numba 9699690-wheel]
  P1 --> G{divisor ≤ √n?}
  P2 --> G
  P3 --> G
  P4 --> G
  G -->|yes| Z1
  G -->|no| Z2[True]
  D -->|no| H0{cubic C complete?}
  H0 -->|yes| P6[OpenMP C cubic search]
  P6 --> Z3{factor?}
  Z3 -->|yes| Z1
  Z3 -->|no| Z2
  H0 -->|no| H{isqrt n ≤ 2.5·10^10 and ≤128-bit?}
  H -->|yes| P5[OpenMP u128 full trial / stdlib wheel]
  P5 --> G
  H -->|no| I[30030-wheel to 1e8 then AKS]
  I --> L{prime?}
  L -->|yes| Z2
  L -->|no| Z1
```

### Fast path — $n \lt 2^{64}$

1. $n \lt 10^4$: tiny pure-Python loop (no NumPy/Numba).
2. If `is_prime_data/wheel_core.so` is present: **OpenMP C**
    - small-prime precheck
    - **precomputed odd primes** $\le 2^{20}$ and exact **2-adic inverse** trial when $\lfloor\sqrt{n}\rfloor \le 1\,048\,576$ (wrap-mul; no wheel `DIV`)
    - **wheel-30 segmented sieve** + memcpy presieve $7\cdot11\cdot13\cdot17$ + OR presieve $19\cdot23\cdot29$ + persisted uint32 marks + **16 KiB L1 tiles for $p<4096$** + `DELTA[64]` extract + 4+4 INV16 wrap-mul when $\sqrt{n}$ is larger (OpenMP when $\lfloor\sqrt{n}\rfloor \ge 10^7$; 128 KiB segments)
3. Else if $n \le 4\cdot10^{12}$: **embedded 30030-wheel** (stdlib only).
4. Else: lazy **Numba** `9699690`-wheel.

### Large path — $n \ge 2^{64}$

1. If $\lfloor\sqrt{n}\rfloor \le 2.5\cdot10^{10}$ and $n$ fits in 128 bits (covers e.g. primes near $10^{20}$): OpenMP **`is_prime_u128_core`**, else stdlib 9699690-wheel.
2. Still larger: 30030-wheel trial up to $\min(10^8,\lfloor\sqrt{n}\rfloor)$, then **AKS** if needed (Kronecker poly mul).

Inspect the live path with [`lab(n)`](api.md).

## Counting, listing, factors

All of these reuse **our** sieves / `is_prime`. No external prime engine.

| API | How |
|-----|-----|
| `next_prime` / `prev_prime` | Table / interval sieve / 30030-wheel + `is_prime` |
| `nth_prime(k)` | Sieve while $p_k$ is moderate; else $\log p_k$ `prime_count` probes |
| `prime_count(n)` | Sieve for $n\le 2\cdot10^7$; Lucy–Hedgehog up to $n\le 2.5\cdot10^{15}$; **Meissel–Lehmer** through $2^{64}-1$ |
| `primes` / `primerange` | Cached odds-only Eratosthenes; **`primerange` yields** (256 KiB windows) |
| `totient` / `primorial` / `divisors` | From `factorint`; `totient_range` is a linear sieve; primorial is a product tree |
| `prime_factors` / `factorint` | 30-wheel trial, Fermat, **two-band cubic search**, deterministic Brent–Pollard ($c=1,2,\ldots$), ECM, SIQS; each prime confirmed with `is_prime` |
| `lehman_factor` | Rising-product 30-wheel to the cube-root budget, then integer-safe Lehman windows. Not the `is_prime` engine. [Cubic search](cubic-search.md) |
| `is_perfect_power` / `is_prime_power` | Newton $k$-th roots; prime exponents only |

## Complexity (word operations)

Let $L = \lfloor\sqrt{n}\rfloor$.

| Path | Worst-case (prime / no small factor) |
|------|--------------------------------------|
| Tiny loop / odd trial | $\Theta(L)=\Theta(\sqrt{n})$ |
| Primorial wheel (stdlib / Numba) | $\Theta((\varphi(W)/W)\cdot L)=\Theta(\sqrt{n})$, $W\in\{30030,9699690\}$ |
| OpenMP precomputed-prime ($L\le 2^{20}$) | $\Theta(\pi(L))=\Theta(\sqrt{n}/\log n)$ |
| OpenMP seg-primes ($t$ threads, large $L$) | $\Theta(\sqrt{n}/t)$ wall-clock *ideally* |
| Partial trial then AKS | Poly in $\log n$ *in theory*; still slow in practice |

Composite early exit is roughly $\Theta(p)$ for least prime factor $p$.

## Building the C core

```bash
bash scripts/compile_wheel_core.sh
```

Regenerate C from the generator (do not hand-edit the `.c` as source of truth):

```bash
python scripts/generate_wheel_core_c.py
```

Full era-by-era notes and **failures not to repeat**: [`docs/ALGORITHM_HISTORY.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md).
