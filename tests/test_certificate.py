"""Pratt / BLS / Atkin–GKM certificates and compositeness witnesses."""

from __future__ import annotations

import copy

import pytest

from best_prime.certificate import primality_certificate, verify_certificate
from best_prime.is_prime import is_prime
from best_prime.primality_ecpp import gk_min_q
from tests.numbers import P40_H1_FRIENDLY, P40_H1_Q

# Combined Theorem 1 specimen: F=6, G=80, gcd=2, n < max(F²G/2, FG²/2).
COMBINED_BLS_PRIME = 10159


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

    def test_huge_composite_factor(self):
        # Huge composite must carry a proper factor, not kind=unsupported.
        n = 10**30 + 1
        c = primality_certificate(n)
        assert c["prime"] is False
        assert 1 < c["factor"] < n
        assert n % c["factor"] == 0
        assert verify_certificate(c)

    def test_unsupported_verifier_false(self):
        assert verify_certificate({"n": 99, "kind": "unsupported"}) is False


class TestBlsCertificate:
    def test_u64_cofactor_does_not_require_numba(self):
        """Stdlib-fallback CI sets OMP_NUM_THREADS and has no Numba."""
        from best_prime.is_prime import _accel_available, _configure_threads, is_prime

        _configure_threads()
        assert is_prime(1_000_003)
        # Accel may or may not be present; the call must not raise either way.
        assert _accel_available() in (True, False)

    def test_p40_round_trip(self):
        c = primality_certificate(P40_H1_FRIENDLY)
        assert c["prime"] is True
        assert c["kind"] in {"bls", "ecpp"}
        assert verify_certificate(c)

    def test_p40_tamper(self):
        c = primality_certificate(P40_H1_FRIENDLY)
        bad = copy.deepcopy(c)
        if c["kind"] == "bls":
            if c.get("side") == "np1":
                bad["inequality"] = "F>sqrt"
            else:
                bad["inequality"] = "FG>sqrt"
        else:
            bad["t"] = int(c["t"]) + 2
        assert verify_certificate(bad) is False

    def test_combined_stores_thm1_not_fg(self):
        c = primality_certificate(COMBINED_BLS_PRIME, kind="bls")
        assert c["kind"] == "bls"
        assert c["side"] == "combined"
        assert c["inequality"] == "combined_thm1"
        assert c["inequality"] != "FG>sqrt"
        F = 1
        for q, e in c["F"].items():
            F *= pow(int(q), int(e))
        G = 1
        for q, e in c["G"].items():
            G *= pow(int(q), int(e))
        assert c["F2G_over_2"] == F * F * G // 2
        assert c["FG2_over_2"] == F * G * G // 2
        assert COMBINED_BLS_PRIME < max(c["F2G_over_2"], c["FG2_over_2"])
        assert verify_certificate(c)
        bad = copy.deepcopy(c)
        bad["inequality"] = "FG>sqrt"
        assert verify_certificate(bad) is False


class TestEcppCertificate:
    def test_p40_kind_ecpp_round_trip(self):
        c = primality_certificate(P40_H1_FRIENDLY, kind="ecpp")
        assert c["kind"] == "ecpp"
        assert c["prime"] is True
        assert int(c["q_cert"]["n"]) >= gk_min_q(P40_H1_FRIENDLY)
        assert P40_H1_Q >= gk_min_q(P40_H1_FRIENDLY)
        assert verify_certificate(c)

    def test_ecpp_tamper(self):
        c = primality_certificate(P40_H1_FRIENDLY, kind="ecpp")
        bad = copy.deepcopy(c)
        bad["t"] = int(c["t"]) + 2
        assert verify_certificate(bad) is False

    def test_ecpp_verifier_uses_gk_min_q(self):
        c = primality_certificate(P40_H1_FRIENDLY, kind="ecpp")
        bad = copy.deepcopy(c)
        q_bad = gk_min_q(P40_H1_FRIENDLY) - 1
        assert q_bad < gk_min_q(P40_H1_FRIENDLY)
        bad["q_cert"] = copy.deepcopy(c["q_cert"])
        bad["q_cert"]["n"] = q_bad
        m = int(c["m"])
        if m % q_bad == 0 and m // q_bad >= 2:
            bad["c"] = m // q_bad
        assert verify_certificate(bad) is False


class TestPrattNoHang:
    def test_hostile_n_minus_1_failure_record(self):
        # 100-digit odd n; complete n−1 factoring must not be attempted.
        n = 10**99 + 3
        c = primality_certificate(n, kind="pratt")
        assert c["kind"] == "pratt"
        assert c.get("error") == "n-1_unfactored"
        assert c.get("prime") is not True
        assert verify_certificate(c) is False

    def test_pratt_composite_is_not_an_error(self):
        for n in (9, 15, 91):
            c = primality_certificate(n, kind="pratt")
            assert c.get("prime") is False
            assert verify_certificate(c)
            if "factor" in c:
                assert 1 < c["factor"] < n and n % c["factor"] == 0


def _forged_nm1(n: int, fmap: dict[int, int]) -> dict:
    """BLS n−1 shape with every Condition-I base equal to n itself."""
    factors = [primality_certificate(q) for q in sorted(fmap)]
    return {
        "n": n,
        "prime": True,
        "kind": "bls",
        "side": "nm1",
        "F": dict(fmap),
        "inequality": "F>sqrt",
        "witnesses": [{"q": q, "a": n} for q in fmap],
        "factors": factors,
    }


class TestVerifierSoundness:
    def test_forged_a_equals_n_rejected(self):
        # F|(n−1), F>√n, real prime children; a=n must not short-circuit Condition I.
        forged = {
            9: {2: 3},
            25: {2: 3, 3: 1},
            91: {2: 1, 3: 2, 5: 1},
        }
        for n, fmap in forged.items():
            cert = _forged_nm1(n, fmap)
            assert verify_certificate(cert) is False

    def test_composite_child_rejected_bls(self):
        c = primality_certificate(COMBINED_BLS_PRIME, kind="bls")
        assert verify_certificate(c)
        bad = copy.deepcopy(c)
        bad["factors"] = [
            {"n": int(child["n"]), "prime": False, "reason": "composite"}
            for child in c["factors"]
        ]
        assert verify_certificate(bad) is False

    def test_composite_child_rejected_ecpp(self):
        c = primality_certificate(P40_H1_FRIENDLY, kind="ecpp")
        assert verify_certificate(c)
        bad = copy.deepcopy(c)
        bad["q_cert"] = {
            "n": int(c["q_cert"]["n"]),
            "prime": False,
            "reason": "composite",
        }
        assert verify_certificate(bad) is False
