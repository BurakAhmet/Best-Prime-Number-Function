"""Computed Hilbert class polynomials match the transcribed |D| ≤ 68 table."""

from __future__ import annotations

import pytest

from best_prime._classpoly_h16 import HILBERT_CLASS_POLY
from best_prime.classpoly import (
    class_number,
    hilbert_class_poly,
    j_from_weber_f,
    reduced_forms,
    weber_f_functions,
    _j_of_form,
    _series_terms,
)
from best_prime.primality_ecpp import (
    CLASS_NUMBER_1_D,
    _J_INVARIANT,
    reduced_form_class_number,
)


class TestReducedForms:
    def test_matches_ecpp_counter(self):
        for d in (-3, -4, -7, -15, -20, -23, -47, -163, -68):
            assert len(reduced_forms(d)) == reduced_form_class_number(d)
            assert class_number(d) == reduced_form_class_number(d)

    def test_principal_form_present(self):
        assert (1, 1, 1) in reduced_forms(-3)
        assert (1, 0, 1) in reduced_forms(-4)


class TestMatchesTranscribed:
    @pytest.mark.parametrize("d", sorted(HILBERT_CLASS_POLY))
    def test_bit_identical(self, d: int):
        got = hilbert_class_poly(d)
        assert got == HILBERT_CLASS_POLY[d]

    def test_h1_is_x_minus_j(self):
        for d in CLASS_NUMBER_1_D:
            assert hilbert_class_poly(d) == (1, -_J_INVARIANT[d])

    def test_degree_equals_class_number(self):
        for d, coeffs in HILBERT_CLASS_POLY.items():
            assert len(coeffs) - 1 == class_number(d)

    def test_weber_f_recovers_j(self):
        from decimal import localcontext

        with localcontext() as ctx:
            ctx.prec = 50
            terms = _series_terms(50)
            for d in (-4, -7, -8, -11):
                a, b, _c = reduced_forms(d)[0]
                f, _f1, _f2 = weber_f_functions(a, b, d, terms)
                jw = j_from_weber_f(f)
                je = _j_of_form(a, b, d, terms)
                assert abs(jw.re - je.re) < 1
                assert abs(jw.im) < 1

    def test_d_neg71_has_class_number_7(self):
        # First discriminant past the transcribed table. Degree only —
        # coefficients are not in Cohen 7.6 / Fungrim 20b6d2.
        assert class_number(-71) == 7
        assert len(hilbert_class_poly(-71)) - 1 == 7
