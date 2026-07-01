"""
Deterministic primality testing for natural numbers.

End-to-end CLI ``TIME`` starts at import (``t0``) and stops after the answer,
so import, table load, JIT, and the check all count. Heavy dependencies
(NumPy/Numba) and large tables load lazily only on hard paths that need them.

Tiered engines: tiny Python loop; 64-bit OpenMP/stdlib/Numba wheels; practical
multi-limb (≤128-bit) OpenMP u128 or stdlib full trial; AKS only for huge n.

Restrictions: deterministic; no stochastic Miller–Rabin; no prime libraries.
"""

from __future__ import annotations

import time

t0 = time.perf_counter_ns()

import math
import os
import sys
import zlib
from array import array

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "is_prime_data")
WHEEL_MOD = 9_699_690
WHEEL_NW = 1_658_880
_WHEEL_START_I = 23
_SMALL_LIMIT = 10_000
# Stdlib wheel wins end-to-end TIME up to this n (avoids NumPy/Numba import).
_PURE_WHEEL_MAX_N = 4_000_000_000_000  # isqrt <= 2_000_000
_PARALLEL_LIMIT = 50_000
# Full deterministic trial (no AKS) when isqrt(n) is at most this (covers ~10^20).
_MAX_FULL_TRIAL_ISQRT = 25_000_000_000  # 2.5e10 → n up to ~6.25e20
_RES_INVALID = 0xFFFFFFFF
_PRECHECK_PRIMES = (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53)

# Embedded classic 30030-wheel steps (zlib); decompress is ~20µs, no file I/O.
_W30030_STEPS_Z = b'x\xdauX\xed\x8a\x1c1\x0c\x83a\x10\xc6\x98\xb0\xec\x8f\xbe\xff\xa3v\x12\x7fD\xce\xecA\xdb\xdb\xcee3v$[r\xae\x1b\x17\xee\xeb\xc6\xfa\x81\x1b\xf2\xfc\xe7\xba\xc7\xf3X/`>\xd7\xe7\x81\xd9\\s)r\xdd\x98\xff\x17\xe8|\x8a\xb9\xeey&\xba\xd6\xfa\x1e&k;\x9b_\x9e\xdb<\x0bb\xf1}\xaduX\x9f\x9f=\xf2\xb5\xcf\x06\xcf\x9f\xe7\xe3\xfc\xf5\x8c\xe9\x8a\xfdF\xc6\'*\xfeZ\xdf\x0f\x1eS,\\_\x9f\x0b\xe7V\xea\xfb)\xae\xe7\xa9\xaf\x9b1\xaa]\xf1\xf9\t\xf0\xd9@#]\x81=O-c\xbf\xcc\xf3XaV\x80k\xaf\xf9\xaf\x07\xbe~\xa1\xf1\xfa\xf9\xb1N\x10s\x83\xb5\xce\xd6\xde\x91\n\xe2\xcdk\xa1\xade\xb9\xa1\xc4\t\xce\x85\xb6B\xf3\x94\x9f\x93\xfb^\xb5lg2\x97\x98\x7f\x05\x7f!\xe7\xb1\x8d\xc8\xe4Iu=\xf7e\x1b\xb9\xdc\x10\x11\xa0\xdc\xf1\xfa\xc0\xce_\xad\xfe\xfd\xc8\xc4Vh7Q\x01\x94\x88\xfaI;t\x05\x89\xe4\xc96\xec2\xcc\xcc\x1e#\xb0\x9b_}~f\x98{C\x0f\x7fq\xae\xc8 \x95\x89m\xd2H\xc3N:t\xfe\xe2M\x86\x8f\xe3\x12\x11j\x87\xce\n\xb9HY\'Ei\xc3<{\xb5\xe4\xc2\x1d\x87=\x16\xc6\x8a:k\t\xecn\xe6\x824\xecd\xd3\xda\xa2L\xe2\xc8\x1c\x12\xc7N:t\xc1\xd0\x86\xdc\x88\xf8\xb2\x9c\x8c\xaans\x81\xa0\x8b\xe0\x83\nR\tW|\xb2\xb6\x8e\x13\x0c. \xcad\xed\xf5\r\xe4\x9c\xac8\xa0\x8b\x93\x91:0\x9bu\x10\xd0\xedj\xfa]w\x92$\x06-\x94*\xbbE\x86\x11\x90X\xe0\x7f\x9d\x99L\xe8\x80\x0e\xdd.;:\'\x1d\x91pq\xc1\xd7\r\xbb\xafw\xc7\x04\x97]\xf4\xbc\xec\x0bT\x9f\xf3\xef\xa7Q\x01\x94\xc8\xc7Oz\x17\xdd\xea\x84\x15_\x03/\xb8\x90\x99\x8c\x84\x8e:!pR\xab\xce.\x93D\x96\x83Q\xd1\xb5>#\xd4\xb6\xea\xbd\xc5\x05\t\x85\x90l\x0b\x1d\xba\xd1;\xa6\x06\x157\x17\xd4\xf9\xd7\x1a\x83\x97\x1dZ\xc3\x0crT\xc7\\T\xb0\x8e\x9cT\xd1}S"\xa8\xc1i\x16\x9d\x9cZ\x87\x86\xdc\n\xee_\x06\xe8\xe5\xa4\xadc\x16\xfe0\xd2\xba,;NXSL\xd4__e\x03\xef\xf7\xde\x16\x96X\xb0\xd8\xc9\xab+8\x98\xb2{\xffZ\xaaTN\xde\xc9\xdejW\x9d\x15\x1d\xbbQ-S%\x1b\x83\'7)\xf7S\xecV\xc3=4\xaca\xe7\xba\x90b\xf7I*\xf8\xeaAZwQc\xe0\x86i\xe1*\xde\x12A\xfd\x92\xfd\x82\'\xa2\xe1+t\xcb\xb6T\xd1\xe9\x0f\xb1\xd3\xaa\xba\xd1\xb4\x0e\x1d\xbaM.D\x10\x9b\xb1\xbe\xe1\xa8\xa23\xd6\xba\x84\x0e\xd7\xdd\x8cJq\x01\x99\xb1\x1b\x15t\xe8\xe4\xec\x98\xead\xdfU\x17\xa7L\xe4B\x96\x1d\x1a\t\x85\xb4\xae\xa8`\r\xb9o5L\x8b\xae@\x90+\xd5\\\xef\x97\x0f\xe3p(\xdd\xcdf\xa1\x14\xc2\xa8+\x90s\xdc\xfdr}\x01e\xb8\x9c\xea\x15\xdf\xa8\x8e\x7f\'\x03\xab\xe8F7)r\x00\x17\xa2TE7\xa9\xa0M\xea\xb4\x17\x1dk\x1d:t\xc5\x85\x94\x8bin?\x81\xc8Cu\xb1\xaa9kR\x97EG\x12v@\x17\x81&\xab\x95\xed\x02\x84\xb5\xeee\x17\xcc\x93\x19\xcdc\x82^\xad\xf9;\x96\xe3H$\xa5I\x1b"w\x97\x08\xbb\x99\x0c?,\xa6\x7f(\x83\xd4\xbd\xe8\xaa;"\x03B"\xac\xaa\x8e\xbcmutt\xa9+.\xc0\xaa\r*{\x00\xc1v\x81U#\xf6\xe2B\xc6T\xd3\xc1<l\xea\x97\x8a\x17\x17\xd0\xc7\x92\x06\x9d\x95O\x19\xd1\x16@n!\x88c\x07p\xd9Y\x8dl\xca\xa8\xe1@\xbb\xc3l\xce\x11\x89\xb0\xd1\xb4\xf1dAUw\xb3BX\xd9sr\x0b\x81\x9c\xa1\x19\xcc_S\x04\x866*|\xb2\xec\x90\xbe\xc1\x1ar\xcaC\xc46)w\xb7\x98*\xd1E\xd3,\x88V\xd1\rR\xba\xab;Gl\xe3X\xc3\xc1\xc38\x94\xd2\xe9a0\xe5p)o1\xbe\xd2H\xfb\x86@\x97:{\x8b1\x93\xf0\x18\xec\x0c4Q\x92Mq.T\xd1\xfd{\xcd\x06\x87\xc6\x96\x97\xb0\xbbq!&\xca\xfb[E\'\xa4u\xd9\xd1\xa5\rv\xd2\x87\x83\xf0hFL\xc8\xae\xa0/S\xa1o{D\xc3A\x9a\x85\xd0\x16=\\\xca1Q\xca\x0f\xec\x16\xab-)\x82f\x1c\x1d\xfb\xd1\xa0\xcb\x0e\xda\x86\x83\xd1\x8a\tm\xac\xe3~)\xdd\xa5\xcc/|\x8e\x91\\\xea\xa4?\x02v\x8e\xc8\xcb\x85\xb8\xc3`\xad\xc3\x81\x9c\x1f\xcd\xb8O*x\xbfTN\xb2k\xddn\x0b\xdd\xa6H\r\x07\xca\x0esPWPJ\xa4:\xfe!a\r:\xd2\x9a\xb5\xdc\x88\x0b\x10\x1c\x06\x13,\xc7\x01\xdd\x17\xe5\xce\x17\x912\x13\xc4e\xc5Qu\x9c\t\xfe\xbcO\xd1\x06^\x9e\x93\xb2]\xa8\xb2C\xf9#\x1aK$\xab\xceZ\xff@\x9f\xc8\xa5\xd9\x94n\x17l\xdf\xfd4\xe7\xf8\x9a\r\xca\xe9\xb5\x86\xa9?\xaeS\xacO\x07\x9aG\xbd\x16~\xea\xa4\xad\x8du\xe7m\x85\xa4E\x0fV[\xf3)!\x11\xe0\xbb\x05n\x99\x93\x7f\xc2\x83\xdd\xe8\xb3\xc1O\x89Xg#\xa7e\xf5\xbb?9\x06\xde\xb4\xe7\xc0M\\P6\x0bg\xc3\xc49Q\xde\xcddj\x92x\xbex\xb0\xbdE\x17\xbb-\x12m:\xe0\x89\xf2\x1b\x97\x15ip\xa9\xec\xa4\xb9\x14;5\xec\x18\xec\xd4x\xa2T\xbet\x8c\xab\xbb\xb7\xd8\xf5\xba\xb3k\xdf\xfd\xac\xbb\xbf\xbc]\x00_.l9\xa6\x8e\x89>\xd8\xedN\xa8\xddc"\xae\xcc\x82\x0c\x83\xc5n~\x90>\x96\xe45j\xbf\x8fu\xb5\x03\xdd\xdb\x86\xb9-n\t7\xae@\xae\xa8\x10\x93\x8dE\xd5\xe1/\xe4\xf6\xb5\xdb\xe7?}euO'
_steps_30030 = None
_steps_9699690 = None
_c_core = None  # ctypes lib or False if missing
_c_core_checked = False

# Lazy singletons
_np = None
_tables = None
_kernels = None
_serial_ready = False
_parallel_ready = False
_threads_configured = False
_thread_count = 1


def _load_c_core():
    """Load prebuilt OpenMP extension if present (skips Numba import/JIT)."""
    global _c_core, _c_core_checked, _thread_count
    if _c_core_checked:
        return _c_core
    _c_core_checked = True
    import ctypes

    path = os.path.join(_DATA_DIR, "wheel_core.so")
    if not os.path.isfile(path):
        _c_core = False
        return _c_core
    lib = ctypes.CDLL(path)
    lib.is_prime_u64_core.argtypes = [ctypes.c_uint64, ctypes.c_int]
    lib.is_prime_u64_core.restype = ctypes.c_int
    # Optional 65–128-bit full-trial entry (regenerated wheel_core).
    if hasattr(lib, "is_prime_u128_core"):
        lib.is_prime_u128_core.argtypes = [
            ctypes.c_uint64,
            ctypes.c_uint64,
            ctypes.c_int,
        ]
        lib.is_prime_u128_core.restype = ctypes.c_int
    nt = os.environ.get("OMP_NUM_THREADS") or os.environ.get("NUMBA_NUM_THREADS")
    if nt:
        _thread_count = max(1, int(nt))
        os.environ["OMP_NUM_THREADS"] = str(_thread_count)
    else:
        _thread_count = os.cpu_count() or 1
        os.environ.setdefault("OMP_NUM_THREADS", str(_thread_count))
    _c_core = lib
    return _c_core

def _numpy():
    global _np
    if _np is None:
        import numpy as np

        _np = np
    return _np


def _configure_threads():
    global _threads_configured, _thread_count
    if _threads_configured:
        return
    nt = os.environ.get("NUMBA_NUM_THREADS") or os.environ.get("OMP_NUM_THREADS")
    if nt:
        _thread_count = max(1, int(nt))
        from numba import set_num_threads

        set_num_threads(_thread_count)
    else:
        from numba import get_num_threads

        _thread_count = int(get_num_threads())
    _threads_configured = True



def _load_tables():
    """Load precomputed arrays needed by the Numba hard path only."""
    global _tables
    if _tables is not None:
        return _tables
    np = _numpy()

    def load(name):
        path = os.path.join(_DATA_DIR, name)
        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"Missing {path}. Run: python scripts/generate_wheel_data.py"
            )
        return np.load(path)

    w2_path = os.path.join(_DATA_DIR, "w9699690_u64x2.npy")
    if os.path.isfile(w2_path):
        w64 = load("w9699690_u64x2.npy")
    else:
        w_wheel = load("w9699690_u8.npy")
        n = int(w_wheel.size)
        w64 = np.empty(n * 2, dtype=np.uint64)
        w64[:n] = w_wheel
        w64[n:] = w_wheel
    res_path = os.path.join(_DATA_DIR, "res9699690_u32.npy")
    if os.path.isfile(res_path):
        res_wheel = load("res9699690_u32.npy")
    else:
        w_wheel = load("w9699690_u8.npy")
        nW = int(w_wheel.size)
        cs = np.empty(nW, dtype=np.int64)
        cs[0] = _WHEEL_START_I
        if nW > 1:
            cs[1:] = _WHEEL_START_I + np.cumsum(w_wheel[:-1], dtype=np.int64)
        res_wheel = np.full(WHEEL_MOD, np.uint32(_RES_INVALID), dtype=np.uint32)
        res_wheel[cs % WHEEL_MOD] = np.arange(nW, dtype=np.uint32)
    g = globals()
    g["W_WHEEL64"] = w64
    g["RES_WHEEL"] = res_wheel
    # legacy exports on demand from small files
    _tables = {
        "W2": w64,
        "RES": res_wheel,
        "nW": np.int64(WHEEL_NW),
        "mod": np.uint64(WHEEL_MOD),
        "start": np.uint64(_WHEEL_START_I),
        "invalid": np.int64(_RES_INVALID),
        "parallel_limit": np.uint64(_PARALLEL_LIMIT),
    }
    return _tables


def _build_kernels():
    global _kernels
    if _kernels is not None:
        return _kernels
    np = _numpy()
    from numba import njit, prange, get_num_threads

    @njit(fastmath=True, cache=True)
    def isqrt_u64(n):
        if n < np.uint64(2):
            return n
        x = np.uint64(n ** 0.5 + 1.0)
        if x == np.uint64(0):
            return np.uint64(0)
        while x > np.uint64(0) and x > n // x:
            x -= np.uint64(1)
        y = x + np.uint64(1)
        if y != np.uint64(0) and y <= n // y:
            x = y
            y = x + np.uint64(1)
            if y != np.uint64(0) and y <= n // y:
                x = y
        return x

    @njit(cache=True)
    def wheel_start(s, RES, mod, start, invalid):
        if s <= start:
            return start, np.int64(0)
        block = (s // mod) * mod
        r = np.int64(s % mod)
        while True:
            wi = np.int64(RES[r])
            if wi != invalid:
                return block + np.uint64(r), wi
            r += np.int64(1)
            if r == np.int64(mod):
                r = np.int64(0)
                block += mod

    def _make_serial():
        @njit(fastmath=True, cache=True)
        def serial_wheel(n, limit, W2, nW, start):
            i = start
            wi = np.int64(0)
            while i + np.uint64(512) <= limit:
                if wi >= nW:
                    wi -= nW
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
                if n % i == 0:
                    return False
                i += W2[wi]; wi += 1
            if wi >= nW:
                wi -= nW
            while i <= limit:
                if n % i == 0:
                    return False
                i += W2[wi]
                wi += 1
                if wi == nW:
                    wi = 0
            return True
        return serial_wheel

    serial_wheel = _make_serial()

    @njit(parallel=True, fastmath=True)
    def parallel_wheel(n, limit, W2, RES, nW, mod, start, invalid):
        nt = get_num_threads()
        flags = np.zeros(nt, dtype=np.uint8)
        span = limit - start + np.uint64(1)
        chunk = (span + np.uint64(nt) - np.uint64(1)) // np.uint64(nt)
        for tid in prange(nt):
            lo = start + np.uint64(tid) * chunk
            hi = lo + chunk - np.uint64(1)
            if hi > limit:
                hi = limit
            if lo > limit:
                continue
            i, wi = wheel_start(lo, RES, mod, start, invalid)
            while i + np.uint64(512) <= hi:
                if wi >= nW:
                    wi -= nW
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
                if n % i == 0:
                    flags[tid] = np.uint8(1)
                    break
                i += W2[wi]; wi += 1
            if flags[tid] == np.uint8(0):
                if wi >= nW:
                    wi -= nW
                while i <= hi:
                    if n % i == 0:
                        flags[tid] = np.uint8(1)
                        break
                    i += W2[wi]
                    wi += 1
                    if wi == nW:
                        wi = 0
        for t in range(nt):
            if flags[t] != np.uint8(0):
                return False
        return True

    _kernels = {
        "isqrt": isqrt_u64,
        "serial": serial_wheel,
        "parallel": parallel_wheel,
        "np": np,
    }
    return _kernels


def _ensure_serial(n: int):
    global _serial_ready
    _configure_threads()
    tables = _load_tables()
    k = _build_kernels()
    if not _serial_ready:
        np = k["np"]
        warm = np.uint64(1_000_003)
        k["serial"](warm, k["isqrt"](warm), tables["W2"], tables["nW"], tables["start"])
        _serial_ready = True
    return tables, k


def _ensure_parallel(n: int):
    global _parallel_ready
    tables, k = _ensure_serial(n)
    if not _parallel_ready and math.isqrt(n) >= _PARALLEL_LIMIT:
        np = k["np"]
        warm = np.uint64(1_000_003)
        k["parallel"](
            warm,
            np.uint64(200_000),
            tables["W2"],
            tables["RES"],
            tables["nW"],
            tables["mod"],
            tables["start"],
            tables["invalid"],
        )
        _parallel_ready = True
    return tables, k


def _is_prime_small(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if (n & 1) == 0 or n % 3 == 0:
        return n in (2, 3)
    r = math.isqrt(n)
    d = 5
    while d <= r:
        if n % d == 0 or n % (d + 2) == 0:
            return False
        d += 6
    return True



def _get_steps_30030():
    global _steps_30030
    if _steps_30030 is None:
        _steps_30030 = array("B", zlib.decompress(_W30030_STEPS_Z))
    return _steps_30030


def _get_steps_9699690():
    global _steps_9699690
    if _steps_9699690 is not None:
        return _steps_9699690
    path = os.path.join(_DATA_DIR, "w9699690_steps.u8")
    buf = array("B")
    if os.path.isfile(path):
        with open(path, "rb") as f:
            buf.fromfile(f, WHEEL_NW)
    else:
        buf.extend(zlib.decompress(_W30030_STEPS_Z))  # should not happen
        path2 = os.path.join(_DATA_DIR, "w9699690_u8.npy")
        np = _numpy()
        buf = array("B", np.load(path2).tobytes())
    _steps_9699690 = buf
    return _steps_9699690


def _precheck(n: int):
    if n < 2:
        return False
    if n < 4:
        return True
    if (n & 1) == 0:
        return False
    for p in _PRECHECK_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False
        if p * p > n:
            return True
    return None


def _wheel_trial(n: int, steps, start: int) -> bool:
    """Unrolled stdlib wheel trial division."""
    limit = math.isqrt(n)
    i = start
    wi = 0
    nW = len(steps)
    # 8× unroll
    while i + 64 <= limit:
        if wi >= nW:
            wi -= nW
        if n % i == 0:
            return False
        i += steps[wi]; wi += 1
        if n % i == 0:
            return False
        i += steps[wi]; wi += 1
        if n % i == 0:
            return False
        i += steps[wi]; wi += 1
        if n % i == 0:
            return False
        i += steps[wi]; wi += 1
        if n % i == 0:
            return False
        i += steps[wi]; wi += 1
        if n % i == 0:
            return False
        i += steps[wi]; wi += 1
        if n % i == 0:
            return False
        i += steps[wi]; wi += 1
        if n % i == 0:
            return False
        i += steps[wi]; wi += 1
    if wi >= nW:
        wi -= nW
    while i <= limit:
        if n % i == 0:
            return False
        i += steps[wi]
        wi += 1
        if wi == nW:
            wi = 0
    return True


def _is_prime_python_wheel(n: int) -> bool:
    decided = _precheck(n)
    if decided is not None:
        return decided
    # Embedded 30030-wheel: exact, no file I/O; slightly denser than 9699690.
    return _wheel_trial(n, _get_steps_30030(), 17)


def _is_prime_u64(n: int, parallel: bool) -> bool:
    decided = _precheck(n)
    if decided is not None:
        return decided
    lib = _load_c_core()
    if lib:
        return bool(lib.is_prime_u64_core(n, 1 if parallel else 0))
    limit_i = math.isqrt(n)
    if parallel and limit_i >= _PARALLEL_LIMIT:
        tables, k = _ensure_parallel(n)
    else:
        tables, k = _ensure_serial(n)
    np = k["np"]
    n64 = np.uint64(n)
    limit = np.uint64(limit_i)
    if parallel and limit_i >= _PARALLEL_LIMIT:
        return bool(
            k["parallel"](
                n64,
                limit,
                tables["W2"],
                tables["RES"],
                tables["nW"],
                tables["mod"],
                tables["start"],
                tables["invalid"],
            )
        )
    return bool(k["serial"](n64, limit, tables["W2"], tables["nW"], tables["start"]))


def _parse_n(n: int | str) -> int:
    if isinstance(n, bool):
        raise TypeError("n must be an int or decimal str, not bool")
    if isinstance(n, str):
        s = n.strip()
        if not s:
            raise ValueError("empty or whitespace-only string is not a valid integer")
        try:
            n_int = int(s)
        except ValueError as exc:
            raise ValueError(f"invalid decimal integer string: {n!r}") from exc
    else:
        if not isinstance(n, int):
            raise TypeError("n must be an int or decimal str")
        n_int = n
    if n_int < 0:
        raise ValueError("n must be a natural number (n >= 0)")
    return n_int


def _phi(x: int) -> int:
    result, n = x, x
    p = 2
    while p * p <= n:
        if n % p == 0:
            while n % p == 0:
                n //= p
            result -= result // p
        p += 1
    if n > 1:
        result -= result // n
    return result


def _mult_order(a: int, r: int) -> int:
    order = _phi(r)
    x = order
    p = 2
    while p * p <= x:
        if x % p == 0:
            while x % p == 0:
                x //= p
            while order % p == 0 and pow(a, order // p, r) == 1:
                order //= p
        p += 1
    if x > 1:
        while order % x == 0 and pow(a, order // x, r) == 1:
            order //= x
    return order


def _is_perfect_power(n: int) -> bool:
    if n < 4:
        return False
    max_b = n.bit_length()
    for b in range(2, max_b + 1):
        lo, hi = 2, 1 << ((n.bit_length() + b - 1) // b)
        while lo <= hi:
            mid = (lo + hi) // 2
            p = pow(mid, b)
            if p == n:
                return True
            if p > n:
                hi = mid - 1
            else:
                lo = mid + 1
    return False


def _poly_mul_mod(a, b, r, mod):
    res = [0] * r
    for i in range(r):
        if not a[i]:
            continue
        ai = a[i]
        for j in range(r):
            if not b[j]:
                continue
            k = i + j
            if k >= r:
                k -= r
            res[k] = (res[k] + ai * b[j]) % mod
    return res


def _poly_pow_mod(base, exp, r, mod):
    result = [0] * r
    result[0] = 1
    e, b = exp, base
    while e:
        if e & 1:
            result = _poly_mul_mod(result, b, r, mod)
        b = _poly_mul_mod(b, b, r, mod)
        e >>= 1
    return result


def _aks_is_prime(n: int) -> bool:
    """AKS primality test (deterministic for all natural numbers)."""
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or _is_perfect_power(n):
        return False

    log2n = n.bit_length()
    log2n_sq = log2n * log2n
    r = 2
    while True:
        g = math.gcd(n % r, r)
        if 1 < g < n:
            return False
        if g == 1 and _mult_order(n % r, r) > log2n_sq:
            break
        if r > log2n_sq * log2n**3 + 1000:
            break
        r += 1

    for a in range(1, r + 1):
        g = math.gcd(a, n)
        if 1 < g < n:
            return False
    if n <= r:
        return True

    max_a = max(1, math.isqrt(_phi(r)) * log2n)
    for a in range(1, max_a + 1):
        base = [0] * r
        base[0] = a % n
        if r > 1:
            base[1] = 1
        lhs = _poly_pow_mod(base, n, r, n)
        rhs = [0] * r
        rhs[n % r] = 1
        rhs[0] = (rhs[0] + a) % n
        if lhs != rhs:
            return False
    return True



def _is_prime_u128_c(n: int, parallel: bool) -> bool | None:
    """OpenMP full trial for 65–128-bit n. Returns None if .so lacks the symbol."""
    lib = _load_c_core()
    if not lib or not hasattr(lib, "is_prime_u128_core"):
        return None
    lo = n & ((1 << 64) - 1)
    hi = n >> 64
    return bool(lib.is_prime_u128_core(lo, hi, 1 if parallel else 0))


def _is_prime_big_full_trial(n: int, parallel: bool) -> bool:
    """Exact wheel trial to isqrt(n) for moderate big ints (no AKS)."""
    decided = _precheck(n)
    if decided is not None:
        return decided
    # Prefer C __int128 path (OpenMP wheel / segmented primes).
    if n.bit_length() <= 128:
        c_result = _is_prime_u128_c(n, parallel)
        if c_result is not None:
            return c_result
    # Stdlib fallback: 9699690-wheel (correct, slower without OpenMP).
    return _wheel_trial(n, _get_steps_9699690(), _WHEEL_START_I)


def _is_prime_big(n: int, *, parallel: bool = True) -> bool:
    """Primality for n >= 2^64. Full trial when practical; else partial + AKS."""
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61):
        if n == p:
            return True
        if n % p == 0:
            return False
    sq = math.isqrt(n)
    # Practical full trial (covers 10^20-scale primes in seconds with OpenMP).
    if sq <= _MAX_FULL_TRIAL_ISQRT and n.bit_length() <= 128:
        return _is_prime_big_full_trial(n, parallel)
    # Larger: cheap factor scan, then AKS (correct but can be very slow).
    limit = min(50_000_000, sq)
    for i in range(67, limit + 1, 2):
        if n % i == 0:
            return False
    if limit >= sq:
        return True
    return _aks_is_prime(n)


def is_prime(n: int | str, *, parallel: bool = True) -> bool:
    """Return True iff ``n`` is prime. Fully deterministic."""
    n_int = _parse_n(n)
    if n_int < _SMALL_LIMIT:
        return _is_prime_small(n_int)
    if n_int < (1 << 64):
        # Prefer OpenMP .so whenever present (fast in-process + solid e2e).
        if _load_c_core():
            return _is_prime_u64(n_int, parallel)
        if n_int <= _PURE_WHEEL_MAX_N:
            return _is_prime_python_wheel(n_int)
        return _is_prime_u64(n_int, parallel)
    return _is_prime_big(n_int, parallel=parallel)


def _isqrt_u64(n):
    """Public helper used by tests; loads kernels on first use."""
    tables, k = _ensure_serial(int(n) if not hasattr(n, "dtype") else int(n))
    np = k["np"]
    return k["isqrt"](np.uint64(int(n)))


def lab(n: int | str, *, parallel: bool = True) -> dict:
    """Diagnostic: path, isqrt, result, elapsed ms for the check only."""
    n_int = _parse_n(n)
    if n_int < _SMALL_LIMIT:
        path = "python_small"
    elif n_int < (1 << 64):
        if _load_c_core():
            path = "u64_wheel_c"
        elif n_int <= _PURE_WHEEL_MAX_N:
            path = "python_wheel"
        else:
            path = "u64_wheel_numba"
    else:
        sq = math.isqrt(n_int) if n_int >= 2 else 0
        lib = _load_c_core()
        if (
            sq <= _MAX_FULL_TRIAL_ISQRT
            and n_int.bit_length() <= 128
            and lib
            and hasattr(lib, "is_prime_u128_core")
        ):
            path = "u128_wheel_c"
        elif sq <= _MAX_FULL_TRIAL_ISQRT and n_int.bit_length() <= 128:
            path = "bigint_wheel"
        else:
            path = "bigint_trial_or_aks"
    info = {
        "n": n_int,
        "bit_length": n_int.bit_length(),
        "path": path,
        "parallel": bool(
            parallel
            and path in {"u64_wheel_numba", "u64_wheel_c", "u128_wheel_c"}
        ),
    }
    if n_int >= 2:
        info["isqrt"] = math.isqrt(n_int)
    else:
        info["isqrt"] = None
    t1 = time.perf_counter()
    prime = is_prime(n_int, parallel=parallel)
    info["elapsed_ms"] = (time.perf_counter() - t1) * 1000.0
    info["e2e_ms"] = (time.perf_counter_ns() - t0) / 1e6
    info["is_prime"] = prime
    notes = {
        "python_small": "Pure-Python trial division for tiny n (no NumPy/Numba).",
        "python_wheel": "Embedded 30030-wheel trial division (stdlib, best e2e TIME).",
        "u64_wheel_c": "OpenMP C extension 9699690-wheel (no Numba JIT).",
        "u64_wheel_numba": "Numba 9699690-wheel trial division up to isqrt(n).",
        "u128_wheel_c": "OpenMP C full trial for 65–128-bit n (wheel / seg-primes; no AKS).",
        "bigint_wheel": "Stdlib 9699690-wheel full trial for moderate big ints (no AKS).",
        "bigint_trial_or_aks": "Huge-int path: partial trial, AKS if needed (may be slow).",
    }
    info["note"] = notes[path]
    return info


def __getattr__(name: str):
    if name in {"W30030", "RES_TO_WI", "W_WHEEL"}:
        np = _numpy()
        mapping = {
            "W30030": "w30030_u8.npy",
            "RES_TO_WI": "res30030_u16.npy",
            "W_WHEEL": "w9699690_u8.npy",
        }
        path = os.path.join(_DATA_DIR, mapping[name])
        val = np.load(path)
        globals()[name] = val
        return val
    if name in {"RES_WHEEL", "W_WHEEL64"}:
        _load_tables()
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _print_result(arg: str, prime: bool, threads: int) -> None:
    print(f"TEST:    {arg} ({len(arg)} chars)")
    print(f"THREADS: {threads}")
    print(f"RESULT:  {'prime' if prime else 'not prime'}")
    dt = time.perf_counter_ns() - t0
    print(f"TIME:    {dt} ns  ({dt / 1e6:.6f} ms)")


def _main_simple(argv: list[str]) -> int:
    """Fast CLI path: no argparse overhead."""
    serial = False
    positional = []
    for a in argv:
        if a == "--serial":
            serial = True
        elif a.startswith("-"):
            return _main_full(argv)
        else:
            positional.append(a)
    arg = positional[0] if positional else "9223372036854775783"
    parallel = not serial
    try:
        n = int(arg.strip())
    except ValueError:
        print(f"invalid decimal integer string: {arg!r}", file=sys.stderr)
        return 2
    if n < 0:
        print("n must be a natural number (n >= 0)", file=sys.stderr)
        return 2

    if n < _SMALL_LIMIT:
        prime = _is_prime_small(n)
        threads = 1
    elif n < (1 << 64):
        if _load_c_core() or n > _PURE_WHEEL_MAX_N:
            prime = _is_prime_u64(n, parallel)
            threads = _thread_count
        else:
            prime = _is_prime_python_wheel(n)
            threads = 1
    else:
        prime = _is_prime_big(n, parallel=parallel)
        # u128 OpenMP path sets _thread_count in _load_c_core.
        threads = (
            _thread_count
            if (
                parallel
                and n.bit_length() <= 128
                and math.isqrt(n) <= _MAX_FULL_TRIAL_ISQRT
                and _load_c_core()
                and hasattr(_c_core, "is_prime_u128_core")
            )
            else 1
        )

    _print_result(str(n) if positional else arg, prime, threads)
    return 0 if prime else 1


def _main_full(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Deterministic is_prime CLI")
    parser.add_argument("n", nargs="?", default="9223372036854775783")
    parser.add_argument("--lab", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--serial", action="store_true")
    args = parser.parse_args(argv)
    parallel = not args.serial
    if args.lab:
        info = lab(args.n, parallel=parallel)
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            print(f"N:         {info['n']}")
            print(f"BITS:      {info['bit_length']}")
            print(f"PATH:      {info['path']}")
            print(f"ISQRT:     {info['isqrt']}")
            print(f"PARALLEL:  {info['parallel']}")
            print(f"RESULT:    {'prime' if info['is_prime'] else 'not prime'}")
            print(f"TIME_MS:   {info['elapsed_ms']:.6f}")
            print(f"E2E_MS:    {info['e2e_ms']:.6f}")
            print(f"NOTE:      {info['note']}")
        return 0 if info["is_prime"] else 1
    return _main_simple(
        ([args.n] if args.n else []) + (["--serial"] if args.serial else [])
    )


def main() -> None:
    argv = sys.argv[1:]
    if any(a in {"--lab", "--json", "-h", "--help"} for a in argv):
        raise SystemExit(_main_full(argv))
    raise SystemExit(_main_simple(argv))


if __name__ == "__main__":
    main()
