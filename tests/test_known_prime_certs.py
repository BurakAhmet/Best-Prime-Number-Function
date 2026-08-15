"""Independent arithmetic check on a fixed prime list.

``verify_certificate`` is search-free. The default suite stays on
numbers the existing engines already prove quickly. FastECPP-band
primes (P100, P131) are ``@slow``.
"""

from __future__ import annotations

import pytest

from best_prime import is_prime, primality_certificate, verify_certificate
from best_prime.primality_ecpp import gk_min_q
from best_prime.primality_fastecpp import fastecpp_search
from tests.numbers import (
    DEFAULT_CLI_N,
    P40_H1_FRIENDLY,
    P100_DIGIT,
    P131_DIGIT,
    USER_C123,
    USER_C123_FACTOR,
)

FIXED_PRIMES = (2, 3, 17, 101, P40_H1_FRIENDLY, DEFAULT_CLI_N)


class TestFixedPrimeList:
    def test_certificate_matches_is_prime(self):
        for p in FIXED_PRIMES:
            assert is_prime(p) is True
            cert = primality_certificate(p)
            assert cert["prime"] is True
            assert cert["kind"] in {"axiom", "pratt", "bls", "ecpp"}
            assert verify_certificate(cert)

    def test_tamper_rejected(self):
        cert = primality_certificate(P40_H1_FRIENDLY)
        bad = dict(cert)
        bad["n"] = int(cert["n"]) + 2
        assert verify_certificate(bad) is False


class TestFastecppBandCertificate:
    def test_composite_not_unsupported(self):
        n = USER_C123
        cert = primality_certificate(n)
        assert cert.get("kind") != "unsupported"
        assert cert["prime"] is False
        assert cert.get("factor") == USER_C123_FACTOR or (
            1 < int(cert["factor"]) < n and n % int(cert["factor"]) == 0
        )
        assert verify_certificate(cert)

    def test_search_rec_is_verifiable_on_small_n(self):
        dec, rec = fastecpp_search(59)
        assert dec is True
        assert rec is not None
        assert "q" in rec
        assert int(rec["q"]) >= gk_min_q(59)
        cert = primality_certificate(59, kind="ecpp")
        assert cert["kind"] == "ecpp"
        assert verify_certificate(cert)


@pytest.mark.slow
def test_p100_fastecpp_certificate():
    cert = primality_certificate(P100_DIGIT)
    assert cert["prime"] is True
    assert cert["kind"] == "ecpp"
    assert verify_certificate(cert)
    assert is_prime(P100_DIGIT) is True


@pytest.mark.slow
def test_p131_fastecpp_certificate():
    cert = primality_certificate(P131_DIGIT)
    assert cert["prime"] is True
    assert cert["kind"] == "ecpp"
    assert verify_certificate(cert)
    assert is_prime(P131_DIGIT) is True
