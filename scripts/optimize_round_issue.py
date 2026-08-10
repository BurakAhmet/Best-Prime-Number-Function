#!/usr/bin/env python3
"""Build the daily Optimization-round issue body for Copilot.

Reads optional baseline / hunt JSON from the Optimize workflow and writes
Markdown that assigns Copilot a real engine hunt (not the TILE catalog).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


SKILL = """\
Treat this as **optimize this** on current `main`.

### Non-negotiable

1. Fully **deterministic**. Serial == parallel. No RNG.
2. **No** stochastic primality engine (no random-base Miller–Rabin / “probably prime”).
3. **No** external prime libraries as the engine.
4. Allowed: NumPy/Numba, in-tree OpenMP `wheel_core.so`, stdlib.
5. Primary metric: end-to-end CLI `TIME` (`python -m best_prime`, `benchmarks/compare_e2e.py`).
6. Read `docs/ALGORITHM_HISTORY.md` **F1–F13** and do **not** repeat them.
7. Edit `scripts/generate_wheel_core_c.py` then regenerate; do **not** hand-edit `wheel_core.c` as source of truth.
8. Code only under `best_prime/`. CLI: `python -m best_prime`.

### Hunt

Pick **one** untried idea that is **not** already in today’s catalog hunt
(`TILE_BYTES` / `TILE_P_MAX` / `PARALLEL_SEG_MIN` one-at-a-time). Prefer:

- Hard-path OpenMP sieve/trial (generator `BODY`)
- Mid-size e2e / import overhead if that is the bottleneck
- `prime_count` / `next_prime` only if `is_prime` is saturated

```bash
bash scripts/compile_wheel_core.sh
cp is_prime_data/wheel_core.so /tmp/orig_wheel_core.so
# change the generator, regenerate, recompile
python3 scripts/generate_wheel_core_c.py && bash scripts/compile_wheel_core.sh
python3 scripts/optimize_hunt.py examine --orig /tmp/orig_wheel_core.so --md /tmp/ex.md
```

### Ship only a real win

- Answers unchanged; `pytest -q -m "not slow"` and determinism green
- Interleaved A/B clearly faster on at least one hard case; no default-suite e2e regression
- Update `docs/ALGORITHM_HISTORY.md` + `CHANGELOG.md`
- Open a PR. Do **not** merge yourself — the Optimize examine workflow will
  merge only if a fresh runner still says it is faster.

If nothing wins: comment on this issue with what you tried and numbers.
Do **not** open an empty or docs-only PR.
"""


def _load(path: Path | None) -> dict | None:
    if not path or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build(baseline: dict | None, hunt: dict | None, run_url: str) -> str:
    lines = [
        "## Optimization round (Copilot)",
        "",
        "Daily **Optimize** workflow opened this issue and assigned **Copilot**",
        "to invent a real engine improvement (the TILE catalog is a separate job).",
        "",
        f"[Actions run]({run_url})" if run_url else "",
        "",
    ]
    if baseline:
        lines += [
            "### Baseline (this runner)",
            "",
            f"SHA `{baseline.get('sha', '?')}` · "
            f"`OMP_NUM_THREADS={baseline.get('omp', '?')}`",
            "",
            "| Case | n | Path | ms |",
            "|------|--:|------|---:|",
        ]
        for r in baseline.get("hard") or []:
            lines.append(
                f"| {r.get('case')} | `{r.get('n')}` | `{r.get('path')}` | {r.get('elapsed_ms')} |"
            )
        lines.append("")
        e2e = (baseline.get("e2e") or {}).get("results") or []
        if e2e:
            lines += [
                "| E2E case | n | ms |",
                "|----------|--:|---:|",
            ]
            for r in e2e:
                lines.append(
                    f"| {r.get('case')} | `{r.get('n')}` | {r.get('e2e_ms')} |"
                )
            lines.append("")
    if hunt:
        lines += ["### Catalog hunt (already tried — do not repeat)", ""]
        winner = hunt.get("winner")
        if winner:
            lines.append(
                f"Catalog already found a knob win (`{winner.get('id')}`); "
                "look for a **different** idea."
            )
            lines.append("")
        for t in hunt.get("tried") or []:
            knobs = t.get("knobs") or {}
            brief = ", ".join(f"{k}={v}" for k, v in knobs.items())
            gm = t.get("geomean_ratio")
            gm_s = "—" if gm is None else f"{gm:.3f}"
            lines.append(
                f"- `{t.get('id')}` ({brief}): geomean {gm_s}, "
                f"win={bool(t.get('win'))}"
            )
        lines.append("")
    lines += [SKILL, ""]
    lines.append(
        "<sub>Opened by the **Optimize** workflow. Label `optimize/round`. "
        "PRs from this issue are examined and merged only if faster than `main`.</sub>"
    )
    return "\n".join(line for line in lines if line is not None)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, default=None)
    p.add_argument("--hunt", type=Path, default=None)
    p.add_argument("--run-url", default="")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    md = build(_load(args.baseline), _load(args.hunt), args.run_url)
    args.out.write_text(md + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
