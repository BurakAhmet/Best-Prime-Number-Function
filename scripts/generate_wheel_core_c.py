#!/usr/bin/env python3
"""Regenerate is_prime_data/wheel_core.c (deterministic; no external prime libs).

Emits a compact OpenMP C engine:
  * precomputed odd primes up to PRE_MAX plus 2-adic inverses / thresholds
    (exact wrap-mul divisibility, no DIV on the mid-size path)
  * wheel-30 segmented sieve + 8-way 2-adic prime-only trial for larger isqrt(n)
    (Newton inv64 from a 16-bit table; exact: odd p | n iff (n*inv)*p < 2^64)
  * memcpy presieve of 7·11·13·17 plus AVX2/scalar OR of 19·23·29
  * contiguous per-thread ranges with persisted uint32 byte-index marks (no per-segment DIV)
  * DELTA[64] extract: one table lookup from ctzll instead of (byte,residue) math
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
 * INV16[(p>>1)&32767] is p^{-1} mod 2^16; two Newton steps lift to mod 2^64.
 * Eight independent inverses hide MUL latency on OoO CPUs.
 */
static uint16_t INV16[32768];
static int INV16_READY = 0;
static void ensure_inv16(void) {
    if (INV16_READY) return;
    for (uint32_t i = 0; i < 32768u; i++) {
        uint32_t a = 2u * i + 1u;
        uint32_t x = INV8[i & 127u];
        x *= 2u - a * x; /* 8 → 16 bits */
        INV16[i] = (uint16_t)x;
    }
    INV16_READY = 1;
}

static inline uint64_t inv64_odd(uint64_t p) {
    uint64_t x = INV16[((uint32_t)p >> 1) & 32767u];
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
    uint64_t x0 = INV16[((uint32_t)p0 >> 1) & 32767u], x1 = INV16[((uint32_t)p1 >> 1) & 32767u];
    uint64_t x2 = INV16[((uint32_t)p2 >> 1) & 32767u], x3 = INV16[((uint32_t)p3 >> 1) & 32767u];
    uint64_t x4 = INV16[((uint32_t)p4 >> 1) & 32767u], x5 = INV16[((uint32_t)p5 >> 1) & 32767u];
    uint64_t x6 = INV16[((uint32_t)p6 >> 1) & 32767u], x7 = INV16[((uint32_t)p7 >> 1) & 32767u];
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
/* DELTA[tz] = (tz>>3)*30 + WR30[tz&7] — one lookup from ctzll of a wheel-30 word. */
static const uint8_t DELTA[64] = {
1,7,11,13,17,19,23,29,31,37,41,43,47,49,53,59,
61,67,71,73,77,79,83,89,91,97,101,103,107,109,113,119,
121,127,131,133,137,139,143,149,151,157,161,163,167,169,173,179,
181,187,191,193,197,199,203,209,211,217,221,223,227,229,233,239,
};

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
            uint64_t q;
            if (num <= UINT32_MAX && span30 <= UINT32_MAX)
                q = (uint32_t)num / (uint32_t)span30;
            else
                q = num / span30;
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

/* First wheel-30 byte index (from 0) of residue ri for prime p, at or after T. */
static inline uint32_t first_mark_g(uint32_t p, uint32_t inv30, int ri, uint64_t T) {
    uint32_t r = WR30[ri];
    uint32_t rp = r % p;
    uint32_t k30 = (uint32_t)(((uint64_t)(p - rp) * inv30) % p);
    uint64_t m = 30ull * k30 + r;
    uint64_t span30 = 30ull * p;
    if (m < T) {
        uint64_t num = T - m;
        uint64_t q = (num <= UINT32_MAX && span30 <= UINT32_MAX)
                         ? (uint32_t)num / (uint32_t)span30
                         : num / span30;
        m += q * span30;
        if (m < T) m += span30;
    }
    return (uint32_t)(m / 30ull);
}

/*
 * Mark residue ri from global byte index ng; return next global index past
 * this segment. Index form (F11-safe): never compute e-s after s passes e.
 */
static inline uint32_t w30_mark_from_g(uint8_t *seg, uint32_t nbytes, uint32_t g0,
                                       uint32_t ng, uint32_t p, int ri) {
    if (ng < g0) return ng;
    uint32_t bi = ng - g0;
    if (bi >= nbytes) return ng;
    uint8_t bit = (uint8_t)(1u << ri);
    uint32_t st = p;
    uint32_t st4 = st << 2;
    for (; (uint64_t)bi + st4 < nbytes; bi += st4) {
        seg[bi] |= bit;
        seg[bi + st] |= bit;
        seg[bi + 2 * st] |= bit;
        seg[bi + 3 * st] |= bit;
    }
    for (; bi < nbytes; bi += st) seg[bi] |= bit;
    return g0 + bi;
}

static uint32_t INV30_CACHE[PRE_NP];
static int INV30_READY = 0;
static void ensure_inv30(void) {
    if (INV30_READY) return;
    for (int k = 0; k < PRE_NP; k++)
        INV30_CACHE[k] = inv_mod_prime(30u % PRE_P[k], PRE_P[k]);
    INV30_READY = 1;
}

/* Repeating wheel-30 bitmap of multiples of 7,11,13,17. Built once; tiled
 * onto each segment with memcpy (replaces memset + those four mark streams).
 * Pattern marks every multiple, including < p^2, so wrapping onto large bases
 * stays exact. A second 19·23·29 pattern is OR'd on top (sequential beats
 * three extra strided streams). */
#define PS_LEN 17017u
#define PS2_LEN 12673u /* 19*23*29 */
static uint8_t PRESIEVE[PS_LEN];
static uint8_t PRESIEVE2[PS2_LEN];
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
    memset(PRESIEVE2, 0, PS2_LEN);
    static const uint32_t ps2[3] = {19, 23, 29};
    for (int t = 0; t < 3; t++) {
        uint32_t p = ps2[t];
        uint32_t inv30 = inv_mod_prime(30u % p, p);
        w30_mark_prime(PRESIEVE2, PS2_LEN, 0, 30ull * PS2_LEN - 1, p, inv30, p);
    }
    PRESIEVE_READY = 1;
}

static inline void or_bytes(uint8_t *dst, const uint8_t *src, uint64_t n) {
    uint64_t i = 0;
#if defined(__AVX2__)
    for (; i + 32 <= n; i += 32) {
        __m256i a = _mm256_loadu_si256((const __m256i *)(dst + i));
        __m256i b = _mm256_loadu_si256((const __m256i *)(src + i));
        _mm256_storeu_si256((__m256i *)(dst + i), _mm256_or_si256(a, b));
    }
#endif
    for (; i + 8 <= n; i += 8) {
        uint64_t a, b;
        memcpy(&a, dst + i, 8);
        memcpy(&b, src + i, 8);
        a |= b;
        memcpy(dst + i, &a, 8);
    }
    for (; i < n; i++) dst[i] |= src[i];
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
    uint64_t idx2 = (base / 30ull) % PS2_LEN;
    done = 0;
    while (done < nbytes) {
        uint64_t chunk = PS2_LEN - idx2;
        if (chunk > nbytes - done) chunk = nbytes - done;
        or_bytes(seg + done, PRESIEVE2 + idx2, chunk);
        done += chunk;
        idx2 = 0;
    }
}

static int w30_nbytes_bits(uint64_t limit) {
    /* Persist + contiguous ranges make smaller segments cheap; 128 KiB
     * fits the sieve in L2 better than 256 KiB on the measured Zen 2. */
    if (limit >= 20000000ull) return 17;
    return 16;
}

/* Shared OpenMP layout: each thread owns a contiguous run of segments and
 * walks mark positions forward (one first-m DIV, then pointer arithmetic). */
static void seg_bounds(uint64_t start0, uint64_t limit, uint64_t NBYTES,
                       int tid, int nt, uint64_t *aligned0, uint64_t *s0,
                       uint64_t *s1, uint64_t *span) {
    *span = NBYTES * 30ull;
    *aligned0 = (start0 / 30ull) * 30ull;
    uint64_t total_bytes = (limit / 30ull) - (*aligned0 / 30ull) + 1;
    uint64_t nsegs = (total_bytes + NBYTES - 1) / NBYTES;
    *s0 = ((uint64_t)tid * nsegs) / (uint64_t)nt;
    *s1 = ((uint64_t)(tid + 1) * nsegs) / (uint64_t)nt;
}

static uint32_t *init_nextg(int k_mark0, int np, uint64_t origin) {
    int nmark = np - k_mark0;
    if (nmark <= 0) return NULL;
    uint32_t *nextg = (uint32_t *)malloc(sizeof(uint32_t) * (size_t)nmark * 8u);
    if (!nextg) return NULL;
    for (int k = k_mark0; k < np; k++) {
        uint32_t p = PRE_P[k];
        uint64_t p2 = (uint64_t)p * (uint64_t)p;
        uint64_t T = p2 > origin ? p2 : origin;
        int slot = (k - k_mark0) * 8;
        for (int ri = 0; ri < 8; ri++)
            nextg[slot + ri] = first_mark_g(p, INV30_CACHE[k], ri, T);
    }
    return nextg;
}

static inline void mark_segment(uint8_t *seg, uint32_t nbytes, uint32_t g0,
                                uint64_t hi, int k_mark0, int np, uint32_t *nextg) {
    if (!nextg) return;
    for (int k = k_mark0; k < np; k++) {
        uint32_t p = PRE_P[k];
        uint64_t p2 = (uint64_t)p * (uint64_t)p;
        if (p2 > hi) break;
        int slot = (k - k_mark0) * 8;
        for (int ri = 0; ri < 8; ri++)
            nextg[slot + ri] = w30_mark_from_g(
                seg, nbytes, g0, nextg[slot + ri], p, ri);
    }
}

__attribute__((hot))
static int seg_primes_u64(uint64_t n, uint64_t limit, int parallel) {
    if (!trial_pre_u64(n, PRE_MAX)) return 0;
    if (limit <= PRE_MAX) return 1;
    ensure_inv16();

    uint64_t bmax = isqrt_u64(limit) + 1;
    if (bmax < 3) bmax = 3;
    int np = 0;
    while (np < PRE_NP && (uint64_t)PRE_P[np] <= bmax) np++;
    if (np < 1) return 1;

    int k0 = 0;
    while (k0 < np && PRE_P[k0] < 7) k0++;
    ensure_presieve();
    ensure_inv30();
    int k_mark0 = k0;
    while (k_mark0 < np && PRE_P[k_mark0] <= 29) k_mark0++;

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
        uint64_t aligned0, s0, s1, span;
        seg_bounds(start0, limit, NBYTES, tid, nt, &aligned0, &s0, &s1, &span);
        uint64_t origin = aligned0 + s0 * span;
        uint32_t *nextg = (s0 < s1) ? init_nextg(k_mark0, np, origin) : NULL;
        if (seg) {
            for (uint64_t s = s0; s < s1 && !found; s++) {
                uint64_t base = aligned0 + s * span;
                uint64_t hi = base + span - 1;
                if (hi > limit) hi = limit;
                if (base > hi) continue;
                uint64_t nbytes = (hi - base) / 30ull + 1;
                if (nbytes > NBYTES) nbytes = NBYTES;
                fill_presieve(seg, nbytes, base);
                mark_segment(seg, (uint32_t)nbytes, (uint32_t)(base / 30ull), hi,
                             k_mark0, np, nextg);

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
                        uint64_t p = base + bi * 30ull + (uint64_t)DELTA[tz];
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
        free(nextg);
    }
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
    ensure_inv30();
    int k_mark0 = k0;
    while (k_mark0 < np && PRE_P[k_mark0] <= 29) k_mark0++;

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
        uint64_t aligned0, s0, s1, span;
        seg_bounds(start0, limit, NBYTES, tid, nt, &aligned0, &s0, &s1, &span);
        uint64_t origin = aligned0 + s0 * span;
        uint32_t *nextg = (s0 < s1) ? init_nextg(k_mark0, np, origin) : NULL;
        if (seg) {
            for (uint64_t s = s0; s < s1 && !found; s++) {
                uint64_t base = aligned0 + s * span;
                uint64_t hi = base + span - 1;
                if (hi > limit) hi = limit;
                if (base > hi) continue;
                uint64_t nbytes = (hi - base) / 30ull + 1;
                if (nbytes > NBYTES) nbytes = NBYTES;
                fill_presieve(seg, nbytes, base);
                mark_segment(seg, (uint32_t)nbytes, (uint32_t)(base / 30ull), hi,
                             k_mark0, np, nextg);

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
                        uint64_t p = base + bi * 30ull + (uint64_t)DELTA[tz];
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
        free(nextg);
    }
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
        "#ifdef __AVX2__",
        "#include <immintrin.h>",
        "#endif",
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
