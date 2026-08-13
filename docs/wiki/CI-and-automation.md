# CI and automation

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI** | push / PR | Restriction linter; `pytest -m "not slow"` on Py 3.9/3.11/3.12; performance vs base; **Certificate of correctness** artifact |
| **Determinism** | push / PR | Repeated serial/parallel trials + `check_determinism.py` |
| **Auto-merge** | CI / Determinism completed | Squash-merge **same-repo** PRs when tests + determinism (+ perf if present) are green |
| **Prime of the day** | daily 12:00 UTC / manual | Deterministic date→`n` challenge via `lab()`; upserts issue labeled `prime-of-the-day` |
| **Optimize** | daily 05:00 UTC / manual | Baseline on the **Optimization log** issue; hunt the compile-time catalog; open a dated **Optimization round** issue and assign **Copilot** (needs `COPILOT_ASSIGN_TOKEN`); catalog/Copilot PRs labeled `optimize/candidate` are examined (interleaved A/B + tests) and squash-merged only if still faster. Generic Auto-merge skips these PRs. |
| **Optimize examine** | `optimize/candidate`, `optimize/auto-*`, or `copilot/*` PRs | Fresh-runner A/B vs `main`; merge only on a confirmed win; **close** empty or losing PRs. |
| **Copilot setup steps** | Copilot coding agent | Install gcc/OpenMP, `pip install -e ".[fast,test]"`, compile `wheel_core.so`. |
| **Issue agent** | issue opened | Keyword answers + restrictions briefing + labels |
| **PR agent** | PR open/sync | Briefing, Copilot review request (best-effort), **auto-approve same-repo PRs** |
| **Project autonomy** | issues / PRs | Label kanban without a human-only lane |
| **Publish wiki** | push to `docs/wiki/**` / `docs/guide/**` / `mkdocs.yml`; **workflow_run** after Auto-merge (only if it merged), Prime of the day, or Optimize (only if it merged); manual dispatch | Compile exhibit Markdown → HTML (KaTeX, lab) **and** MkDocs library guide at `/guide/`; deploy GitHub Pages. Needed because `GITHUB_TOKEN` merges do not start `on: push` workflows. |
| **Publish package** | release / manual | GHCR container (Packages section). Slim image needs `gcc` + `libc6-dev`. |
| **Publish PyPI** | release / manual | sdist + **platform** wheels (`BEST_PRIME_REQUIRE_NATIVE=1`); attach to the GitHub Release; upload to PyPI if Trusted Publisher is configured |

## Local commands

```bash
python3 scripts/check_restrictions.py
pytest -q -m "not slow"
pytest -q                                          # includes @pytest.mark.slow + Hypothesis
NUMBA_NUM_THREADS=2 python benchmarks/check_determinism.py
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py
python -m best_prime --lab 10000000000000000000000000000000000000121
python -m best_prime --lab --json 97
```

## Auto-approve / auto-merge policy

- **Same-repository** PRs may be auto-approved (PR agent) and auto-merged (Auto-merge) after green **CI** + **Determinism**.
- Auto-merge treats jobs named `Tests (… Python …)` as the test gate (legacy `Tests (Python 3.12)` and current `Tests (ubuntu-latest / Python 3.12)` both count).
- Branch protection requires **`Tests (ubuntu-latest / Python 3.12)`** and the **`Determinism`** gate job (not the per-version `Repeated-trial determinism (Python X)` cells).
- **`optimize/candidate` PRs are not auto-merged.** Optimize examine merges them only when they are actually faster than `main`.
- **Copilot** is the daily *idea* hunter (assigned to `[Optimize] daily …` issues). The catalog job only tries TILE / pmax / OpenMP knobs.
- To auto-assign Copilot, add repo secret **`COPILOT_ASSIGN_TOKEN`**: a PAT (user who can assign Copilot) with read/write **Issues, Contents, Pull requests, Actions**. Without it the issue is still created — click **Assign to Copilot** on the issue.
- **Forks are not auto-approved or auto-merged.**
- Approval **does not** waive CI — gates stay on green checks.

## Certificate of correctness

CI job **Certificate of correctness** re-runs restriction lint, fast pytest, and determinism, then uploads `attestation.json` (git SHA, run id, gate statuses).
