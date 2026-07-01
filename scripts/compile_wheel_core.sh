#!/usr/bin/env bash
# Single supported build path for the OpenMP hard-64-bit engine.
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
DATA="$ROOT/is_prime_data"
if [[ ! -f "$DATA/wheel_core.c" ]]; then
  echo "wheel_core.c missing; generating from w9699690_u8.npy" >&2
  python3 "$ROOT/scripts/generate_wheel_core_c.py"
fi
# Prefer native tuning when available; fall back to portable x86-64-v2.
ARCH_FLAGS=(-march=native -mtune=native)
if ! gcc -march=native -E -x c /dev/null -o /dev/null 2>/dev/null; then
  ARCH_FLAGS=(-march=x86-64-v2)
fi
# Link -lm last (isqrt is integer-only, but keep -lm for portability).
# -funroll-loops helps the 4-way independent-mod hot path.
gcc -O3 -fPIC -shared -fopenmp \
  "${ARCH_FLAGS[@]}" \
  -funroll-loops -fomit-frame-pointer \
  -o "$DATA/wheel_core.so" "$DATA/wheel_core.c" -lm -fopenmp
echo "Built $DATA/wheel_core.so"
