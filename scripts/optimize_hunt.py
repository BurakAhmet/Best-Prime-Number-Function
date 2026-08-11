#!/usr/bin/env python3
"""Deterministic catalog hunt for the Optimize workflow.

Tries a small set of compile-time knobs (TILE_BYTES / TILE_P_MAX /
PARALLEL_SEG_MIN) with interleaved A/B against the current wheel_core.so.
Does not invent new algorithms and does not touch forbidden engines.

Subcommands:
  hunt     search the catalog (default)
  apply    write winning knobs into generate_wheel_core_c.py and regenerate C
  examine  A/B the in-tree .so against --orig and optionally run e2e
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "is_prime_data"
GEN = ROOT / "scripts" / "generate_wheel_core_c.py"
COMPILE = ROOT / "scripts" / "compile_wheel_core.sh"
SO = DATA / "wheel_core.so"

# Defaults must match scripts/generate_wheel_core_c.py.
DEFAULTS = {
    "tile_bytes": 16384,
    "tile_p_max": 4096,
    "parallel_seg_min": 10_000_000,
}

# One-at-a-time plus one combo. Skip F10–F13 (no mid-size OpenMP, no wheel-210,
# no 16-way trial, no tiling every prime).
CANDIDATES: list[dict] = [
    {"id": "tile-8k", "tile_bytes": 8192},
    {"id": "tile-32k", "tile_bytes": 32768},
    {"id": "tile-64k", "tile_bytes": 65536},
    {"id": "pmax-128", "tile_p_max": 128},
    {"id": "pmax-192", "tile_p_max": 192},
    {"id": "pmax-384", "tile_p_max": 384},
    {"id": "pmax-512", "tile_p_max": 512},
    {"id": "par-5e6", "parallel_seg_min": 5_000_000},
    {"id": "par-2e7", "parallel_seg_min": 20_000_000},
    {"id": "tile-32k-p384", "tile_bytes": 32768, "tile_p_max": 384},
]

HARD = [
    ("semiprime 1e9s", (10**9 + 7) * (10**9 + 9), 0),
    ("M61", (1 << 61) - 1, 1),
    ("near 2^63", 9_223_372_036_854_775_783, 1),
    ("DEFAULT_N", 18_446_744_073_709_551_557, 1),
]

# Conservative vs GHA 2-thread noise. Interleaved same-machine A/B only.
MIN_GEOMEAN_SPEEDUP = 0.06
MIN_CASES_FASTER = 2
CASE_FASTER = 0.04
CASE_REGRESS = 0.05
MIN_PAIR_WIN_FRAC = 0.66
E2E_THRESHOLD = 0.15


def _load_so(path: Path):
    import ctypes

    lib = ctypes.CDLL(os.fspath(path))
    lib.is_prime_u64_core.argtypes = [ctypes.c_uint64, ctypes.c_int]
    lib.is_prime_u64_core.restype = ctypes.c_int
    return lib


def _time_u64(lib, n: int, parallel: int = 1) -> tuple[int, float]:
    t0 = time.perf_counter()
    ans = int(lib.is_prime_u64_core(n, parallel))
    return ans, (time.perf_counter() - t0) * 1000.0


def interleaved_case(orig, cand, n: int, expect: int, pairs: int) -> dict:
    o_ms: list[float] = []
    c_ms: list[float] = []
    o_ans = c_ans = None
    pair_wins = 0
    for _ in range(pairs):
        o_ans, ot = _time_u64(orig, n)
        c_ans, ct = _time_u64(cand, n)
        o_ms.append(ot)
        c_ms.append(ct)
        if ct < ot:
            pair_wins += 1
    o_mean = sum(o_ms) / len(o_ms)
    c_mean = sum(c_ms) / len(c_ms)
    return {
        "orig_ms": round(min(o_ms), 3),
        "cand_ms": round(min(c_ms), 3),
        "orig_mean_ms": round(o_mean, 3),
        "cand_mean_ms": round(c_mean, 3),
        "ratio": round(c_mean / o_mean, 4) if o_mean > 0 else None,
        "pair_wins": pair_wins,
        "pairs": pairs,
        "orig_ans": o_ans,
        "cand_ans": c_ans,
        "expect": expect,
        "answers_ok": o_ans == expect and c_ans == expect,
    }


def geomean(values: list[float]) -> float:
    if not values:
        return float("nan")
    acc = 0.0
    for v in values:
        if v <= 0:
            return float("nan")
        acc += math.log(v)
    return math.exp(acc / len(values))


def decide(cases: list[dict]) -> dict:
    """Return {win, reasons, geomean_ratio, n_faster} from interleaved case rows."""
    reasons: list[str] = []
    if not cases:
        return {"win": False, "reasons": ["no cases"], "geomean_ratio": None, "n_faster": 0}
    if any(not c.get("answers_ok", False) for c in cases):
        return {
            "win": False,
            "reasons": ["answer mismatch (correctness)"],
            "geomean_ratio": None,
            "n_faster": 0,
        }
    ratios = [float(c["ratio"]) for c in cases if c.get("ratio")]
    gm = geomean(ratios) if ratios else float("nan")
    n_faster = 0
    for c in cases:
        ratio = c.get("ratio")
        if ratio is None:
            continue
        frac = c["pair_wins"] / c["pairs"] if c["pairs"] else 0.0
        if ratio <= 1.0 - CASE_FASTER and frac >= MIN_PAIR_WIN_FRAC:
            n_faster += 1
        if ratio >= 1.0 + CASE_REGRESS:
            reasons.append(
                f"{c.get('case', '?')} regress {ratio:.3f} (≥ {1 + CASE_REGRESS:.2f})"
            )
    if gm > 1.0 - MIN_GEOMEAN_SPEEDUP:
        reasons.append(
            f"geomean ratio {gm:.3f} (need ≤ {1.0 - MIN_GEOMEAN_SPEEDUP:.2f})"
        )
    if n_faster < MIN_CASES_FASTER:
        reasons.append(f"only {n_faster} case(s) clearly faster (need {MIN_CASES_FASTER})")
    win = not reasons
    return {
        "win": win,
        "reasons": reasons if not win else ["clear same-machine speedup"],
        "geomean_ratio": None if math.isnan(gm) else round(gm, 4),
        "n_faster": n_faster,
    }


def knobs_of(cand: dict) -> dict:
    out = dict(DEFAULTS)
    for k in DEFAULTS:
        if k in cand:
            out[k] = int(cand[k])
    return out


def cflags_for(knobs: dict) -> str:
    return (
        f"-DTILE_BYTES={knobs['tile_bytes']}u "
        f"-DTILE_P_MAX={knobs['tile_p_max']}u "
        f"-DPARALLEL_SEG_MIN={knobs['parallel_seg_min']}ull"
    )


def compile_so(dest: Path, knobs: dict | None = None) -> None:
    env = os.environ.copy()
    if knobs is not None:
        env["WHEEL_CORE_CFLAGS"] = cflags_for(knobs)
    else:
        env.pop("WHEEL_CORE_CFLAGS", None)
    subprocess.check_call(["bash", str(COMPILE)], cwd=ROOT, env=env)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SO, dest)


def apply_knobs(knobs: dict) -> None:
    text = GEN.read_text(encoding="utf-8")
    mapping = {
        "TILE_BYTES": knobs["tile_bytes"],
        "TILE_P_MAX": knobs["tile_p_max"],
        "PARALLEL_SEG_MIN": knobs["parallel_seg_min"],
    }
    for name, val in mapping.items():
        rendered = f"{val:_}" if val >= 1_000_000 else str(val)
        text, n = re.subn(
            rf"^({name} = )\d+(?:_\d+)*\s*$",
            rf"\g<1>{rendered}",
            text,
            count=1,
            flags=re.M,
        )
        if n != 1:
            raise SystemExit(f"failed to patch {name} in {GEN}")
    GEN.write_text(text, encoding="utf-8")
    subprocess.check_call([sys.executable, str(GEN)], cwd=ROOT)


def _run_e2e(so_path: Path, dest: Path, repeats: int) -> dict:
    backup = Path("/tmp/wheel_core.examine.bak.so")
    if SO.is_file():
        shutil.copy2(SO, backup)
    try:
        shutil.copy2(so_path, SO)
        subprocess.check_call(
            [
                sys.executable,
                str(ROOT / "benchmarks" / "compare_e2e.py"),
                "--repeats",
                str(repeats),
                "--json",
                str(dest),
            ],
            cwd=ROOT,
        )
    finally:
        if backup.is_file():
            shutil.copy2(backup, SO)
    return json.loads(dest.read_text(encoding="utf-8"))


def e2e_ok(baseline: Path, candidate: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_e2e_regression.py"),
            "--baseline",
            str(baseline),
            "--candidate",
            str(candidate),
            "--threshold",
            str(E2E_THRESHOLD),
            "--min-ms",
            "1.0",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out


def _warmup(lib) -> None:
    _time_u64(lib, 1_000_000_007)


def hunt(args: argparse.Namespace) -> dict:
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    orig_so = work / "orig.so"
    print("Compiling baseline …", flush=True)
    compile_so(orig_so)
    orig = _load_so(orig_so)
    _warmup(orig)

    tried = []
    winner = None
    for spec in CANDIDATES:
        knobs = knobs_of(spec)
        if knobs == DEFAULTS:
            continue
        dest = work / f"{spec['id']}.so"
        print(f"Compiling {spec['id']} ({cflags_for(knobs)}) …", flush=True)
        try:
            compile_so(dest, knobs)
        except subprocess.CalledProcessError as exc:
            tried.append({"id": spec["id"], "knobs": knobs, "error": str(exc), "win": False})
            continue
        cand = _load_so(dest)
        _warmup(cand)
        rows = []
        for name, n, expect in HARD:
            row = interleaved_case(orig, cand, n, expect, args.pairs)
            row["case"] = name
            row["n"] = n
            rows.append(row)
            print(
                f"  {name}: orig {row['orig_mean_ms']:.1f} → cand {row['cand_mean_ms']:.1f} "
                f"({row['ratio']:.3f}x) pairs {row['pair_wins']}/{row['pairs']}",
                flush=True,
            )
        decision = decide(rows)
        entry = {
            "id": spec["id"],
            "knobs": knobs,
            "cases": rows,
            **decision,
        }
        tried.append(entry)
        print(f"  verdict {spec['id']}: win={decision['win']} {decision['reasons']}", flush=True)
        if decision["win"]:
            gm = decision["geomean_ratio"] or 1.0
            if winner is None or gm < (winner.get("geomean_ratio") or 1.0):
                winner = entry

    e2e_report = None
    if winner is not None and not args.skip_e2e:
        print("E2E check on best candidate …", flush=True)
        base_json = work / "e2e_orig.json"
        cand_json = work / "e2e_cand.json"
        _run_e2e(orig_so, base_json, max(1, args.e2e_repeats))
        _run_e2e(work / f"{winner['id']}.so", cand_json, max(1, args.e2e_repeats))
        ok, log = e2e_ok(base_json, cand_json)
        e2e_report = {"ok": ok, "log": log}
        if not ok:
            winner["win"] = False
            winner["reasons"] = list(winner.get("reasons") or []) + ["e2e regression"]
            winner = None

    # Restore in-tree .so to baseline.
    shutil.copy2(orig_so, SO)

    payload = {
        "defaults": DEFAULTS,
        "pairs": args.pairs,
        "omp": os.environ.get("OMP_NUM_THREADS") or "unset",
        "winner": winner,
        "tried": tried,
        "e2e": e2e_report,
    }
    args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md = hunt_markdown(payload)
    if args.md:
        args.md.write_text(md, encoding="utf-8")
    print(md)
    return payload


def hunt_markdown(payload: dict) -> str:
    lines = [
        "## Optimization hunt",
        "",
        f"`OMP_NUM_THREADS={payload.get('omp')}` · {payload.get('pairs')} interleaved pairs",
        "",
        "| Id | Knobs | Geomean | Faster cases | Win? |",
        "|----|-------|--------:|-------------:|:----:|",
    ]
    for t in payload.get("tried") or []:
        knobs = t.get("knobs") or {}
        brief = ", ".join(
            f"{k}={v}" for k, v in knobs.items() if v != DEFAULTS.get(k)
        ) or "(defaults)"
        gm = t.get("geomean_ratio")
        gm_s = "—" if gm is None else f"{gm:.3f}"
        lines.append(
            f"| `{t.get('id')}` | {brief} | {gm_s} | {t.get('n_faster', 0)} | "
            f"{'yes' if t.get('win') else 'no'} |"
        )
    w = payload.get("winner")
    lines += ["", "### Decision", ""]
    if w:
        pct = (1.0 - float(w["geomean_ratio"])) * 100
        lines.append(
            f"**Winner `{w['id']}`** — hard-path geomean **{pct:.1f}%** faster "
            f"(ratio {w['geomean_ratio']})."
        )
        lines.append("")
        lines.append("| Case | Orig mean ms | Cand mean ms | Ratio | Pairs |")
        lines.append("|------|-------------:|-------------:|------:|------:|")
        for c in w.get("cases") or []:
            lines.append(
                f"| {c['case']} | {c['orig_mean_ms']:.1f} | {c['cand_mean_ms']:.1f} | "
                f"{c['ratio']:.3f} | {c['pair_wins']}/{c['pairs']} |"
            )
    else:
        lines.append("No catalog candidate beat main under the win gates. No PR.")
    if payload.get("e2e"):
        lines += ["", "E2E gate: **" + ("pass" if payload["e2e"].get("ok") else "fail") + "**"]
    lines.append("")
    return "\n".join(lines) + "\n"


def examine(args: argparse.Namespace) -> dict:
    orig = _load_so(args.orig)
    cand_so = Path(args.cand) if args.cand else SO
    cand = _load_so(cand_so)
    _warmup(orig)
    _warmup(cand)
    rows = []
    for name, n, expect in HARD:
        row = interleaved_case(orig, cand, n, expect, args.pairs)
        row["case"] = name
        row["n"] = n
        rows.append(row)
    decision = decide(rows)
    e2e_report = None
    if not args.skip_e2e:
        work = Path(args.work)
        work.mkdir(parents=True, exist_ok=True)
        base_json = work / "e2e_orig.json"
        cand_json = work / "e2e_cand.json"
        _run_e2e(Path(args.orig), base_json, max(1, args.e2e_repeats))
        _run_e2e(cand_so, cand_json, max(1, args.e2e_repeats))
        ok, log = e2e_ok(base_json, cand_json)
        e2e_report = {"ok": ok, "log": log}
        if not ok:
            decision["win"] = False
            decision["reasons"] = list(decision.get("reasons") or []) + ["e2e regression"]
    payload = {"cases": rows, "e2e": e2e_report, **decision}
    args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.md:
        args.md.write_text(examine_markdown(payload), encoding="utf-8")
    print(examine_markdown(payload))
    return payload


def examine_markdown(payload: dict) -> str:
    lines = [
        "## Examine (same-machine A/B vs main `.so`)",
        "",
        f"Geomean ratio **{payload.get('geomean_ratio')}** · "
        f"faster cases **{payload.get('n_faster')}** · "
        f"win **{payload.get('win')}**",
        "",
        "| Case | Orig mean ms | Cand mean ms | Ratio | Pairs | OK |",
        "|------|-------------:|-------------:|------:|------:|:--:|",
    ]
    for c in payload.get("cases") or []:
        lines.append(
            f"| {c['case']} | {c['orig_mean_ms']:.1f} | {c['cand_mean_ms']:.1f} | "
            f"{c['ratio']:.3f} | {c['pair_wins']}/{c['pairs']} | "
            f"{'yes' if c['answers_ok'] else 'NO'} |"
        )
    lines += ["", "Reasons: " + "; ".join(payload.get("reasons") or ["—"]), ""]
    if payload.get("e2e"):
        lines.append("E2E: **" + ("pass" if payload["e2e"].get("ok") else "FAIL") + "**")
        lines.append("")
        log = (payload["e2e"].get("log") or "").strip()
        if log:
            lines += ["```", log[:4000], "```", ""]
    return "\n".join(lines) + "\n"


def cmd_apply(args: argparse.Namespace) -> None:
    if args.from_json:
        data = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        winner = data.get("winner")
        if not winner:
            raise SystemExit("hunt JSON has no winner")
        knobs = knobs_of(winner["knobs"])
    else:
        knobs = knobs_of(
            {
                "tile_bytes": args.tile_bytes,
                "tile_p_max": args.tile_p_max,
                "parallel_seg_min": args.parallel_seg_min,
            }
        )
    apply_knobs(knobs)
    print("Applied", knobs, "and regenerated", DATA / "wheel_core.c")


def append_docs(knobs: dict, hunt: dict) -> None:
    """Append Unreleased changelog + a short ALGORITHM_HISTORY note."""
    w = hunt.get("winner") or {}
    gm = w.get("geomean_ratio")
    pct = f"{(1.0 - gm) * 100:.1f}%" if gm else "?"
    ident = w.get("id") or "catalog"
    knob_txt = ", ".join(f"{k}={v}" for k, v in knobs.items())
    rejected = [
        t["id"] for t in hunt.get("tried") or [] if t.get("id") != ident
    ]

    cl = ROOT / "CHANGELOG.md"
    text = cl.read_text(encoding="utf-8")
    bullet = (
        f"- Auto-optimize **`{ident}`** (`{knob_txt}`): hard-path geomean "
        f"**{pct}** faster on the Optimize runner. Rejected this round: "
        f"{', '.join(f'`{r}`' for r in rejected) or 'none'}.\n"
    )
    marker = "## [Unreleased]\n"
    insert_at = text.find(marker)
    if insert_at == -1:
        text = marker + "\n### Changed\n" + bullet + "\n" + text
    else:
        changed = text.find("### Changed\n", insert_at)
        unreleased_end = text.find("\n## [", insert_at + len(marker))
        if changed != -1 and (unreleased_end == -1 or changed < unreleased_end):
            pos = changed + len("### Changed\n")
            text = text[:pos] + bullet + text[pos:]
        else:
            pos = insert_at + len(marker)
            text = text[:pos] + "\n### Changed\n" + bullet + text[pos:]
    cl.write_text(text, encoding="utf-8")

    hist = ROOT / "docs" / "ALGORITHM_HISTORY.md"
    htxt = hist.read_text(encoding="utf-8")
    note = (
        "\n### Auto-optimize catalog\n\n"
        f"Optimize workflow accepted **`{ident}`** ({knob_txt}). "
        f"Hard-path geomean {pct} vs previous defaults on the Actions runner. "
        "Source of truth remains `scripts/generate_wheel_core_c.py` "
        "(compile-time `-DTILE_*` overrides used only during the hunt).\n"
    )
    if "### Auto-optimize catalog" in htxt:
        htxt = re.sub(
            r"\n### Auto-optimize catalog\n\n.*?(?=\n## |\n### |\Z)",
            note,
            htxt,
            count=1,
            flags=re.S,
        )
    else:
        anchor = "## Failures & anti-patterns"
        if anchor in htxt:
            htxt = htxt.replace(anchor, note + "\n" + anchor, 1)
        else:
            htxt += note
    hist.write_text(htxt, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--pairs", type=int, default=3)
        sp.add_argument("--e2e-repeats", type=int, default=2)
        sp.add_argument("--skip-e2e", action="store_true")
        sp.add_argument("--work", type=Path, default=Path("/tmp/optimize_hunt"))
        sp.add_argument("--json", type=Path, default=Path("optimize_hunt.json"))
        sp.add_argument("--md", type=Path, default=None)

    h = sub.add_parser("hunt", help="Search the catalog")
    add_common(h)

    e = sub.add_parser("examine", help="A/B in-tree .so against --orig")
    add_common(e)
    e.add_argument("--orig", type=Path, required=True)
    e.add_argument("--cand", type=Path, default=None)

    a = sub.add_parser("apply", help="Write knobs into the generator")
    a.add_argument("--from-json", type=Path, default=None)
    a.add_argument("--tile-bytes", type=int, default=None)
    a.add_argument("--tile-p-max", type=int, default=None)
    a.add_argument("--parallel-seg-min", type=int, default=None)

    d = sub.add_parser("docs", help="Append changelog + algorithm history")
    d.add_argument("--from-json", type=Path, required=True)

    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.cmd == "hunt":
        hunt(args)
        return 0
    if args.cmd == "examine":
        payload = examine(args)
        return 0 if payload.get("win") else 1
    if args.cmd == "apply":
        cmd_apply(args)
        return 0
    if args.cmd == "docs":
        data = json.loads(args.from_json.read_text(encoding="utf-8"))
        winner = data.get("winner")
        if not winner:
            raise SystemExit("no winner in hunt JSON")
        append_docs(knobs_of(winner["knobs"]), data)
        return 0
    raise SystemExit(f"unknown cmd {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
