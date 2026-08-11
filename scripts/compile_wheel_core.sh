#!/usr/bin/env bash
# Single supported build path for the OpenMP hard-64-bit engine.
# Linux: gcc + libgomp → wheel_core.so
# macOS: clang + Homebrew libomp → wheel_core.dylib (also copied to .so)
# Windows: use MinGW gcc if present (setup.py), or skip (stdlib/Numba fallback).
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
DATA="$ROOT/is_prime_data"
if [[ ! -f "$DATA/wheel_core.c" ]]; then
  echo "wheel_core.c missing; generating via scripts/generate_wheel_core_c.py" >&2
  python3 "$ROOT/scripts/generate_wheel_core_c.py"
fi

UNAME="$(uname -s)"
CC="${CC:-}"
OUT_EXT=so
OPENMP_FLAGS=(-fopenmp)
ARCH_FLAGS=()

if [[ "$UNAME" == Darwin ]]; then
  OUT_EXT=dylib
  CC="${CC:-clang}"
  if [[ -d /opt/homebrew/opt/libomp ]]; then
    OPENMP_FLAGS=(-Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -L/opt/homebrew/opt/libomp/lib -lomp)
  elif [[ -d /usr/local/opt/libomp ]]; then
    OPENMP_FLAGS=(-Xpreprocessor -fopenmp -I/usr/local/opt/libomp/include -L/usr/local/opt/libomp/lib -lomp)
  else
    echo "macOS: install libomp (brew install libomp) for the OpenMP core." >&2
  fi
  if "$CC" -march=native -E -x c /dev/null -o /dev/null 2>/dev/null; then
    ARCH_FLAGS=(-march=native -mtune=native)
  fi
else
  CC="${CC:-gcc}"
  ARCH_FLAGS=(-march=native -mtune=native)
  if ! "$CC" -march=native -E -x c /dev/null -o /dev/null 2>/dev/null; then
    ARCH_FLAGS=(-march=x86-64-v2)
  fi
fi

EXTRA=()
if [[ -n "${WHEEL_CORE_CFLAGS:-}" ]]; then
  # Intentional word-split: caller passes a gcc flag string.
  # shellcheck disable=SC2206
  EXTRA=( ${WHEEL_CORE_CFLAGS} )
fi

OUT="$DATA/wheel_core.$OUT_EXT"
# -funroll-loops + LTO help the independent-mod / segmented-prime hot paths.
"$CC" -O3 -flto -fPIC -shared \
  "${ARCH_FLAGS[@]}" \
  "${OPENMP_FLAGS[@]}" \
  -funroll-loops -fomit-frame-pointer \
  "${EXTRA[@]}" \
  -o "$OUT" "$DATA/wheel_core.c" -lm "${OPENMP_FLAGS[@]}"
# ctypes loader also accepts wheel_core.so on every platform.
if [[ "$OUT_EXT" != so ]]; then
  cp -f "$OUT" "$DATA/wheel_core.so"
fi
echo "Built $OUT ${WHEEL_CORE_CFLAGS:-}"
