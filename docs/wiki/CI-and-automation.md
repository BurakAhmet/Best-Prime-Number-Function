# CI and automation

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI** | push / PR | `pytest -m "not slow"` on Py 3.9/3.11/3.12; performance vs base commit (fail if >20% slower) |
| **Determinism** | push / PR | Repeated serial/parallel trials + `check_determinism.py` |
| **Issue agent** | issue opened | Keyword answers + restrictions briefing + labels |
| **PR agent** | PR open/sync | Briefing, Copilot review request (best-effort), **auto-approve same-repo PRs** |
| **Publish wiki** | push to `docs/wiki/**` | Deploy wiki site to GitHub Pages |

## Local commands

```bash
pytest -q -m "not slow"
pytest -q                                          # includes @pytest.mark.slow
NUMBA_NUM_THREADS=2 python benchmarks/check_determinism.py
NUMBA_NUM_THREADS=$(nproc) python benchmarks/compare_speed.py
```

## Auto-approve policy

- **Same-repository** PRs may be auto-approved by PR agent to ease review.
- **Forks are not auto-approved.**
- Approval **does not** waive CI — keep branch protection on green **CI** + **Determinism**.
