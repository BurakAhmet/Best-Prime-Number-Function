"""Class-number-1 and small-h Atkin–Morain ECPP."""

from __future__ import annotations

import math

import pytest

from best_prime._classpoly_h16 import HILBERT_CLASS_POLY
from best_prime.primality_ecpp import (
    CLASS_NUMBER_1_D,
    _J_INVARIANT,
    _admissible_pairs,
    ecpp_primality,
    gk_min_q,
    hilbert_root_mod_n,
    reduced_form_class_number,
)
from tests.numbers import (
    CARMICHAEL,
    P10_9_7,
    P40_H1_A,
    P40_H1_C,
    P40_H1_FRIENDLY,
    P40_H1_Q,
    P40_H1_T,
    P40_H1_V,
    P100_DIGIT,
    SMALL_PRIMES,
)


class TestGkMinQ:
    def test_rejects_r_plus_1_window(self):
        # n = (r+1)^4 − 1 ⇒ {n^{1/4}} is just below 1.
        r = 100
        n = (r + 1) ** 4 - 1
        assert math.isqrt(math.isqrt(n)) == r
        x = n**0.25
        q = (r + 1) ** 2 + 1
        assert (r + 1) ** 2 < q <= (x + 1) ** 2
        assert q < gk_min_q(n)
        assert not (q >= gk_min_q(n))

    def test_p40_q_meets_bound(self):
        assert P40_H1_Q >= gk_min_q(P40_H1_FRIENDLY)


class TestP40H1Friendly:
    def test_published_identities(self):
        n = P40_H1_FRIENDLY
        assert n == P40_H1_A**2 + P40_H1_V**2
        assert 4 * n == P40_H1_T**2 + 4 * P40_H1_V**2
        assert n + 1 + P40_H1_T == P40_H1_C * P40_H1_Q
        assert P40_H1_Q >= gk_min_q(n)

    def test_ecpp_true(self):
        n = P40_H1_FRIENDLY
        assert ecpp_primality(n) is True


class TestEcppDecisions:
    def test_modest_primes_never_false(self):
        for p in SMALL_PRIMES + [P10_9_7, 1_000_003]:
            assert ecpp_primality(p) is not False

    def test_composites_never_true(self):
        for n in (9, 15, 25, 91, 121, 561) + CARMICHAEL[:4]:
            assert ecpp_primality(n) is not True

    def test_serial_parallel_same_boolean(self):
        for n in (97, 91, 1_000_003, 9, P10_9_7):
            assert ecpp_primality(n, parallel=True) == ecpp_primality(
                n, parallel=False
            )

    def test_squares_false(self):
        for n in (9, 25, 121, 111**2):
            assert ecpp_primality(n) is False

    def test_below_two_false(self):
        assert ecpp_primality(0) is False
        assert ecpp_primality(1) is False

    def test_admissible_pairs_include_split_pieces(self):
        # Two large factors of m must both be offered (smallest first),
        # not only their product leftover.
        n = 10**8 + 7
        min_q = gk_min_q(n)
        p, r = min_q + 10, min_q + 30
        m = 2 * p * r
        pairs = _admissible_pairs(m, n, {2: 1}, p * r, [p, r])
        qs = [q for q, _c, proven in pairs if not proven]
        assert p in qs and r in qs
        assert qs[0] == p and qs[1] == r
        assert all(m // q >= 2 for q, _c, _pr in pairs)


class TestHilbertClassPoly:
    def test_h1_is_x_minus_j(self):
        for d in CLASS_NUMBER_1_D:
            assert HILBERT_CLASS_POLY[d] == (1, -_J_INVARIANT[d])

    def test_cohen_table_7_6_literals(self):
        # Cohen, A Course in Computational Algebraic Number Theory, Table 7.6.
        assert HILBERT_CLASS_POLY[-15] == (1, 191025, -121287375)
        assert HILBERT_CLASS_POLY[-20] == (1, -1264000, -681472000)
        assert HILBERT_CLASS_POLY[-23] == (
            1,
            3491750,
            -5151296875,
            12771880859375,
        )

    def test_reduced_form_class_numbers(self):
        assert reduced_form_class_number(-3) == 1
        assert reduced_form_class_number(-4) == 1
        assert reduced_form_class_number(-15) == 2
        assert reduced_form_class_number(-20) == 2
        assert reduced_form_class_number(-23) == 3
        assert reduced_form_class_number(-163) == 1

    def test_cz_root_of_h15(self):
        h = HILBERT_CLASS_POLY[-15]
        found = False
        for p in (19, 29, 31, 41, 59, 61, 71, 79, 89, 101):
            root = hilbert_root_mod_n(h, p)
            if root is None or isinstance(root, tuple):
                continue
            acc = 0
            for c in h:
                acc = (acc * root + c) % p
            assert acc == 0
            found = True
            break
        assert found


@pytest.mark.slow
@pytest.mark.xfail(
    reason=(
        "transcribed H_D only covers |D|<=68 (Cohen 7.6 / Fungrim 20b6d2); "
        "P100_DIGIT needs a larger published table before this is a CI gate. "
        "ecpp_primality only — never is_prime (AKS hang on a miss)."
    ),
    strict=False,
)
def test_p100_digit_ecpp_only():
    assert P100_DIGIT == 10**99 + 289
    assert ecpp_primality(P100_DIGIT, max_h=16) is True
