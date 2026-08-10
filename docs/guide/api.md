# API reference

Import the public API from **`best_prime`**. Every result is **exact and deterministic**. No stochastic Miller–Rabin, no prime libraries as the engine.

```python
from best_prime import is_prime, next_prime, totient, primorial, primerange
```

Runnable tours: [`examples/basic_usage.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/examples/basic_usage.py) · [`examples/library_tour.py`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/examples/library_tour.py).

The same catalogue is kept in the exhibit wiki as [`docs/wiki/Library.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/wiki/Library.md).

**Input contract (shared).** `n` is a non-negative `int` or a decimal `str` (whitespace / leading zeros OK). `bool` is rejected. `parallel=True` only affects OpenMP / Numba on large $\sqrt{n}$; serial and parallel **always agree**.

!!! warning "AI-designed"
    This repository is AI-designed. Review before production or research-critical use.

---

## Constants

| Name | Meaning | Example |
|------|---------|---------|
| `__version__` | Installed package version | `"1.10.0"` |
| `DEFAULT_N` | CLI default / hardest 64-bit yardstick: largest prime $<2^{64}$ | `18446744073709551557` |
| `PRIME_COUNT_MAX_N` | Max $n$ for `prime_count` | $2^{64}-1$ |
| `TOTIENT_RANGE_MAX` | Max $n$ for `totient_range` | $2\cdot10^{7}$ |

```python
from best_prime import DEFAULT_N, PRIME_COUNT_MAX_N, __version__
assert DEFAULT_N == 18446744073709551557
assert is_prime(DEFAULT_N)  # wants wheel_core.so
```

---

## Primality

### `is_prime(n, *, parallel=True) -> bool`

`True` iff $n$ is prime. Fully deterministic: exact trial through practical $\sqrt{n}$, then AKS only for huge $n$.

```python
is_prime(17)                       # True
is_prime(100)                      # False
is_prime("00017")                  # True
is_prime(10**9 + 7)                # True
is_prime(10**9 + 7, parallel=False)
is_prime("100000000000000000039")  # True  (~10^20, u128 path)
```

### `lab(n, *, parallel=True) -> dict`

Same check plus diagnostics: `is_prime`, `path`, `isqrt`, `elapsed_ms` (check only), `e2e_ms` (since process start), `note`.

```python
info = lab(10**9 + 7)
info["is_prime"], info["path"], info["isqrt"]
# (True, 'u64_wheel_c', 31622)   # path depends on wheel_core.so
```

Typical `path` values: `python_small`, `u64_wheel_c`, `u128_wheel_c`, `python_wheel`, `bigint_wheel`, `bigint_trial_or_aks`. See [Engines](engines.md).

---

## Neighbours and the $k$-th prime

### `next_prime(n, k=1, *, parallel=True) -> int`

The $k$-th prime **strictly greater than** $n$.

```python
next_prime(14)      # 17
next_prime(14, 3)   # 23
next_prime(100)     # 101
```

### `prev_prime(n, k=1, *, parallel=True) -> int`

The $k$-th prime **strictly less than** $n$. Raises if fewer than $k$ primes exist below $n`.

```python
prev_prime(14)      # 13
prev_prime(10, 3)   # 3
prev_prime(2)       # ValueError
```

### `nth_prime(k) -> int`

The $k$-th prime, 1-based (`nth_prime(1) == 2`). Large $k$ binary-searches `prime_count` instead of listing every prime up to $p_k$.

```python
nth_prime(1)        # 2
nth_prime(5)        # 11
nth_prime(10_001)   # 104743
```

---

## Counting and listing

### `prime_count(n) -> int`

$\pi(n)$: number of primes $\le n$. Sieve / Lucy–Hedgehog while $\sqrt{n}\le 5\cdot10^7$; Meissel–Lehmer through $2^{64}-1$.

```python
prime_count(10)        # 4
prime_count(100)       # 25
prime_count(10**12)    # 37607912018
```

$n >$ `PRIME_COUNT_MAX_N` raises `ValueError`.

### `primes(n) -> list[int]`

All primes $\le n$ as a list (empty if $n<2$).

```python
primes(10)    # [2, 3, 5, 7]
primes(1)     # []
```

### `primerange(a, b) -> Iterator[int]`

Primes $p$ with $a \le p \lt b$ (half-open, like `range`). **Generator** — a long interval never holds every prime at once. Materialize with `list(...)`.

```python
list(primerange(10, 20))     # [11, 13, 17, 19]
sum(primerange(1, 100))      # 1060
for p in primerange(10**9, 10**9 + 50):
    ...
```

---

## Factoring and powers

### `prime_factors(n, *, parallel=True) -> list[int]`

Prime factors with multiplicity, ascending. `[]` if $n<2$.

```python
prime_factors(360)    # [2, 2, 2, 3, 3, 5]
prime_factors(17)     # [17]
prime_factors(1)      # []
```

### `factorint(n, *, parallel=True) -> dict[int, int]`

Prime $\to$ exponent. Empty if $n<2`.

```python
factorint(360)    # {2: 3, 3: 2, 5: 1}
```

### `is_perfect_power(n) -> bool`

$n=a^b$ with $a>1$, $b>1$.

```python
is_perfect_power(36)    # True   (6^2)
is_perfect_power(8)     # True   (2^3)
is_perfect_power(12)    # False
```

### `is_prime_power(n, *, parallel=True) -> bool`

$n=p^k$ for prime $p$ and $k\ge 1$ (ordinary primes count).

```python
is_prime_power(8)     # True    (2^3)
is_prime_power(7)     # True
is_prime_power(36)    # False   (6^2, 6 not prime)
```

---

## Multiplicative functions

All of these factor **once** via `factorint` (except `totient_range`, which is a linear sieve).

### `totient(n, *, parallel=True) -> int` · alias `euler_phi`

Euler $\varphi(n)$: count of $k\in\{1,\ldots,n\}$ coprime to $n$. $\varphi(0)=0$.

```python
totient(1)     # 1
totient(10)    # 4     (1, 3, 7, 9)
totient(360)   # 96
euler_phi(10)  # 4
```

### `totient_range(limit) -> list[int]`

$[\varphi(0),\ldots,\varphi(\mathrm{limit})]$ in $O(\mathrm{limit})$ time. `limit ≤ TOTIENT_RANGE_MAX` ($2\cdot10^7$).

```python
totient_range(10)
# [0, 1, 1, 2, 2, 4, 2, 6, 4, 6, 4]
```

### `carmichael_lambda(n, *, parallel=True) -> int`

Carmichael $\lambda(n)$: exponent of $(\mathbb{Z}/n\mathbb{Z})^*$.

```python
carmichael_lambda(8)     # 2
carmichael_lambda(15)    # 4
carmichael_lambda(21)    # 6
```

### `primorial(n, *, nth=False) -> int`

Product of primes $\le n$, or (if `nth=True`) of the first $n$ primes. Empty product is $1$. Uses a product tree, not a left fold.

```python
primorial(1)              # 1
primorial(7)              # 210      = 2·3·5·7
primorial(11)             # 2310
primorial(4, nth=True)    # 210      = p1·p2·p3·p4
```

### `divisors(n, *, parallel=True) -> list[int]`

Positive divisors of $n$, ascending. Undefined for $0`.

```python
divisors(12)    # [1, 2, 3, 4, 6, 12]
divisors(1)     # [1]
```

### `divisor_count(n, *, parallel=True) -> int`

$d(n)$: number of positive divisors.

```python
divisor_count(12)    # 6
divisor_count(7)     # 2
```

### `divisor_sum(n, k=1, *, parallel=True) -> int`

$\sigma_k(n)$: $\sum_{d\mid n} d^k$. `k=0` is $d(n)$.

```python
divisor_sum(12)       # 28   = 1+2+3+4+6+12
divisor_sum(12, 0)    # 6
divisor_sum(12, 2)    # 1+4+9+16+36+144
```

### `omega(n)` · `bigomega(n)` · `radical(n)`

$\omega(n)$ distinct prime factors; $\Omega(n)$ with multiplicity; $\mathrm{rad}(n)$ product of distinct primes.

```python
omega(12)       # 2     (2 and 3)
bigomega(12)    # 3     (2·2·3)
radical(12)     # 6     (2·3)
radical(1)      # 1
```

### `is_squarefree(n, *, parallel=True) -> bool`

No square other than $1$ divides $n$. $1$ is square-free; $0$ is not.

```python
is_squarefree(6)     # True
is_squarefree(12)    # False
is_squarefree(1)     # True
```

### `is_semiprime(n, *, parallel=True) -> bool`

$n=pq$ for primes $p,q$ (not necessarily distinct): $4$, $6$, $9$, $15$, …

```python
is_semiprime(6)     # True
is_semiprime(9)     # True
is_semiprime(8)     # False
```

### `is_carmichael(n, *, parallel=True) -> bool`

Square-free composite $n$ with $p-1\mid n-1$ for every prime $p\mid n$.

```python
is_carmichael(561)     # True
is_carmichael(1105)    # True
is_carmichael(7)       # False
```

---

## Modular arithmetic

### `gcd(*args) -> int`

Greatest common divisor. `gcd()` is $0$; negatives allowed.

```python
gcd(12, 18)         # 6
gcd(12, 18, 30)     # 6
gcd(-12, 18)        # 6
```

### `egcd(a, b) -> tuple[int, int, int]`

$(g,x,y)$ with $ax+by=g=\gcd(a,b)$.

```python
g, x, y = egcd(240, 46)
assert g == 2 and 240 * x + 46 * y == g
```

### `modinv(a, m) -> int`

Inverse of $a$ modulo $m>1$. Raises `ValueError` if none exists.

```python
modinv(3, 11)             # 4
(3 * modinv(3, 11)) % 11  # 1
```

### `crt(remainders, moduli) -> int`

Solve $x\equiv r_i\pmod{m_i}$. Moduli need not be pairwise coprime; inconsistent systems raise. Result in $[0,\mathrm{lcm}(m))$.

```python
crt([2, 3, 2], [3, 5, 7])    # 23
23 % 3, 23 % 5, 23 % 7       # (2, 3, 2)
```

### `jacobi(a, n) -> int`

Jacobi symbol $(a/n)\in\{-1,0,1\}$. $n$ must be odd and positive.

```python
jacobi(2, 15)    # 1
jacobi(2, 5)     # -1
jacobi(0, 5)     # 0
```

---

## Related

- [Engines](engines.md) — which path runs
- [Restrictions](restrictions.md) — why not Miller–Rabin
- [Command line](cli.md)
- [Contributing](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/CONTRIBUTING.md)
