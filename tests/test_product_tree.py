"""Product / remainder tree batch trial."""

from __future__ import annotations

import math

from best_prime.product_tree import (
    batch_smooth_kernel,
    peel_kernel,
    primorial,
    product_tree,
    remainder_tree,
)


def test_remainder_tree_matches_mod():
    vals = [3, 5, 7, 11, 13, 17]
    tree = product_tree(vals)
    a = 2 * 3 * 5 * 7 * 11 * 13 * 17 * 19
    rems = remainder_tree(a, tree)
    assert rems == [a % v for v in vals]


def test_batch_smooth_kernel_matches_gcd():
    bound = 200
    a = primorial(bound)
    ms = [1001, 2**8 * 3**3 * 97, 10**12 + 39, 23 * 29 * 10007]
    got = batch_smooth_kernel(ms, bound)
    assert got == [math.gcd(m, a) for m in ms]


def test_peel_kernel_strips_smooth_part():
    m = 2**5 * 3**2 * 5 * 97 * 101
    ker = 2 * 3 * 5
    smooth, rem = peel_kernel(m, ker)
    assert rem == 97 * 101
    assert smooth == 2**5 * 3**2 * 5


def test_empty_and_singleton():
    assert batch_smooth_kernel([], 100) == []
    assert batch_smooth_kernel([30], 10) == [math.gcd(30, primorial(10))]
