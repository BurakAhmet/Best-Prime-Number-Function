/* Two-band cubic factor search (Lehman + 30-wheel). Deterministic, no RNG.
 * Linked into wheel_core.so. n = hi<<64 | lo, up to 128 bits when 4*k*n fits.
 */
#include <math.h>
#include <stdint.h>
#ifdef _OPENMP
#include <omp.h>
#endif

typedef unsigned __int128 u128;

/* Residues coprime to 30, as offsets from 7, 37, 67, … */
static const uint8_t W30_OFF[8] = {0, 4, 6, 10, 12, 16, 22, 24};

static u128 u128_from_halves(uint64_t lo, uint64_t hi) {
    return ((u128)hi << 64) | (u128)lo;
}

static uint64_t isqrt_u64(uint64_t n) {
    if (n < 2) {
        return n;
    }
    uint64_t s = (uint64_t)(sqrt((double)n) + 0.5);
    if (s > UINT64_C(0xffffffff)) {
        s = UINT64_C(0xffffffff);
    }
    uint64_t sq = s * s;
    if (sq == n) {
        return s;
    }
    if (sq > n) {
        do {
            s--;
            sq = s * s;
        } while (s && sq > n);
        return s;
    }
    for (;;) {
        uint64_t np1 = s + 1;
        if (np1 > UINT64_C(0xffffffff)) {
            return s;
        }
        if (np1 * np1 > n) {
            return s;
        }
        s = np1;
    }
}

static int is_square_u64(uint64_t n, uint64_t *out) {
    uint64_t s = isqrt_u64(n);
    if (s * s != n) {
        return 0;
    }
    *out = s;
    return 1;
}

static uint64_t isqrt_u128(u128 n) {
    if (n <= UINT64_MAX) {
        return isqrt_u64((uint64_t)n);
    }
    uint64_t hi = (uint64_t)(n >> 64);
    uint64_t a = isqrt_u64(hi);
    uint64_t x = a << 32;
    if (x == 0) {
        x = 1;
    }
    for (int i = 0; i < 5; i++) {
        uint64_t q = (uint64_t)(n / x);
        uint64_t y = (x >> 1) + (q >> 1) + (x & q & 1);
        if (y == 0) {
            y = 1;
        }
        if (y == x) {
            break;
        }
        x = y;
    }
    if (x > 1 && n / x < x) {
        x--;
    }
    if (x > 1 && n / x < x) {
        x--;
    }
    if (x < UINT64_MAX && n / (x + 1) >= (x + 1)) {
        x++;
    }
    if (x < UINT64_MAX && n / (x + 1) >= (x + 1)) {
        x++;
    }
    return x;
}

static u128 ceil_isqrt_u128(u128 n) {
    uint64_t s = isqrt_u128(n);
    if ((u128)s * (u128)s == n) {
        return (u128)s;
    }
    if (s == UINT64_MAX) {
        return (u128)s;
    }
    return (u128)s + 1;
}

static uint64_t ceil_icbrt_u128(u128 n) {
    if (n <= 1) {
        return (uint64_t)n;
    }
    uint64_t lo = 1, hi = UINT64_C(1) << 43;
    while (lo < hi) {
        uint64_t mid = lo + (hi - lo) / 2;
        u128 c = (u128)mid * mid * mid;
        if (c < n) {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    return lo;
}

static uint64_t lehman_extra(uint64_t cub, uint64_t k) {
    uint64_t need = (cub + 16ull * k - 1ull) / (16ull * k);
    uint64_t s = isqrt_u64(need);
    if (s > UINT64_MAX / s) {
        return s;
    }
    return (s * s == need) ? s : s + 1;
}

static u128 gcd_u128(u128 a, u128 b) {
    while (b) {
        u128 t = a % b;
        a = b;
        b = t;
    }
    return a;
}

static uint64_t small_factor(u128 n, u128 g) {
    if (g <= 1 || g >= n) {
        return 0;
    }
    u128 other = n / g;
    u128 s = g < other ? g : other;
    if (s > UINT64_MAX) {
        return 0;
    }
    return (uint64_t)s;
}

static uint64_t wheel_band(u128 n, uint64_t limit, int parallel) {
    if (limit < 7) {
        return 0;
    }
    int is64 = n <= UINT64_MAX;
    uint64_t n64 = is64 ? (uint64_t)n : 0;
    uint64_t found = 0;
    int use_omp = 0;
#ifdef _OPENMP
    use_omp = parallel && limit >= 200000u;
#endif
    if (use_omp) {
#ifdef _OPENMP
#pragma omp parallel for schedule(static, 2048)
        for (uint64_t base = 7; base <= limit; base += 30) {
            if (found) {
                continue;
            }
            for (int i = 0; i < 8; i++) {
                uint64_t p = base + W30_OFF[i];
                if (p > limit) {
                    break;
                }
                int hit = is64 ? (n64 % p == 0) : ((n % (u128)p) == 0);
                if (hit) {
#pragma omp atomic write
                    found = p;
                    break;
                }
            }
        }
#endif
        return found;
    }
    for (uint64_t base = 7; base <= limit; base += 30) {
        for (int i = 0; i < 8; i++) {
            uint64_t p = base + W30_OFF[i];
            if (p > limit) {
                return 0;
            }
            int hit = is64 ? (n64 % p == 0) : ((n % (u128)p) == 0);
            if (hit) {
                return p;
            }
        }
    }
    return 0;
}

static uint64_t try_k(u128 n, uint64_t cub, uint64_t k) {
    if (k != 0 && n > (((u128)-1) / 4) / k) {
        return 0;
    }
    u128 fourkn = (u128)4 * (u128)k * n;
    u128 a0 = ceil_isqrt_u128(fourkn);
    uint64_t extra = lehman_extra(cub, k);
    u128 a_max = a0 + extra;
    for (u128 a = a0; a <= a_max; a++) {
        u128 b2 = a * a - fourkn;
        uint64_t b;
        if (b2 > UINT64_MAX) {
            b = isqrt_u128(b2);
            if ((u128)b * (u128)b != b2) {
                continue;
            }
        } else if (!is_square_u64((uint64_t)b2, &b)) {
            continue;
        }
        uint64_t f = small_factor(n, gcd_u128(a + (u128)b, n));
        if (!f) {
            u128 d = a > (u128)b ? a - (u128)b : (u128)b - a;
            f = small_factor(n, gcd_u128(d, n));
        }
        if (f) {
            return f;
        }
    }
    return 0;
}

static uint64_t lehman_windows(u128 n, uint64_t cub, uint64_t k_max, int parallel) {
    uint64_t found = 0;
    int use_omp = 0;
#ifdef _OPENMP
    use_omp = parallel && k_max >= 4096u;
#endif
    if (use_omp) {
#ifdef _OPENMP
#pragma omp parallel for schedule(static, 1024)
        for (uint64_t k = 1; k <= k_max; k++) {
            if (found) {
                continue;
            }
            uint64_t f = try_k(n, cub, k);
            if (f) {
#pragma omp atomic write
                found = f;
            }
        }
#endif
        return found;
    }
    for (uint64_t k = 1; k <= k_max; k++) {
        uint64_t f = try_k(n, cub, k);
        if (f) {
            return f;
        }
    }
    return 0;
}

/* Return a proper factor ≤ 2^64-1, or 0 if none in the budget.
 * k_max is the inclusive cube-root budget (0 = skip both bands after 2,3,5).
 */
uint64_t lehman_factor_u128(uint64_t lo, uint64_t hi, uint64_t k_max, int parallel) {
    u128 n = u128_from_halves(lo, hi);
    if (n < 4) {
        return 0;
    }
    if ((n % 2) == 0) {
        return 2;
    }
    if ((n % 3) == 0) {
        return 3;
    }
    if ((n % 5) == 0) {
        return 5;
    }
    uint64_t r = isqrt_u128(n);
    if ((u128)r * (u128)r == n && r > 1) {
        return r;
    }
    uint64_t cub = ceil_icbrt_u128(n);
    uint64_t budget = k_max < cub ? k_max : cub;
    uint64_t f = wheel_band(n, budget, parallel);
    if (f) {
        return f;
    }
    return lehman_windows(n, cub, budget, parallel);
}
