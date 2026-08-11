"""Canonical test integers — shared, deterministic, no RNG.

Every constant here is a fixed mathematical specimen. Import these instead of
re-deriving literals in individual test modules.
"""
from __future__ import annotations

# Largest prime strictly less than 2^64 (hard 64-bit specimen, not CLI default).
LARGEST_PRIME_LT_2_64 = 18_446_744_073_709_551_557
# CLI default: 70-bit prime, OpenMP u128 full trial (isqrt ~ 24494897427).
DEFAULT_CLI_N = 600_000_000_000_000_000_001
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
