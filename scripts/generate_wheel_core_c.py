#!/usr/bin/env python3
"""Regenerate is_prime_data/wheel_core.c from w9699690_u8.npy (deterministic)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "is_prime_data"

BODY = r"""
/* BEGIN_WHEEL_CORE_BODY */

static uint32_t RES_TO_WI[WHEEL_MOD];
static int RES_READY = 0;

static void ensure_res(void) {
    if (RES_READY) return;
    for (uint32_t i = 0; i < WHEEL_MOD; i++) RES_TO_WI[i] = 0xFFFFFFFFu;
    uint64_t x = WHEEL_START;
    for (int64_t wi = 0; wi < (int64_t)WHEEL_NW; wi++) {
        RES_TO_WI[(uint32_t)(x % WHEEL_MOD)] = (uint32_t)wi;
        x += WSTEPS[wi];
    }
    RES_READY = 1;
}

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

static void wheel_start_fast(uint64_t s, uint64_t *i_out, int64_t *wi_out) {
    ensure_res();
    if (s <= WHEEL_START) { *i_out = WHEEL_START; *wi_out = 0; return; }
    uint64_t block = (s / WHEEL_MOD) * WHEEL_MOD;
    uint32_t r = (uint32_t)(s % WHEEL_MOD);
    for (;;) {
        uint32_t wi = RES_TO_WI[r];
        if (wi != 0xFFFFFFFFu) { *i_out = block + r; *wi_out = (int64_t)wi; return; }
        r++; if (r == WHEEL_MOD) { r = 0; block += WHEEL_MOD; }
    }
}

/* 4-way mod ILP; no large auxiliary buffers (keeps e2e TIME low for moderate n). */
__attribute__((hot))
static int serial_wheel(uint64_t n, uint64_t limit) {
    uint64_t i = WHEEL_START;
    int64_t wi = 0;
    while (i + 128 <= limit) {
        if (wi + 32 <= (int64_t)WHEEL_NW) {
            for (int g = 0; g < 8; g++) {
                const uint8_t *ws = &WSTEPS[wi];
                uint64_t i0 = i;
                uint64_t i1 = i0 + ws[0];
                uint64_t i2 = i1 + ws[1];
                uint64_t i3 = i2 + ws[2];
                uint64_t r0 = n % i0;
                uint64_t r1 = n % i1;
                uint64_t r2 = n % i2;
                uint64_t r3 = n % i3;
                if (r0 == 0 || r1 == 0 || r2 == 0 || r3 == 0) return 0;
                i = i3 + ws[3];
                wi += 4;
            }
        } else {
            for (int k = 0; k < 32; k++) {
                if (n % i == 0) return 0;
                i += WSTEPS[wi];
                wi++;
                if (wi == (int64_t)WHEEL_NW) wi = 0;
            }
        }
        if (wi == (int64_t)WHEEL_NW) wi = 0;
    }
    while (i <= limit) {
        if (n % i == 0) return 0;
        i += WSTEPS[wi];
        wi++;
        if (wi == (int64_t)WHEEL_NW) wi = 0;
    }
    return 1;
}

__attribute__((hot))
static int parallel_wheel(uint64_t n, uint64_t limit) {
    ensure_res();
    volatile int found = 0;
#ifdef _OPENMP
#pragma omp parallel shared(found)
    {
        int tid = omp_get_thread_num();
        int nt = omp_get_num_threads();
        uint64_t span = limit - WHEEL_START + 1;
        uint64_t chunk = (span + (uint64_t)nt - 1) / (uint64_t)nt;
        uint64_t lo = WHEEL_START + (uint64_t)tid * chunk;
        uint64_t hi = lo + chunk - 1;
        if (hi > limit) hi = limit;
        if (lo <= limit && !found) {
            uint64_t i; int64_t wi;
            wheel_start_fast(lo, &i, &wi);
            while (i + 128 <= hi && !found) {
                if (wi + 32 <= (int64_t)WHEEL_NW) {
                    for (int g = 0; g < 8; g++) {
                        const uint8_t *ws = &WSTEPS[wi];
                        uint64_t i0 = i;
                        uint64_t i1 = i0 + ws[0];
                        uint64_t i2 = i1 + ws[1];
                        uint64_t i3 = i2 + ws[2];
                        uint64_t r0 = n % i0;
                        uint64_t r1 = n % i1;
                        uint64_t r2 = n % i2;
                        uint64_t r3 = n % i3;
                        if (r0 == 0 || r1 == 0 || r2 == 0 || r3 == 0) {
                            found = 1;
                            goto done_thread;
                        }
                        i = i3 + ws[3];
                        wi += 4;
                    }
                } else {
                    for (int k = 0; k < 32; k++) {
                        if (n % i == 0) { found = 1; goto done_thread; }
                        i += WSTEPS[wi];
                        wi++;
                        if (wi == (int64_t)WHEEL_NW) wi = 0;
                    }
                }
                if (wi == (int64_t)WHEEL_NW) wi = 0;
            }
            if (!found) {
                while (i <= hi) {
                    if (n % i == 0) { found = 1; break; }
                    i += WSTEPS[wi]; wi++;
                    if (wi == (int64_t)WHEEL_NW) wi = 0;
                }
            }
        }
    done_thread:;
    }
    return !found;
#else
    return serial_wheel(n, limit);
#endif
}

/*
 * Parallel segmented sieve + prime-only trial division.
 * For large isqrt(n), sieving out composites (~3.5x fewer mod operations than
 * the 9699690-wheel) more than pays for the sieve. Fully deterministic;
 * implements the sieve ourselves (no primesieve / external prime engine).
 */
__attribute__((hot))
static int parallel_seg_primes(uint64_t n, uint64_t limit) {
    if (limit < 3) return 1;

    uint64_t bmax = isqrt_u64(limit) + 1;
    if (bmax < 100) bmax = 100;
    if (bmax > limit) bmax = limit;

    uint8_t *sv = (uint8_t *)calloc((size_t)bmax + 1, 1);
    if (!sv) return serial_wheel(n, limit);
    for (uint64_t p = 2; p * p <= bmax; p++) {
        if (!sv[p]) {
            for (uint64_t j = p * p; j <= bmax; j += p) sv[j] = 1;
        }
    }
    uint32_t *primes = (uint32_t *)malloc(sizeof(uint32_t) * ((size_t)bmax / 2 + 8));
    if (!primes) { free(sv); return serial_wheel(n, limit); }
    int np = 0;
    for (uint64_t p = 2; p <= bmax; p++) {
        if (!sv[p]) primes[np++] = (uint32_t)p;
    }
    free(sv);

    for (int i = 0; i < np; i++) {
        uint64_t p = primes[i];
        if (p > limit) break;
        if (n % p == 0) { free(primes); return n == p; }
        if (p * p > n) { free(primes); return 1; }
    }
    if (bmax >= limit) { free(primes); return 1; }

    volatile int found = 0;
    uint64_t start = bmax + 1;
    if ((start & 1ull) == 0) start++;

    const uint64_t SEG_ODDS = 1u << 19;

#ifdef _OPENMP
#pragma omp parallel shared(found)
#endif
    {
        uint8_t *seg = (uint8_t *)malloc(SEG_ODDS);
        if (seg) {
#ifdef _OPENMP
            int tid = omp_get_thread_num();
            int nt = omp_get_num_threads();
#else
            int tid = 0, nt = 1;
#endif
            uint64_t stride = SEG_ODDS * 2 * (uint64_t)nt;
            for (uint64_t lo = start + (uint64_t)tid * SEG_ODDS * 2;
                 lo <= limit && !found;
                 lo += stride) {
                uint64_t hi = lo + SEG_ODDS * 2 - 2;
                if (hi > limit) hi = limit;
                if ((hi & 1ull) == 0) {
                    if (hi == 0) continue;
                    hi--;
                }
                if (lo > hi) continue;
                uint64_t n_odds = ((hi - lo) >> 1) + 1;
                if (n_odds > SEG_ODDS) n_odds = SEG_ODDS;
                memset(seg, 0, (size_t)n_odds);

                for (int k = 1; k < np; k++) {
                    uint64_t p = primes[k];
                    uint64_t p2 = p * p;
                    if (p2 > hi) break;
                    uint64_t m;
                    if (p2 >= lo) m = p2;
                    else {
                        uint64_t r = lo % p;
                        m = r ? lo + (p - r) : lo;
                    }
                    if ((m & 1ull) == 0) m += p;
                    uint64_t step = p << 1;
                    for (; m <= hi; m += step) {
                        uint64_t idx = (m - lo) >> 1;
                        if (idx < n_odds) seg[idx] = 1;
                    }
                }

                for (uint64_t idx = 0; idx < n_odds; idx++) {
                    if (seg[idx]) continue;
                    uint64_t p = lo + (idx << 1);
                    if (p > limit) break;
                    if (n % p == 0) {
                        if (n != p) found = 1;
                        break;
                    }
                }
            }
            free(seg);
        }
    }
    free(primes);
    return !found;
}

static int precheck(uint64_t n) {
    if (n < 2) return 0;
    if (n < 4) return 1;
    if ((n & 1ull) == 0) return 0;
    static const uint64_t P[] = {
        3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,
        101,103,107,109,113
    };
    for (int k = 0; k < (int)(sizeof P / sizeof P[0]); k++) {
        uint64_t p = P[k];
        if (n == p) return 1;
        if (n % p == 0) return 0;
        if (p * p > n) return 1;
    }
    return -1;
}

int is_prime_u64_core(uint64_t n, int parallel) {
    int pc = precheck(n);
    if (pc >= 0) return pc;
    uint64_t limit = isqrt_u64(n);
    if (parallel && limit >= PARALLEL_LIMIT) {
        if (limit >= SEG_PRIME_LIMIT) return parallel_seg_primes(n, limit);
        return parallel_wheel(n, limit);
    }
    return serial_wheel(n, limit);
}

"""


def main() -> None:
    w = np.load(DATA / "w9699690_u8.npy")
    nw = int(len(w))
    lines = [
        "#include <stdint.h>",
        "#include <stdlib.h>",
        "#include <string.h>",
        "#ifdef _OPENMP",
        "#include <omp.h>",
        "#endif",
        f"#define WHEEL_NW {nw}",
        "#define WHEEL_MOD 9699690u",
        "#define WHEEL_START 23ull",
        "#define PARALLEL_LIMIT 50000ull",
        "#define SEG_PRIME_LIMIT 200000000ull",
        f"static const uint8_t WSTEPS[{nw}] = {{",
    ]
    row = []
    for x in w:
        row.append(str(int(x)))
        if len(row) == 32:
            lines.append(",".join(row) + ",")
            row = []
    if row:
        lines.append(",".join(row))
    lines.append("};")
    out = "\n".join(lines) + "\n" + BODY
    (DATA / "wheel_core.c").write_text(out)
    print(f"Wrote {DATA / 'wheel_core.c'} ({len(out)} bytes)")


if __name__ == "__main__":
    main()
