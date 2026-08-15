"""Canonical test integers — shared, deterministic, no RNG.

Every constant here is a fixed mathematical specimen. Import these instead of
re-deriving literals in individual test modules.
"""
from __future__ import annotations

# Largest prime strictly less than 2^64 (hard 64-bit specimen, not CLI default).
LARGEST_PRIME_LT_2_64 = 18_446_744_073_709_551_557
# CLI default: 147-bit prime; n−1 factors → Pocklington (u128_nm1).
DEFAULT_CLI_N = 100_000_000_000_000_000_000_000_000_000_000_000_000_000_031
# Smooth n−1 specimen used by the n−1 Pocklington path tests (former default).
SMOOTH_NM1_PRIME = 600_000_000_000_000_000_001
NEAR_2_63_PRIME = 9_223_372_036_854_775_783
M61 = (1 << 61) - 1  # 2305843009213693951
M31 = (1 << 31) - 1  # 2147483647
P10_9_7 = 1_000_000_007
P10_9_9 = 1_000_000_009
P12_DIGIT = 999_999_999_989
P10_20 = 100_000_000_000_000_000_039  # next prime after 10^20 (67-bit)
SEMIPRIME_1E9 = P10_9_7 * P10_9_9

# Chernick Carmichael: sympy.ntheory.primetest.mr(n, [2,3,5]) is True; exact trial is False.
MR_LIAR = 3_943_673_813_084_040_361
MR_LIAR_FACTORS = (869_461, 1_738_921, 2_608_381)

SMALL_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
    73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151,
    157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233,
    239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317,
    331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419,
    421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503,
    509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 601, 607,
    613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 701,
    709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809, 811,
    821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887, 907, 911,
    919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997,
]

CARMICHAEL = (561, 1105, 1729, 2465, 2821, 6601, 8911, 10585, 15841, 29341)
POULET = (341, 561, 645, 1105, 1387, 1729, 1905)  # base-2 Fermat pseudoprimes
FERMAT_COMPOSITE = (
    (1 << 32) + 1,  # F5 = 4294967297 = 641 × 6700417
    (1 << 64) + 1,  # F6
)

# Precomputed-prime table edges (PRE_MAX = 2^20).
P_LE_2_20 = 1_048_573
P_GT_2_20 = 1_048_583
P_GT_2_20_B = 1_048_601
P_NEAR_1E6 = 999_983
P_NEAR_1E6_B = 999_979

LARGE_PRIMES_FAST = [
    P10_9_7,
    P10_9_9,
    M31,
    4_294_967_291,
    P12_DIGIT,
    1_000_000_000_039,
    999_999_999_999_999_989,
]

LARGE_PRIMES_SLOW = [M61, NEAR_2_63_PRIME, LARGEST_PRIME_LT_2_64, DEFAULT_CLI_N]

LARGE_COMPOSITES = [
    (1 << 63) - 1,
    (1 << 32) - 1,
    1_000_000_000_000,
    NEAR_2_63_PRIME - 1,
    LARGEST_PRIME_LT_2_64 - 1,
    SEMIPRIME_1E9,
    MR_LIAR,
]

# 66-bit prime; n+1 = 2^10 · 5^7 · 7^9 · 11^4 (fully trial-smooth). n−1 is
# not trial-smooth enough for Pocklington, so BLS settles on the n+1 side.
NP1_SMOOTH_PRIME = 47_265_372_806_959_999_999
# Smaller n+1-smooth prime for Lucas / default-suite checks.
NP1_SMOOTH_SMALL = 4_801_999  # n+1 = 2^4 · 5^3 · 7^4

# Class-number-1 ECPP fixture: n = a² + v² (D = −4), single-step GK.
P40_H1_A = 10**19 + 50
P40_H1_V = 23
P40_H1_T = 2 * P40_H1_A
P40_H1_D = -4
P40_H1_FRIENDLY = P40_H1_A**2 + P40_H1_V**2  # 100000000000000001000000000000000003029
P40_H1_C = 2865377017242656090
P40_H1_Q = 34899421401875313457

# Smallest n-digit primes (OEIS A003617). Tests-only; not CLI defaults.
P100_DIGIT = 10**99 + 289
P200_DIGIT = 10**199 + 153
P201_DIGIT = 10**200 + 357
P300_DIGIT = 10**299 + 669
P500_DIGIT = 10**499 + 153
P1000_DIGIT = 10**999 + 7

# 131-digit CM-friendly prime 10^130+1113. Proved by in-tree ECPP (D=−19).
# Not the CLI default (F6). Default-suite tests must not call is_prime on it.
P131_DIGIT = 10**130 + 1113
# Smallest 132-digit prime (10^131+63). Pages lab yardstick for computed H_D.
P132_DIGIT = 10**131 + 63
# Smallest 150-digit prime (10^149+183). Pages lab 150-digit gate.
P150_DIGIT = 10**149 + 183

# User-reported CLI / lab specimens (exact decimals they typed).
# 10^130+1113 is prime; the 132-digit look-alike 10^131+1113 is 193 · q.
USER_P131 = 10**130 + 1113
USER_P131_NEXT = 10**130 + 1189
USER_C132_LOOKALIKE = 10**131 + 1113
USER_C132_FACTOR = 193
USER_P132 = 10**131 + 63
USER_P150 = 10**149 + 183
# 123-digit Fermat composite; prev_prime and is-prime CLI both used this.
USER_C123 = 10**122 + 1203
USER_C123_FACTOR = 5_482_299_091
USER_C123_PREV = 10**122 + 1119
# 122-digit neighbor of the same shape (larger prime gap / harder CM tree).
USER_N122 = 10**121 + 1203
USER_N122_PREV = 10**121 + 531
