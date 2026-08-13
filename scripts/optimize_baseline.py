#!/usr/bin/env python3
"""Snapshot e2e + in-process timings for a GitHub optimization round.

Writes JSON (and optional Markdown) that the Optimize workflow posts on the
standing Optimization log issue. Not an optimizer itself — just the yardstick.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARD = [
    ("semiprime 1e9s", (10**9 + 7) * (10**9 + 9)),
    ("M61", (1 << 61) - 1),
    ("near 2^63", 9_223_372_036_854_775_783),
    ("DEFAULT_N", 7_000_000_000_000_000_000_037),
]


def _run_e2e(repeats: int) -> dict:
    dest = Path("/tmp/optimize_e2e.json")
    cmd = [
        sys.executable,
        str(ROOT / "benchmarks" / "compare_e2e.py"),
        "--repeats",
        str(repeats),
        "--json",
        str(dest),
    ]
    subprocess.check_call(cmd, cwd=ROOT)
    return json.loads(dest.read_text(encoding="utf-8"))


def _lab_cases(repeats: int) -> list[dict]:
    sys.path.insert(0, str(ROOT))
    from best_prime import lab  # noqa: WPS433

    rows = []
    lab(10**9 + 7)  # warm
    for name, n in HARD:
        best = None
        last = None
        reps = repeats if n < 10**15 else max(1, repeats - 1)
        for _ in range(reps):
            info = lab(n)
            last = info
            ms = float(info["elapsed_ms"])
            best = ms if best is None else min(best, ms)
        rows.append(
            {
                "case": name,
                "n": n,
                "is_prime": last["is_prime"],
                "path": last["path"],
                "elapsed_ms": round(best, 3),
            }
        )
    return rows


def to_markdown(payload: dict) -> str:
    lines = [
        f"## Optimization baseline — `{payload['date']}`",
        "",
        f"SHA `{payload['sha']}` · `OMP_NUM_THREADS={payload['omp']}` · "
        f"host `{payload['host']}`",
        "",
        "### Default e2e CLI (`python -m best_prime`)",
        "",
        "| Case | n | Prime? | E2E ms |",
        "|------|--:|:------:|-------:|",
    ]
    for r in payload["e2e"]["results"]:
        lines.append(
            f"| {r['case']} | `{r['n']}` | {'yes' if r['is_prime'] else 'no'} | {r['e2e_ms']:.3f} |"
        )
    lines += [
        "",
        "### In-process hard path (`lab` / check only)",
        "",
        "| Case | n | Path | ms |",
        "|------|--:|------|---:|",
    ]
    for r in payload["hard"]:
        lines.append(
            f"| {r['case']} | `{r['n']}` | `{r['path']}` | {r['elapsed_ms']:.3f} |"
        )
    lines += [
        "",
        "### Agent brief (same as saying *optimize this*)",
        "",
        "1. Deterministic; no Miller–Rabin; no primesieve/`sympy.isprime` as engine.",
        "2. Read `docs/ALGORITHM_HISTORY.md` **F1–F13**. Do not repeat them.",
        "3. Interleaved A/B vs previous `wheel_core.so`. Primary metric: e2e CLI `TIME`.",
        "4. Edit `scripts/generate_wheel_core_c.py`, regenerate, recompile.",
        "5. Ship a PR only on a real win; no empty PRs.",
        "6. Code only in `best_prime/`. CLI: `python -m best_prime`.",
        "",
        "The same **Optimize** workflow also hunts `scripts/optimize_hunt.py`",
        "and will open / examine / merge a PR only if a catalog candidate is faster.",
        "Novel ideas still go through an **Optimization round** issue or Grok.",
        "",
        "Skill: `.grok/skills/optimize-primes/SKILL.md`.",
        "",
        "<sub>Posted by the **Optimize** workflow.</sub>",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repeats", type=int, default=2)
    p.add_argument("--json", type=Path, default=Path("/tmp/optimize_baseline.json"))
    p.add_argument("--md", type=Path, default=None)
    args = p.parse_args()

    sha = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
    ).strip()
    payload = {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "sha": sha,
        "omp": os.environ.get("OMP_NUM_THREADS") or os.environ.get("NUMBA_NUM_THREADS") or "unset",
        "host": os.uname().nodename,
        "unix": int(time.time()),
        "e2e": _run_e2e(args.repeats),
        "hard": _lab_cases(args.repeats),
    }
    args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md = to_markdown(payload)
    if args.md:
        args.md.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
