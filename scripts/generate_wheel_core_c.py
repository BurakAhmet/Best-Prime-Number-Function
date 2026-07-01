#!/usr/bin/env python3
"""Regenerate is_prime_data/wheel_core.c from w9699690_u8.npy then compile .so."""
import subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "is_prime_data"
w = np.load(DATA / "w9699690_u8.npy")
lines = [
    "#include <stdint.h>", "#include <math.h>",
    "#ifdef _OPENMP", "#include <omp.h>", "#endif",
    f"#define WHEEL_NW {len(w)}", "#define WHEEL_MOD 9699690u",
    "#define WHEEL_START 23ull", "#define PARALLEL_LIMIT 50000ull",
    "static const uint8_t WSTEPS[WHEEL_NW] = {",
]
row = []
for x in w:
    row.append(str(int(x)))
    if len(row) == 32:
        lines.append(",".join(row) + ",")
        row = []
if row:
    lines.append(",".join(row))
lines.append("};")
body_path = DATA / "wheel_core_body.c"
if not body_path.is_file():
    # body embedded in existing wheel_core.c after static array — extract from marker
    pass
# Read body from current file after "};\n"
cur = (DATA / "wheel_core.c").read_text()
idx = cur.find("};\n") 
if idx < 0:
    idx = cur.find("};")
body = cur[idx + 2:]
# find second }; for array end - first line ending with };
parts = cur.split("\n")
end = 0
for i, line in enumerate(parts):
    if line.strip() == "};":
        end = i
        break
body = "\n".join(parts[end + 1:])
(DATA / "wheel_core.c").write_text("\n".join(lines) + "\n" + body)
print("wrote", DATA / "wheel_core.c")
subprocess.check_call(["bash", str(ROOT / "scripts/compile_wheel_core.sh")])
