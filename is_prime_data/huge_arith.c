/* In-tree modular exponentiation for huge odd moduli.
 *
 * Deterministic. No RNG. Not a primality oracle — arithmetic only.
 * Used by Tonelli / Fermat / Cornacchia on 512-bit+ n.
 *
 * Limbs are little-endian uint64. Requires GCC/Clang __uint128_t.
 *
 * Paths:
 *   small n  — CIOS Montgomery (schoolbook), 6-bit window
 *   large n  — school / Karatsuba / Toom-3 multiply + Barrett reduction
 *
 * The previous even-limb Karatsuba wrote one past a 2n-limb product
 * (add_n carry into p[4k]) and dropped borrow from z1's extra limbs.
 */

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define HUGE_MAX_LIMBS 1024
#define HUGE_WINDOW 6
#define HUGE_PRE (1u << HUGE_WINDOW)
#define KARAT_THRESH 16
#define TOOM_THRESH 64
#define BARRETT_THRESH 200
/* 8-bit NTT is correct but slower than Toom-3 at ≤1024 limbs (L=16n). */
#define NTT_THRESH 2048
#define NTT_MOD 998244353u
#define NTT_ROOT 3u

#ifdef _MSC_VER
int huge_powmod(const uint64_t *base, size_t nbase, const uint64_t *exp,
                size_t nexp, const uint64_t *mod, size_t nmod, uint64_t *out) {
    (void)base;
    (void)nbase;
    (void)exp;
    (void)nexp;
    (void)mod;
    (void)nmod;
    (void)out;
    return -1;
}
int huge_mul(const uint64_t *a, size_t na, const uint64_t *b, size_t nb,
             uint64_t *out) {
    (void)a;
    (void)na;
    (void)b;
    (void)nb;
    (void)out;
    return -1;
}
int huge_arith_max_limbs(void) { return 0; }
#else

typedef unsigned __int128 u128;

/* ------------------------------------------------------------------ */
/* tiny helpers                                                        */
/* ------------------------------------------------------------------ */

static int cmp_be(const uint64_t *a, const uint64_t *b, size_t n) {
    size_t i = n;
    while (i--) {
        if (a[i] != b[i]) {
            return a[i] > b[i] ? 1 : -1;
        }
    }
    return 0;
}

static uint64_t sub_n(uint64_t *a, const uint64_t *b, size_t n) {
    uint64_t br = 0;
    for (size_t i = 0; i < n; i++) {
        uint64_t ai = a[i];
        uint64_t bi = b[i];
        uint64_t t = ai - bi;
        uint64_t br1 = ai < bi;
        uint64_t t2 = t - br;
        uint64_t br2 = t < br;
        a[i] = t2;
        br = br1 | br2;
    }
    return br;
}

static uint64_t add_n_c(uint64_t *a, const uint64_t *b, size_t n) {
    uint64_t c = 0;
    for (size_t i = 0; i < n; i++) {
        u128 t = (u128)a[i] + b[i] + c;
        a[i] = (uint64_t)t;
        c = (uint64_t)(t >> 64);
    }
    return c;
}

static void add_spread(uint64_t *a, size_t na, const uint64_t *b, size_t nb) {
    if (nb > na) {
        nb = na;
    }
    uint64_t c = add_n_c(a, b, nb);
    size_t i = nb;
    while (c && i < na) {
        u128 t = (u128)a[i] + c;
        a[i] = (uint64_t)t;
        c = (uint64_t)(t >> 64);
        i++;
    }
}

static void sub_spread(uint64_t *a, size_t na, const uint64_t *b, size_t nb) {
    if (nb > na) {
        nb = na;
    }
    uint64_t br = sub_n(a, b, nb);
    size_t i = nb;
    while (br && i < na) {
        uint64_t ai = a[i];
        a[i] = ai - br;
        br = ai < br;
        i++;
    }
}

static void shl1_mod(uint64_t *x, const uint64_t *m, size_t n) {
    uint64_t c = 0;
    for (size_t i = 0; i < n; i++) {
        uint64_t t = (x[i] << 1) | c;
        c = x[i] >> 63;
        x[i] = t;
    }
    if (c || cmp_be(x, m, n) >= 0) {
        sub_n(x, m, n);
    }
}

static size_t trim(const uint64_t *a, size_t n) {
    while (n > 0 && a[n - 1] == 0) {
        n--;
    }
    return n;
}

/* ------------------------------------------------------------------ */
/* bump-pointer scratch                                                */
/* ------------------------------------------------------------------ */

typedef struct {
    uint64_t *base;
    size_t cap;
    size_t used;
} Pool;

static uint64_t *pool_alloc(Pool *p, size_t n) {
    if (!p || p->used + n > p->cap) {
        return NULL;
    }
    uint64_t *r = p->base + p->used;
    p->used += n;
    return r;
}

/* ------------------------------------------------------------------ */
/* schoolbook                                                          */
/* ------------------------------------------------------------------ */

static void school_mul_rect(uint64_t *p, const uint64_t *a, size_t na,
                            const uint64_t *b, size_t nb) {
    memset(p, 0, (na + nb) * sizeof(uint64_t));
    for (size_t i = 0; i < nb; i++) {
        u128 c = 0;
        uint64_t bi = b[i];
        for (size_t j = 0; j < na; j++) {
            c += (u128)p[i + j] + (u128)a[j] * bi;
            p[i + j] = (uint64_t)c;
            c >>= 64;
        }
        p[i + na] = (uint64_t)c;
    }
}

static void school_mul(uint64_t *p, const uint64_t *a, const uint64_t *b,
                       size_t n) {
    school_mul_rect(p, a, n, b, n);
}

/* ------------------------------------------------------------------ */
/* 8-bit NTT (mod 998244353). Coeffs of a 1024-limb product fit.       */
/* ------------------------------------------------------------------ */

static uint32_t ntt_mul32(uint32_t a, uint32_t b) {
    return (uint32_t)((uint64_t)a * b % NTT_MOD);
}

static uint32_t ntt_pow32(uint32_t a, uint32_t e) {
    uint32_t r = 1;
    while (e) {
        if (e & 1u) {
            r = ntt_mul32(r, a);
        }
        a = ntt_mul32(a, a);
        e >>= 1;
    }
    return r;
}

static uint32_t ntt_inv32(uint32_t a) { return ntt_pow32(a, NTT_MOD - 2); }

static void ntt_bitrev(uint32_t *a, size_t n) {
    size_t j = 0;
    for (size_t i = 1; i < n; i++) {
        size_t bit = n >> 1;
        for (; j & bit; bit >>= 1) {
            j ^= bit;
        }
        j ^= bit;
        if (i < j) {
            uint32_t t = a[i];
            a[i] = a[j];
            a[j] = t;
        }
    }
}

static void ntt_transform(uint32_t *a, size_t n, int invert) {
    ntt_bitrev(a, n);
    for (size_t len = 2; len <= n; len <<= 1) {
        uint32_t wlen = ntt_pow32(NTT_ROOT, (NTT_MOD - 1) / (uint32_t)len);
        if (invert) {
            wlen = ntt_inv32(wlen);
        }
        for (size_t i = 0; i < n; i += len) {
            uint32_t w = 1;
            size_t half = len >> 1;
            for (size_t j = 0; j < half; j++) {
                uint32_t u = a[i + j];
                uint32_t v = ntt_mul32(a[i + j + half], w);
                uint32_t s = u + v;
                if (s >= NTT_MOD) {
                    s -= NTT_MOD;
                }
                uint32_t d = u + NTT_MOD - v;
                if (d >= NTT_MOD) {
                    d -= NTT_MOD;
                }
                a[i + j] = s;
                a[i + j + half] = d;
                w = ntt_mul32(w, wlen);
            }
        }
    }
    if (invert) {
        uint32_t ninv = ntt_inv32((uint32_t)n);
        for (size_t i = 0; i < n; i++) {
            a[i] = ntt_mul32(a[i], ninv);
        }
    }
}

static void ntt_split8(uint32_t *d, const uint64_t *a, size_t n) {
    for (size_t i = 0; i < n; i++) {
        uint64_t w = a[i];
        d[8 * i + 0] = (uint32_t)(w & 0xffu);
        d[8 * i + 1] = (uint32_t)((w >> 8) & 0xffu);
        d[8 * i + 2] = (uint32_t)((w >> 16) & 0xffu);
        d[8 * i + 3] = (uint32_t)((w >> 24) & 0xffu);
        d[8 * i + 4] = (uint32_t)((w >> 32) & 0xffu);
        d[8 * i + 5] = (uint32_t)((w >> 40) & 0xffu);
        d[8 * i + 6] = (uint32_t)((w >> 48) & 0xffu);
        d[8 * i + 7] = (uint32_t)((w >> 56) & 0xffu);
    }
}

static int ntt_mul_limbs(uint64_t *p, const uint64_t *a, size_t na,
                         const uint64_t *b, size_t nb) {
    size_t nd = 8 * (na + nb);
    size_t L = 1;
    while (L < nd) {
        L <<= 1;
    }
    if (L > 65536) {
        return 0;
    }
    uint32_t *A = (uint32_t *)calloc(L, sizeof(uint32_t));
    uint32_t *B = NULL;
    int square = (a == b && na == nb);
    if (!A) {
        return 0;
    }
    if (!square) {
        B = (uint32_t *)calloc(L, sizeof(uint32_t));
        if (!B) {
            free(A);
            return 0;
        }
    }
    ntt_split8(A, a, na);
    ntt_transform(A, L, 0);
    if (square) {
        for (size_t i = 0; i < L; i++) {
            A[i] = ntt_mul32(A[i], A[i]);
        }
    } else {
        ntt_split8(B, b, nb);
        ntt_transform(B, L, 0);
        for (size_t i = 0; i < L; i++) {
            A[i] = ntt_mul32(A[i], B[i]);
        }
        free(B);
    }
    ntt_transform(A, L, 1);

    memset(p, 0, (na + nb) * sizeof(uint64_t));
    uint64_t carry = 0;
    for (size_t i = 0; i < L; i++) {
        carry += A[i];
        uint32_t dig = (uint32_t)(carry & 0xffu);
        carry >>= 8;
        size_t li = i >> 3;
        if (li < na + nb) {
            p[li] |= (uint64_t)dig << ((i & 7u) * 8u);
        }
    }
    free(A);
    return carry == 0;
}

/* ------------------------------------------------------------------ */
/* two's-complement fixed-width (Toom-3 interpolation)                 */
/* ------------------------------------------------------------------ */

static void z_load(uint64_t *d, size_t w, const uint64_t *s, size_t n) {
    memset(d, 0, w * sizeof(uint64_t));
    if (n > w) {
        n = w;
    }
    if (n) {
        memcpy(d, s, n * sizeof(uint64_t));
    }
}

static void z_add(uint64_t *d, size_t w, const uint64_t *a, const uint64_t *b) {
    uint64_t c = 0;
    for (size_t i = 0; i < w; i++) {
        u128 t = (u128)a[i] + b[i] + c;
        d[i] = (uint64_t)t;
        c = (uint64_t)(t >> 64);
    }
}

static void z_sub(uint64_t *d, size_t w, const uint64_t *a, const uint64_t *b) {
    uint64_t br = 0;
    for (size_t i = 0; i < w; i++) {
        uint64_t ai = a[i];
        uint64_t bi = b[i];
        uint64_t t = ai - bi;
        uint64_t br1 = ai < bi;
        uint64_t t2 = t - br;
        uint64_t br2 = t < br;
        d[i] = t2;
        br = br1 | br2;
    }
}

static void z_shl1(uint64_t *a, size_t w) {
    uint64_t c = 0;
    for (size_t i = 0; i < w; i++) {
        uint64_t t = (a[i] << 1) | c;
        c = a[i] >> 63;
        a[i] = t;
    }
}

static void z_sar1(uint64_t *a, size_t w) {
    uint64_t sign = a[w - 1] >> 63;
    uint64_t c = sign;
    for (size_t i = w; i-- > 0;) {
        uint64_t t = a[i];
        a[i] = (t >> 1) | (c << 63);
        c = t & 1;
    }
}

static int z_isneg(const uint64_t *a, size_t w) { return (int)(a[w - 1] >> 63); }

static void z_negate(uint64_t *a, size_t w) {
    uint64_t br = 1;
    for (size_t i = 0; i < w; i++) {
        u128 t = (u128)(uint64_t)(~a[i]) + br;
        a[i] = (uint64_t)t;
        br = (uint64_t)(t >> 64);
    }
}

static void z_divexact3(uint64_t *a, size_t w) {
    int neg = z_isneg(a, w);
    if (neg) {
        z_negate(a, w);
    }
    uint64_t cy = 0;
    for (size_t i = 0; i < w; i++) {
        uint64_t s = a[i];
        uint64_t y = s - cy;
        uint64_t borrow = s < cy;
        uint64_t q = y * 0xAAAAAAAAAAAAAAABULL;
        a[i] = q;
        u128 t = (u128)q * 3u;
        cy = (uint64_t)(t >> 64) + borrow;
    }
    if (neg) {
        z_negate(a, w);
    }
}

/* ------------------------------------------------------------------ */
/* Karatsuba (even n, extra-bit sums, no write past 2n)                */
/* ------------------------------------------------------------------ */

static void mul_nn(uint64_t *p, const uint64_t *a, size_t na, const uint64_t *b,
                   size_t nb, Pool *pool);
static void sqr_nn(uint64_t *p, const uint64_t *a, size_t n, Pool *pool);

static void karatsuba_n(uint64_t *p, const uint64_t *a, const uint64_t *b,
                        size_t n, Pool *pool) {
    if (n <= KARAT_THRESH || !pool) {
        school_mul(p, a, b, n);
        return;
    }
    if (n & 1u) {
        /* Pad to even. Product of (n+1)×(n+1) with high limbs 0. */
        size_t mark = pool->used;
        uint64_t *ap = pool_alloc(pool, n + 1);
        uint64_t *bp = pool_alloc(pool, n + 1);
        uint64_t *pp = pool_alloc(pool, 2 * n + 2);
        if (!ap || !bp || !pp) {
            pool->used = mark;
            school_mul(p, a, b, n);
            return;
        }
        memcpy(ap, a, n * sizeof(uint64_t));
        ap[n] = 0;
        memcpy(bp, b, n * sizeof(uint64_t));
        bp[n] = 0;
        karatsuba_n(pp, ap, bp, n + 1, pool);
        memcpy(p, pp, 2 * n * sizeof(uint64_t));
        pool->used = mark;
        return;
    }

    size_t k = n / 2;
    size_t mark = pool->used;
    uint64_t *z0 = pool_alloc(pool, 2 * k + 1);
    uint64_t *z2 = pool_alloc(pool, 2 * k + 1);
    uint64_t *z1 = pool_alloc(pool, 2 * k + 2);
    uint64_t *sa = pool_alloc(pool, k + 1);
    uint64_t *sb = pool_alloc(pool, k + 1);
    if (!z0 || !z2 || !z1 || !sa || !sb) {
        pool->used = mark;
        school_mul(p, a, b, n);
        return;
    }
    memset(z0, 0, (2 * k + 1) * sizeof(uint64_t));
    memset(z2, 0, (2 * k + 1) * sizeof(uint64_t));
    memset(z1, 0, (2 * k + 2) * sizeof(uint64_t));

    karatsuba_n(z0, a, b, k, pool);
    karatsuba_n(z2, a + k, b + k, k, pool);

    memcpy(sa, a, k * sizeof(uint64_t));
    sa[k] = add_n_c(sa, a + k, k);
    memcpy(sb, b, k * sizeof(uint64_t));
    sb[k] = add_n_c(sb, b + k, k);

    karatsuba_n(z1, sa, sb, k, pool);
    if (sa[k]) {
        add_spread(z1 + k, k + 2, sb, k);
    }
    if (sb[k]) {
        add_spread(z1 + k, k + 2, sa, k);
    }
    if (sa[k] && sb[k]) {
        uint64_t one = 1;
        add_spread(z1 + 2 * k, 2, &one, 1);
    }
    sub_spread(z1, 2 * k + 2, z0, 2 * k);
    sub_spread(z1, 2 * k + 2, z2, 2 * k);

    memset(p, 0, 2 * n * sizeof(uint64_t));
    memcpy(p, z0, 2 * k * sizeof(uint64_t));
    add_spread(p + k, 2 * n - k, z1, 2 * k + 2);
    add_spread(p + 2 * k, 2 * n - 2 * k, z2, 2 * k);
    pool->used = mark;
}

/* ------------------------------------------------------------------ */
/* Toom-3 (Bodrato interpolation at 0, 1, −1, −2, ∞)                   */
/* ------------------------------------------------------------------ */

static int toom3_n(uint64_t *p, const uint64_t *a, const uint64_t *b, size_t n,
                   Pool *pool);

static void mul_nn(uint64_t *p, const uint64_t *a, size_t na, const uint64_t *b,
                   size_t nb, Pool *pool) {
    if (na < nb) {
        const uint64_t *t = a;
        a = b;
        b = t;
        size_t tn = na;
        na = nb;
        nb = tn;
    }
    if (nb == 0) {
        memset(p, 0, na * sizeof(uint64_t));
        return;
    }
    if (nb <= KARAT_THRESH || !pool) {
        school_mul_rect(p, a, na, b, nb);
        return;
    }
    if (na == nb) {
        if (na >= NTT_THRESH && ntt_mul_limbs(p, a, na, b, nb)) {
            return;
        }
        if (na >= TOOM_THRESH) {
            if (toom3_n(p, a, b, na, pool)) {
                return;
            }
        }
        karatsuba_n(p, a, b, na, pool);
        return;
    }
    /* Pad the shorter operand. */
    size_t mark = pool->used;
    uint64_t *bp = pool_alloc(pool, na);
    uint64_t *pp = pool_alloc(pool, 2 * na);
    if (!bp || !pp) {
        pool->used = mark;
        school_mul_rect(p, a, na, b, nb);
        return;
    }
    memset(bp, 0, na * sizeof(uint64_t));
    memcpy(bp, b, nb * sizeof(uint64_t));
    mul_nn(pp, a, na, bp, na, pool);
    memcpy(p, pp, (na + nb) * sizeof(uint64_t));
    pool->used = mark;
}

static void eval_points(uint64_t *p1, uint64_t *pm1, uint64_t *pm2, size_t ev,
                        const uint64_t *x0, size_t n0, const uint64_t *x1,
                        size_t n1, const uint64_t *x2, size_t n2, uint64_t *t,
                        uint64_t *tt) {
    /* p1 = x0+x1+x2, pm1 = x0-x1+x2, pm2 = x0-2x1+4x2  (two's complement) */
    z_load(p1, ev, x0, n0);
    z_load(t, ev, x1, n1);
    z_add(p1, ev, p1, t);
    z_load(tt, ev, x2, n2);
    z_add(p1, ev, p1, tt);

    z_load(pm1, ev, x0, n0);
    z_add(pm1, ev, pm1, tt);
    z_sub(pm1, ev, pm1, t);

    z_load(pm2, ev, x2, n2);
    z_shl1(pm2, ev);
    z_shl1(pm2, ev); /* 4 x2 */
    z_load(tt, ev, x0, n0);
    z_add(pm2, ev, pm2, tt);
    z_load(t, ev, x1, n1);
    z_shl1(t, ev); /* 2 x1 */
    z_sub(pm2, ev, pm2, t);
}

static void signed_mul(uint64_t *out, size_t ow, uint64_t *xa, size_t ev,
                       uint64_t *xb, Pool *pool) {
    int sa = z_isneg(xa, ev);
    int sb = z_isneg(xb, ev);
    if (sa) {
        z_negate(xa, ev);
    }
    if (sb) {
        z_negate(xb, ev);
    }
    size_t na = trim(xa, ev);
    size_t nb = trim(xb, ev);
    memset(out, 0, ow * sizeof(uint64_t));
    if (na && nb) {
        mul_nn(out, xa, na, xb, nb, pool);
    }
    if (sa ^ sb) {
        z_negate(out, ow);
    }
}

static void signed_sqr(uint64_t *out, size_t ow, uint64_t *xa, size_t ev,
                       Pool *pool) {
    if (z_isneg(xa, ev)) {
        z_negate(xa, ev);
    }
    size_t na = trim(xa, ev);
    memset(out, 0, ow * sizeof(uint64_t));
    if (na) {
        sqr_nn(out, xa, na, pool);
    }
}

static int toom3_n(uint64_t *p, const uint64_t *a, const uint64_t *b, size_t n,
                   Pool *pool) {
    if (!pool || n < 6) {
        return 0;
    }
    size_t k = (n + 2) / 3;
    size_t n0 = k;
    size_t n1 = k;
    size_t n2 = n - 2 * k;
    if (n2 == 0 || n2 > k) {
        return 0;
    }
    const uint64_t *a0 = a, *a1 = a + k, *a2 = a + 2 * k;
    const uint64_t *b0 = b, *b1 = b + k, *b2 = b + 2 * k;

    size_t ev = k + 4;
    size_t ic = 2 * ev + 4;
    size_t mark = pool->used;

    uint64_t *pa1 = pool_alloc(pool, ev);
    uint64_t *pam1 = pool_alloc(pool, ev);
    uint64_t *pam2 = pool_alloc(pool, ev);
    uint64_t *pb1 = pool_alloc(pool, ev);
    uint64_t *pbm1 = pool_alloc(pool, ev);
    uint64_t *pbm2 = pool_alloc(pool, ev);
    uint64_t *t = pool_alloc(pool, ev);
    uint64_t *tt = pool_alloc(pool, ev);
    uint64_t *r0 = pool_alloc(pool, ic);
    uint64_t *r1 = pool_alloc(pool, ic);
    uint64_t *r2 = pool_alloc(pool, ic);
    uint64_t *r3 = pool_alloc(pool, ic);
    uint64_t *r4 = pool_alloc(pool, ic);
    uint64_t *tmp = pool_alloc(pool, ic);
    if (!pa1 || !pam1 || !pam2 || !pb1 || !pbm1 || !pbm2 || !t || !tt || !r0 ||
        !r1 || !r2 || !r3 || !r4 || !tmp) {
        pool->used = mark;
        return 0;
    }

    eval_points(pa1, pam1, pam2, ev, a0, n0, a1, n1, a2, n2, t, tt);
    memset(r0, 0, ic * sizeof(uint64_t));
    memset(r4, 0, ic * sizeof(uint64_t));
    if (a == b) {
        sqr_nn(r0, a0, n0, pool);
        sqr_nn(r4, a2, n2, pool);
        signed_sqr(r1, ic, pa1, ev, pool);
        signed_sqr(r2, ic, pam1, ev, pool);
        signed_sqr(r3, ic, pam2, ev, pool);
    } else {
        eval_points(pb1, pbm1, pbm2, ev, b0, n0, b1, n1, b2, n2, t, tt);
        mul_nn(r0, a0, n0, b0, n0, pool);
        mul_nn(r4, a2, n2, b2, n2, pool);
        signed_mul(r1, ic, pa1, ev, pb1, pool);
        signed_mul(r2, ic, pam1, ev, pbm1, pool);
        signed_mul(r3, ic, pam2, ev, pbm2, pool);
    }

    /* Bodrato interpolation. r1=r(1), r2=r(-1), r3=r(-2) reused as dest. */
    /* r3 ← (r(-2) − r(1)) / 3 */
    z_sub(tmp, ic, r3, r1);
    memcpy(r3, tmp, ic * sizeof(uint64_t));
    z_divexact3(r3, ic);
    /* r1 ← (r(1) − r(−1)) / 2 */
    z_sub(tmp, ic, r1, r2);
    memcpy(r1, tmp, ic * sizeof(uint64_t));
    z_sar1(r1, ic);
    /* r2 ← r(−1) − r(0) */
    z_sub(r2, ic, r2, r0);
    /* tmp ← (r2 − r3) / 2 */
    z_sub(tmp, ic, r2, r3);
    z_sar1(tmp, ic);
    /* r3 ← tmp + 2 r(∞) */
    memcpy(r3, r4, ic * sizeof(uint64_t));
    z_shl1(r3, ic);
    z_add(r3, ic, tmp, r3);
    /* r2 ← r2 + r1 − r4 */
    z_add(tmp, ic, r2, r1);
    z_sub(r2, ic, tmp, r4);
    /* r1 ← r1 − r3 */
    z_sub(r1, ic, r1, r3);

    if (z_isneg(r0, ic) || z_isneg(r1, ic) || z_isneg(r2, ic) ||
        z_isneg(r3, ic) || z_isneg(r4, ic)) {
        pool->used = mark;
        return 0;
    }

    memset(p, 0, 2 * n * sizeof(uint64_t));
    add_spread(p, 2 * n, r0, trim(r0, ic));
    add_spread(p + k, 2 * n - k, r1, trim(r1, ic));
    add_spread(p + 2 * k, 2 * n - 2 * k, r2, trim(r2, ic));
    add_spread(p + 3 * k, 2 * n - 3 * k, r3, trim(r3, ic));
    if (4 * k < 2 * n) {
        add_spread(p + 4 * k, 2 * n - 4 * k, r4, trim(r4, ic));
    }
    pool->used = mark;
    return 1;
}

/* ------------------------------------------------------------------ */
/* squaring                                                            */
/* ------------------------------------------------------------------ */

static void sqr_nn(uint64_t *p, const uint64_t *a, size_t n, Pool *pool);

static void karatsuba_sqr(uint64_t *p, const uint64_t *a, size_t n, Pool *pool) {
    if (n <= KARAT_THRESH || !pool) {
        school_mul(p, a, a, n);
        return;
    }
    if (n & 1u) {
        size_t mark = pool->used;
        uint64_t *ap = pool_alloc(pool, n + 1);
        uint64_t *pp = pool_alloc(pool, 2 * n + 2);
        if (!ap || !pp) {
            pool->used = mark;
            school_mul(p, a, a, n);
            return;
        }
        memcpy(ap, a, n * sizeof(uint64_t));
        ap[n] = 0;
        karatsuba_sqr(pp, ap, n + 1, pool);
        memcpy(p, pp, 2 * n * sizeof(uint64_t));
        pool->used = mark;
        return;
    }
    size_t k = n / 2;
    size_t mark = pool->used;
    uint64_t *z0 = pool_alloc(pool, 2 * k + 1);
    uint64_t *z2 = pool_alloc(pool, 2 * k + 1);
    uint64_t *z1 = pool_alloc(pool, 2 * k + 2);
    uint64_t *tw = pool_alloc(pool, 2 * k + 1);
    if (!z0 || !z2 || !z1 || !tw) {
        pool->used = mark;
        school_mul(p, a, a, n);
        return;
    }
    memset(z0, 0, (2 * k + 1) * sizeof(uint64_t));
    memset(z2, 0, (2 * k + 1) * sizeof(uint64_t));
    memset(z1, 0, (2 * k + 2) * sizeof(uint64_t));
    sqr_nn(z0, a, k, pool);
    sqr_nn(z2, a + k, k, pool);
    mul_nn(z1, a, k, a + k, k, pool);
    /* 2 * al * ah */
    uint64_t c = 0;
    for (size_t i = 0; i < 2 * k; i++) {
        uint64_t t = (z1[i] << 1) | c;
        c = z1[i] >> 63;
        tw[i] = t;
    }
    tw[2 * k] = c;

    memset(p, 0, 2 * n * sizeof(uint64_t));
    memcpy(p, z0, 2 * k * sizeof(uint64_t));
    add_spread(p + k, 2 * n - k, tw, 2 * k + 1);
    add_spread(p + 2 * k, 2 * n - 2 * k, z2, 2 * k);
    pool->used = mark;
}

static void sqr_nn(uint64_t *p, const uint64_t *a, size_t n, Pool *pool) {
    if (n == 0) {
        return;
    }
    if (n <= KARAT_THRESH || !pool) {
        school_mul(p, a, a, n);
        return;
    }
    if (n >= NTT_THRESH && ntt_mul_limbs(p, a, n, a, n)) {
        return;
    }
    if (n >= TOOM_THRESH) {
        if (toom3_n(p, a, a, n, pool)) {
            return;
        }
    }
    karatsuba_sqr(p, a, n, pool);
}

/* ------------------------------------------------------------------ */
/* public multiply                                                     */
/* ------------------------------------------------------------------ */

int huge_mul(const uint64_t *a, size_t na, const uint64_t *b, size_t nb,
             uint64_t *out) {
    if (!a || !b || !out || na == 0 || nb == 0) {
        return -1;
    }
    if (na > HUGE_MAX_LIMBS || nb > HUGE_MAX_LIMBS) {
        return -1;
    }
    size_t need = 64 * (na > nb ? na : nb) + 4096;
    uint64_t *buf = (uint64_t *)malloc(need * sizeof(uint64_t));
    if (!buf) {
        school_mul_rect(out, a, na, b, nb);
        return 0;
    }
    Pool pool;
    pool.base = buf;
    pool.cap = need;
    pool.used = 0;
    mul_nn(out, a, na, b, nb, &pool);
    free(buf);
    return 0;
}

/* ------------------------------------------------------------------ */
/* Barrett reduction                                                   */
/* ------------------------------------------------------------------ */

static void barrett_mu(uint64_t *mu, uint64_t *r2, const uint64_t *m, size_t n) {
    uint64_t rem[HUGE_MAX_LIMBS + 2];
    memset(rem, 0, (n + 1) * sizeof(uint64_t));
    memset(mu, 0, (n + 1) * sizeof(uint64_t));
    rem[0] = 1;
    for (size_t step = 0; step < 64 * 2 * n; step++) {
        uint64_t c = 0;
        for (size_t i = 0; i <= n; i++) {
            uint64_t t = (rem[i] << 1) | c;
            c = rem[i] >> 63;
            rem[i] = t;
        }
        if (rem[n] || cmp_be(rem, m, n) >= 0) {
            uint64_t br = sub_n(rem, m, n);
            rem[n] -= br;
            size_t bit = 64 * 2 * n - 1 - step;
            mu[bit / 64] |= 1ULL << (bit % 64);
        }
    }
    memcpy(r2, rem, n * sizeof(uint64_t));
}

static void barrett_red(uint64_t *out, const uint64_t *x, const uint64_t *m,
                        const uint64_t *mu, size_t n, Pool *pool) {
    /* q3 = floor( (x[n-1 : 2n] * mu) / 2^{64(n+1)} ) */
    size_t mark = pool->used;
    uint64_t *qprod = pool_alloc(pool, 2 * (n + 1));
    uint64_t *xh = pool_alloc(pool, n + 1);
    if (!qprod || !xh) {
        pool->used = mark;
        /* Slow fallback: x mod m via repeated sub (should never run). */
        memcpy(out, x, n * sizeof(uint64_t));
        return;
    }
    memcpy(xh, x + (n - 1), (n + 1) * sizeof(uint64_t));
    mul_nn(qprod, xh, n + 1, mu, n + 1, pool);
    uint64_t *q3 = qprod + (n + 1);

    uint64_t *qm = pool_alloc(pool, 2 * n + 2);
    if (!qm) {
        pool->used = mark;
        memcpy(out, x, n * sizeof(uint64_t));
        return;
    }
    memset(qm, 0, (2 * n + 2) * sizeof(uint64_t));
    mul_nn(qm, q3, n + 1, m, n, pool);

    uint64_t r[HUGE_MAX_LIMBS + 2];
    memset(r, 0, (n + 2) * sizeof(uint64_t));
    memcpy(r, x, (n + 1) * sizeof(uint64_t));
    uint64_t br = sub_n(r, qm, n + 1);
    /* If q3 was high, r is negative and wrapped. Add m until it unwraps. */
    int guard = 0;
    while (br && guard++ < 8) {
        uint64_t c = add_n_c(r, m, n);
        u128 t = (u128)r[n] + c;
        r[n] = (uint64_t)t;
        br = (t >> 64) ? 0 : 1;
    }
    guard = 0;
    while ((r[n] || cmp_be(r, m, n) >= 0) && guard++ < 8) {
        uint64_t sbr = sub_n(r, m, n);
        if (r[n] < sbr) {
            r[n] = 0;
            break;
        }
        r[n] -= sbr;
    }
    memcpy(out, r, n * sizeof(uint64_t));
    pool->used = mark;
}

static void barrett_mul(uint64_t *out, const uint64_t *a, const uint64_t *b,
                        const uint64_t *m, const uint64_t *mu, size_t n,
                        Pool *pool) {
    size_t mark = pool->used;
    uint64_t *prod = pool_alloc(pool, 2 * n + 2);
    if (!prod) {
        pool->used = mark;
        memset(out, 0, n * sizeof(uint64_t));
        return;
    }
    memset(prod, 0, (2 * n + 2) * sizeof(uint64_t));
    if (a == b) {
        sqr_nn(prod, a, n, pool);
    } else {
        mul_nn(prod, a, n, b, n, pool);
    }
    barrett_red(out, prod, m, mu, n, pool);
    pool->used = mark;
}

/* ------------------------------------------------------------------ */
/* CIOS Montgomery (small n)                                           */
/* ------------------------------------------------------------------ */

static uint64_t inv64(uint64_t x) {
    uint64_t y = 1;
    y *= 2 - x * y;
    y *= 2 - x * y;
    y *= 2 - x * y;
    y *= 2 - x * y;
    y *= 2 - x * y;
    y *= 2 - x * y;
    return y;
}

static void mont_mul(uint64_t *t, const uint64_t *a, const uint64_t *b,
                     const uint64_t *m, size_t n, uint64_t n0inv) {
    uint64_t tmp[HUGE_MAX_LIMBS + 2];
    memset(tmp, 0, (n + 2) * sizeof(uint64_t));
    for (size_t i = 0; i < n; i++) {
        u128 c = 0;
        uint64_t bi = b[i];
        size_t j = 0;
        for (; j + 3 < n; j += 4) {
            c += (u128)tmp[j] + (u128)a[j] * bi;
            tmp[j] = (uint64_t)c;
            c >>= 64;
            c += (u128)tmp[j + 1] + (u128)a[j + 1] * bi;
            tmp[j + 1] = (uint64_t)c;
            c >>= 64;
            c += (u128)tmp[j + 2] + (u128)a[j + 2] * bi;
            tmp[j + 2] = (uint64_t)c;
            c >>= 64;
            c += (u128)tmp[j + 3] + (u128)a[j + 3] * bi;
            tmp[j + 3] = (uint64_t)c;
            c >>= 64;
        }
        for (; j < n; j++) {
            c += (u128)tmp[j] + (u128)a[j] * bi;
            tmp[j] = (uint64_t)c;
            c >>= 64;
        }
        c += tmp[n];
        tmp[n] = (uint64_t)c;
        tmp[n + 1] = (uint64_t)(c >> 64);

        uint64_t mu = tmp[0] * n0inv;
        c = (u128)tmp[0] + (u128)mu * m[0];
        c >>= 64;
        j = 1;
        for (; j + 3 < n; j += 4) {
            c += (u128)tmp[j] + (u128)mu * m[j];
            tmp[j - 1] = (uint64_t)c;
            c >>= 64;
            c += (u128)tmp[j + 1] + (u128)mu * m[j + 1];
            tmp[j] = (uint64_t)c;
            c >>= 64;
            c += (u128)tmp[j + 2] + (u128)mu * m[j + 2];
            tmp[j + 1] = (uint64_t)c;
            c >>= 64;
            c += (u128)tmp[j + 3] + (u128)mu * m[j + 3];
            tmp[j + 2] = (uint64_t)c;
            c >>= 64;
        }
        for (; j < n; j++) {
            c += (u128)tmp[j] + (u128)mu * m[j];
            tmp[j - 1] = (uint64_t)c;
            c >>= 64;
        }
        c += tmp[n];
        tmp[n - 1] = (uint64_t)c;
        tmp[n] = tmp[n + 1] + (uint64_t)(c >> 64);
    }
    while (tmp[n] || cmp_be(tmp, m, n) >= 0) {
        uint64_t br = sub_n(tmp, m, n);
        if (tmp[n] < br) {
            tmp[n] = 0;
            break;
        }
        tmp[n] -= br;
    }
    memcpy(t, tmp, n * sizeof(uint64_t));
}

static void mont_sqr(uint64_t *t, const uint64_t *a, const uint64_t *m, size_t n,
                     uint64_t n0inv) {
    mont_mul(t, a, a, m, n, n0inv);
}

static size_t bitlen_limbs(const uint64_t *a, size_t n) {
    while (n > 0 && a[n - 1] == 0) {
        n--;
    }
    if (n == 0) {
        return 0;
    }
    size_t bits = (n - 1) * 64;
    uint64_t top = a[n - 1];
    while (top) {
        bits++;
        top >>= 1;
    }
    return bits;
}

static int bit_at(const uint64_t *a, size_t bit) {
    return (int)((a[bit / 64] >> (bit % 64)) & 1u);
}

static int powmod_cios(const uint64_t *base, size_t nbase, const uint64_t *exp,
                       size_t nexp, const uint64_t *m, size_t n, uint64_t *out) {
    uint64_t a[HUGE_MAX_LIMBS];
    uint64_t r[HUGE_MAX_LIMBS];
    uint64_t one[HUGE_MAX_LIMBS];
    uint64_t r2[HUGE_MAX_LIMBS];
    uint64_t tmp[HUGE_MAX_LIMBS];
    memset(a, 0, n * sizeof(uint64_t));
    size_t copy = nbase < n ? nbase : n;
    memcpy(a, base, copy * sizeof(uint64_t));
    if (cmp_be(a, m, n) >= 0) {
        sub_n(a, m, n);
    }

    uint64_t n0inv = 0u - inv64(m[0]);
    memset(r2, 0, n * sizeof(uint64_t));
    r2[0] = 1;
    size_t doubles = 2 * 64 * n;
    for (size_t i = 0; i < doubles; i++) {
        shl1_mod(r2, m, n);
    }

    mont_mul(tmp, a, r2, m, n, n0inv);
    memcpy(a, tmp, n * sizeof(uint64_t));

    uint64_t *pre = (uint64_t *)malloc(HUGE_PRE * n * sizeof(uint64_t));
    if (!pre) {
        return -1;
    }
    memset(one, 0, n * sizeof(uint64_t));
    one[0] = 1;
    mont_mul(pre + 0 * n, one, r2, m, n, n0inv);
    memcpy(pre + 1 * n, a, n * sizeof(uint64_t));
    for (size_t i = 2; i < HUGE_PRE; i++) {
        mont_mul(pre + i * n, pre + (i - 1) * n, a, m, n, n0inv);
    }

    memcpy(r, pre + 0 * n, n * sizeof(uint64_t));
    size_t ebits = bitlen_limbs(exp, nexp);
    int i = (int)ebits - 1;
    while (i >= 0) {
        if (!bit_at(exp, (size_t)i)) {
            mont_sqr(tmp, r, m, n, n0inv);
            memcpy(r, tmp, n * sizeof(uint64_t));
            i--;
            continue;
        }
        int lo = i - (int)HUGE_WINDOW + 1;
        if (lo < 0) {
            lo = 0;
        }
        unsigned w = 0;
        for (int k = i; k >= lo; k--) {
            w = (w << 1) | (unsigned)bit_at(exp, (size_t)k);
        }
        int nsq = i - lo + 1;
        for (int s = 0; s < nsq; s++) {
            mont_sqr(tmp, r, m, n, n0inv);
            memcpy(r, tmp, n * sizeof(uint64_t));
        }
        mont_mul(tmp, r, pre + (size_t)w * n, m, n, n0inv);
        memcpy(r, tmp, n * sizeof(uint64_t));
        i = lo - 1;
    }
    memset(one, 0, n * sizeof(uint64_t));
    one[0] = 1;
    mont_mul(out, r, one, m, n, n0inv);
    free(pre);
    return 0;
}

static int powmod_barrett(const uint64_t *base, size_t nbase, const uint64_t *exp,
                          size_t nexp, const uint64_t *m, size_t n,
                          uint64_t *out) {
    uint64_t a[HUGE_MAX_LIMBS];
    uint64_t r[HUGE_MAX_LIMBS];
    uint64_t tmp[HUGE_MAX_LIMBS];
    uint64_t mu[HUGE_MAX_LIMBS + 1];
    uint64_t r2[HUGE_MAX_LIMBS];
    memset(a, 0, n * sizeof(uint64_t));
    size_t copy = nbase < n ? nbase : n;
    memcpy(a, base, copy * sizeof(uint64_t));
    if (cmp_be(a, m, n) >= 0) {
        sub_n(a, m, n);
    }
    barrett_mu(mu, r2, m, n);
    (void)r2;

    size_t need = 64 * (n + 2) + 4096;
    uint64_t *buf = (uint64_t *)malloc(need * sizeof(uint64_t));
    uint64_t *pre = (uint64_t *)malloc(HUGE_PRE * n * sizeof(uint64_t));
    if (!buf || !pre) {
        free(buf);
        free(pre);
        return -1;
    }
    Pool pool;
    pool.base = buf;
    pool.cap = need;
    pool.used = 0;

    memset(pre + 0 * n, 0, n * sizeof(uint64_t));
    pre[0] = 1;
    memcpy(pre + 1 * n, a, n * sizeof(uint64_t));
    for (size_t i = 2; i < HUGE_PRE; i++) {
        barrett_mul(pre + i * n, pre + (i - 1) * n, a, m, mu, n, &pool);
    }

    memset(r, 0, n * sizeof(uint64_t));
    r[0] = 1;
    size_t ebits = bitlen_limbs(exp, nexp);
    int i = (int)ebits - 1;
    while (i >= 0) {
        if (!bit_at(exp, (size_t)i)) {
            barrett_mul(tmp, r, r, m, mu, n, &pool);
            memcpy(r, tmp, n * sizeof(uint64_t));
            i--;
            continue;
        }
        int lo = i - (int)HUGE_WINDOW + 1;
        if (lo < 0) {
            lo = 0;
        }
        unsigned w = 0;
        for (int k = i; k >= lo; k--) {
            w = (w << 1) | (unsigned)bit_at(exp, (size_t)k);
        }
        int nsq = i - lo + 1;
        for (int s = 0; s < nsq; s++) {
            barrett_mul(tmp, r, r, m, mu, n, &pool);
            memcpy(r, tmp, n * sizeof(uint64_t));
        }
        barrett_mul(tmp, r, pre + (size_t)w * n, m, mu, n, &pool);
        memcpy(r, tmp, n * sizeof(uint64_t));
        i = lo - 1;
    }
    memcpy(out, r, n * sizeof(uint64_t));
    free(buf);
    free(pre);
    return 0;
}

int huge_powmod(const uint64_t *base, size_t nbase, const uint64_t *exp,
                size_t nexp, const uint64_t *mod, size_t nmod, uint64_t *out) {
    if (nmod == 0 || nmod > HUGE_MAX_LIMBS || (mod[0] & 1u) == 0) {
        return -1;
    }
    while (nmod > 1 && mod[nmod - 1] == 0) {
        nmod--;
    }
    if (nmod == 0 || (mod[0] & 1u) == 0) {
        return -1;
    }
    if (nmod == 1 && mod[0] == 1) {
        memset(out, 0, sizeof(uint64_t));
        return 0;
    }
    if (nbase > nmod) {
        return -1;
    }

    uint64_t m[HUGE_MAX_LIMBS];
    memset(m, 0, nmod * sizeof(uint64_t));
    memcpy(m, mod, nmod * sizeof(uint64_t));

    size_t ebits = bitlen_limbs(exp, nexp);
    if (ebits == 0) {
        memset(out, 0, nmod * sizeof(uint64_t));
        out[0] = 1;
        return 0;
    }
    int azero = 1;
    for (size_t i = 0; i < nbase && i < nmod; i++) {
        if (base[i]) {
            azero = 0;
            break;
        }
    }
    if (azero) {
        memset(out, 0, nmod * sizeof(uint64_t));
        return 0;
    }

    if (nmod >= BARRETT_THRESH) {
        return powmod_barrett(base, nbase, exp, nexp, m, nmod, out);
    }
    return powmod_cios(base, nbase, exp, nexp, m, nmod, out);
}

int huge_arith_max_limbs(void) { return HUGE_MAX_LIMBS; }

#endif
