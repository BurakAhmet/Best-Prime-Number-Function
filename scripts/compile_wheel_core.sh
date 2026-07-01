#!/bin/sh
set -e
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
gcc -O3 -fPIC -shared -fopenmp -lm -o "$ROOT/is_prime_data/wheel_core.so" "$ROOT/is_prime_data/wheel_core.c"
echo "Built $ROOT/is_prime_data/wheel_core.so"
