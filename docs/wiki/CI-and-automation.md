# CI and automation

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI** | push / PR | **Tiered:** PR code → Linux 3.12 tests + lint + determinism trials + perf; PR docs-only → required-check stubs; **main** → 3.9/3.12/3.13 + macOS/Windows, Docker, wheel smoke, no-compiler, attestation |
| **Determinism** | push to `main` | Multi-version repeated trials (PR determinism runs inside the CI Linux 3.12 job) |
| **Auto-merge** | PR / check_suite | Squash-merge **same-repo** PRs when **required** gates are green (not the full matrix) |
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

## Tiered CI (PR vs main)

| Change type | What runs |
|-------------|-----------|
| **PR — engine/tooling** (`best_prime/`, `tests/`, `scripts/`, workflows, packaging, …) | Lint; **Tests (ubuntu-latest / Python 3.12)**; E2E performance; Determinism on 3.12 |
| **PR — docs/meta only** | Stubs that still report the required check names (no install/compile/suite) |
| **push to `main`** | Full matrix (Py 3.9–3.13 + macOS/Windows 3.12), no-compiler, Docker, wheel smoke, lightweight attestation |

Scope detection: `scripts/ci_change_scope.sh` (shared by CI + Determinism).

Linux 3.12 runs **one** `pytest` pass with coverage (no second full re-run). Attestation on `main` writes JSON from green gates and does **not** re-install/re-test.

## Local commands

```bash
python3 scripts/check_restrictions.py
pytest -q -m "not slow"
pytest -q                                          # includes @pytest.mark.slow + Hypothesis
NUMBA_NUM_THREADS=2 python benchmarks/check_determinism.py
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py
python -m best_prime --lab 100000000000000000000000000000000000000000031
python -m best_prime --lab --json 97
```

## Auto-approve / auto-merge policy

- **Same-repository** PRs may be auto-approved (PR agent) and auto-merged (Auto-merge) after green **required** checks.
- Auto-merge waits only for:
  - **`Tests (ubuntu-latest / Python 3.12)`** (legacy `Tests (Python 3.12)` still matches)
  - **`Determinism`** (the gate job name — not `Repeated-trial determinism (Python X)` cells)
  - **E2E performance** if that check is present (absent/skipped is OK)
- It does **not** wait for macOS/Windows or other Python versions (those run on `main` only).
- Branch protection requires **`Tests (ubuntu-latest / Python 3.12)`** and the **`Determinism`** gate job.
- **`optimize/candidate` PRs are not auto-merged.** Optimize examine merges them only when they are actually faster than `main`.
- **Copilot** is the daily *idea* hunter (assigned to `[Optimize] daily …` issues). The catalog job only tries TILE / pmax / OpenMP knobs.
- To auto-assign Copilot, add repo secret **`COPILOT_ASSIGN_TOKEN`**: a PAT (user who can assign Copilot) with read/write **Issues, Contents, Pull requests, Actions**. Without it the issue is still created — click **Assign to Copilot** on the issue.
- **Forks are not auto-approved or auto-merged.**
- Approval **does not** waive CI — gates stay on green checks.

## Certificate of correctness

CI job **Certificate of correctness** runs on **push to `main` only**. It records gate statuses into `attestation.json` (git SHA, run id) without re-running the full pytest/determinism suite. The Linux 3.12 test cell uploads `engine_sample.json` for the artifact bundle.
