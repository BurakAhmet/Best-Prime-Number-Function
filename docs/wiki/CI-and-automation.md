# CI and automation

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI** | push / PR | `pytest -m "not slow"`; performance vs base commit |
| **Determinism** | push / PR | Repeated serial/parallel trials must agree |
| **Issue agent** | issue opened | Auto-answer + labels + agent briefing |
| **PR agent** | PR opened/sync | Briefing comment, best-effort Copilot review request, **auto-approve same-repo PRs** |

Fork PRs are **not** auto-approved. Merge should still respect status checks.
