# Deterministic Atkin–Morain ECPP

A deterministic primality proof for $n$ that is **too large for complete cubic search or u128 trial**, when combined BLS cannot factor enough of $n\pm 1$. The prover builds an elliptic curve over $\mathbb{Z}/n\mathbb{Z}$ whose order is known from complex multiplication, then reduces primality of $n$ to primality of a strictly smaller prime $q$.

!!! tip "Still-larger $n$ only"
    Mid-size 64-bit $n$ stay on wheel trial. Hard 64-bit and cubic-budget multi-limb try [combined BLS](nm1-proof.md) first, then cubic search. For $n\ge 256$ bits, `is_prime` tries ECPP **before** a deep BLS peel. Curve orders are split with deterministic Montgomery/Suyama ECM (fixed $\sigma=6,7,\ldots$). AKS remains the last resort so every natural number still has a complete algorithm.

## Why this beats AKS at this scale

Kronecker AKS is a teaching/CI engine: `_aks_is_prime(10007)` is already ~0.79 s. For a 100-digit prime the modulus $r$ is thousands and each $(X+a)^n \bmod (X^r-1,\,n)$ is hopeless. ECPP is the product path for *general* 100-digit $n$ (hostile $n\pm 1$, no hand-picked discriminant). Combined BLS still wins first on special form (smooth-ish $n\pm 1$).

No RNG. No “random curve.” No probable-prime control flow. Discriminants, twists, and points are walked in a **fixed order**. A failed point inversion that yields $1 < g < n$ is a composite proof; a curve of the wrong order is “try the next pair,” not a primality claim. The [Pages lab](https://burakahmet.github.io/Best-Prime-Number-Function/) runs the same class-number-1 ladder (Jacobian mul, stacked Montgomery peel) and proves the 131-digit specimen $10^{130}+1113$ in-tab.

## Goldwasser–Kilian (the only ECPP primality claim)

Let $E: y^2 = x^3 + ax + b$ over $\mathbb{Z}/n\mathbb{Z}$, $m\in\mathbb{Z}$, $q$ prime, $q\mid m$, and $P\in E(\mathbb{Z}/n\mathbb{Z})$ such that

1. $[m]P = O$
2. $[m/q]P$ is defined and $\ne O$
3. $q > (n^{1/4}+1)^2$

Then $n$ is prime (Goldwasser–Kilian 1986). CM supplies $m = n+1\pm t$ from Cornacchia ($t^2 + |D|v^2 = 4n$). We never need Schoof point counting.

**Integer form — `gk_min_q`.** $q > (\lfloor n^{1/4}\rfloor+1)^2$ is **strictly weaker** than the theorem: if $r=\lfloor n^{1/4}\rfloor$ and $x=n^{1/4}$, then $(r+1)^2 < (x+1)^2$, so every $q$ in $((r+1)^2,\,(x+1)^2]$ would be accepted and is **not** a Goldwasser–Kilian $q$.

```python
def gk_min_q(n: int) -> int:
    """Smallest integer q guaranteed to satisfy q > (n^{1/4}+1)²."""
    r = isqrt(isqrt(n))          # floor(n^{1/4})
    return (r + 2) ** 2          # (r+2)² > (x+1)² for all real x ∈ [r, r+1)
```

The prover requires $q \ge \mathrm{gk\_min\_q}(n)$. Do **not** use $(r+1)^2$. Sufficiency matters more than tightness.

## Class-number-1 is not a random-100-digit engine

`max_h=1` walks thirteen discriminants in increasing $|D|$:

```text
D ∈ (−3, −4, −7, −8, −11, −12, −16, −19, −27, −28, −43, −67, −163)
```

$h(D)=1$ is sufficiency that $\bigl(\frac{D}{n}\bigr)=1$ plus local conditions $\Rightarrow 4n=t^2+|D|v^2$ (the principal form is the only class). It is **not** sufficiency that one of ~26 values of $m$ is $c\cdot q$ with $c$ factorable in-budget and $q$ prime above the GK bound.

This tree peels factors of $m$ of at most **~25–30 digits**. For a random 100-digit $m\approx 10^{99}$:

- If nothing peels, $P(\text{remainder prime})\approx 1/\ln(10^{99})\approx 1/228$.
- ~13 discriminants, ~half pass Jacobi, two signs: on the order of **15–20** usable $m$. Expected successes $\ll 1$.
- A single-step downrun to a complete-engine $q$ needs both $q\ge\mathrm{gk\_min\_q}(n)$ ($\gtrsim 10^{49.5}$ at 100 digits) and $q\lesssim 10^{28}$ (cubic C; ~21 digits without `.so`). Those cannot hold together. The same two inequalities imply $n\lesssim 10^{56}$ in the best case.

The published ~39-digit fixture $P_{40}$ (`$(10^{19}+50)^2+23^2$`, $D=-4$) is an h=1-friendly **single-step** specimen. Class-number-1 is a curve-construction convenience, not a random-100-digit completeness claim.

## Small-$h$ CM — the general 100-digit gate

`max_h=16` then walks transcribed Hilbert class polynomials $H_D$ for fundamental $D<0$ with $h(D)\le 16$ and $|D|\le 2000$ (`best_prime/_classpoly_h16.py`). The table is a **citation**, not a computation: no runtime $j(\tau)$, no PARI/Sage/`cm`.

| Source | What is transcribed |
|--------|---------------------|
| Cohen, *A Course in Computational Algebraic Number Theory*, Table 7.1 | Class-number-1: $H_D(X)=X-j(D)$ |
| Cohen ibid. Table 7.6 / §7.3.3, Fungrim 20b6d2 | Small $h>1$ as far as those listings go |

A root of $H_D$ mod $n$ is found by numbered Cantor–Zassenhaus (`$X+1,\,X+2,\,\ldots$`). Then the same curve / point / recurse as h=1.

**General 100-digit completeness is this layer.** A hostile 100-digit prime (no smooth $n\pm 1$, no hand-picked $D$) is allowed to claim a proof only after small-$h$ CM. FastECPP ($D_{\max}\sim L^2$, product trees, MPI) is out of this program.

## Determinism

Search is a **prefix barrier**, not a race:

1. Increasing $|D|$ as written. $D=-3$ must fully fail (including its factoring budget) before $D=-4$ may be accepted.
2. Fixed twist generators ($C_4$ / $C_6$ for $D=-4$ / $-3$; $r\in\{0,1\}$ times signs of $t$ otherwise).
3. Points $x=1,2,\ldots,4096$ (`POINT_X_MAX`).
4. Cornacchia certificate $t$ is the **least** $t>0$ over all lifts, ties broken by least $v$.

`parallel` may speed *internal* arithmetic on a small $q$ already inside a complete engine. It **must not** change which $(D,\,\text{twist},\,\text{point})$ wins. `lab` path `bigint_ecpp` is therefore **not** in the `parallel` set.

Re-entrancy: never call `is_prime(n)` from inside `ecpp_primality(n)`; never ECPP on an integer $\ge$ the current $n$; cofactor proofs use `_prove_strictly_smaller` and **never AKS**.

## Dispatch

```text
still-larger n (past cubic / u128 trial)
  n.bit_length() ≥ 256
    → ecpp_primality(n, max_h=16) first
         class-number-1 (13 D); peel m with Montgomery ECM
         then small-h CM (h(D) ≤ 16)
         True / False → settle
  else combined BLS, then the same ECPP
  None → _aks_is_prime
```

`lab(n)["path"]` is `bigint_ecpp` when ECPP settles. The 147-bit CLI default `DEFAULT_N` stays on `u128_nm1` (n−1 cooperates). It is **not** moved to a 100-digit prime.

## Certificates (design)

`is_prime` / `ecpp_primality` return a boolean only. They never build a certificate tree.

`primality_certificate` follows the **same ladder** and is meant to emit `kind` equal to which theorem settled (`bls` / `ecpp` / `pratt` / `axiom`). That emission is the certificate PR (not on every branch yet). Until then, $n\ge 2^{64}$ outside `cubic_complete_ready` returns `{"n": n, "kind": "unsupported"}` **without** calling `is_prime`, ECPP, or AKS — refuse the API rather than hang in Pratt `n-1`.

Designed ECPP cert (`kind='ecpp'`): $D$, Cornacchia $(t,v)$, curve $(a,b)$, $m=n+1\pm t$, cofactor $c$, point $P$, recursive `q_cert`. Verifier is arithmetic, no search: $t^2+|D|v^2=4n$, $q\ge\mathrm{gk\_min\_q}(n)$, $P$ on $E$, $[c]P\ne O$ and $[m]P=O$, then recurse. Combined BLS certs store Combined Theorem 1’s cubic products, **not** $FG>\sqrt{n}$.

## Related

- [n−1 / BLS](nm1-proof.md) — Combined Theorem 1; C-less cubic wall
- [Engines](engines.md) — full ladder
- [Restrictions](restrictions.md)
- [`docs/ALGORITHM_HISTORY.md`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md)
