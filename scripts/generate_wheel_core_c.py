#!/usr/bin/env python3
"""Regenerate is_prime_data/wheel_core.c (deterministic; no external prime libs).

Emits a compact OpenMP C engine:
  * precomputed odd primes up to PRE_MAX plus 2-adic inverses / thresholds
    (exact wrap-mul divisibility, no DIV on the mid-size path)
  * wheel-30 segmented sieve + 8-way 2-adic prime-only trial for larger isqrt(n)
    (Newton inv64 from an 8-bit table; exact: odd p | n iff (n*inv)*p < 2^64)
  * memcpy presieve of 7·11·13·17 (pattern length 17017) + 32-bit mark starts
  * uint64 ctzll extract of unset wheel-30 bits (8 bytes / iteration)
  * same sieve model for u128 full trial (128-bit DIV; wrap-mul is 64-bit)

The 9699690-wheel table is intentionally *not* embedded: it bloated the .so
and lost to prime-only trial once a modest prime table is available. Numba /
stdlib fallbacks in is_prime.py still use the on-disk wheel assets.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "is_prime_data"

# Covers default e2e mid-size primes (12-digit isqrt = 999_999) with headroom.
PRE_MAX = 1_048_576  # 2^20

BODY = r"""
/* BEGIN_WHEEL_CORE_BODY */

static inline uint64_t isqrt_u64(uint64_t n) {
    if (n < 2) return n;
    int lz = __builtin_clzll(n);
    int b = 64 - lz;
    uint64_t x = 1ull << ((unsigned)(b + 1) / 2);
    if (x == 0) x = UINT64_C(0xffffffffffffffff);
    for (;;) {
        uint64_t y = (x + n / x) >> 1;
        if (y >= x) return x;
        x = y;
    }
}

/* Largest index i with PRE_P[i] <= limit (exclusive end). */
static int pre_end_for_limit(uint64_t limit) {
    int lo = 0, hi = PRE_NP;
    while (lo < hi) {
        int mid = lo + ((hi - lo) >> 1);
        if ((uint64_t)PRE_P[mid] <= limit) lo = mid + 1;
        else hi = mid;
    }
    return lo;
}

/*
 * Exact 2-adic divisibility: for odd p, n % p == 0 iff
 * (n * inv64(p)) <= floor((2^64-1)/p)  (uint64 wrap).
 * 8-way independent muls hide latency on OoO CPUs.
 */
__attribute__((hot))
static int trial_pre_u64(uint64_t n, uint64_t limit) {
    int end = pre_end_for_limit(limit);
    int i = 0;
    for (; i + 8 <= end; i += 8) {
        if (n * PRE_INV[i] <= PRE_TH[i] || n * PRE_INV[i + 1] <= PRE_TH[i + 1] ||
            n * PRE_INV[i + 2] <= PRE_TH[i + 2] || n * PRE_INV[i + 3] <= PRE_TH[i + 3] ||
            n * PRE_INV[i + 4] <= PRE_TH[i + 4] || n * PRE_INV[i + 5] <= PRE_TH[i + 5] ||
            n * PRE_INV[i + 6] <= PRE_TH[i + 6] || n * PRE_INV[i + 7] <= PRE_TH[i + 7])
            return 0;
    }
    for (; i < end; i++) {
        if (n * PRE_INV[i] <= PRE_TH[i]) return 0;
    }
    return 1;
}

/*
 * Exact 64-bit divisibility without DIV.
 * Theorem (odd p, n < 2^64): p | n  iff  (n * p^{-1} mod 2^64) * p  < 2^64.
 * INV8[(p>>1)&127] is p^{-1} mod 256; three Newton steps lift to mod 2^64.
 * Eight independent inverses hide MUL latency on OoO CPUs.
 */
static inline uint64_t inv64_odd(uint64_t p) {
    uint64_t x = INV8[(p >> 1) & 127];
    x *= 2 - p * x;
    x *= 2 - p * x;
    x *= 2 - p * x;
    return x;
}

static inline int divides_u64(uint64_t n, uint64_t p) {
    uint64_t q = n * inv64_odd(p);
    return ((unsigned __int128)q * p) >> 64 == 0;
}

static inline int any_div8_u64(uint64_t n, const uint64_t *b) {
    uint64_t p0 = b[0], p1 = b[1], p2 = b[2], p3 = b[3];
    uint64_t p4 = b[4], p5 = b[5], p6 = b[6], p7 = b[7];
    uint64_t x0 = INV8[(p0 >> 1) & 127], x1 = INV8[(p1 >> 1) & 127];
    uint64_t x2 = INV8[(p2 >> 1) & 127], x3 = INV8[(p3 >> 1) & 127];
    uint64_t x4 = INV8[(p4 >> 1) & 127], x5 = INV8[(p5 >> 1) & 127];
    uint64_t x6 = INV8[(p6 >> 1) & 127], x7 = INV8[(p7 >> 1) & 127];
    x0 *= 2 - p0 * x0; x1 *= 2 - p1 * x1; x2 *= 2 - p2 * x2; x3 *= 2 - p3 * x3;
    x4 *= 2 - p4 * x4; x5 *= 2 - p5 * x5; x6 *= 2 - p6 * x6; x7 *= 2 - p7 * x7;
    x0 *= 2 - p0 * x0; x1 *= 2 - p1 * x1; x2 *= 2 - p2 * x2; x3 *= 2 - p3 * x3;
    x4 *= 2 - p4 * x4; x5 *= 2 - p5 * x5; x6 *= 2 - p6 * x6; x7 *= 2 - p7 * x7;
    x0 *= 2 - p0 * x0; x1 *= 2 - p1 * x1; x2 *= 2 - p2 * x2; x3 *= 2 - p3 * x3;
    x4 *= 2 - p4 * x4; x5 *= 2 - p5 * x5; x6 *= 2 - p6 * x6; x7 *= 2 - p7 * x7;
    uint64_t q0 = n * x0, q1 = n * x1, q2 = n * x2, q3 = n * x3;
    uint64_t q4 = n * x4, q5 = n * x5, q6 = n * x6, q7 = n * x7;
    return ((unsigned __int128)q0 * p0) >> 64 == 0 ||
           ((unsigned __int128)q1 * p1) >> 64 == 0 ||
           ((unsigned __int128)q2 * p2) >> 64 == 0 ||
           ((unsigned __int128)q3 * p3) >> 64 == 0 ||
           ((unsigned __int128)q4 * p4) >> 64 == 0 ||
           ((unsigned __int128)q5 * p5) >> 64 == 0 ||
           ((unsigned __int128)q6 * p6) >> 64 == 0 ||
           ((unsigned __int128)q7 * p7) >> 64 == 0;
}

static int precheck(uint64_t n) {
    if (n < 2) return 0;
    if (n < 4) return 1;
    if ((n & 1ull) == 0) return 0;
    static const uint64_t P[] = {
        3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,
        101,103,107,109,113,127,131,137,139,149,151,157,163,167,173,179,181,
        191,193,197,199,211,223,227,229,233,239,241,251,257,263,269,271
    };
    for (int k = 0; k < (int)(sizeof P / sizeof P[0]); k++) {
        uint64_t p = P[k];
        if (n == p) return 1;
        if (n % p == 0) return 0;
        if (p * p > n) return 1;
    }
    return -1;
}

/*
 * Wheel-30 segmented sieve (1 byte / 30 numbers, bits = residues
 * 1,7,11,13,17,19,23,29) then 8-way 2-adic prime-only trial.
 * Bakes out 2/3/5 so those hottest marking streams disappear.
 * Fully deterministic; sieve is ours (no primesieve / external prime engine).
 */
static const uint8_t WR30[8] = {1, 7, 11, 13, 17, 19, 23, 29};

static uint32_t inv_mod_prime(uint32_t a, uint32_t p) {
    int64_t t = 0, nt = 1;
    int64_t r = (int64_t)p, nr = (int64_t)(a % p);
    while (nr) {
        int64_t q = r / nr, tmp = nt;
        nt = t - q * nt;
        t = tmp;
        tmp = nr;
        nr = r - q * nr;
        r = tmp;
    }
    if (t < 0) t += (int64_t)p;
    return (uint32_t)t;
}

static inline void w30_mark_prime(uint8_t *seg, uint64_t nbytes, uint64_t base,
                                  uint64_t hi, uint64_t p, uint32_t inv30,
                                  uint64_t p2) {
    uint64_t span30 = 30ull * p;
    uint64_t st = p;
    uint32_t pu = (uint32_t)p;
    for (int ri = 0; ri < 8; ri++) {
        uint32_t r = WR30[ri];
        uint32_t rp = r % pu;
        uint32_t k30 = (uint32_t)(((uint64_t)(pu - rp) * inv30) % pu);
        uint64_t m = 30ull * k30 + r;
        uint64_t T = p2 > base ? p2 : base;
        if (m < T) {
            uint64_t num = T - m;
            uint64_t q = num / span30;
            m += q * span30;
            if (m < T) m += span30;
        }
        if (m > hi) continue;
        uint64_t bi = (m - base) / 30ull;
        uint8_t bit = (uint8_t)(1u << ri);
        uint64_t st4 = st << 2;
        for (; bi + st4 < nbytes; bi += st4) {
            seg[bi] |= bit;
            seg[bi + st] |= bit;
            seg[bi + 2 * st] |= bit;
            seg[bi + 3 * st] |= bit;
        }
        for (; bi < nbytes; bi += st) seg[bi] |= bit;
    }
}

/* Repeating wheel-30 bitmap of multiples of 7,11,13,17. Built once; tiled
 * onto each segment with memcpy (replaces memset + those four mark streams).
 * Pattern marks every multiple, including < p^2, so wrapping onto large bases
 * stays exact. */
#define PS_LEN 17017u
static uint8_t PRESIEVE[PS_LEN];
static int PRESIEVE_READY = 0;

static void ensure_presieve(void) {
    if (PRESIEVE_READY) return;
    memset(PRESIEVE, 0, PS_LEN);
    static const uint32_t ps[4] = {7, 11, 13, 17};
    for (int t = 0; t < 4; t++) {
        uint32_t p = ps[t];
        uint32_t inv30 = inv_mod_prime(30u % p, p);
        w30_mark_prime(PRESIEVE, PS_LEN, 0, 30ull * PS_LEN - 1, p, inv30, p);
    }
    PRESIEVE_READY = 1;
}

static inline void fill_presieve(uint8_t *seg, uint64_t nbytes, uint64_t base) {
    uint64_t idx = (base / 30ull) % PS_LEN;
    uint64_t done = 0;
    while (done < nbytes) {
        uint64_t chunk = PS_LEN - idx;
        if (chunk > nbytes - done) chunk = nbytes - done;
        memcpy(seg + done, PRESIEVE + idx, (size_t)chunk);
        done += chunk;
        idx = 0;
    }
}

static int w30_nbytes_bits(uint64_t limit) {
    if (limit >= 500000000ull) return 18; /* 256 KiB — L2-friendly hard path */
    if (limit >= 20000000ull) return 17;
    return 16;
}

__attribute__((hot))
static int seg_primes_u64(uint64_t n, uint64_t limit, int parallel) {
    if (!trial_pre_u64(n, PRE_MAX)) return 0;
    if (limit <= PRE_MAX) return 1;

    uint64_t bmax = isqrt_u64(limit) + 1;
    if (bmax < 3) bmax = 3;
    int np = 0;
    while (np < PRE_NP && (uint64_t)PRE_P[np] <= bmax) np++;
    if (np < 1) return 1;

    int k0 = 0;
    while (k0 < np && PRE_P[k0] < 7) k0++;
    ensure_presieve();
    int k_mark0 = k0;
    while (k_mark0 < np && PRE_P[k_mark0] <= 17) k_mark0++;
    uint32_t *inv30 = (uint32_t *)malloc(sizeof(uint32_t) * (size_t)np);
    if (!inv30) return 0;
    for (int k = k_mark0; k < np; k++)
        inv30[k] = inv_mod_prime(30u % PRE_P[k], PRE_P[k]);

    volatile int found = 0;
    uint64_t start0 = (uint64_t)PRE_MAX + 1;
    if (start0 < 7) start0 = 7;
    const uint64_t NBYTES = 1ull << w30_nbytes_bits(limit);
    int use_parallel = 0;
#ifdef _OPENMP
    use_parallel = parallel && (limit >= PARALLEL_SEG_MIN);
#endif

#ifdef _OPENMP
#pragma omp parallel shared(found) if(use_parallel)
#endif
    {
#ifdef _OPENMP
        int tid = omp_get_thread_num();
        int nt = omp_get_num_threads();
#else
        int tid = 0, nt = 1;
        (void)use_parallel;
#endif
        uint8_t *seg = (uint8_t *)malloc((size_t)NBYTES);
        uint64_t buf[8];
        uint64_t span = NBYTES * 30ull;
        uint64_t stride = span * (uint64_t)nt;
        uint64_t origin = (start0 / 30ull) * 30ull + (uint64_t)tid * span;
        if (seg) {
            for (uint64_t base = origin; base <= limit && !found; base += stride) {
                uint64_t hi = base + span - 1;
                if (hi > limit) hi = limit;
                if (base > hi) continue;
                uint64_t nbytes = (hi - base) / 30ull + 1;
                if (nbytes > NBYTES) nbytes = NBYTES;
                fill_presieve(seg, nbytes, base);

                for (int k = k_mark0; k < np; k++) {
                    uint64_t p = PRE_P[k];
                    uint64_t p2 = p * p;
                    if (p2 > hi) break;
                    w30_mark_prime(seg, nbytes, base, hi, p, inv30[k], p2);
                }

                int nb = 0;
                uint64_t bi = 0;
                uint64_t n8 = nbytes & ~(uint64_t)7;
                for (; bi < n8; bi += 8) {
                    uint64_t w;
                    memcpy(&w, seg + bi, 8);
                    w = ~w;
                    if (!w) continue;
                    do {
                        int tz = __builtin_ctzll(w);
                        w &= w - 1;
                        int b = tz >> 3;
                        int ri = tz & 7;
                        uint64_t p = base + (bi + (uint64_t)b) * 30ull + (uint64_t)WR30[ri];
                        if (p < start0) continue;
                        if (p > limit) {
                            w = 0;
                            break;
                        }
                        buf[nb++] = p;
                        if (nb == 8) {
                            if (any_div8_u64(n, buf)) {
                                found = 1;
                                goto done_u64;
                            }
                            nb = 0;
                        }
                    } while (w);
                }
                for (; bi < nbytes; bi++) {
                    uint8_t bits = (uint8_t)~seg[bi];
                    uint64_t blk = base + bi * 30ull;
                    while (bits) {
                        int ri = __builtin_ctz((unsigned)bits);
                        bits = (uint8_t)(bits & (bits - 1));
                        uint64_t p = blk + (uint64_t)WR30[ri];
                        if (p < start0) continue;
                        if (p > limit) break;
                        buf[nb++] = p;
                        if (nb == 8) {
                            if (any_div8_u64(n, buf)) {
                                found = 1;
                                goto done_u64;
                            }
                            nb = 0;
                        }
                    }
                }
                if (!found) {
                    for (int t = 0; t < nb; t++) {
                        if (divides_u64(n, buf[t])) {
                            found = 1;
                            break;
                        }
                    }
                }
            done_u64:;
            }
            free(seg);
        }
    }
    free(inv30);
    return !found;
}

int is_prime_u64_core(uint64_t n, int parallel) {
    int pc = precheck(n);
    if (pc >= 0) return pc;
    uint64_t limit = isqrt_u64(n);
    if (limit <= PRE_MAX) return trial_pre_u64(n, limit);
    return seg_primes_u64(n, limit, parallel);
}

/* ---- 65..128-bit path: full deterministic prime trial ---- */

typedef unsigned __int128 u128;

static inline u128 u128_from_halves(uint64_t lo, uint64_t hi) {
    return ((u128)hi << 64) | (u128)lo;
}

static inline uint64_t isqrt_u128(u128 n) {
    if (n < 2) return (uint64_t)n;
    if (n <= (u128)UINT64_MAX) return isqrt_u64((uint64_t)n);
    uint64_t lo = 1ull << 32;
    uint64_t hi = UINT64_MAX;
    while (lo < hi) {
        uint64_t mid = lo + ((hi - lo + 1) >> 1);
        if (mid != 0 && n / mid >= mid) lo = mid;
        else hi = mid - 1;
    }
    return lo;
}

static int precheck_u128(u128 n) {
    if (n < 2) return 0;
    if (n < 4) return 1;
    if ((n & 1) == 0) return 0;
    static const uint64_t P[] = {
        3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,
        101,103,107,109,113,127,131,137,139,149,151,157,163,167,173,179,181,
        191,193,197,199,211,223,227,229,233,239,241,251,257,263,269,271
    };
    for (int k = 0; k < (int)(sizeof P / sizeof P[0]); k++) {
        uint64_t p = P[k];
        if (n == p) return 1;
        if (n % p == 0) return 0;
        if ((u128)p * (u128)p > n) return 1;
    }
    return -1;
}

__attribute__((hot))
static int trial_pre_u128(u128 n, uint64_t limit) {
    int end = pre_end_for_limit(limit);
    int i = 0;
    for (; i + 8 <= end; i += 8) {
        uint64_t p0 = PRE_P[i], p1 = PRE_P[i + 1], p2 = PRE_P[i + 2], p3 = PRE_P[i + 3];
        uint64_t p4 = PRE_P[i + 4], p5 = PRE_P[i + 5], p6 = PRE_P[i + 6], p7 = PRE_P[i + 7];
        if ((n % p0) == 0 || (n % p1) == 0 || (n % p2) == 0 || (n % p3) == 0 ||
            (n % p4) == 0 || (n % p5) == 0 || (n % p6) == 0 || (n % p7) == 0)
            return 0;
    }
    for (; i < end; i++) {
        if ((n % PRE_P[i]) == 0) return 0;
    }
    return 1;
}

static inline int any_div8_u128(u128 n, const uint64_t *b) {
    return (n % b[0]) == 0 || (n % b[1]) == 0 || (n % b[2]) == 0 || (n % b[3]) == 0 ||
           (n % b[4]) == 0 || (n % b[5]) == 0 || (n % b[6]) == 0 || (n % b[7]) == 0;
}

__attribute__((hot))
static int seg_primes_u128(u128 n, uint64_t limit, int parallel) {
    if (!trial_pre_u128(n, PRE_MAX)) return 0;
    if (limit <= PRE_MAX) return 1;

    uint64_t bmax = isqrt_u64(limit) + 1;
    if (bmax < 3) bmax = 3;
    int np = 0;
    while (np < PRE_NP && (uint64_t)PRE_P[np] <= bmax) np++;
    if (np < 1) return 1;

    int k0 = 0;
    while (k0 < np && PRE_P[k0] < 7) k0++;
    ensure_presieve();
    int k_mark0 = k0;
    while (k_mark0 < np && PRE_P[k_mark0] <= 17) k_mark0++;
    uint32_t *inv30 = (uint32_t *)malloc(sizeof(uint32_t) * (size_t)np);
    if (!inv30) return 0;
    for (int k = k_mark0; k < np; k++)
        inv30[k] = inv_mod_prime(30u % PRE_P[k], PRE_P[k]);

    volatile int found = 0;
    uint64_t start0 = (uint64_t)PRE_MAX + 1;
    if (start0 < 7) start0 = 7;
    const uint64_t NBYTES = 1ull << w30_nbytes_bits(limit);
    int use_parallel = 0;
#ifdef _OPENMP
    use_parallel = parallel && (limit >= PARALLEL_SEG_MIN);
#endif

#ifdef _OPENMP
#pragma omp parallel shared(found) if(use_parallel)
#endif
    {
#ifdef _OPENMP
        int tid = omp_get_thread_num();
        int nt = omp_get_num_threads();
#else
        int tid = 0, nt = 1;
        (void)use_parallel;
#endif
        uint8_t *seg = (uint8_t *)malloc((size_t)NBYTES);
        uint64_t buf[8];
        uint64_t span = NBYTES * 30ull;
        uint64_t stride = span * (uint64_t)nt;
        uint64_t origin = (start0 / 30ull) * 30ull + (uint64_t)tid * span;
        if (seg) {
            for (uint64_t base = origin; base <= limit && !found; base += stride) {
                uint64_t hi = base + span - 1;
                if (hi > limit) hi = limit;
                if (base > hi) continue;
                uint64_t nbytes = (hi - base) / 30ull + 1;
                if (nbytes > NBYTES) nbytes = NBYTES;
                fill_presieve(seg, nbytes, base);

                for (int k = k_mark0; k < np; k++) {
                    uint64_t p = PRE_P[k];
                    uint64_t p2 = p * p;
                    if (p2 > hi) break;
                    w30_mark_prime(seg, nbytes, base, hi, p, inv30[k], p2);
                }

                int nb = 0;
                uint64_t bi = 0;
                uint64_t n8 = nbytes & ~(uint64_t)7;
                for (; bi < n8; bi += 8) {
                    uint64_t w;
                    memcpy(&w, seg + bi, 8);
                    w = ~w;
                    if (!w) continue;
                    do {
                        int tz = __builtin_ctzll(w);
                        w &= w - 1;
                        int b = tz >> 3;
                        int ri = tz & 7;
                        uint64_t p = base + (bi + (uint64_t)b) * 30ull + (uint64_t)WR30[ri];
                        if (p < start0) continue;
                        if (p > limit) {
                            w = 0;
                            break;
                        }
                        buf[nb++] = p;
                        if (nb == 8) {
                            if (any_div8_u128(n, buf)) {
                                found = 1;
                                goto done_u128;
                            }
                            nb = 0;
                        }
                    } while (w);
                }
                for (; bi < nbytes; bi++) {
                    uint8_t bits = (uint8_t)~seg[bi];
                    uint64_t blk = base + bi * 30ull;
                    while (bits) {
                        int ri = __builtin_ctz((unsigned)bits);
                        bits = (uint8_t)(bits & (bits - 1));
                        uint64_t p = blk + (uint64_t)WR30[ri];
                        if (p < start0) continue;
                        if (p > limit) break;
                        buf[nb++] = p;
                        if (nb == 8) {
                            if (any_div8_u128(n, buf)) {
                                found = 1;
                                goto done_u128;
                            }
                            nb = 0;
                        }
                    }
                }
                if (!found) {
                    for (int t = 0; t < nb; t++) {
                        if ((n % buf[t]) == 0) {
                            found = 1;
                            break;
                        }
                    }
                }
            done_u128:;
            }
            free(seg);
        }
    }
    free(inv30);
    return !found;
}

/* n = hi * 2^64 + lo  (little-endian limbs). Full trial to isqrt(n). */
int is_prime_u128_core(uint64_t lo, uint64_t hi, int parallel) {
    u128 n = u128_from_halves(lo, hi);
    int pc = precheck_u128(n);
    if (pc >= 0) return pc;
    uint64_t limit = isqrt_u128(n);
    if (limit <= PRE_MAX) return trial_pre_u128(n, limit);
    return seg_primes_u128(n, limit, parallel);
}

"""


def _odd_primes_to(limit: int) -> list[int]:
    sv = bytearray(limit + 1)
    sv[0] = sv[1] = 1
    for p in range(2, int(limit**0.5) + 1):
        if sv[p]:
            continue
        step = p
        start = p * p
        sv[start : limit + 1 : step] = b"\x01" * (((limit - start) // step) + 1)
    return [p for p in range(3, limit + 1) if not sv[p]]


def _emit_u8(name: str, vals: list[int]) -> list[str]:
    lines = [f"static const uint8_t {name}[{len(vals)}] = {{"]
    row: list[str] = []
    for v in vals:
        row.append(str(int(v)))
        if len(row) == 16:
            lines.append(",".join(row) + ",")
            row = []
    if row:
        lines.append(",".join(row))
    lines.append("};")
    return lines


def _inv8_table() -> list[int]:
    """p^{-1} mod 256 for every odd byte; index = (p >> 1) & 127."""
    out: list[int] = []
    for i in range(128):
        a = 2 * i + 1
        x = a
        for _ in range(3):
            x = (x * (2 - a * x)) & 255
        if (a * x) & 255 != 1:
            raise SystemExit(f"INV8 build failed for a={a}")
        out.append(x)
    return out


def _emit_u32(name: str, vals: list[int]) -> list[str]:
    lines = [f"static const uint32_t {name}[{len(vals)}] = {{"]
    row: list[str] = []
    for v in vals:
        row.append(str(int(v)))
        if len(row) == 16:
            lines.append(",".join(row) + ",")
            row = []
    if row:
        lines.append(",".join(row))
    lines.append("};")
    return lines


def _emit_u64_hex(name: str, vals: list[int]) -> list[str]:
    lines = [f"static const uint64_t {name}[{len(vals)}] = {{"]
    row: list[str] = []
    for v in vals:
        row.append(f"0x{v:x}ull")
        if len(row) == 8:
            lines.append(",".join(row) + ",")
            row = []
    if row:
        lines.append(",".join(row))
    lines.append("};")
    return lines


def main() -> None:
    primes = _odd_primes_to(PRE_MAX)
    mod = 1 << 64
    invs = [pow(p, -1, mod) for p in primes]
    thresh = [(mod - 1) // p for p in primes]
    for p, inv in zip(primes, invs):
        if (p * inv) % mod != 1:
            raise SystemExit(f"bad 2-adic inverse for p={p}")

    lines = [
        "#include <stdint.h>",
        "#include <stdlib.h>",
        "#include <string.h>",
        "#ifdef _OPENMP",
        "#include <omp.h>",
        "#endif",
        f"#define PRE_MAX {PRE_MAX}u",
        f"#define PRE_NP {len(primes)}",
        "/* Parallel segmented sieve only when isqrt(n) is large enough that",
        "   OpenMP overhead is repaid (mid-size uses serial precomputed trial). */",
        "#define PARALLEL_SEG_MIN 10000000ull",
    ]
    lines.extend(_emit_u8("INV8", _inv8_table()))
    lines.extend(_emit_u32("PRE_P", primes))
    lines.extend(_emit_u64_hex("PRE_INV", invs))
    lines.extend(_emit_u64_hex("PRE_TH", thresh))
    out = "\n".join(lines) + "\n" + BODY
    dest = DATA / "wheel_core.c"
    dest.write_text(out)
    print(
        f"Wrote {dest} ({len(out)} bytes, {len(primes)} odd primes ≤ {PRE_MAX})"
    )


if __name__ == "__main__":
    main()
