"""Determinism: same n ⇒ same boolean, including threads and call order.

Complements benchmarks/check_determinism.py (CI script). These pytest cases
cover extra specimens and a small multi-thread smoke test on the pure-Python
band (OpenMP is not required to be re-entrant from many Python threads).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from best_prime.is_prime import is_prime, lab
from tests.numbers import (
    CARMICHAEL,
    FERMAT_COMPOSITE,
    MR_LIAR,
    P10_9_7,
    P12_DIGIT,
    P_GT_2_20,
    P_LE_2_20,
    POULET,
    SEMIPRIME_1E9,
)

DETERMINISM_CASES: list[tuple[object, bool]] = [
    (0, False),
    (1, False),
    (2, True),
    (3, True),
    (4, False),
    ("007", True),
    ("  97  ", True),
    ("+17", True),
    (97, True),
    (561, False),
    (P10_9_7, True),
    (P12_DIGIT, True),
    (SEMIPRIME_1E9, False),
    (MR_LIAR, False),
    (P_LE_2_20, True),
    (P_GT_2_20 * 1_048_601, False),
    ((1 << 32) - 1, False),
    ((1 << 64), False),
    ((1 << 64) + 1, False),
    ("9" * 100, False),
    *[(n, False) for n in CARMICHAEL[:5]],
    *[(n, False) for n in POULET[:4]],
    *[(n, False) for n in FERMAT_COMPOSITE],
]


CASES = DETERMINISM_CASES


class TestRepeatedCalls:
    @pytest.mark.parametrize("n,expected", CASES, ids=lambda v: str(v)[:24])
    def test_five_serial_trials_agree(self, n, expected):
        got = [is_prime(n, parallel=False) for _ in range(5)]
        assert got == [expected] * 5

    @pytest.mark.parametrize(
        "n,expected",
        [(P10_9_7, True), (P12_DIGIT, True), (SEMIPRIME_1E9, False), (MR_LIAR, False)],
    )
    def test_serial_equals_parallel(self, n, expected):
        s = is_prime(n, parallel=False)
        p = is_prime(n, parallel=True)
        assert s is p is expected

    def test_interleaved_order_does_not_change_answers(self):
        seq = [is_prime(n) for n, _ in CASES]
        again = [is_prime(n) for n, _ in CASES]
        assert seq == again
        assert seq == [e for _, e in CASES]

    def test_lab_boolean_matches_is_prime(self):
        for n, expected in CASES[:12]:
            assert lab(n)["is_prime"] is is_prime(n) is expected


class TestThreadedSmallBand:
    """Pure-Python band only — no OpenMP re-entry from many host threads."""

    def test_thread_pool_small_n_agrees(self):
        ns = list(range(0, 400)) + [x for x, _ in CASES if isinstance(x, int) and x < 10_000]

        def one(n: int) -> tuple[int, bool]:
            return n, is_prime(n)

        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = [pool.submit(one, n) for n in ns]
            got = [f.result() for f in as_completed(futs)]
        by_n = dict(got)
        for n in ns:
            assert by_n[n] is is_prime(n, parallel=False)
