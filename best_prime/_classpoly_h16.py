"""Transcribed Hilbert class polynomials H_D for small-h CM ECPP.

Coefficients are copied from published listings. This module does not
evaluate j(τ) and does not call PARI, Sage, or classpoly.

Sources
-------
* Class-number-1 (the 13 discriminants): H_D(X) = X − j(D) with j(D)
  from Cohen, *A Course in Computational Algebraic Number Theory*,
  Table 7.1 (same integers as ``primality_ecpp._J_INVARIANT``).
* Small h > 1: Cohen ibid. Table 7.6 / §7.3.3 for D ∈ {−15, −20, −23,
  −24, −31, −35, −39, −40, …} as far as that table goes, cross-checked
  against Fungrim entry 20b6d2 (Johansson), “Table of H_D(x) for
  |D| ≤ 68”, https://fungrim.org/entry/20b6d2/ .  The X^{h−1}
  coefficients also match OEIS A305494 (Manyama).
* D = −163 is only in Table 7.1 (h = 1); Fungrim’s table stops at −68.
* Non-fundamental Fungrim rows that are not among the 13 class-number-1
  orders (−32, −36, −44, −48, −60, −63, −64) are omitted: the walk only
  consumes fundamental D (plus those 13).

A discriminant that is not in those listings is omitted.  Format: D →
monic coefficients, highest degree first.
"""

from __future__ import annotations

H_CAP = 16
D_TABLE_MAX = 2000

# D -> (c_h, c_{h-1}, ..., c_0), monic.
HILBERT_CLASS_POLY: dict[int, tuple[int, ...]] = {
    # Cohen Table 7.1: H_D(X) = X − j(D)
    -3: (1, 0),
    -4: (1, -1728),
    -7: (1, 3375),
    -8: (1, -8000),
    -11: (1, 32768),
    -12: (1, -54000),
    -16: (1, -287496),
    -19: (1, 884736),
    -27: (1, 12288000),
    -28: (1, -16581375),
    -43: (1, 884736000),
    -67: (1, 147197952000),
    -163: (1, 262537412640768000),
    # Cohen Table 7.6 / Fungrim 20b6d2
    -15: (1, 191025, -121287375),
    -20: (1, -1264000, -681472000),
    -23: (1, 3491750, -5151296875, 12771880859375),
    -24: (1, -4834944, 14670139392),
    -31: (1, 39491307, -58682638134, 1566028350940383),
    -35: (1, 117964800, -134217728000),
    -39: (
        1,
        331531596,
        -429878960946,
        109873509788637459,
        20919104368024767633,
    ),
    -40: (1, -425692800, 9103145472000),
    -47: (
        1,
        2257834125,
        -9987963828125,
        5115161850595703125,
        -14982472850828613281250,
        16042929600623870849609375,
    ),
    -51: (1, 5541101568, 6262062317568),
    -52: (1, -6896880000, -567663552000000),
    -55: (
        1,
        13136684625,
        -20948398473375,
        172576736359017890625,
        -18577989025032784359375,
    ),
    -56: (
        1,
        -16220384512,
        2059647197077504,
        2257767342088912896,
        10064086044321563803648,
    ),
    -59: (1, 30197678080, -140811576541184, 374643194001883136),
    -68: (
        1,
        -178211040000,
        -75843692160000000,
        -318507038720000000000,
        -2089297506304000000000000,
    ),
}
