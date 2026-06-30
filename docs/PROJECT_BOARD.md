# Autonomous project board

This repository is managed **without a human-only column**. Work moves through labels that power GitHub **Projects** views (and work even if you only use Issues filters).

## 1. Kanban (`status/*`)

| Label | Column |
|-------|--------|
| `status/backlog` | Backlog |
| `status/ready` | Ready |
| `status/in-progress` | In progress |
| `status/in-review` | In review |
| `status/done` | Done |

**Automation (`Project autonomy` workflow):**

- New issues (non-quality) → `status/backlog` + `agent/triaged`
- PR opened/sync → `status/in-review` + `agent/waiting-ci`
- Issue/PR closed (merged) → `status/done` + `agent/done`
- PR closed unmerged → `status/backlog` + `agent/triaged`

## 2. Type views (filter by label)

| View | Filter |
|------|--------|
| Bugs | `bug` |
| Enhancements | `enhancement` |
| Restrictions / design | `restrictions` or `restriction-risk/high` |
| Performance | `performance` or `area/benchmarks` |
| Agents / automation | `area/agents` or `agent/*` |

## 3. Release / quality checklist

Issues titled `[Quality] …` use:

| Label | Meaning |
|-------|---------|
| `quality/checklist` | Is a checklist item |
| `quality/todo` | Not started |
| `quality/partial` | Partial |
| `quality/done` | Complete |

Filter: `label:quality/checklist`. Seeded items track CI, determinism, performance gate, wiki alignment, docs, AI warning.

## 4. Agent ops (fully autonomous)

**No “Needs human” column.** Pipeline:

| Label | Stage |
|-------|--------|
| `agent/triaged` | Intake complete (issue agent / autonomy workflow) |
| `agent/implementing` | Agent implementing (optional use) |
| `agent/waiting-ci` | PR waiting on CI / determinism |
| `agent/done` | Pipeline complete |

Agents and Actions move items end-to-end: triage → implement → CI → done.

## Extra fields (labels)

- **Area:** `area/core`, `area/tests`, `area/ci`, `area/docs`, `area/benchmarks`, `area/agents`
- **Priority:** `priority/p0` … `priority/p3`
- **Size:** `size/S`, `size/M`, `size/L`
- **Restriction risk:** `restriction-risk/low`, `restriction-risk/high`

## Creating the GitHub Project UI board

1. Open the repo → **Projects** → New project → Board.
2. Name it **Best-Prime-Number-Function**.
3. Set Status options to match `status/*` or use **Filter views**:
   - Kanban: group/filter by `status/backlog` … `status/done` (or use an automation to map labels → Status field).
4. Add saved views for Bugs / Enhancements / Restrictions / Performance / Agents / Quality.
5. Enable **Auto-add** issues and PRs from this repository.

If your `gh` token has the `project` scope (`gh auth refresh -h github.com -s project,read:project`), you can also run:

```bash
gh project create --owner BurakAhmet --title "Best-Prime-Number-Function"
gh project link <number> --owner BurakAhmet --repo Best-Prime-Number-Function
```

Label automation works regardless of whether the Project UI is linked.
