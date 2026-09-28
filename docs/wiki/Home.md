# Check a number

Type a natural number. This page either finishes a proof or shows a factor.

> [!NOTE]
> The lab in this tab is an exhibit. The Python library is the same idea with a faster native core. A miss here is inconclusive; `is_prime` may still settle it.

<!-- acta-specimen -->

<div id="prime-lab-root"></div>

## What “prime” means here

`is_prime` returns true only when a proof finishes, and false only when compositeness is proved. Otherwise it raises `UnsettledPrimalityError`. It does not answer “probably.”

| Size | Proof |
|------|--------|
| Small, and most 64-bit values | Trial division up to the square root |
| Harder 64-bit, and up to 256 bits | Combined BLS on $n-1$ and $n+1$, then a cubic search if those will not factor |
| 256 bits and wider, in the library | Cyclotomic proof while the modulus ladder covers $\sqrt{n}$, through 5000 digits. $10^{999}+7$ is about 43 seconds on 12 cores. $10^{1099}+73$ is about 158 seconds |
| 256 bits and wider, in this tab | Same cyclotomic proof, including next and previous prime. 10^999+7 is about three minutes on 12 cores |

Stochastic Miller–Rabin and external prime libraries are not the engine. AKS is not in the library.

On this machine a hard 64-bit check is about 2 ms end to end. With no argument, `is-prime` checks the 150-digit prime $10^{149}+183$. **All factors** lists every positive divisor of the number in the box. The same deterministic factorization builds that list in `factors` in the Python library.

A 1000-digit prime, such as $10^{999}+7$, is a cyclotomic proof: about three minutes in this tab on 12 cores, and about 43 seconds in the Python library. The same proof covers every integer through 5000 digits. $10^{1099}+73$ took about 158 seconds in the library.

## Try it from the shell

```bash
pip install best-prime-number-function
is-prime 1000000007
```

The install guide, the function list, and the proof write-ups are in the [library guide](guide/).

## Pages

| | |
|--|--|
| [Library guide](guide/) | Install, API, CLI, engines |
| [Library reference](Library) | Every public function |
| [Algorithm overview](Algorithm-overview) | Which proof runs |
| [Restrictions](Project-restrictions) | What the project will not do |
| [Benchmarks](Benchmarks) | End-to-end CLI time |
| [Hall of fame](Hall-of-fame) | Specimen primes |
