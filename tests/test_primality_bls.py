"""BLS n+1 and Combined Theorem 1 (Layer 1)."""

from __future__ import annotations

import math

from best_prime.is_prime import is_prime, lab
from best_prime.primality_nm1 import (
    _bls_cubic_ok,
    _combined_theorem1_ok,
    _lucas_uv,
    bls_primality,
    bls_side,
    nm1_primality,
)
from tests.numbers import (
    DEFAULT_CLI_N,
    M61,
    NP1_SMOOTH_PRIME,
    NP1_SMOOTH_SMALL,
    SEMIPRIME_1E9,
    SMOOTH_NM1_PRIME,
)


def _naive_lucas(k: int, P: int, Q: int, n: int) -> tuple[int, int]:
    if k == 0:
        return 0, 2
    if k == 1:
        return 1, P % n
    um2, um1 = 0, 1
    vm2, vm1 = 2, P % n
    for _ in range(2, k + 1):
        u = (P * um1 - Q * um2) % n
        v = (P * vm1 - Q * vm2) % n
        um2, um1 = um1, u
        vm2, vm1 = vm1, v
    return um1, vm1


class TestCombinedTheorem1Predicate:
    def test_rejects_fg_gt_sqrt_when_cubic_fails(self):
        # F, G even, gcd=2, FG > √n, but n >= max(F²G/2, FG²/2).
        F, G, n = 10, 14, 1000
        assert math.gcd(F, G) == 2
        assert F * G > math.isqrt(n)
        assert n >= max(F * F * G // 2, F * G * G // 2)
        assert not _combined_theorem1_ok(n, F, G)

    def test_accepts_true_cubic_bound(self):
        F, G, n = 20, 22, 100
        assert math.gcd(F, G) == 2
        assert n < max(F * F * G // 2, F * G * G // 2)
        assert _combined_theorem1_ok(n, F, G)

    def test_requires_gcd_exactly_2(self):
        assert not _combined_theorem1_ok(100, 20, 20)


class TestLucasLadder:
    def test_matches_naive_fibonacci(self):
        # P=1, Q=-1 → U_k = F_k, V_k = L_k.
        P, Q = 1, -1
        mod = 1_000_000_007
        for k in range(0, 40):
            got = _lucas_uv(k, P, Q, mod)
            assert not isinstance(got, int)
            u, v, _qk = got
            nu, nv = _naive_lucas(k, P, Q, mod)
            assert u == nu
            assert v == nv

    def test_matches_naive_other_params(self):
        P, Q, mod = 1, -2, 97
        for k in (0, 1, 2, 5, 8, 13, 21):
            got = _lucas_uv(k, P, Q, mod)
            assert not isinstance(got, int)
            u, v, _qk = got
            nu, nv = _naive_lucas(k, P, Q, mod)
            assert u == nu
            assert v == nv


class TestBlsPrimality:
    def test_squares_false(self):
        for n in (9, 25, 121, 111 ** 2, 10**10 * 10**10):
            assert bls_primality(n) is False
            assert nm1_primality(n) is False

    def test_small_composites_false(self):
        for n in (91, 121, 221, SEMIPRIME_1E9):
            assert bls_primality(n) is False

    def test_existing_nm1_still_true(self):
        assert nm1_primality(SMOOTH_NM1_PRIME) is True
        assert nm1_primality(M61) is True
        assert nm1_primality(DEFAULT_CLI_N) is True
        assert bls_primality(SMOOTH_NM1_PRIME) is True
        assert bls_primality(M61) is True

    def test_np1_smooth_small(self):
        assert bls_primality(NP1_SMOOTH_SMALL) is True
        assert is_prime(NP1_SMOOTH_SMALL) is True

    def test_np1_smooth_lab_bigint_bls(self):
        assert bls_primality(NP1_SMOOTH_PRIME) is True
        assert bls_side(NP1_SMOOTH_PRIME) == "np1"
        info = lab(NP1_SMOOTH_PRIME)
        assert info["is_prime"] is True
        assert info["path"] == "bigint_bls"
        assert info["note"]

    def test_serial_parallel_agree(self):
        for n in (
            NP1_SMOOTH_SMALL,
            NP1_SMOOTH_PRIME,
            SEMIPRIME_1E9,
            121,
            SMOOTH_NM1_PRIME,
        ):
            assert bls_primality(n, parallel=True) == bls_primality(n, parallel=False)
            assert is_prime(n, parallel=True) is is_prime(n, parallel=False)

    def test_cubic_extra_still_ok(self):
        n = 10**96 + 127
        F = 2 * 55667 * 195376548589 * 323382331513450093
        assert _bls_cubic_ok(n, F)
