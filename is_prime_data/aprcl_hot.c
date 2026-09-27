/* Jacobi-sum product in Z[zeta_r]/(n). GMP arithmetic only. */
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

typedef unsigned long mp_limb_t;
typedef unsigned long mp_bitcnt_t;
typedef struct {
    int _mp_alloc;
    int _mp_size;
    mp_limb_t *_mp_d;
} __mpz_struct;
typedef __mpz_struct mpz_t[1];

extern void __gmpz_init(mpz_t);
extern void __gmpz_clear(mpz_t);
extern void __gmpz_set(mpz_t, const mpz_t);
extern void __gmpz_set_ui(mpz_t, unsigned long);
extern void __gmpz_mul(mpz_t, const mpz_t, const mpz_t);
extern void __gmpz_mod(mpz_t, const mpz_t, const mpz_t);
extern void __gmpz_addmul(mpz_t, const mpz_t, const mpz_t);
extern void __gmpz_submul(mpz_t, const mpz_t, const mpz_t);
extern void __gmpz_import(mpz_t, size_t, int, size_t, int, size_t, const void *);
extern int __gmpz_cmp(const mpz_t, const mpz_t);
extern void __gmpz_mul_ui(mpz_t, const mpz_t, unsigned long);
extern unsigned long __gmpz_fdiv_q_ui(mpz_t, const mpz_t, unsigned long);
extern size_t __gmpz_sizeinbase(const mpz_t, int);
extern int __gmpz_tstbit(const mpz_t, mp_bitcnt_t);
extern void __gmpz_sqrt(mpz_t, const mpz_t);
extern void __gmpz_powm_ui(mpz_t, const mpz_t, unsigned long, const mpz_t);
extern int __gmpz_divisible_p(const mpz_t, const mpz_t);
extern int __gmpz_cmp_ui(const mpz_t, unsigned long);

#define mpz_init __gmpz_init
#define mpz_clear __gmpz_clear
#define mpz_set __gmpz_set
#define mpz_set_ui __gmpz_set_ui
#define mpz_mul __gmpz_mul
#define mpz_mod __gmpz_mod
#define mpz_addmul __gmpz_addmul
#define mpz_submul __gmpz_submul
#define mpz_import __gmpz_import
#define mpz_cmp __gmpz_cmp
#define mpz_mul_ui __gmpz_mul_ui
#define mpz_fdiv_q_ui __gmpz_fdiv_q_ui
#define mpz_sizeinbase __gmpz_sizeinbase
#define mpz_tstbit __gmpz_tstbit
#define mpz_sqrt __gmpz_sqrt
#define mpz_powm_ui __gmpz_powm_ui
#define mpz_divisible_p __gmpz_divisible_p
#define mpz_cmp_ui __gmpz_cmp_ui

#define APR_MAX 40

static int mpz_zero(const mpz_t z) { return z[0]._mp_size == 0; }

static int make_phi(unsigned r, mpz_t *phi, int *deg_out) {
    unsigned p = 2, x = r, e = 0;
    while (x % p != 0) {
        if (p * p > x) {
            p = x;
            break;
        }
        p++;
    }
    while (x % p == 0) {
        x /= p;
        e++;
    }
    if (x != 1 || e == 0) {
        return -1;
    }
    unsigned pk = 1;
    for (unsigned i = 1; i < e; i++) {
        pk *= p;
    }
    int deg = (int)(pk * (p - 1));
    if (deg <= 0 || deg >= APR_MAX) {
        return -1;
    }
    for (int i = 0; i <= deg; i++) {
        mpz_set_ui(phi[i], 0);
    }
    for (unsigned i = 0; i < p; i++) {
        mpz_set_ui(phi[(int)(i * pk)], 1);
    }
    *deg_out = deg;
    return 0;
}

/* Reduce poly[0..len) modulo monic phi of degree deg. Result length deg. */
static void reduce(mpz_t *poly, int len, mpz_t *phi, int deg, const mpz_t n, mpz_t scratch) {
    for (int i = len - 1; i >= deg; i--) {
        if (mpz_zero(poly[i])) {
            continue;
        }
        mpz_set(scratch, poly[i]);
        mpz_set_ui(poly[i], 0);
        int shift = i - deg;
        for (int j = 0; j < deg; j++) {
            mpz_submul(poly[shift + j], scratch, phi[j]);
            mpz_mod(poly[shift + j], poly[shift + j], n);
        }
    }
    for (int i = 0; i < deg; i++) {
        mpz_mod(poly[i], poly[i], n);
    }
}

static void pmul(mpz_t *dst, mpz_t *a, mpz_t *b, int deg, mpz_t *phi, const mpz_t n,
                 mpz_t *raw, mpz_t scratch) {
    int nraw = 2 * deg - 1;
    for (int i = 0; i < nraw; i++) {
        mpz_set_ui(raw[i], 0);
    }
    for (int i = 0; i < deg; i++) {
        if (mpz_zero(a[i])) {
            continue;
        }
        for (int j = 0; j < deg; j++) {
            if (!mpz_zero(b[j])) {
                mpz_addmul(raw[i + j], a[i], b[j]);
            }
        }
    }
    for (int i = 0; i < nraw; i++) {
        mpz_mod(raw[i], raw[i], n);
    }
    reduce(raw, nraw, phi, deg, n, scratch);
    for (int i = 0; i < deg; i++) {
        mpz_set(dst[i], raw[i]);
    }
}

/* Exponent m with elem = zeta^m, or -1 when elem is not a power of zeta. */
static int is_power(mpz_t *elem, int deg, unsigned r, mpz_t *phi, const mpz_t n, mpz_t scratch) {
    mpz_t raw[APR_MAX * 2];
    for (int i = 0; i < APR_MAX * 2; i++) {
        mpz_init(raw[i]);
    }
    int found = -1;
    for (unsigned m = 0; m < r; m++) {
        for (int i = 0; i < APR_MAX * 2; i++) {
            mpz_set_ui(raw[i], 0);
        }
        mpz_set_ui(raw[m], 1);
        int len = (int)m + 1;
        if (len < deg) {
            len = deg;
        }
        reduce(raw, len, phi, deg, n, scratch);
        int same = 1;
        for (int i = 0; i < deg; i++) {
            if (mpz_cmp(elem[i], raw[i]) != 0) {
                same = 0;
                break;
            }
        }
        if (same) {
            found = (int)m;
            break;
        }
    }
    for (int i = 0; i < APR_MAX * 2; i++) {
        mpz_clear(raw[i]);
    }
    return found;
}

int aprcl_product_ok(const uint64_t *mod_limbs, size_t nlimbs, unsigned r,
                     const uint64_t *base_limbs, int base_len,
                     const unsigned *idxs, int nidx) {
    if (!mod_limbs || nlimbs == 0 || r < 2 || r >= APR_MAX || !idxs || nidx <= 0) {
        return -1;
    }
    mpz_t n, scratch;
    mpz_init(n);
    mpz_init(scratch);
    mpz_import(n, nlimbs, -1, sizeof(uint64_t), 0, 0, mod_limbs);

    mpz_t phi[APR_MAX];
    for (int i = 0; i < APR_MAX; i++) {
        mpz_init(phi[i]);
    }
    int deg = 0;
    if (make_phi(r, phi, &deg) != 0) {
        mpz_clear(n);
        mpz_clear(scratch);
        return -1;
    }

    mpz_t base[APR_MAX], acc[APR_MAX], cur[APR_MAX];
    mpz_t raw[APR_MAX * 2];
    for (int i = 0; i < APR_MAX; i++) {
        mpz_init(base[i]);
        mpz_init(acc[i]);
        mpz_init(cur[i]);
    }
    for (int i = 0; i < APR_MAX * 2; i++) {
        mpz_init(raw[i]);
    }
    for (int i = 0; i < base_len && i < deg; i++) {
        mpz_import(base[i], nlimbs, -1, sizeof(uint64_t), 0, 0,
                   base_limbs + (size_t)i * nlimbs);
        mpz_mod(base[i], base[i], n);
    }
    reduce(base, deg, phi, deg, n, scratch);

    /* floor(n*i/r) = (n//r)*i + ((n%r)*i)//r, so the Galois product is
       s1^(n//r) * alpha with exponents < r. One large exponentiation. */
    mpz_t s1[APR_MAX], alpha[APR_MAX], img[APR_MAX], powered[APR_MAX];
    mpz_t exponent;
    for (int i = 0; i < APR_MAX; i++) {
        mpz_init(s1[i]);
        mpz_init(alpha[i]);
        mpz_init(img[i]);
        mpz_init(powered[i]);
    }
    mpz_init(exponent);
    mpz_set_ui(s1[0], 1);
    mpz_set_ui(alpha[0], 1);
    for (int i = 1; i < deg; i++) {
        mpz_set_ui(s1[i], 0);
        mpz_set_ui(alpha[i], 0);
    }
    unsigned long nmod = mpz_fdiv_q_ui(exponent, n, r);

    int ok = 1;
    int glen_cap = deg * (int)r + 2;
    mpz_t *gal = malloc(sizeof(mpz_t) * (size_t)glen_cap);
    if (!gal) {
        ok = -1;
    } else {
        for (int i = 0; i < glen_cap; i++) {
            mpz_init(gal[i]);
        }
    }
    for (int k = 0; k < nidx && ok == 1; k++) {
        unsigned idx = idxs[k];
        if (idx == 0 || idx >= r) {
            continue;
        }
        unsigned inv = 0;
        for (unsigned v = 1; v < r; v++) {
            if ((unsigned long)v * idx % r == 1u) {
                inv = v;
                break;
            }
        }
        if (inv == 0) {
            continue;
        }
        for (int i = 0; i < glen_cap; i++) {
            mpz_set_ui(gal[i], 0);
        }
        for (int i = 0; i < deg; i++) {
            mpz_set(gal[(size_t)i * inv], base[i]);
        }
        int glen = (deg - 1) * (int)inv + 1;
        if (glen < deg) {
            glen = deg;
        }
        reduce(gal, glen, phi, deg, n, scratch);
        for (int i = 0; i < deg; i++) {
            mpz_set(img[i], gal[i]);
        }
        /* img^idx, idx < r. */
        mpz_set_ui(powered[0], 1);
        for (int i = 1; i < deg; i++) {
            mpz_set_ui(powered[i], 0);
        }
        mpz_set_ui(cur[0], 1);
        for (int i = 1; i < deg; i++) {
            mpz_set_ui(cur[i], 0);
        }
        for (int i = 0; i < deg; i++) {
            mpz_set(cur[i], img[i]);
        }
        {
            unsigned e = idx;
            int first = 1;
            mpz_set_ui(powered[0], 1);
            for (int i = 1; i < deg; i++) {
                mpz_set_ui(powered[i], 0);
            }
            while (e) {
                if (e & 1u) {
                    pmul(powered, powered, cur, deg, phi, n, raw, scratch);
                }
                e >>= 1;
                if (e) {
                    pmul(cur, cur, cur, deg, phi, n, raw, scratch);
                }
                first = 0;
            }
            (void)first;
        }
        pmul(s1, s1, powered, deg, phi, n, raw, scratch);
        unsigned long small = (nmod * idx) / r;
        if (small) {
            for (int i = 0; i < deg; i++) {
                mpz_set(cur[i], img[i]);
            }
            mpz_set_ui(powered[0], 1);
            for (int i = 1; i < deg; i++) {
                mpz_set_ui(powered[i], 0);
            }
            unsigned e = (unsigned)small;
            while (e) {
                if (e & 1u) {
                    pmul(powered, powered, cur, deg, phi, n, raw, scratch);
                }
                e >>= 1;
                if (e) {
                    pmul(cur, cur, cur, deg, phi, n, raw, scratch);
                }
            }
            pmul(alpha, alpha, powered, deg, phi, n, raw, scratch);
        }
    }
    if (ok == 1) {
        /* acc = s1^exponent * alpha, exponent = n//r. Window 4. */
        mpz_t table[16][APR_MAX];
        for (int t = 0; t < 16; t++) {
            for (int i = 0; i < deg; i++) {
                mpz_init(table[t][i]);
            }
        }
        mpz_set_ui(table[0][0], 1);
        for (int i = 1; i < deg; i++) {
            mpz_set_ui(table[0][i], 0);
        }
        for (int i = 0; i < deg; i++) {
            mpz_set(table[1][i], s1[i]);
        }
        for (int t = 2; t < 16; t++) {
            pmul(table[t], table[t - 1], s1, deg, phi, n, raw, scratch);
        }
        mpz_set_ui(acc[0], 1);
        for (int i = 1; i < deg; i++) {
            mpz_set_ui(acc[i], 0);
        }
        unsigned long bits = mpz_sizeinbase(exponent, 2);
        int started = 0;
        if (mpz_zero(exponent)) {
            started = 1;
        }
        for (long bit = (long)bits - 1; bit >= 0;) {
            int nb = 4;
            if (bit + 1 < nb) {
                nb = (int)bit + 1;
            }
            unsigned w = 0;
            for (int s = 0; s < nb; s++) {
                w = (w << 1) | (unsigned)mpz_tstbit(exponent, (mp_bitcnt_t)(bit - s));
            }
            if (!started) {
                if (w == 0) {
                    bit -= nb;
                    continue;
                }
                for (int i = 0; i < deg; i++) {
                    mpz_set(acc[i], table[w][i]);
                }
                started = 1;
                bit -= nb;
                continue;
            }
            for (int s = 0; s < nb; s++) {
                pmul(acc, acc, acc, deg, phi, n, raw, scratch);
            }
            if (w) {
                pmul(acc, acc, table[w], deg, phi, n, raw, scratch);
            }
            bit -= nb;
        }
        pmul(acc, acc, alpha, deg, phi, n, raw, scratch);
        {
            int h = is_power(acc, deg, r, phi, n, scratch);
            ok = h < 0 ? 0 : h + 1;
        }
        for (int t = 0; t < 16; t++) {
            for (int i = 0; i < deg; i++) {
                mpz_clear(table[t][i]);
            }
        }
    }
    if (gal) {
        for (int i = 0; i < glen_cap; i++) {
            mpz_clear(gal[i]);
        }
        free(gal);
    }
    mpz_clear(exponent);
    for (int i = 0; i < APR_MAX; i++) {
        mpz_clear(s1[i]);
        mpz_clear(alpha[i]);
        mpz_clear(img[i]);
        mpz_clear(powered[i]);
    }
    for (int i = 0; i < APR_MAX; i++) {
        mpz_clear(base[i]);
        mpz_clear(acc[i]);
        mpz_clear(cur[i]);
        mpz_clear(phi[i]);
    }
    for (int i = 0; i < APR_MAX * 2; i++) {
        mpz_clear(raw[i]);
    }
    mpz_clear(scratch);
    mpz_clear(n);
    return ok;
}

/* True when some n^{start+j} mod s, j = 1..count, is a proper divisor of n. */
int aprcl_residue_divides(const uint64_t *n_limbs, size_t nlimbs,
                          const uint64_t *s_limbs, size_t slimbs,
                          uint64_t start, uint64_t count) {
    if (!n_limbs || !s_limbs || nlimbs == 0 || slimbs == 0 || count == 0) {
        return -1;
    }
    mpz_t n, s, base, acc, root, tmp;
    mpz_init(n);
    mpz_init(s);
    mpz_init(base);
    mpz_init(acc);
    mpz_init(root);
    mpz_init(tmp);
    mpz_import(n, nlimbs, -1, sizeof(uint64_t), 0, 0, n_limbs);
    mpz_import(s, slimbs, -1, sizeof(uint64_t), 0, 0, s_limbs);
    mpz_sqrt(root, n);
    mpz_mod(base, n, s);
    mpz_powm_ui(acc, base, start, s);
    int hit = 0;
    for (uint64_t j = 0; j < count; j++) {
        mpz_mul(acc, acc, base);
        mpz_mod(acc, acc, s);
        if (mpz_cmp_ui(acc, 1) > 0 && mpz_cmp(acc, root) <= 0 && mpz_divisible_p(n, acc)) {
            hit = 1;
            break;
        }
    }
    mpz_clear(tmp);
    mpz_clear(root);
    mpz_clear(acc);
    mpz_clear(base);
    mpz_clear(s);
    mpz_clear(n);
    return hit;
}

/* Smallest primitive root modulo an odd prime q, matching the Python search. */
static unsigned long prim_root(unsigned long q) {
    unsigned long n = q - 1;
    unsigned long fac[64];
    int nf = 0;
    unsigned long x = n;
    for (unsigned long d = 2; d * d <= x; d += (d == 2 ? 1 : 2)) {
        if (x % d == 0) {
            fac[nf++] = d;
            while (x % d == 0) {
                x /= d;
            }
        }
    }
    if (x > 1) {
        fac[nf++] = x;
    }
    for (unsigned long g = 2;; g++) {
        int ok = 1;
        for (int i = 0; i < nf; i++) {
            unsigned long e = n / fac[i];
            unsigned long p = 1, base = g % q;
            while (e) {
                if (e & 1ul) {
                    p = (p * base) % q;
                }
                base = (base * base) % q;
                e >>= 1;
            }
            if (p == 1) {
                ok = 0;
                break;
            }
        }
        if (ok) {
            return g;
        }
    }
}

/* which = 1: j(chi, chi). which = 2: j(chi, chi^2). Coefficients in out[0..r). */
int aprcl_jacobi_sum(unsigned long q, unsigned r, int which, long long *out) {
    if (q < 3 || r < 1 || (q - 1) % r != 0 || !out || (which != 1 && which != 2)) {
        return -1;
    }
    unsigned long *ind = calloc(q, sizeof(unsigned long));
    if (!ind) {
        return -1;
    }
    unsigned long g = prim_root(q);
    unsigned long step = (q - 1) / r;
    unsigned long x = 1;
    for (unsigned long i = 0; i < q - 1; i++) {
        ind[x] = (i * step) % r;
        x = x * g % q;
    }
    for (unsigned i = 0; i < r; i++) {
        out[i] = 0;
    }
    int mult = (which == 2) ? 2 : 1;
    for (unsigned long t = 1; t < q; t++) {
        unsigned long u = (q + 1 - t) % q;
        if (u == 0) {
            continue;
        }
        unsigned long slot = (ind[t] + (unsigned long)mult * ind[u]) % r;
        out[slot] -= 1;
    }
    free(ind);
    return 0;
}
