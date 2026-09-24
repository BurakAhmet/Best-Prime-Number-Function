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

static int is_power(mpz_t *elem, int deg, unsigned r, mpz_t *phi, const mpz_t n, mpz_t scratch) {
    mpz_t raw[APR_MAX * 2];
    for (int i = 0; i < APR_MAX * 2; i++) {
        mpz_init(raw[i]);
    }
    int found = 0;
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
            found = 1;
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

    unsigned long bits = mpz_sizeinbase(n, 2);
    mpz_t *squares = malloc(sizeof(mpz_t) * bits * (size_t)deg);
    if (!squares) {
        return -1;
    }
    for (unsigned long b = 0; b < bits; b++) {
        for (int i = 0; i < deg; i++) {
            mpz_init(squares[(b * (size_t)deg) + (size_t)i]);
        }
    }
    for (int i = 0; i < deg; i++) {
        mpz_set(squares[i], base[i]);
    }
    for (unsigned long b = 1; b < bits; b++) {
        pmul(&squares[b * (size_t)deg], &squares[(b - 1) * (size_t)deg],
             &squares[(b - 1) * (size_t)deg], deg, phi, n, raw, scratch);
    }

    mpz_t exponent;
    mpz_init(exponent);
    mpz_set_ui(acc[0], 1);
    for (int i = 1; i < deg; i++) {
        mpz_set_ui(acc[i], 0);
    }
    int ok = 1;
    for (int k = 0; k < nidx && ok == 1; k++) {
        unsigned idx = idxs[k];
        if (idx == 0 || idx >= r) {
            continue;
        }
        mpz_set_ui(cur[0], 1);
        for (int i = 1; i < deg; i++) {
            mpz_set_ui(cur[i], 0);
        }
        mpz_mul_ui(exponent, n, idx);
        mpz_fdiv_q_ui(exponent, exponent, r);
        unsigned long eb = mpz_sizeinbase(exponent, 2);
        for (unsigned long bit = 0; bit < eb && bit < bits; bit++) {
            if (mpz_tstbit(exponent, bit)) {
                pmul(cur, cur, &squares[bit * (size_t)deg], deg, phi, n, raw, scratch);
            }
        }
        unsigned inv = 0;
        for (unsigned v = 1; v < r; v++) {
            if ((unsigned long)v * idx % r == 1u) {
                inv = v;
                break;
            }
        }
        int glen = deg * (int)inv + 1;
        if (glen < deg) {
            glen = deg;
        }
        mpz_t *gal = malloc(sizeof(mpz_t) * (size_t)glen);
        if (!gal) {
            ok = -1;
            break;
        }
        for (int i = 0; i < glen; i++) {
            mpz_init(gal[i]);
        }
        for (int i = 0; i < deg; i++) {
            mpz_set(gal[(size_t)i * inv], cur[i]);
        }
        reduce(gal, glen, phi, deg, n, scratch);
        for (int i = 0; i < deg; i++) {
            mpz_set(cur[i], gal[i]);
            mpz_clear(gal[i]);
        }
        for (int i = deg; i < glen; i++) {
            mpz_clear(gal[i]);
        }
        free(gal);
        pmul(acc, acc, cur, deg, phi, n, raw, scratch);
    }
    if (ok == 1) {
        ok = is_power(acc, deg, r, phi, n, scratch);
    }

    mpz_clear(exponent);
    for (unsigned long b = 0; b < bits; b++) {
        for (int i = 0; i < deg; i++) {
            mpz_clear(squares[(b * (size_t)deg) + (size_t)i]);
        }
    }
    free(squares);
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
