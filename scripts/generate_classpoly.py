#!/usr/bin/env python3
"""Packer for transcribed Hilbert class polynomials.

Reads a cited coefficient listing (or ``best_prime/_classpoly_h16.py``)
and emits ``best_prime/_classpoly_h16.py``.  Does not evaluate j(τ).
Does not call PARI, Sage, classpoly, or any computer-algebra system.

Listing sources (integers only, already published):

* Cohen, *A Course in Computational Algebraic Number Theory*, Table 7.1
  (class-number-1 j(D); H_D(X) = X − j(D)).
* Cohen ibid. Table 7.6 / §7.3.3 and Fungrim entry 20b6d2
  (https://fungrim.org/entry/20b6d2/), |D| ≤ 68.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODULE = ROOT / "best_prime" / "_classpoly_h16.py"

# Cited transcription.  One D per line: D: c_h, c_{h-1}, ..., c_0
# Do not add a row unless the integers appear in a source above.
LISTING = """
# Cohen Table 7.1 — H_D(X) = X − j(D)
-3: 1, 0
-4: 1, -1728
-7: 1, 3375
-8: 1, -8000
-11: 1, 32768
-12: 1, -54000
-16: 1, -287496
-19: 1, 884736
-27: 1, 12288000
-28: 1, -16581375
-43: 1, 884736000
-67: 1, 147197952000
-163: 1, 262537412640768000
# Cohen Table 7.6 / Fungrim 20b6d2
-15: 1, 191025, -121287375
-20: 1, -1264000, -681472000
-23: 1, 3491750, -5151296875, 12771880859375
-24: 1, -4834944, 14670139392
-31: 1, 39491307, -58682638134, 1566028350940383
-32: 1, -52250000, 12167000000
-35: 1, 117964800, -134217728000
-36: 1, -153542016, -1790957481984
-39: 1, 331531596, -429878960946, 109873509788637459, 20919104368024767633
-40: 1, -425692800, 9103145472000
-44: 1, -1122662608, 270413882112, -653249011576832
-47: 1, 2257834125, -9987963828125, 5115161850595703125, -14982472850828613281250, 16042929600623870849609375
-48: 1, -2835810000, 6549518250000
-51: 1, 5541101568, 6262062317568
-52: 1, -6896880000, -567663552000000
-55: 1, 13136684625, -20948398473375, 172576736359017890625, -18577989025032784359375
-56: 1, -16220384512, 2059647197077504, 2257767342088912896, 10064086044321563803648
-59: 1, 30197678080, -140811576541184, 374643194001883136
-60: 1, -37018076625, 153173312762625
-63: 1, 67515199875, -193068841781250, 4558451243295023437500, -6256903954262253662109375
-64: 1, -82226316240, -7367066619912
-68: 1, -178211040000, -75843692160000000, -318507038720000000000, -2089297506304000000000000
"""

_ROW = re.compile(
    r"^\s*(-?\d+)\s*:\s*([-+0-9][-+0-9,\s]*)$",
)

_HEADER = '''"""Transcribed Hilbert class polynomials H_D for small-h CM ECPP.

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

A discriminant that is not in those listings is omitted.  Format: D →
monic coefficients, highest degree first.
"""

from __future__ import annotations

H_CAP = 16
D_TABLE_MAX = 2000

# D -> (c_h, c_{h-1}, ..., c_0), monic.
HILBERT_CLASS_POLY: dict[int, tuple[int, ...]] = {
'''


def parse_listing(text: str) -> dict[int, tuple[int, ...]]:
    """Parse ``D: c_h, ..., c_0`` rows.  No evaluation of j(τ)."""
    table: dict[int, tuple[int, ...]] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = _ROW.match(line)
        if m is None:
            raise ValueError(f"bad listing row: {raw!r}")
        d = int(m.group(1))
        coeffs = tuple(int(p.strip()) for p in m.group(2).split(",") if p.strip())
        if not coeffs or coeffs[0] != 1:
            raise ValueError(f"H_{d} is not monic: {coeffs!r}")
        table[d] = coeffs
    return table


def load_module_table(path: Path) -> dict[int, tuple[int, ...]]:
    """Read HILBERT_CLASS_POLY from a packed module via AST (no exec)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.AnnAssign, ast.Assign)):
            continue
        names: list[str] = []
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
            value = node.value
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        else:
            continue
        if "HILBERT_CLASS_POLY" not in names or value is None:
            continue
        raw = ast.literal_eval(value)
        if not isinstance(raw, dict):
            raise ValueError("HILBERT_CLASS_POLY is not a dict")
        return {int(k): tuple(int(c) for c in v) for k, v in raw.items()}
    raise ValueError(f"no HILBERT_CLASS_POLY in {path}")


def _fmt_tuple(coeffs: tuple[int, ...]) -> str:
    if len(coeffs) <= 4 and max(len(str(c)) for c in coeffs) <= 18:
        return "(" + ", ".join(str(c) for c in coeffs) + ")"
    inner = ",\n        ".join(str(c) for c in coeffs)
    return "(\n        " + inner + ",\n    )"


def emit_module(table: dict[int, tuple[int, ...]]) -> str:
    h1 = (-3, -4, -7, -8, -11, -12, -16, -19, -27, -28, -43, -67, -163)
    lines = [_HEADER]
    lines.append("    # Cohen Table 7.1: H_D(X) = X − j(D)\n")
    for d in h1:
        lines.append(f"    {d}: {_fmt_tuple(table[d])},\n")
    rest = sorted((d for d in table if d not in h1), key=lambda d: abs(d))
    if rest:
        lines.append("    # Cohen Table 7.6 / Fungrim 20b6d2\n")
        for d in rest:
            lines.append(f"    {d}: {_fmt_tuple(table[d])},\n")
    lines.append("}\n")
    return "".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-module",
        type=Path,
        nargs="?",
        const=DEFAULT_MODULE,
        help="re-pack the existing module instead of the embedded listing",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_MODULE,
        help="destination path (default: best_prime/_classpoly_h16.py)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare listing and module; do not write",
    )
    args = parser.parse_args(argv)
    if args.from_module is not None:
        table = load_module_table(args.from_module)
    else:
        table = parse_listing(LISTING)
    text = emit_module(table)
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.is_file() else ""
        packed = parse_listing(LISTING)
        if args.output.is_file():
            packed_mod = load_module_table(args.output)
            if packed != packed_mod:
                print("listing and module disagree", file=sys.stderr)
                return 1
        if current and current != text:
            # formatting-only drift is ok if the dict matches
            print("ok (dict matches; formatting may differ)")
        else:
            print("ok")
        return 0
    args.output.write_text(text, encoding="utf-8")
    print(f"wrote {args.output} ({len(table)} discriminants)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
