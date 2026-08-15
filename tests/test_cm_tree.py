"""CM downrun recording: D, class number, cofactor sizes."""

from __future__ import annotations

from best_prime.cm_tree import (
    discriminant_class_number,
    format_tree,
    last_cm_tree,
    record_from_cert,
    record_from_rec,
    tree_from_cert,
    tree_from_rec,
)
from best_prime.is_prime import lab
from best_prime.primality_ecpp import CLASS_NUMBER_1_D, gk_min_q
from best_prime.primality_fastecpp import fastecpp_search
from best_prime.certificate import primality_certificate


class TestClassNumber:
    def test_h1_list(self):
        for D in CLASS_NUMBER_1_D:
            assert discriminant_class_number(D) == 1


class TestTreeFromSearch:
    def test_fastecpp_59(self):
        dec, rec = fastecpp_search(59)
        assert dec is True
        assert rec is not None
        tree = record_from_rec(59, rec)
        assert tree
        assert last_cm_tree() == tree
        assert tree[0]["n_digits"] == 2
        assert tree[0]["D"] < 0
        assert tree[0]["h"] is not None and tree[0]["h"] >= 1
        assert tree[0]["q_bits"] >= 1
        assert rec["q"] >= gk_min_q(59)
        assert "->" in format_tree(tree) or len(tree) == 1


class TestTreeFromCert:
    def test_p40_ecpp(self):
        from tests.numbers import P40_H1_FRIENDLY

        cert = primality_certificate(P40_H1_FRIENDLY, kind="ecpp")
        tree = tree_from_cert(cert)
        assert tree
        assert tree[0]["D"] == int(cert["D"])
        assert tree[0]["h"] == 1
        assert record_from_cert(cert) == tree

    def test_pratt_has_no_tree(self):
        cert = primality_certificate(17)
        assert tree_from_cert(cert) == []
        assert tree_from_rec(17, None) == []


class TestLabTree:
    def test_tiny_has_no_tree(self):
        info = lab(97)
        assert info.get("cm_tree") is None

    def test_lab_does_not_leak_prior_tree(self):
        dec, rec = fastecpp_search(59)
        assert dec is True
        record_from_rec(59, rec)
        assert last_cm_tree()
        info = lab(97)
        assert info["cm_tree"] is None
