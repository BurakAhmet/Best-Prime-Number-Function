"""n−1 / n+1 / combined BLS primality — complete deterministic proofs.

Brillhart–Lehmer–Selfridge:

* Fermat filter with fixed bases (composite if a^{n−1} ≢ 1 mod n).
* Pocklington on a fully factored F | (n−1) (condition I).
* Lucas U-sequence on a fully factored G | (n+1) (condition II).
* n−1: F > √n, or BLS Theorem 5 when n < 2F³.
* n+1: G > √n, or G = n+1 (complete factorization). No n+1 cubic extra.
* Combined Theorem 1: gcd(F, G) = 2 and n < max(F²G/2, FG²/2).

Deterministic. No RNG. Not Miller–Rabin as the engine.
"""

from __future__ import annotations

import math
import threading
import zlib
from typing import Optional

_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)

_TRIAL_BOUND = 100_000
_TRIAL_PRIME_CACHE_MAX = 5_000_000
# First peel of n±1. Deepen to ``_TRIAL_PRIME_CACHE_MAX`` only when the
# leftover is Fermat-composite. DEFAULT_N is 2·5·13·q with q a 140-bit
# prime: a 5e6 scan never finds another factor and dominated CLI TIME.
_CHEAP_TRIAL_BOUND = 50_000
# Pollard p−1 stage-1 bound (smooth factors of n±1 cofactors).
P1_B1_SMALL = 100_000
SIQS_MIN_BITS = 80
SIQS_MAX_BITS = 200
_SELFRIDGE_D_LIMIT = 256

Result = Optional[bool]

_primes_cache: tuple[int, ...] | None = None
_primes_cache_limit = 0
# Must match scripts/generate_wheel_core_c.py PRE_MAX (embedded odd primes).
_PRE_MAX_C = 1 << 20
_C_SPLIT_CAP = 64
_c_split_ready = False
_c_ps = None
_c_es = None
_c_rem = None
_c_complete = None
_c_limbs_rem = None
_c_rn = None
_c_split_lock = threading.Lock()


def _primes_upto(limit: int) -> tuple[int, ...]:
    global _primes_cache, _primes_cache_limit
    need = min(int(limit), _TRIAL_PRIME_CACHE_MAX)
    if _primes_cache is None or _primes_cache_limit < need:
        from .prime_sieve import _sieve_primes_upto

        _primes_cache = tuple(_sieve_primes_upto(need))
        _primes_cache_limit = need
    return _primes_cache


def _adaptive_trial_bound(m: int) -> int:
    bits = m.bit_length()
    if bits <= 40:
        return _TRIAL_BOUND
    if bits <= 80:
        return 1_000_000
    if bits <= 160:
        return _TRIAL_PRIME_CACHE_MAX
    if bits <= 280:
        return 200_000
    return 50_000


def _max_splits(bits: int) -> int:
    if bits <= 64:
        return 48
    if bits <= 160:
        return 48
    if bits <= 250:
        return 24
    if bits <= 512:
        return 8
    return 16


def _p1_b1(bits: int) -> int:
    if bits <= 80:
        return P1_B1_SMALL
    if bits <= 160:
        return 250_000
    return 200_000


def _brent_curve_count(bits: int) -> int:
    if bits <= 80:
        return 63
    if bits <= 160:
        return 16
    return 0


def _ecm_max_ms(bits: int) -> int:
    if bits <= 40:
        return 50
    if bits <= 64:
        return 200
    if bits <= 80:
        return 500
    if bits <= 100:
        return 2000
    if bits <= 160:
        return 8000
    if bits <= 220:
        return 600
    if bits <= 512:
        return 200
    if bits <= 1100:
        return 3_000
    if bits <= 1700:
        return 5_000
    return 500


def _siqs_max_ms(bits: int) -> int:
    if bits <= 100:
        return 5000
    return 20000


def _trial_split_py(m: int, bound: int, min_p: int = 2) -> tuple[dict[int, int], int]:
    """Peel prime powers in ``[min_p, bound]``. Returns (factors, remaining)."""
    fac: dict[int, int] = {}
    if m <= 1:
        return fac, m
    bound = min(int(bound), _TRIAL_PRIME_CACHE_MAX)
    for p in _primes_upto(bound):
        if p < min_p:
            continue
        if p > bound or p * p > m:
            break
        if m % p == 0:
            e = 0
            while m % p == 0:
                m //= p
                e += 1
            fac[p] = fac.get(p, 0) + e
            if m == 1:
                break
    return fac, m


def _bind_c_split(lib: object) -> bool:
    """Set ctypes signatures once. False when this .so has no splitter."""
    global _c_split_ready
    if _c_split_ready:
        return True
    if not hasattr(lib, "trial_split_odd_u64"):
        return False
    import ctypes

    u32 = ctypes.c_uint32
    u64 = ctypes.c_uint64
    lib.trial_split_odd_u64.argtypes = [
        u64,
        u64,
        ctypes.POINTER(u32),
        ctypes.POINTER(u32),
        ctypes.c_int,
        ctypes.POINTER(u64),
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.trial_split_odd_u64.restype = ctypes.c_int
    lib.trial_split_odd_limbs.argtypes = [
        u64,
        u64,
        u64,
        u64,
        ctypes.c_int,
        u64,
        ctypes.POINTER(u32),
        ctypes.POINTER(u32),
        ctypes.c_int,
        ctypes.POINTER(u64),
        ctypes.POINTER(u64),
        ctypes.POINTER(u64),
        ctypes.POINTER(u64),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.trial_split_odd_limbs.restype = ctypes.c_int
    global _c_ps, _c_es, _c_rem, _c_complete, _c_limbs_rem, _c_rn
    _c_ps = (ctypes.c_uint32 * _C_SPLIT_CAP)()
    _c_es = (ctypes.c_uint32 * _C_SPLIT_CAP)()
    _c_rem = ctypes.c_uint64()
    _c_complete = ctypes.c_int()
    _c_limbs_rem = tuple(ctypes.c_uint64() for _ in range(4))
    _c_rn = ctypes.c_int()
    _c_split_ready = True
    return True


def _trial_split_c(m: int, bound: int) -> tuple[dict[int, int], int, bool] | None:
    """Odd peel via wheel_core. None → caller uses Python.

    The third value is True when every prime ≤ min(bound, √m) was covered.
    """
    if m <= 1 or bound < 3:
        return {}, m, True
    from .is_prime import _load_c_core

    lib = _load_c_core()
    if not lib:
        return None
    with _c_split_lock:
        if not _bind_c_split(lib):
            return None
        return _trial_split_c_locked(lib, m, bound, _c_ps, _c_es, _c_complete)


def _trial_split_c_locked(lib, m: int, bound: int, ps, es, complete):
    import ctypes

    if m.bit_length() <= 64:
        rem = _c_rem
        nf = int(
            lib.trial_split_odd_u64(
                m, bound, ps, es, _C_SPLIT_CAP, ctypes.byref(rem), ctypes.byref(complete)
            )
        )
        if nf < 0:
            return None
        fac = {int(ps[i]): int(es[i]) for i in range(nf)}
        return fac, int(rem.value), bool(complete.value)
    if m.bit_length() > 256:
        return None
    nlimbs = (m.bit_length() + 63) // 64
    limbs = [0, 0, 0, 0]
    mm = m
    for i in range(nlimbs):
        limbs[i] = mm & ((1 << 64) - 1)
        mm >>= 64
    r0, r1, r2, r3 = _c_limbs_rem
    rn = _c_rn
    nf = int(
        lib.trial_split_odd_limbs(
            limbs[0],
            limbs[1],
            limbs[2],
            limbs[3],
            nlimbs,
            bound,
            ps,
            es,
            _C_SPLIT_CAP,
            ctypes.byref(r0),
            ctypes.byref(r1),
            ctypes.byref(r2),
            ctypes.byref(r3),
            ctypes.byref(rn),
            ctypes.byref(complete),
        )
    )
    if nf < 0:
        return None
    fac = {int(ps[i]): int(es[i]) for i in range(nf)}
    got = int(r0.value)
    nout = int(rn.value)
    if nout > 1:
        got |= int(r1.value) << 64
    if nout > 2:
        got |= int(r2.value) << 128
    if nout > 3:
        got |= int(r3.value) << 192
    return fac, got, bool(complete.value)


_ODD_GAPS_Z = b'x\xdaM\x98\xd1\x8a\xe4:\x12D\xc1\x98\xc4\x88D\x18a\x8c0F\x14E\xd14\xc3<,\x97a\x1e\x96e\x9f\xf7\xff\xbfh\xe3\x84<\x97KO\xf7t\xbbl)3222\xe4eY\xf9\x8a%\xf8\xe9\xffb\x8d\xcd\x17\xab.\x97%\x82\xebE\x172}g\x89y_\xa9\xdc\x13\xfa$\xb6\xf0C[\xe1\xfe\xf9x\xea\xcf5riQ\xb8\xdd?\xf4P\x16o\x93\xba\xa9\xe8K\x976\xfd[kIo1\xd7\xd4\xf7\xa1\xc5\xf4|(\x06\xad\x9e3\x12/\xdf\x1c\xa8\x9e<\x17\xad\xa0\xdf\xd2qgi\x7f\xd2\xc8%\xde\xba\xde\xbc\x18\xc1\x04\xbb\xea\xd7\xcc-g\xa0\xce\x8d\xdb\xcb\xa1\'\xba6\xd6\xfeZ3\x9ac\xccm\xaf\xac\xa4\xcb\xba\xb4\xec\xcb\xa9\r\xf5\xf7F\x08\xb5(-?\xb1\x1b\x86\xadu\xad\xb9\xebS\xbe\x95Q\xeav`\xa8\x13\xcct\x16\xa9\x05\xaeFNK\x9czt[\xb3\x96y\xff\x13\xa4\x96\x9e@\xe8\xca^\x01umN\xb0$(,\xb7?_\x95\x822>\xca\xb2_\nU\xbb\x91\xcfIyn!\xac\xfd\x04.`\xee\xcb\x1e\xc7\xeeJ\x9ez\xa6\xcct)@\xa9\xe1\x92\xedI\xfdV\x97A\x11\x0b.\xe5\nh\xfa\xde\xda\x04(\xd7C\xd1\x1a\xe1s\x89]\x99G*Me\xb4\xb4^\xa8\x8a\xbe\xfc_l\x83\x0c\xa24\xe1\xac\xb2\xaf\xe1\xd5H\xaf+\xce]\x9b\xb4\xddA\x88\x0c\x99m!\xbd\xbe\xceM\xea\xd05q)M\xa6B\\\xe1\x9a\xefI$If\xb76U\xac\t\x01z\x86\xd2\x8b\xaaHG\x84\x8b\x93\xa0\xad4\xd6f\x06\xac\x17\xdc*/\xd7hu \x02\xf3\xd0=c5\xaa&\xd5\xb3\x89\xaeg\xbd\xf5\xb3m\xae\x1b\xb5H\xd8\xbce\xe9\x8b)\xda&\x8d\xd3\xf4W\x88\xe4\x11e\xeb\x82\xa5i\xc1\xa10\x01\x82\xa4\xb2\xed\xcai\xb2U\x01v\x95B\xbf\x1f\xf0g\x87\xfb*J\x8c\xd9)D\x9eP\xb8j#1E\xa5\xd2F\x156\x10\xc9\xa8.\xd8.\xac[\xec-\x16\xaa2Y\xef\xc0s\xf6R\xd5\xe5\xe3i\xa4\xd0R\xeb2\xd6\x1e\x02\xd9\xe87s/\x97\x1c\xc2\xe2\x04d\x81\xc4\x1a\x1dL\xb2\x11\xa7\x9e\x8fu\xf6s\xaa\xacJ}\xcc\xba\xc4;]\x8f\xa3\x88\xddpC\x95t\x03A\xa0t\x06M\xcd\x9a&\x81\xaaw\xc4\x00\xe8\x84\xae\xf08\xc9D\xd5\x12\x1f\xb4[\x1au\x11x\xd9\x05Gi\xf0\x99\xa2\x81\xf8\xd4\x98\x13\xae\xa5\n\x0b\xad?5\xcdg(W\xc4q\xfej\xe6\xfc\xb3\x0e\x92T\x15\x10M\x18omy:\nE\xc0/\x04\xb9f\xcb\x83(\x1d\x8b\xa0\x83\xbbyn7\x12\xb3\xb8\xdd\xb4\xf8\xbd\x9dSl\xd4(\xa1\x0f\xbcIT\xb5kyM\xe9rE\xe9\xc0\x9d\xe2\xf7\xa3L\xf4\xb5\xc6\x03\xe0\xa1v|\x8a\x99\xec\xaf\x16.\xb3\x02B\x07\xb2\xec\xbavo\xfe\xb3\xa3n\xaaj\xe6{\xb1>\xc0\xdf\xe8\x02y\n\xde$\x8f\x16\xbf@G\xf2D+vrxKhrv\x9bb\x15p\xdc\x92\x85?\x0c\xc4fJ\x01\x81\x1b.\xad\x97"j\x8a\xd8\xc2H\xf7\x90\x13M\x9c\x9f\xd5$Z[Z\xbe\xd55l\x14uX\xb2\x14\xa1\xb5i\xb8\x11D\xf3\xb4d\xdeu\x07\x9a\xc3M ]*Uiz\xe3\xd8\x8f\xf2\xa8oy\xfap\xa3f\xa5A+\xb4\xd9\xa4\x82\xf7M\x94D\xfb\x8e\x0f k\xb1\xaa\xdb\x87\x05\xbc\xc6i\xec7K\xad\xa0\xad{}\xc6\xd2\xbd\xdca\xe1\xc9\xfa\xa8#1@\xf9\x1d\xdc\xa1\xa7\xf2\xb9\x82\x9fY\xc7Z\xcf\xcdSF[A\nUB\xb9\x87u\xcdRK\x93\xb72\'Q\xaag\xe8\x88c%\x1f\x00R\xd3@\xe7\x19\xcb\xcf?\xa3\xa0z\xcf\xf84\xb3R\xf0T\x89\xa3V\xbd\xfa\x9f\x81\xe9\xfa\xfc@\xa1\x82n\xadq7\xcbZ$\xb8\xd2\xd9\x80|I$\x15\xc0Xs\x0e\x11\xab\xe1\x85\xb0w\x94-\xefgt\xea\xd6C\x9f\x13\xb8GE\xdf\x9d\xd0\xb9AGt\xbd\xbdg\x817\x1a\xc0\x02#R\xcd\x923\xf5\x8e$R7.\x85\\\xbaX\xa1\x94\x057\xd5\x92\x08\xd3\xa8\xa8\xd4$\xfc\xd2o\x12EtO\x8f\xb68\xc4-\'\x8a\xa8\xfa&}\x98\x1e\x0f\x00\n\xe3u\x8b\xb2\xd2\xbeR\x8c~t$S\x89\x88T\x8c\xd0\xf8\x1ce\x80\xe3\xad\xdb\xd5c*\xbc\x0b\xf0\xd6PU+wf\xb3\xe2\x14{\xc4\xb2\xfaM\xa1\xb3\x1a\xcb\xed\xb1\x0c\xfa\xbc\xc3w\xd0\x8f\xf8u\xb8v*\xa7\xeeT\xe1\xd3.@?\xce\xf0E\x8f\xe6j\xd6kpd<\x98K&\xa2\xb5\xf44)\xd7\xf4+(\xb2\xf8#\x1c\xde\x9eP)\x8cU\xa4T\xfd\xce\xc6l\x9evG\x0f\xb5\xe5\x9b\xb6/\x93\xd2),\x9a\xfd\x84DD\xa3\xdc\x19\xc1&\xb5\xa7\xeat\x9c\x9b\xea\x8a\xea\x0e\x0f\x0eq\xf1=\x8d\x00Rw\xcf>\xb0b\x0c\xf6\x9c;)\xd7J\x8358\xacD\x9a\xda\xb5\xed\xa8"MG\xf4\xc4\x01\xfc,\xa5\xa2~Z\xa6C\xc8\xf5\x83$*\xef>\'z+\xc74I\xdf\x14\x9e\xb9\x95S\n\x13\xbdE~\xe2\x83\x87\xebQ\xa9\x80\xee\xde\xe2\x99%\x9e\n\xd9\xaa\x06T`\x1cBS\xa7\x18O\x8cQ.\xa2\xf2\x9e\xb5\xe7\xd4V]\xb7H\xea\x97\xe1\x96\x1a\xe7\xf2\xd8\n\xb4{\xe99aQ\x85\xef\xbf\xa5_\xe3\xc5\xb37f\xecRX\x86/\xd8\x8d\x8fHgw\xe1\xc6\xb9\x88\x1c\xae\xcb\x7f\xb4\xdcn\x8bdvu\xbev-y0\x91Q^\xd4\x83\xf0{C\x82\xab\xad\xcd\xc10\xc9\x18\xcel\xfb^\x8c\x18\x8d\xd3\x1a\xc3\xd7~\xf6\x97\x16\xde]^\xb8\xea\x14\x113\x82dv4\xbe\xc3\x12\xbex\xab}\xb1\xf5\xd2\x0c\x05\x983Q\x8b@M\xed[/\xec\xae\xc8!H\xd9g\xa3\xf5\x94S^\xa2\xa1\x88\xa0\x0b\x8f\x89*\x8f\x95j\xc2\x13S\x96\xd3\x1b4\x1b\x93\x13\xfb)\xf41\xca\x0c\xf1\xb6\x7f\xc4\xae\x9b\xf9G\xdf\r\xa9\xf0@=\xc3\xed)\xa1\xd4\x93C\xaaXw\xab\xc4\xfaz\xccT8\xe8p\xb1_\xcc\xedY\x18a\xa7\x81{\x90\xaf\xa7\xd7\x9d\x10y+\xffz89\x96\x0f\xc0\x01\xd5\xae%+T\xf14M{\xda\xe94\x17\x8b(m\'\xa6\xc0\xc6\x03\xaal8L\x15\xbe\rx\x11\xd7Z\xfbi\xd3_\x99AaG\xddx\x10|<\xfa\x91S\xb5\xf8Q\xda\xb5\xceN\x91\x1a\x19\xfa|\x0b\x1bO\x1aj\r\\\x9aTGb\xb4\xf6f\xdf\x18\x93vv\xb5\x8a\xa5\x91\xcf\x89\x1a\tF\x99\x84\xbe\xaa\xce\'\'\x10+S\xdb\xbf\xc2Q\xa4\xbd\xdd\x10\xd9$\x16Y\x9e\x03E\xb6\xc3vAU\xaa\x0f4c\x99\xec\xa7i/\x0f"\x8f\xca\xc1T\x15\x1dI\xf1\x7f\xd3s{\x8a\xe1x\x8f\xddp\xa7}\xb8\xd4\xf4\x8c68)l\xfb_\x81\\\x05\x97f{\xf0\xa9\xcd\x81n<@\xf0c\x1a\xcenZ\x98\xadV\xb1\x9e\xc0\xde\x91&j\x89\xc7\x91\x84\xbe}\xa8\x18\xa7\xad\x8d-\xd6\xd5\xec\xcbq7\x80UA\xc4:"\xa8\x15\xc2T\x94\xec\xdf\xd6\x087y4\xb6\xaa\xc3\xc6\xdf\x1el\xff\xdbN\xceL_R\xf1fx0\x8f>\xfe08\x1b\x08\xca\xe0\xd1\xa6m\xfd\xefj\x9b\x92:v\xac\x0cp\x8b\x15\xc6\xa48\xb7S\xed\xd0\xf29\x8b\x88\xd7\n}\xb1\n\xe3\xdb\xbd\xaf\xcdX\xbb\x8c\x996\x80\xc5\x0c\xde\x1fd\\\xec\x1b}b\xd3\x8fqH\xae\xe8\xb4\x03&\xd6\xd2,&\x08\xe7\xb0(\x9arX\x8c\xfa;~\xb1~^\xf3,@=\xdb\x94Y{vJwt"\x15c\x84\xd5\x85[g^\xd9\xd61K\xe4l~6W\xfc\x9f\xd6J\r\xe7\x83\x8dO\r\x96\xd4yJK\x1c\x10\x91M\x9f\xaa3Gs\x0b\xe9\xa9K\xc1\xee\x8cO+\x9c*=<\x9d!\x15\xa2/q9b\xce\x07&r\xf8\xfc\'uE<T\xd66\xdeT\xb4\xed\xf3\x98\\~\xda\x96\n\xe8\x9b>\x1e\x9a0\xd5\x87\x00:\xe5\x9ch\xd8\xcbi\xcf/\x1f\xb2\xbe\x7fp\xa1;\x18{\x0cj\xec\xeahQ\xf7\x0cB\xdc\x18\xb6\nT\xa6\xde\x00\xbe,\x99\xe8\xdaji\xb0]^\xca\x0f\x9cTsW\x94\nk\xb7\xf2\xc5\xf5\x03 .!"\xbf"qz\xc6x\xda|\xfb\xc8\xaf\xd5\x14\xf1.\x8eq\xb6R<>\x95\xe0\xf2M\xd3C\x9eE\x8d\x1d\xbf9\x1b\x7f\x94\xde\xe5QGs\xe6\x8eCB\xe1\x7fk\xd3\xc1\xdb\x84\xdd\x1d\xc2\xe1\x85Y\x19\x941SK @Z\xfe\xe5\xb9\x9fS\xd4\xc9\x833\x9fVxo\x0c;\x84l(\xf8g\xbc\xe8d5me\xd4y\\y\xd9\xabF\xdf\x18fsH``b\x9e\xf3\xfdF\xa2\xb91u\xd0K\xbf\x14a\x00g\xebd\xc2\xd8\xd0f4,\xf6\xce\xaf\n|X\x95\x9bSH\xe7\xb0j\xceC\xfef\x15\xd4\xae}\xd6\xfd\xe3w\x0b\xc5+\x94p\xc7\\\x9a#M\xdb\xa8*\xb5?p\xfe\x07\x03\x88j\xc8\x89k\xd31\x9b\x0f\xcf\xcf\xc9HTz\xf9\xc5\x88n\xfaU\xe5\x86\x0eJ\x87\xe5\x88\xc3\x06\x02\\\xd2/\x1fn*4\x894\xc7\xc5\xbf\xf1\xe2q\xbf\xd6a6zNi\x10\x8e\xd5 \xaa\xb10\x0e\xe8\xae\x05U\xb5W\x8d\xb1\x91\xe9\xd3\xa3\xf4\x00s\xf4\xf1I\x9a\x91\x14:\xb41g\xaa_g\x88ln\x91\xf8\x81\xbb\xc6<%/\x05\x9a\xad\x88:g\x00q~YwD\xc8\x16\x7f\xcd\x8ex\xd1\x8bv\xc5\x83\xf7\x06\xca4\xf5t\x9f\'\x0b\x18=\x1a\xaf;\xa6\xa1`\xd0\xc2=\xce\x1a\\\xb2\xa3>\x18_\xc9\xec\x10\x17\xe9^\xa5P\xfbG\xed\xaf\x9e\xb8\xa3m\xb3N\x89\xa9\xe1\xa0\xe7\xa3\xecI\xae\xe1cAi\xafy>\xe7\x15\x11m\\\xado\x9e\xba\xb4\xe2{\x1e\xd2\x18\xd8:N\xba\xbd|dU\x9a\xdd\xbc-\x17G\xb0\xb5[aT\xd7\xceQ\x94\x81\xd1\xe9\xf2\xc5\xd0\x86\x0f\xfc\xc0\xd5m7\x7f\xd9\xf3\xc3\x19\xb0\xeb\x1e\xd3\xd1\xbe\x19\xef9_\x8e\xb0\x9b\x0f\xb3Z\x11\xd9W\xa6\x03Y)\x9d\x03$\x93E\x0f\x1b\xff\xb5\xf5y\xd2\xf9\n\n\xa0\x0fSc\x1d]}\xde\x1b\t\xf0\x86\xbd0\x8ft\x8e\xf8?\xc8K\xc3M'
_odd_groups: tuple[tuple[int, tuple[int, ...]], ...] | None = None


def _odd_prime_groups() -> tuple[tuple[int, tuple[int, ...]], ...]:
    """Products of odd primes ≤ 49999. Built once from a gap table."""
    global _odd_groups
    if _odd_groups is not None:
        return _odd_groups
    raw = zlib.decompress(_ODD_GAPS_Z)
    primes = [3]
    p = 3
    for d in raw:
        p += d
        primes.append(p)
    groups: list[tuple[int, tuple[int, ...]]] = []
    cur = 1
    curp: list[int] = []
    for prime in primes:
        if curp and cur.bit_length() + prime.bit_length() > 240:
            groups.append((cur, tuple(curp)))
            cur = prime
            curp = [prime]
        else:
            cur *= prime
            curp.append(prime)
    if curp:
        groups.append((cur, tuple(curp)))
    _odd_groups = tuple(groups)
    return _odd_groups


def _trial_split_small(m: int, bound: int) -> tuple[dict[int, int], int]:
    """Prime powers ≤ bound, using the embedded table. No ctypes."""
    fac: dict[int, int] = {}
    if m <= 1 or bound < 2:
        return fac, m
    if m >= 4 and (m & 1) == 0:
        e = 0
        while (m & 1) == 0:
            m >>= 1
            e += 1
        fac[2] = e
        if m == 1 or bound < 3:
            return fac, m
    if bound < 3:
        return fac, m
    for prod, plist in _odd_prime_groups():
        if m == 1 or plist[0] > bound or plist[0] * plist[0] > m:
            break
        use = plist
        gprod = prod
        if plist[-1] > bound:
            use = tuple(prime for prime in plist if prime <= bound)
            if not use:
                break
            gprod = 1
            for prime in use:
                gprod *= prime
        if math.gcd(m, gprod) == 1:
            continue
        stop = False
        for prime in use:
            # p > √m means m is 1 or prime. Do not record that prime as a
            # factor: trial stops at √m and leaves a prime cofactor.
            if prime * prime > m:
                stop = True
                break
            if m % prime != 0:
                continue
            e = 0
            while m % prime == 0:
                m //= prime
                e += 1
            fac[prime] = fac.get(prime, 0) + e
            if m == 1:
                stop = True
                break
        if stop:
            break
    return fac, m


def _core_open() -> bool:
    """True when wheel_core is already loaded. Does not dlopen it."""
    from .is_prime import _c_core, _c_core_checked

    return bool(_c_core_checked and _c_core)


def _brent_local(n: int, c: int, max_r: int = 1 << 18) -> int:
    """Deterministic Brent. Returns a divisor of n (maybe n)."""
    y = 2 % n
    g = 1
    q = 1
    ys = y
    r = 1
    step = 512
    x = y
    while g == 1 and r <= max_r:
        x = y
        for _ in range(r):
            y = (y * y + c) % n
        k = 0
        while k < r and g == 1:
            ys = y
            lim = r - k
            if lim > step:
                lim = step
            for _ in range(lim):
                y = (y * y + c) % n
                diff = x - y
                if diff < 0:
                    diff = -diff
                q = (q * diff) % n
            g = math.gcd(q, n)
            k += step
        r <<= 1
    if g == 1:
        return n
    if g == n:
        while True:
            ys = (ys * ys + c) % n
            g = math.gcd(abs(x - ys), n)
            if g > 1:
                break
    return g


def _proved_prime_upto_cheap(n: int) -> bool:
    if n <= 1:
        return False
    sq = math.isqrt(n)
    if sq > _CHEAP_TRIAL_BOUND:
        return False
    fac, rem = _trial_split(n, sq)
    return rem == n and not fac


def _brent_finish(n: int) -> tuple[dict[int, int], int] | None:
    """Split a ≤96-bit composite without opening wheel_core."""
    if n.bit_length() > 96 or _core_open():
        return None
    factor = None
    for c in (1, 2, 3):
        g = _brent_local(n, c)
        if 1 < g < n:
            factor = g
            break
    if factor is None:
        return None
    fac: dict[int, int] = {}
    still: list[int] = []
    for part in (factor, n // factor):
        sub, rem = _trial_split_staged(part)
        for p, e in sub.items():
            fac[p] = fac.get(p, 0) + e
        if rem > 1:
            still.append(rem)
    packed: list[int] = []
    for rem in still:
        if _proved_prime_upto_cheap(rem):
            fac[rem] = fac.get(rem, 0) + 1
        else:
            packed.append(rem)
    if len(packed) > 1:
        return None
    return fac, (packed[0] if packed else 1)


def _trial_split(m: int, bound: int) -> tuple[dict[int, int], int]:
    """Peel prime powers ≤ bound. Returns (factors, remaining).

    Integers up to 80 bits, and bounds ≤ 50_000, use embedded prime
    products so a cold CLI does not dlopen wheel_core. Wider integers
    and deeper bounds use that core. Above 2^20 the tail stays in Python.
    """
    fac: dict[int, int] = {}
    if m <= 1:
        return fac, m
    bound = min(int(bound), _TRIAL_PRIME_CACHE_MAX)
    if bound <= _CHEAP_TRIAL_BOUND and m.bit_length() <= 80 and not _core_open():
        return _trial_split_small(m, bound)
    # p*p > m stops before the prime is peeled, so m==2 stays a cofactor.
    if bound >= 2 and m >= 4 and (m & 1) == 0:
        e = 0
        while (m & 1) == 0:
            m >>= 1
            e += 1
        fac[2] = e
        if m == 1 or bound < 3:
            return fac, m
    got = _trial_split_c(m, bound)
    if got is None:
        extra, m = _trial_split_py(m, bound, min_p=3)
        fac.update(extra)
        return fac, m
    extra, m, complete = got
    for p, e in extra.items():
        fac[p] = fac.get(p, 0) + e
    if not complete and m > 1:
        tail, m = _trial_split_py(m, bound, min_p=_PRE_MAX_C + 1)
        for p, e in tail.items():
            fac[p] = fac.get(p, 0) + e
    return fac, m


def _looks_prime(c: int) -> bool:
    """Fermat bases 2…13: True means 'try a complete proof', not 'is prime'."""
    if c < 2:
        return False
    if c in (2, 3, 5, 7):
        return True
    if (c & 1) == 0:
        return False
    for a in _BASES[:6]:
        if a % c == 0:
            return c == a
        if pow(a, c - 1, c) != 1:
            return False
    return True


def _trial_split_staged(m: int) -> tuple[dict[int, int], int]:
    """Cheap trial, then deepen to the leftover's adaptive bound if composite.

    Bound follows the integer still being split, not the parent. A 140-bit
    prime leftover of DEFAULT_N must not trigger a 5e6 scan of that prime.
    """
    if m <= 1:
        return {}, m
    cheap = min(_CHEAP_TRIAL_BOUND, _adaptive_trial_bound(m))
    fac, rem = _trial_split(m, cheap)
    if rem <= 1 or _looks_prime(rem):
        return fac, rem
    full = _adaptive_trial_bound(rem)
    # Opening wheel_core for one factor just above 50_000 costs more than
    # a short Brent search on a ≤96-bit leftover. The core is used once
    # it is already loaded, and whenever Brent does not split n.
    if rem.bit_length() <= 96 and full > cheap and not _core_open():
        finished = _brent_finish(rem)
        if finished is not None:
            extra, rem = finished
            for p, e in extra.items():
                fac[p] = fac.get(p, 0) + e
            return fac, rem
    # A Fermat-composite above 96 bits almost never has its smallest prime
    # factor in (2^20, 5·10^6]. Scanning that range builds a Python prime
    # tuple. Brent / ECM / SIQS find a 21-bit factor far sooner, and the
    # embedded table already covers every prime ≤ 2^20.
    if rem.bit_length() > 96:
        full = min(full, _PRE_MAX_C)
    if full > cheap:
        extra, rem = _trial_split(rem, full)
        for p, e in extra.items():
            fac[p] = fac.get(p, 0) + e
    return fac, rem


def _F_value(fac: dict[int, int]) -> int:
    prod = 1
    for q, e in fac.items():
        prod *= pow(q, e)
    return prod


def _primes_for_bound(fac: dict[int, int], target: int) -> list[int]:
    """Largest-first primes of ``fac`` whose product exceeds ``target``."""
    primes = sorted(fac.keys(), reverse=True)
    used: list[int] = []
    prod = 1
    for q in primes:
        e = fac[q]
        for _ in range(e):
            if prod > target:
                break
            prod *= q
        used.append(q)
        if prod > target:
            break
    return used


def _prove_strictly_smaller(
    c: int,
    parent: int,
    *,
    parallel: bool,
    allow_ecpp: bool = False,
    max_h: int = 1,
) -> Result:
    """True / False / None. ``c`` must be < ``parent``. Never AKS."""
    assert 1 < c < parent
    if c < 10_000:
        from .is_prime import _is_prime_small

        return _is_prime_small(c)
    from .factor_lehman import cubic_complete_ready
    from .is_prime import _MAX_FULL_TRIAL_ISQRT, is_prime

    if cubic_complete_ready(c) or c < (1 << 64) or (
        math.isqrt(c) <= _MAX_FULL_TRIAL_ISQRT and c.bit_length() <= 128
    ):
        return bool(is_prime(c, parallel=parallel))
    # 128+ bit cofactors: class-number-1 ECPP first (this is the P131
    # downrun). ≥256 bits: do *not* then run BLS / h≤16 — FastECPP
    # recurses if h=1 misses. Store the witness so the parent certificate
    # does not re-search q.
    from .child_rec import _set_child_rec

    if allow_ecpp and c.bit_length() >= 128:
        from .primality_ecpp import _ecpp_search

        decided, rec = _ecpp_search(c, parallel=parallel, max_h=1)
        if decided is True:
            if rec:
                _set_child_rec(c, rec)
            return True
        if decided is False:
            return False
        if c.bit_length() >= 256:
            return None
    decided, data = _bls_proof(c, parallel=parallel)
    if decided is True:
        if data and data.get("side") in ("nm1", "np1", "combined"):
            _set_child_rec(c, dict(data))
        return True
    if decided is False:
        return False
    if allow_ecpp:
        from .primality_ecpp import _ecpp_search

        decided, rec = _ecpp_search(c, parallel=parallel, max_h=max_h)
        if decided is True:
            if rec:
                _set_child_rec(c, rec)
            return True
        if decided is False:
            return False
    return None


def _pollard_p1(n: int, B1: int = P1_B1_SMALL) -> int | None:
    """Pollard p−1 stage 1 (fixed B1). Returns a proper factor or None."""
    if n < 4 or n % 2 == 0:
        return 2 if n % 2 == 0 and n > 2 else None
    a = 2
    for p in _primes_upto(B1):
        if p > B1:
            break
        # a := a^{p^e} mod n with p^e ≤ B1 maximal
        pe = p
        while pe <= B1 // p:
            pe *= p
        a = pow(a, pe, n)
        if a == 0:
            return None
    g = math.gcd(a - 1, n)
    if 1 < g < n:
        return g
    return None


def _try_split_cofactor(c: int, *, parallel: bool) -> int | None:
    """Proper factor of composite c, or None.

    Mid-size: trial → Fermat → Brent → p−1 → cubic → ECM → SIQS.
    Multi-limb (bits > 160): p−1 then Montgomery ECM; skip long Brent/cubic.
    """
    from .factor_ecm import ecm_factor
    from .factor_lehman import _c_lehman_ready, _ceil_icbrt, lehman_factor
    from .prime_factors import _brent, _fermat_split

    bits = c.bit_length()
    fac, rem = _trial_split(c, _adaptive_trial_bound(c))
    if fac:
        if rem == 1:
            return min(fac)
        if rem > 1 and rem < c:
            return min(fac)

    if bits <= 200:
        f = _fermat_split(c)
        if f is not None and 1 < f < c:
            return f

    # 10k-digit p−1 (B1=2e5) is tens of seconds of 33k-bit pow and
    # cannot prove primality. Trial already ran. FastECPP / Fermat own
    # this band. DEFAULT_N is 147-bit and never reaches here.
    if bits > 3_500:
        return None

    # A 55-bit factor of a ~110-bit cofactor (37-digit primes) is not a
    # Brent problem: curves out to 2^16 still miss and cost seconds, and
    # a 50_000-step Lehman search after that costs ~20 s. ECM at B1=5000
    # finds that factor. Brent stays the tool only through 96 bits.
    if 80 < bits <= 160:
        # B1=5000 finds factors near 40 bits. A 55-bit factor of the
        # 37-digit prime's n+1 cofactor needs B1=11000; the 2^22 Brent
        # search that used to run first took about five seconds.
        f = ecm_factor(c, max_ms=_ecm_max_ms(bits), B1=11_000, max_curves=16)
        if f is not None and 1 < f < c:
            return f
        f = _pollard_p1(c, B1=min(_p1_b1(bits), 50_000))
        if f is not None:
            return f
        f = lehman_factor(c, k_max=2_000, parallel=parallel)
        if f is not None and 1 < f < c:
            return f
        if SIQS_MIN_BITS <= bits <= SIQS_MAX_BITS:
            from .factor_siqs import siqs_factor

            f = siqs_factor(c, max_ms=_siqs_max_ms(bits))
            if f is not None and 1 < f < c:
                return f
        return None

    if bits <= 96:
        for cv in range(1, 5):
            g = _brent(c, cv, max_r=1 << 18)
            if 1 < g < c:
                return g

    if bits > 160:
        f = _pollard_p1(c, B1=_p1_b1(bits))
        if f is not None:
            return f

    if bits <= 96:
        for cv in range(1, _brent_curve_count(bits) + 1):
            g = _brent(c, cv)
            if 1 < g < c:
                return g

    if bits <= 160:
        f = _pollard_p1(c, B1=_p1_b1(bits))
        if f is not None:
            return f

        cub = _ceil_icbrt(c)
        if _c_lehman_ready() and bits <= 128 and c > 1:
            max_k = ((1 << 128) - 1) // (4 * c)
            budget = min(max_k, cub, 100_000)
            if budget >= 16:
                f = lehman_factor(c, k_max=int(budget), parallel=parallel)
                if f is not None and 1 < f < c:
                    return f
        else:
            budget = min(cub, 50_000)
            if budget >= 16:
                f = lehman_factor(c, k_max=int(budget), parallel=parallel)
                if f is not None and 1 < f < c:
                    return f

    f = ecm_factor(c, max_ms=_ecm_max_ms(bits))
    if f is not None and 1 < f < c:
        return f
    # bits > 160: ECPP peels need a cheap miss, not a multi-minute SIQS.
    # Mid-size BLS (DEFAULT_N / hard55 leftovers) stays ≤160 and may SIQS.
    if bits > 160:
        return None
    if SIQS_MIN_BITS <= bits <= SIQS_MAX_BITS:
        from .factor_siqs import siqs_factor

        f = siqs_factor(c, max_ms=_siqs_max_ms(bits))
        if f is not None and 1 < f < c:
            return f
    return None


def _peel_leftover(
    c: int,
    fac: dict[int, int],
    stack: list[int],
    unproven: set[int],
    parent: int,
    *,
    parallel: bool,
    allow_split: bool,
) -> bool:
    """Absorb ``c`` into ``fac`` / ``stack``. True if a splitter call was made."""
    if c <= 1 or c in unproven:
        return False
    sub, r2 = _trial_split_staged(c)
    for p, e in sub.items():
        fac[p] = fac.get(p, 0) + e
    if r2 == 1:
        return False
    c = r2
    proved = _prove_strictly_smaller(c, parent, parallel=parallel, allow_ecpp=False)
    if proved is True:
        fac[c] = fac.get(c, 0) + 1
        return False
    if not allow_split:
        unproven.add(c)
        return False
    f = _try_split_cofactor(c, parallel=parallel)
    if f is None or f <= 1 or f >= c:
        unproven.add(c)
        return True
    stack.append(f)
    stack.append(c // f)
    return True


def _factor_enough(n: int, *, parallel: bool) -> dict[int, int] | None:
    """Factor n−1 until product of proven prime powers F > √n.

    Does **not** require factoring the full cofactor R = (n−1)/F.
    Returns the prime→exponent map for F, or None if F cannot be built.
    Unproven leftovers are never inserted into F and are not re-split.
    """
    target = math.isqrt(n)
    m = n - 1
    fac: dict[int, int] = {}
    peeled, rem = _trial_split_staged(m)
    fac.update(peeled)
    stack: list[int] = [rem] if rem > 1 else []
    unproven: set[int] = set()
    splits = 0
    max_splits = _max_splits(n.bit_length())

    def done() -> bool:
        F = _F_value(fac)
        return F > target or n < 2 * F * F * F

    if done():
        return fac

    while stack and not done():
        c = stack.pop()
        if c <= 1 or c in unproven:
            continue
        sub, r2 = _trial_split_staged(c)
        for p, e in sub.items():
            fac[p] = fac.get(p, 0) + e
        if r2 == 1:
            if done():
                return fac
            continue
        c = r2
        proved = _prove_strictly_smaller(c, n, parallel=parallel, allow_ecpp=False)
        if proved is True:
            fac[c] = fac.get(c, 0) + 1
            if done():
                return fac
            continue
        if splits >= max_splits:
            return None
        splits += 1
        f = _try_split_cofactor(c, parallel=parallel)
        if f is None or f <= 1 or f >= c:
            unproven.add(c)
            continue
        stack.append(f)
        stack.append(c // f)

    return fac if done() else None


def _factor_done(n: int, F: int, G: int) -> bool:
    """Stop peeling n±1 when any BLS theorem's size predicate holds."""
    target = math.isqrt(n)
    if F > target:
        return True
    if n < 2 * F * F * F and _bls_cubic_ok(n, F):
        return True
    if G > target:
        return True
    if G == n + 1:
        return True
    if math.gcd(F, G) == 2 and n < max(F * F * G // 2, F * G * G // 2):
        return True
    return False


def _factor_nm1_np1(
    n: int, *, parallel: bool
) -> tuple[dict[int, int], dict[int, int]]:
    """Peel n−1 and n+1 until a BLS size predicate holds or the abort table fires.

    Returns proven prime-power maps (F, G). Unproven leftovers never enter them.
    """
    fac_f: dict[int, int] = {}
    fac_g: dict[int, int] = {}
    unproven: set[int] = set()

    # DEFAULT_N shape: n−1 = tiny × one large prime. Prove that leftover
    # and skip n+1 (a 5e6 scan of hostile n+1 was most of CLI TIME).
    # Mid-size n+1 specimens (e.g. NP1_SMOOTH, 58-bit leftover) stay below
    # this cutoff so the existing short-side interleave still picks n+1.
    cheap = min(_CHEAP_TRIAL_BOUND, _adaptive_trial_bound(n - 1))
    peeled_fast, rem_fast = _trial_split(n - 1, cheap)
    if (
        rem_fast > 1
        and rem_fast.bit_length() >= 96
        and _looks_prime(rem_fast)
    ):
        proved = _prove_strictly_smaller(
            rem_fast, n, parallel=parallel, allow_ecpp=False
        )
        if proved is True:
            peeled_fast[rem_fast] = peeled_fast.get(rem_fast, 0) + 1
            if _factor_done(n, _F_value(peeled_fast), 1):
                return peeled_fast, fac_g

    peeled_f, rem_f = _trial_split_staged(n - 1)
    fac_f.update(peeled_f)
    peeled_g, rem_g = _trial_split(n + 1, cheap)
    fac_g.update(peeled_g)
    stack_f: list[int] = [rem_f] if rem_f > 1 else []
    stack_g: list[int] = [rem_g] if rem_g > 1 else []
    splits = 0
    max_splits = _max_splits(n.bit_length())

    if _factor_done(n, _F_value(fac_f), _F_value(fac_g)):
        return fac_f, fac_g

    while stack_f or stack_g:
        if _factor_done(n, _F_value(fac_f), _F_value(fac_g)):
            break
        F = _F_value(fac_f)
        G = _F_value(fac_g)
        allow = splits < max_splits
        if stack_f and (not stack_g or F <= G):
            c = stack_f.pop()
            if _peel_leftover(
                c, fac_f, stack_f, unproven, n, parallel=parallel, allow_split=allow
            ):
                splits += 1
        else:
            c = stack_g.pop()
            if _peel_leftover(
                c, fac_g, stack_g, unproven, n, parallel=parallel, allow_split=allow
            ):
                splits += 1

    return fac_f, fac_g


def _pocklington_witnesses(
    n: int, primes_of_F: list[int]
) -> tuple[Result, list[dict[str, int]] | None]:
    """Pocklington plus the (q, a) pairs. False is a composite proof."""
    fermat_ok: dict[int, bool] = {}
    witnesses: list[dict[str, int]] = []
    for q in primes_of_F:
        found: int | None = None
        for a in _BASES:
            if a % n == 0:
                return (n == a), None
            ok = fermat_ok.get(a)
            if ok is None:
                ok = pow(a, n - 1, n) == 1
                fermat_ok[a] = ok
            if not ok:
                return False, None
            if math.gcd(pow(a, (n - 1) // q, n) - 1, n) == 1:
                found = a
                break
        if found is None:
            return None, None
        witnesses.append({"q": int(q), "a": int(found)})
    return True, witnesses


def _pocklington(n: int, primes_of_F: list[int]) -> Result:
    """Pocklington: each q | F needs some fixed base a (bases may differ)."""
    decided, _wit = _pocklington_witnesses(n, primes_of_F)
    return decided


def _lucas_uv(k: int, P: int, Q: int, n: int) -> tuple[int, int, int] | int:
    """Binary Lucas ladder: ``(U_k, V_k, Q^k mod n)``, or a proper factor of ``n``."""
    if n <= 2:
        return n if n > 1 else 1
    D = P * P - 4 * Q
    try:
        inv2 = pow(2, -1, n)
    except ValueError:
        g = math.gcd(2, n)
        return g if g > 1 else 1
    U, V, Qk = 0, 2, 1
    if k == 0:
        return U, V, Qk % n
    for bit in range(k.bit_length() - 1, -1, -1):
        U = (U * V) % n
        V = (V * V - 2 * Qk) % n
        Qk = (Qk * Qk) % n
        if (k >> bit) & 1:
            Up = ((P * U + V) * inv2) % n
            Vp = ((D * U + P * V) * inv2) % n
            Qk = (Qk * Q) % n
            U, V = Up, Vp
    return U, V, Qk


def _selfridge_D():
    d = 5
    sign = 1
    for _ in range(_SELFRIDGE_D_LIMIT):
        yield sign * d
        d += 2
        sign = -sign


def _condition_II_record(
    n: int, primes_of_G: list[int]
) -> tuple[Result, dict | None]:
    """Lucas condition (II) plus the (D, P, Q) witness. False is composite."""
    if not primes_of_G:
        return None, None
    from .ntheory import jacobi

    qs = [int(q) for q in primes_of_G]
    for D in _selfridge_D():
        j = jacobi(D, n)
        if j == 0:
            g = math.gcd(abs(D), n)
            if 1 < g < n:
                return False, None
            continue
        if j != -1:
            continue
        P = 1
        Q = (1 - D) // 4
        uv = _lucas_uv(n + 1, P, Q, n)
        if isinstance(uv, int):
            if 1 < uv < n:
                return False, None
            continue
        if uv[0] % n != 0:
            continue
        ok = True
        for q in qs:
            if q <= 1 or (n + 1) % q != 0:
                ok = False
                break
            uvq = _lucas_uv((n + 1) // q, P, Q, n)
            if isinstance(uvq, int):
                if 1 < uvq < n:
                    return False, None
                ok = False
                break
            g = math.gcd(uvq[0], n)
            if 1 < g < n:
                return False, None
            if g != 1:
                ok = False
                break
        if ok:
            return True, {"D": int(D), "P": 1, "Q": int(Q), "qs": qs}
    return None, None


def _combined_theorem1_ok(n: int, F: int, G: int) -> bool:
    """Combined Theorem 1 size predicate (not ``FG > √n``)."""
    if F <= 1 or G <= 1 or n <= 1:
        return False
    if math.gcd(F, G) != 2:
        return False
    return n < max(F * F * G // 2, F * G * G // 2)


def _early_reject(n: int) -> Result:
    """Shared tiny / Fermat filter. None means keep going."""
    if n < 2:
        return False
    if n in (2, 3, 5, 7):
        return True
    if n % 2 == 0 or n % 3 == 0 or n % 5 == 0:
        return False
    if n > 1 and math.isqrt(n) ** 2 == n:
        return False
    for a in _BASES[:6]:  # 2..13 enough for almost all composites
        if a % n == 0:
            return n == a
        if pow(a, n - 1, n) != 1:
            return False
    return None


def nm1_primality(n: int, *, parallel: bool = True) -> Result:
    """Try to settle primality of ``n`` via n−1 (Pocklington / Theorem 5).

    True / False / None (inconclusive).
    """
    early = _early_reject(n)
    if early is not None:
        return early

    fac = _factor_enough(n, parallel=parallel)
    if fac is None:
        return None

    # Sanity: F divides n−1
    F = _F_value(fac)
    if F <= 1 or (n - 1) % F != 0:
        return None
    sqrt_n = math.isqrt(n)
    cubic = n < 2 * F * F * F
    if F <= sqrt_n and not cubic:
        return None

    primes = sorted(fac.keys(), reverse=True)
    target = sqrt_n if F > sqrt_n else _icbrt(n)
    used: list[int] = []
    prod = 1
    for q in primes:
        e = fac[q]
        for _ in range(e):
            if prod > target:
                break
            prod *= q
        used.append(q)
        if prod > target:
            break

    decided = _pocklington(n, used)
    if decided is True and prod <= sqrt_n and not _bls_cubic_ok(n, prod):
        return None
    return decided


def _canon_fac(fac: dict[int, int]) -> dict[int, int]:
    return {int(q): int(fac[q]) for q in sorted(fac)}


def _nm1_record(
    n: int, fac_f: dict[int, int], primes: list[int], inequality: str
) -> tuple[Result, dict | None]:
    decided, wit = _pocklington_witnesses(n, primes)
    if decided is True and wit is not None:
        fmap = {int(q): int(fac_f[q]) for q in sorted(primes) if q in fac_f}
        return True, {
            "side": "nm1",
            "F": fmap,
            "inequality": inequality,
            "witnesses": wit,
        }
    if decided is not None:
        return decided, {"side": "nm1"}
    return None, None


def _np1_record(
    n: int, fac_g: dict[int, int], primes: list[int]
) -> tuple[Result, dict | None]:
    decided, luc = _condition_II_record(n, primes)
    if decided is True and luc is not None:
        gmap = {int(q): int(fac_g[q]) for q in sorted(primes) if q in fac_g}
        return True, {
            "side": "np1",
            "G": gmap,
            "inequality": "G>sqrt",
            "witnesses": [],
            "lucas": luc,
        }
    if decided is not None:
        return decided, {"side": "np1"}
    return None, None


def _bls_proof(n: int, *, parallel: bool = True) -> tuple[Result, dict | None]:
    """n−1, then n+1, then Combined Theorem 1. Payload is the cert witness."""
    early = _early_reject(n)
    if early is not None:
        return early, {"side": "nm1"}

    fac_f, fac_g = _factor_nm1_np1(n, parallel=parallel)
    F = _F_value(fac_f)
    G = _F_value(fac_g)
    sqrt_n = math.isqrt(n)

    if F > 1 and (n - 1) % F == 0 and F > sqrt_n:
        decided, rec = _nm1_record(
            n, fac_f, _primes_for_bound(fac_f, sqrt_n), "F>sqrt"
        )
        if decided is not None:
            return decided, rec

    if F > 1 and (n - 1) % F == 0 and n < 2 * F * F * F and _bls_cubic_ok(n, F):
        decided, rec = _nm1_record(
            n, fac_f, _primes_for_bound(fac_f, _icbrt(n)), "F>sqrt"
        )
        if decided is not None:
            return decided, rec

    if G > 1 and (n + 1) % G == 0 and G > sqrt_n:
        decided, rec = _np1_record(n, fac_g, _primes_for_bound(fac_g, sqrt_n))
        if decided is not None:
            return decided, rec

    if G == n + 1 and G > 1:
        decided, rec = _np1_record(n, fac_g, list(fac_g.keys()))
        if decided is not None:
            return decided, rec

    if _combined_theorem1_ok(n, F, G):
        dec_i, wit = _pocklington_witnesses(n, list(fac_f.keys()))
        if dec_i is False:
            return False, {"side": "combined"}
        if dec_i is True and wit is not None:
            dec_ii, luc = _condition_II_record(n, list(fac_g.keys()))
            if dec_ii is False:
                return False, {"side": "combined"}
            if dec_ii is True and luc is not None:
                return True, {
                    "side": "combined",
                    "F": _canon_fac(fac_f),
                    "G": _canon_fac(fac_g),
                    "inequality": "combined_thm1",
                    "F2G_over_2": F * F * G // 2,
                    "FG2_over_2": F * G * G // 2,
                    "witnesses": wit,
                    "lucas": luc,
                }
            if dec_ii is not None:
                return dec_ii, {"side": "combined"}

    return None, None


def _bls_decide(n: int, *, parallel: bool = True) -> tuple[Result, str | None]:
    """n−1, then n+1, then Combined Theorem 1. Side is nm1 / np1 / combined."""
    decided, rec = _bls_proof(n, parallel=parallel)
    if decided is None:
        return None, None
    side = rec.get("side") if rec else "nm1"
    return decided, side


def bls_primality(n: int, *, parallel: bool = True) -> Result:
    """n−1, then n+1, then Combined Theorem 1, sharing one factoring effort."""
    decided, _side = _bls_decide(n, parallel=parallel)
    return decided


def bls_side(n: int, *, parallel: bool = True) -> str | None:
    """Which theorem proved primality: ``nm1``, ``np1``, ``combined``, or None."""
    decided, side = _bls_decide(n, parallel=parallel)
    return side if decided is True else None


def _icbrt(n: int) -> int:
    if n < 8:
        return 0 if n < 1 else 1
    x = 1 << ((n.bit_length() + 2) // 3)
    while True:
        y = (2 * x + n // (x * x)) // 3
        if y >= x:
            return x
        x = y


def _bls_cubic_ok(n: int, F: int) -> bool:
    """BLS n^{1/3} extra: n < 2F³, R = rF+s, r odd or s²−4r not square."""
    if F <= 1 or (n - 1) % F != 0:
        return False
    if n >= 2 * F * F * F:
        return False
    R = (n - 1) // F
    if R <= 0 or math.gcd(F, R) != 1:
        return False
    r, s = divmod(R, F)
    if not (0 < s < F):
        return False
    if r & 1:
        return True
    disc = s * s - 4 * r
    if disc < 0:
        return True
    root = math.isqrt(disc)
    return root * root != disc


def nm1_ready(n: int) -> bool:
    """Whether multi-limb / hard paths should try n−1."""
    if n >= (1 << 64):
        return True
    from .factor_lehman import cubic_complete_ready

    return cubic_complete_ready(n)
