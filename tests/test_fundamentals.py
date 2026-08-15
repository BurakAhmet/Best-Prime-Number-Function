"""Committed FastECPP discriminant catalog matches live class numbers."""

from __future__ import annotations

from best_prime._fundamentals import D_CATALOG_MAX, FUNDAMENTAL_DH
from best_prime.classpoly import class_number
from best_prime.primality_ecpp import _is_fundamental_discriminant
from best_prime.primality_fastecpp import _discriminants


def test_catalog_sample_matches_live():
    for d, h in FUNDAMENTAL_DH[::200]:
        assert _is_fundamental_discriminant(d)
        assert class_number(d) == h


def test_catalog_is_increasing_abs_d():
    absds = [-d for d, _h in FUNDAMENTAL_DH]
    assert absds == sorted(absds)
    assert absds[0] >= 15
    assert absds[-1] <= D_CATALOG_MAX


def test_discriminants_helper_respects_caps():
    rows = _discriminants(200, 4)
    assert all(-d <= 200 and 2 <= h <= 4 for d, h in rows)
    assert (-15, 2) in rows
    assert (-23, 3) in rows
    assert all(d != -3 for d, _h in rows)  # class-number-1 omitted
