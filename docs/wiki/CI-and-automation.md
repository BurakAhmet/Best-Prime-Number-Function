# CI and automation

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI** | push / PR | Restriction linter; `pytest -m "not slow"` on Py 3.9/3.11/3.12; performance vs base; **Certificate of correctness** artifact |
| **Determinism** | push / PR | Repeated serial/parallel trials + `check_determinism.py` |
| **Auto-merge** | CI / Determinism completed | Squash-merge **same-repo** PRs when tests + determinism (+ perf if present) are green |
| **Prime of the day** | daily 12:00 UTC / manual | Deterministic date→`n` challenge via `lab()`; upserts issue labeled `prime-of-the-day` |
| **Issue agent** | issue opened | Keyword answers + restrictions briefing + labels |
| **PR agent** | PR open/sync | Briefing, Copilot review request (best-effort), **auto-approve same-repo PRs** |
| **Project autonomy** | issues / PRs | Label kanban without a human-only lane |
| **Publish wiki** | push to `docs/wiki/**` | Deploy wiki site to GitHub Pages |
| **Publish package** | release / manual | GHCR container (Packages section) |

## Local commands

```bash
python3 scripts/check_restrictions.py
pytest -q -m "not slow"
pytest -q                                          # includes @pytest.mark.slow + Hypothesis
NUMBA_NUM_THREADS=2 python benchmarks/check_determinism.py
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py
python is_prime.py --lab 9223372036854775783
python is_prime.py --lab --json 97
```

## Auto-approve / auto-merge policy

- **Same-repository** PRs may be auto-approved (PR agent) and auto-merged (Auto-merge) after green **CI** + **Determinism**.
- **Forks are not auto-approved or auto-merged.**
- Approval **does not** waive CI — gates stay on green checks.

## Certificate of correctness

CI job **Certificate of correctness** re-runs restriction lint, fast pytest, and determinism, then uploads `attestation.json` (git SHA, run id, gate statuses).
