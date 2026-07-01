#!/usr/bin/env bash
# Single supported build path for the OpenMP hard-64-bit engine.
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
DATA="$ROOT/is_prime_data"
if [[ ! -f "$DATA/wheel_core.c" ]]; then
  echo "wheel_core.c missing; generating from w9699690_u8.npy" >&2
  python3 "$ROOT/scripts/generate_wheel_core_c.py"
fi
gcc -O3 -fPIC -shared -fopenmp -lm -o "$DATA/wheel_core.so" "$DATA/wheel_core.c"
echo "Built $DATA/wheel_core.so"
