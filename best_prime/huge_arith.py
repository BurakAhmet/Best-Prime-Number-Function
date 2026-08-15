"""In-tree ``pow(base, exp, mod)`` for huge odd moduli.

CIOS Montgomery below ~200 limbs; Karatsuba / Toom-3 + Barrett above.
Falls back to CPython ``pow`` when the native library is missing, the
modulus is even / tiny, or the limb count exceeds the C cap. Not a
primality oracle. Deterministic. Does not change ``DEFAULT_N``.
"""

from __future__ import annotations

import os
from array import array

HUGE_POW_MIN_BITS = 512

_lib = None
_lib_checked = False
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "is_prime_data")
_DATA_DIR = os.path.normpath(_DATA_DIR)


def _load():
    global _lib, _lib_checked
    if _lib_checked:
        return _lib
    _lib_checked = True
    import ctypes

    for name in ("huge_arith.so", "huge_arith.dylib", "huge_arith.dll"):
        path = os.path.join(_DATA_DIR, name)
        if not os.path.isfile(path):
            continue
        try:
            lib = ctypes.CDLL(path)
        except OSError:
            continue
        lib.huge_powmod.argtypes = [
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint64),
        ]
        lib.huge_powmod.restype = ctypes.c_int
        lib.huge_arith_max_limbs.argtypes = []
        lib.huge_arith_max_limbs.restype = ctypes.c_int
        if hasattr(lib, "huge_mul"):
            lib.huge_mul.argtypes = [
                ctypes.POINTER(ctypes.c_uint64),
                ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_uint64),
                ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_uint64),
            ]
            lib.huge_mul.restype = ctypes.c_int
        _lib = lib
        return _lib
    _lib = False
    return _lib


def _to_limbs(n: int) -> array:
    if n < 0:
        raise ValueError("limbs require a non-negative integer")
    if n == 0:
        return array("Q", [0])
    return array("Q", n.to_bytes((n.bit_length() + 63) // 64 * 8, "little"))


def _from_limbs(buf: array) -> int:
    return int.from_bytes(buf.tobytes(), "little")


def native_available() -> bool:
    return bool(_load())


def powmod(base: int, exp: int, mod: int) -> int:
    """``pow(base, exp, mod)`` via C Montgomery when it can win."""
    if mod <= 0:
        raise ValueError("powmod() requires a positive modulus")
    if exp < 0:
        raise ValueError("powmod() does not invert")
    if (mod & 1) == 0 or mod.bit_length() < HUGE_POW_MIN_BITS:
        return pow(base, exp, mod)
    lib = _load()
    if not lib:
        return pow(base, exp, mod)
    max_limbs = int(lib.huge_arith_max_limbs())
    nlimbs = (mod.bit_length() + 63) // 64
    if nlimbs > max_limbs:
        return pow(base, exp, mod)
    base %= mod
    if base == 0:
        return 0 if exp else 1
    if exp == 0:
        return 1
    import ctypes

    b = _to_limbs(base)
    e = _to_limbs(exp)
    m = _to_limbs(mod)
    # Pad modulus / base to the same limb count.
    while len(m) < nlimbs:
        m.append(0)
    while len(b) < nlimbs:
        b.append(0)
    if len(b) > nlimbs:
        return pow(base, exp, mod)
    out = array("Q", [0]) * nlimbs
    bp = (ctypes.c_uint64 * len(b)).from_buffer(b)
    ep = (ctypes.c_uint64 * len(e)).from_buffer(e)
    mp = (ctypes.c_uint64 * len(m)).from_buffer(m)
    op = (ctypes.c_uint64 * nlimbs).from_buffer(out)
    rc = lib.huge_powmod(bp, len(b), ep, len(e), mp, len(m), op)
    if rc != 0:
        return pow(base, exp, mod)
    return _from_limbs(out)


def native_mul(a: int, b: int):
    """Native school/Karatsuba/Toom-3 product, or None if the .so is missing."""
    if a < 0 or b < 0:
        raise ValueError("native_mul requires non-negative integers")
    lib = _load()
    if not lib or not hasattr(lib, "huge_mul"):
        return None
    import ctypes

    la = _to_limbs(a)
    lb = _to_limbs(b)
    out = array("Q", [0]) * (len(la) + len(lb))
    ap = (ctypes.c_uint64 * len(la)).from_buffer(la)
    bp = (ctypes.c_uint64 * len(lb)).from_buffer(lb)
    op = (ctypes.c_uint64 * len(out)).from_buffer(out)
    rc = lib.huge_mul(ap, len(la), bp, len(lb), op)
    if rc != 0:
        return None
    return _from_limbs(out)
