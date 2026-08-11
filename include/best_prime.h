/* SPDX-License-Identifier: MIT
 *
 * Public C API for the in-tree OpenMP primality core
 * (is_prime_data/wheel_core.c). Build with scripts/compile_wheel_core.sh
 * or `make -C native`. Fully deterministic: no Miller–Rabin.
 *
 *   #include <best_prime.h>
 *   if (best_prime_u64(17, 1)) { /* prime */ }
 */
#ifndef BEST_PRIME_H
#define BEST_PRIME_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Return 1 if n is prime, 0 otherwise.
 * `parallel` is 0 for serial OpenMP, nonzero to use OMP_NUM_THREADS.
 * Result never depends on `parallel` or the thread schedule.
 */
int is_prime_u64_core(uint64_t n, int parallel);

/*
 * 65–128-bit n = lo + (hi << 64). Same contract as is_prime_u64_core.
 * Full trial while isqrt(n) is practical; not AKS.
 */
int is_prime_u128_core(uint64_t lo, uint64_t hi, int parallel);

/* Friendlier aliases (same symbols). */
#define best_prime_u64 is_prime_u64_core
#define best_prime_u128 is_prime_u128_core

#ifdef __cplusplus
}
#endif

#endif /* BEST_PRIME_H */
