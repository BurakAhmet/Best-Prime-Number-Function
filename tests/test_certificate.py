"""Pratt certificates and compositeness witnesses."""

from __future__ import annotations

import pytest

from best_prime.certificate import primality_certificate, verify_certificate
from best_prime.is_prime import is_prime


class TestCertificate:
    def test_two(self):
        c = primality_certificate(2)
        assert c["kind"] == "axiom"
        assert verify_certificate(c)

    def test_small_primes(self):
        for p in (3, 5, 17, 97, 101):
            c = primality_certificate(p)
            assert c["prime"] is True
            assert c["kind"] == "pratt"
            assert verify_certificate(c)
            assert is_prime(p)

    def test_composite_factor(self):
        c = primality_certificate(91)
        assert c["prime"] is False
        assert c["factor"] in (7, 13)
        assert 91 % c["factor"] == 0
        assert verify_certificate(c)

    def test_below_two(self):
        for n in (0, 1):
            c = primality_certificate(n)
            assert c["prime"] is False
            assert verify_certificate(c)

    def test_string_input(self):
        c = primality_certificate("17")
        assert verify_certificate(c) and c["n"] == 17

    def test_tampered_witness(self):
        c = primality_certificate(17)
        c["witness"] = 1
        assert verify_certificate(c) is False

    def test_bool_rejected(self):
        with pytest.raises(TypeError):
            primality_certificate(True)  # type: ignore[arg-type]
