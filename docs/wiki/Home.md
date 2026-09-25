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
| 256 bits up to 800 bits | Elliptic-curve proof (FastECPP) |
| 800 bits and wider | Cyclotomic proof, then FastECPP if that modulus is no longer enough |

Stochastic Miller–Rabin and external prime libraries are not the engine. AKS is not in the library.

On this machine a hard 64-bit check is about 2 ms end to end, and the 147-bit default is about 5 ms.

## Try it from the shell

```bash
pip install best-prime-number-function
is-prime 1000000007
```

With no argument, `is-prime` checks the 147-bit default. The install guide, the function list, and the proof write-ups are in the [library guide](guide/).

## Pages

| | |
|--|--|
| [Library guide](guide/) | Install, API, CLI, engines |
| [Library reference](Library) | Every public function |
| [Algorithm overview](Algorithm-overview) | Which proof runs |
| [Restrictions](Project-restrictions) | What the project will not do |
| [Benchmarks](Benchmarks) | End-to-end CLI time |
| [Hall of fame](Hall-of-fame) | Specimen primes |
