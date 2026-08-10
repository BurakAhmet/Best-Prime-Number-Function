# Install

Package name on disk: **`best-prime-number-function`**. Import the API as **`best_prime`**.

Requires **Python 3.9+**. The core install has **no required third-party dependencies**. OpenMP C is compiled at install time when `gcc` + OpenMP are present.

## From GitHub

```bash
pip install "git+https://github.com/BurakAhmet/Best-Prime-Number-Function.git"
```

Optional extras:

```bash
# NumPy / Numba fallbacks + faster Lucy π (OpenMP C still needs gcc)
pip install "git+https://github.com/BurakAhmet/Best-Prime-Number-Function.git#egg=best-prime-number-function[fast]"

# tests
pip install "git+https://github.com/BurakAhmet/Best-Prime-Number-Function.git#egg=best-prime-number-function[test]"

# this documentation site (MkDocs Material)
pip install "git+https://github.com/BurakAhmet/Best-Prime-Number-Function.git#egg=best-prime-number-function[docs]"
```

## Editable clone (hacking)

```bash
git clone https://github.com/BurakAhmet/Best-Prime-Number-Function.git
cd Best-Prime-Number-Function
pip install -e ".[dev]"
```

If hard primes feel slow, ensure the OpenMP core built successfully:

```bash
bash scripts/compile_wheel_core.sh
```

Then (optional) pin threads for the heavy paths. Unset means “all CPUs”:

```bash
export OMP_NUM_THREADS=$(nproc)   # also read as NUMBA_NUM_THREADS on the Numba path
```

Sanity check:

```bash
python -c "from best_prime import is_prime, next_prime; print(is_prime(17), next_prime(14, 3))"
is-prime 1000000007
```

On Linux after a successful compile, `lab(10**9 + 7)["path"]` is `u64_wheel_c`.

## Extras

| Extra | Adds |
|-------|------|
| *(none)* | Stdlib wheels + Python Lucy; OpenMP C if a compiler is present at install |
| `[fast]` | `numpy`, `numba` — 9699690-wheel fallback and faster Lucy $\pi$ |
| `[test]` | `pytest`, `hypothesis` |
| `[docs]` | `mkdocs-material` — `mkdocs serve` / `mkdocs build` |
| `[dev]` | test + fast + build tools |

## Platforms

| Platform | `wheel_core.so` (OpenMP C) | Fallback |
|----------|----------------------------|----------|
| **Linux x86_64** (CI, Docker) | Built in CI; `lab(n)["path"] == "u64_wheel_c"` is asserted | — |
| **macOS / Windows / other** | Build locally if `gcc`/`clang` + OpenMP are available | Embedded 30030-wheel (stdlib) and/or **Numba** 9699690-wheel |
| **Pure Python** (no compiler, no Numba) | Unavailable | Stdlib paths only ($n \le 4\cdot10^{12}$ fully covered; harder 64-bit wants Numba or a local `.so`) |

The committed `.so` is a Linux convenience artifact. **Source of truth** is `is_prime_data/wheel_core.c`, rebuilt in CI.

## Build this guide locally

```bash
pip install -e ".[docs]"
mkdocs serve          # http://127.0.0.1:8000
mkdocs build --strict
```

Published URL: [burakahmet.github.io/Best-Prime-Number-Function/guide/](https://burakahmet.github.io/Best-Prime-Number-Function/guide/).
