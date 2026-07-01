#!/usr/bin/env python3
"""Append a prime-of-the-day e2e timing row to docs/wiki/Hall-of-fame.md."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOF = ROOT / "docs" / "wiki" / "Hall-of-fame.md"
MARKER = "<!-- potd-log:start -->"
MARKER_END = "<!-- potd-log:end -->"


def ensure_log_section(text: str) -> str:
    if MARKER in text:
        return text
    section = f"""

## Prime-of-the-day log

Automated weekly/daily entries from the **Prime of the day** workflow (`path` + e2e `TIME`).

{MARKER}
| Date (UTC) | n | Prime? | Path | E2E ms | Check ms |
|------------|--:|:------:|------|-------:|---------:|
{MARKER_END}
"""
    return text.rstrip() + section + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", type=Path, required=True, help="potd payload JSON")
    p.add_argument("--hof", type=Path, default=HOF)
    args = p.parse_args()
    potd = json.loads(args.json.read_text())
    date = potd["date"]
    n = potd["n"]
    is_prime = "yes" if potd["is_prime"] else "no"
    path = potd.get("path", "?")
    e2e = potd.get("e2e_ms", potd.get("elapsed_ms", ""))
    check = potd.get("elapsed_ms", "")
    row = f"| {date} | `{n}` | {is_prime} | `{path}` | {e2e} | {check} |"

    text = args.hof.read_text(encoding="utf-8") if args.hof.is_file() else "# Hall of fame\n"
    text = ensure_log_section(text)
    # idempotent: replace existing row for same date
    start = text.index(MARKER) + len(MARKER)
    end = text.index(MARKER_END)
    block = text[start:end]
    lines = [ln for ln in block.splitlines() if ln.strip()]
    header = [ln for ln in lines if ln.startswith("| Date") or ln.startswith("|--") or ln.startswith("| ---")]
    data = [ln for ln in lines if ln.startswith("| ") and ln not in header]
    data = [ln for ln in data if f"| {date} |" not in ln]
    data.insert(0, row)
    # keep last 60 entries
    data = data[:60]
    new_block = "\n" + "\n".join(header + data) + "\n"
    text = text[:start] + new_block + text[end:]
    args.hof.write_text(text, encoding="utf-8")
    print(f"Updated {args.hof} with {date} row")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
