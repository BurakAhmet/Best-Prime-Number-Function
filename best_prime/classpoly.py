"""Deterministic Hilbert class polynomials from reduced forms and j(τ).

``hilbert_class_poly(D)`` enumerates reduced positive-definite forms of
discriminant ``D`` and evaluates ``j(τ)`` by the Eisenstein/Δ q-expansion
in ``decimal`` arithmetic. Coefficients are reconstructed by nearest-integer
rounding. No PARI, Sage, FLINT, Enge ``cm``, or other CAS.

The transcribed table in ``_classpoly_h16`` is the bit-identical oracle for
``|D| ≤ 68`` (Cohen 7.1 / 7.6, Fungrim 20b6d2). This module computes those
same integers, then any larger fundamental (or order) discriminant the
FastECPP walk asks for.
"""

from __future__ import annotations

import math
from decimal import (
    Decimal,
    localcontext,
    ROUND_HALF_EVEN,
)
from functools import lru_cache

# Extra decimal digits on top of the Cohen-style height bound.
_GUARD_DIGITS = 24
# Retry ceiling if nearest-integer reconstruction is ambiguous.
_PREC_RETRIES = 4
_ROUND_TOL = Decimal("0.05")


class ClassPolyError(ValueError):
    """Could not reconstruct integer coefficients at the working precision."""


class _C:
    """Complex decimal. Internal to the q-expansion."""

    __slots__ = ("re", "im")

    def __init__(self, re: Decimal | int | str, im: Decimal | int | str = 0) -> None:
        self.re = re if isinstance(re, Decimal) else Decimal(re)
        self.im = im if isinstance(im, Decimal) else Decimal(im)

    def __add__(self, other: _C | Decimal | int) -> _C:
        if isinstance(other, _C):
            return _C(self.re + other.re, self.im + other.im)
        o = other if isinstance(other, Decimal) else Decimal(other)
        return _C(self.re + o, self.im)

    def __radd__(self, other: Decimal | int) -> _C:
        return self + other

    def __sub__(self, other: _C | Decimal | int) -> _C:
        if isinstance(other, _C):
            return _C(self.re - other.re, self.im - other.im)
        o = other if isinstance(other, Decimal) else Decimal(other)
        return _C(self.re - o, self.im)

    def __rsub__(self, other: Decimal | int) -> _C:
        o = other if isinstance(other, Decimal) else Decimal(other)
        return _C(o - self.re, -self.im)

    def __neg__(self) -> _C:
        return _C(-self.re, -self.im)

    def __mul__(self, other: _C | Decimal | int) -> _C:
        if isinstance(other, _C):
            return _C(
                self.re * other.re - self.im * other.im,
                self.re * other.im + self.im * other.re,
            )
        o = other if isinstance(other, Decimal) else Decimal(other)
        return _C(self.re * o, self.im * o)

    def __rmul__(self, other: Decimal | int) -> _C:
        return self * other

    def __truediv__(self, other: _C | Decimal | int) -> _C:
        if isinstance(other, _C):
            den = other.re * other.re + other.im * other.im
            return _C(
                (self.re * other.re + self.im * other.im) / den,
                (self.im * other.re - self.re * other.im) / den,
            )
        o = other if isinstance(other, Decimal) else Decimal(other)
        return _C(self.re / o, self.im / o)

    def __pow__(self, exp: int) -> _C:
        if exp < 0:
            return (_C(1) / self) ** (-exp)
        result = _C(1)
        base = self
        e = exp
        while e:
            if e & 1:
                result = result * base
            base = base * base
            e >>= 1
        return result

    def abs2(self) -> Decimal:
        return self.re * self.re + self.im * self.im


def reduced_forms(D: int) -> list[tuple[int, int, int]]:
    """Reduced positive-definite forms of discriminant ``D``.

    Same reduction as ``primality_ecpp.reduced_form_class_number``
    (``|b| ≤ a ≤ c``, and ``b ≥ 0`` when ``a = c`` or ``a = |b|``), then
    keep only primitive forms (``gcd(a,b,c) = 1``). Imprimitive forms
    belong to a proper sub-order; the ring class polynomial of
    discriminant ``D`` is the product over primitive classes. For
    fundamental ``D`` every reduced form is primitive.
    """
    if D >= 0 or D % 4 not in (0, 1):
        return []
    out: list[tuple[int, int, int]] = []
    a_max = math.isqrt((-D) // 3)
    for a in range(1, a_max + 1):
        for b in range(-a, a + 1):
            rhs = b * b - D
            four_a = 4 * a
            if rhs % four_a != 0:
                continue
            c = rhs // four_a
            if a > c:
                continue
            if (a == c or a == abs(b)) and b < 0:
                continue
            if math.gcd(math.gcd(a, abs(b)), c) != 1:
                continue
            out.append((a, b, c))
    return out


@lru_cache(maxsize=8192)
def class_number(D: int) -> int:
    """Number of reduced primitive positive-definite forms of discriminant ``D``."""
    return len(reduced_forms(D))


def _pi() -> Decimal:
    """π at the current decimal precision (Python docs series)."""
    three = Decimal(3)
    lasts = Decimal(0)
    t = three
    s = three
    n = 1
    na = 0
    d = 0
    da = 24
    while s != lasts:
        lasts = s
        n, na = n + na, na + 8
        d, da = d + da, da + 32
        t = (t * n) / d
        s += t
    return +s


def _sin_cos(x: Decimal) -> tuple[Decimal, Decimal]:
    """``(sin x, cos x)`` by Taylor after reduction to ``[-π/4, π/4]``."""
    pi = _pi()
    half_pi = pi / 2
    twopi = pi * 2
    x = x % twopi
    if x > pi:
        x -= twopi
    # x ∈ (−π, π]
    sign_sin = Decimal(1)
    sign_cos = Decimal(1)
    if x < 0:
        sign_sin = Decimal(-1)
        x = -x
    # x ∈ [0, π]
    if x > half_pi:
        x = pi - x
        sign_cos = Decimal(-1)
    # x ∈ [0, π/2]
    swap = False
    if x > pi / 4:
        x = half_pi - x
        swap = True
    # Taylor of sin / cos on [0, π/4]
    from decimal import getcontext

    lim = Decimal(10) ** -(getcontext().prec - 2)
    x2 = x * x
    sin_x = x
    term = x
    n = 1
    while True:
        term *= -x2 / Decimal((2 * n) * (2 * n + 1))
        sin_x += term
        if abs(term) < lim:
            break
        n += 1
        if n > getcontext().prec * 4:
            break
    cos_x = Decimal(1)
    term = Decimal(1)
    n = 1
    while True:
        term *= -x2 / Decimal((2 * n - 1) * (2 * n))
        cos_x += term
        if abs(term) < lim:
            break
        n += 1
        if n > getcontext().prec * 4:
            break
    if swap:
        sin_x, cos_x = cos_x, sin_x
    return sign_sin * sin_x, sign_cos * cos_x


def _sigma3_table(limit: int) -> list[int]:
    """σ₃(n) = ∑_{d|n} d³ for n = 0..limit (σ₃(0) unused)."""
    sig = [0] * (limit + 1)
    for d in range(1, limit + 1):
        d3 = d * d * d
        for n in range(d, limit + 1, d):
            sig[n] += d3
    return sig


def _series_terms(prec: int) -> int:
    """q-expansion length. Reduced τ always has |q| ≤ exp(−π√3) ≈ 0.00433."""
    # n * log10(1/0.00433) ≳ prec + 8  ⇒  n ≳ (prec + 8) / 2.36
    return max(24, (prec + 16) * 10 // 23)


def _j_from_q(q: _C, terms: int) -> _C:
    """j(τ) = E₄(q)³ / Δ(q) with Δ = q ∏ (1 − qⁿ)²⁴ (Ramanujan)."""
    sig = _sigma3_table(terms)
    # E4 = 1 + 240 ∑ σ₃(n) q^n
    qn = q
    e4 = _C(1)
    two40 = Decimal(240)
    for n in range(1, terms + 1):
        e4 = e4 + qn * (two40 * Decimal(sig[n]))
        qn = qn * q
    # Δ = q ∏_{n=1}^N (1 − q^n)^24
    qn = q
    delta = q
    one = _C(1)
    for _n in range(1, terms + 1):
        delta = delta * ((one - qn) ** 24)
        qn = qn * q
    # E₄³ − E₆² = 1728 Δ, so j = 1728 E₄³ / (E₄³ − E₆²) = E₄³ / Δ.
    return (e4 * e4 * e4) / delta


def _cis(theta: Decimal) -> _C:
    s, c = _sin_cos(theta)
    return _C(c, s)


def _q_from_tau(re: Decimal, im: Decimal) -> _C:
    """q = exp(2πi (re + i im)) = exp(−2π im) exp(2πi re)."""
    pi = _pi()
    abs_q = (-(pi + pi) * im).exp()
    if re == 0:
        return _C(abs_q)
    return _cis((pi + pi) * re) * abs_q


def _q_for_form(a: int, b: int, abs_d: int) -> _C:
    """q = exp(2πi τ) for τ = (−b + √D) / (2a)."""
    root = Decimal(abs_d).sqrt()
    aa = Decimal(a)
    re = Decimal(-b) / (aa + aa)
    im = root / (aa + aa)
    return _q_from_tau(re, im)


def _eta_from_tau(re: Decimal, im: Decimal, terms: int) -> _C:
    """η(τ) = q^{1/24} ∏ (1 − qⁿ), q = exp(2πi τ)."""
    pi = _pi()
    # q^{1/24} = exp(2πi τ / 24) = exp(−π im / 12) exp(πi re / 12)
    pref = (-pi * im / Decimal(12)).exp()
    q24 = _cis(pi * re / Decimal(12)) * pref
    q = _q_from_tau(re, im)
    acc = q24
    qn = q
    one = _C(1)
    for _n in range(1, terms + 1):
        acc = acc * (one - qn)
        qn = qn * q
    return acc


def _tau_parts(a: int, b: int, abs_d: int) -> tuple[Decimal, Decimal]:
    root = Decimal(abs_d).sqrt()
    aa = Decimal(a)
    return Decimal(-b) / (aa + aa), root / (aa + aa)


def weber_f_functions(a: int, b: int, D: int, terms: int) -> tuple[_C, _C, _C]:
    """``(f, f1, f2)`` at τ = (−b + √D)/(2a).

    f  = e^{−πi/24} η((τ+1)/2) / η(τ)
    f1 = η(τ/2) / η(τ)
    f2 = √2 η(2τ) / η(τ)
    """
    re, im = _tau_parts(a, b, -D)
    two = Decimal(2)
    eta = _eta_from_tau(re, im, terms)
    eta_half = _eta_from_tau(re / two, im / two, terms)
    eta_dbl = _eta_from_tau(re * two, im * two, terms)
    eta_shift = _eta_from_tau((re + 1) / two, im / two, terms)
    pi = _pi()
    # e^{−πi/24} = cis(−π/24)
    twist = _cis(-pi / Decimal(24))
    f = twist * eta_shift / eta
    f1 = eta_half / eta
    root2 = two.sqrt()
    f2 = eta_dbl * root2 / eta
    return f, f1, f2


def j_from_weber_f(f: _C) -> _C:
    """j = (f²⁴ − 16)³ / f²⁴."""
    u = f ** 24
    return ((u - 16) ** 3) / u


def j_from_weber_f2(f2: _C) -> _C:
    """j = (f₂²⁴ + 16)³ / f₂²⁴."""
    u = f2 ** 24
    return ((u + 16) ** 3) / u


def _j_of_form(a: int, b: int, D: int, terms: int) -> _C:
    return _j_from_q(_q_for_form(a, b, -D), terms)


def _height_digits(D: int, forms: list[tuple[int, int, int]]) -> int:
    """Cohen-style decimal-digit bound for the largest |coeff| of H_D."""
    if not forms:
        return _GUARD_DIGITS
    # log10 |j(τ)| ≈ π √|D| / (a ln 10)
    # Working in floats is enough for a *bound*; bump if reconstruction fails.
    s = 0.0
    root = math.sqrt(-D)
    ln10 = math.log(10.0)
    for a, _b, _c in forms:
        s += (math.pi * root) / (a * ln10)
    return int(s) + len(forms) + _GUARD_DIGITS


def _nearest_int(x: Decimal) -> int:
    return int(x.to_integral_value(rounding=ROUND_HALF_EVEN))


def _poly_times_linear(coeffs: list[_C], root: _C) -> list[_C]:
    """High-degree-first monic ``p(X)`` ← ``p(X) · (X − root)``."""
    n = len(coeffs)
    out = [_C(0) for _ in range(n + 1)]
    # (X^n + c_{n-1} X^{n-1} + … + c_0)(X − r)
    out[0] = coeffs[0]
    for i in range(n):
        out[i + 1] = out[i + 1] - root * coeffs[i]
        if i + 1 < n:
            out[i + 1] = out[i + 1] + coeffs[i + 1]
    return out


def _reconstruct(coeffs: list[_C]) -> tuple[int, ...]:
    out: list[int] = []
    for c in coeffs:
        if abs(c.im) > _ROUND_TOL:
            raise ClassPolyError(f"imaginary part {c.im} not near 0")
        n = _nearest_int(c.re)
        if abs(c.re - Decimal(n)) > _ROUND_TOL:
            raise ClassPolyError(f"real part {c.re} not near an integer")
        out.append(n)
    if not out or out[0] != 1:
        raise ClassPolyError("polynomial is not monic")
    return tuple(out)


def _compute_hd(D: int, prec: int) -> tuple[int, ...]:
    forms = reduced_forms(D)
    if not forms:
        raise ClassPolyError(f"no reduced forms for D={D}")
    terms = _series_terms(prec)
    with localcontext() as ctx:
        ctx.prec = prec
        ctx.rounding = ROUND_HALF_EVEN
        js = [_j_of_form(a, b, D, terms) for a, b, _c in forms]
        poly = [_C(1)]
        for jv in js:
            poly = _poly_times_linear(poly, jv)
        return _reconstruct(poly)


@lru_cache(maxsize=512)
def hilbert_class_poly(D: int) -> tuple[int, ...]:
    """Monic Hilbert class polynomial of discriminant ``D``, high degree first.

    Works for any negative ``D ≡ 0 or 1 (mod 4)`` (fundamental or not).
    Cached. Raises ``ClassPolyError`` if integer reconstruction fails after
    precision retries — that is a bug / precision underestimate, not a
    primality decision.
    """
    if D >= 0 or D % 4 not in (0, 1):
        raise ValueError(f"D must be a negative discriminant, got {D}")
    forms = reduced_forms(D)
    if not forms:
        raise ClassPolyError(f"no reduced forms for D={D}")
    prec = max(40, _height_digits(D, forms))
    last: ClassPolyError | None = None
    for _ in range(_PREC_RETRIES):
        try:
            return _compute_hd(D, prec)
        except (ClassPolyError, ZeroDivisionError, ArithmeticError) as exc:
            last = ClassPolyError(str(exc))
            prec = prec * 2 + 16
    assert last is not None
    raise last


def hilbert_class_poly_cached_or_table(D: int) -> tuple[int, ...]:
    """Prefer the transcribed table, else compute."""
    from ._classpoly_h16 import HILBERT_CLASS_POLY

    hit = HILBERT_CLASS_POLY.get(D)
    if hit is not None:
        return hit
    return hilbert_class_poly(D)
