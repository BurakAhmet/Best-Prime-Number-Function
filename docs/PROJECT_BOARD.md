# Autonomous project board

This repository is managed **without a human-only column**. Work moves through **labels** that power GitHub **Projects** views (and work even if you only use Issues filters).

**Design script:** `python3 scripts/design_github_project.py`  
(requires `gh auth` with `read:project` + `project` scopes)

## 1. Kanban (`status/*` → Project **Status**)

| Label | Project Status column |
|-------|------------------------|
| `status/backlog` | **Backlog** |
| `status/ready` | **Ready** |
| `status/in-progress` | **In progress** |
| `status/in-review` | **In review** |
| `status/done` | **Done** |

**Automation (`Project autonomy` workflow):**

- New issues (non-quality) → `status/backlog` + `agent/triaged`
- PR opened/sync → `status/in-review` + `agent/waiting-ci`
- Issue/PR closed (merged) → `status/done` + `agent/done`
- PR closed unmerged → `status/backlog` + `agent/triaged`

## 2. Project fields (created by design script)

| Field | Options | Source labels |
|-------|---------|---------------|
| **Status** | Backlog, Ready, In progress, In review, Done | `status/*` |
| **Priority** | P0–P3 | `priority/p0` … `p3` |
| **Size** | S, M, L | `size/S` … `L` |
| **Area** | core, tests, ci, docs, benchmarks, agents | `area/*` |
| **Restriction risk** | Low, High | `restriction-risk/*` |
| **Agent stage** | Triaged, Implementing, Waiting CI, Done | `agent/*` |

## 3. Saved views (create in Project UI)

| View | Layout | Configuration |
|------|--------|----------------|
| **Kanban** | Board | Group by **Status**; optional filter out Done |
| **Agent ops** | Board | Group by **Agent stage** |
| **Quality** | Table | Filter titles `[Quality]` or label `quality/checklist` |
| **Bugs** | Table / Board | Filter label `bug` |
| **Enhancements** | Table / Board | Filter label `enhancement` |
| **Restrictions** | Table | Filter label `restrictions` or Restriction risk = High |
| **Performance** | Table | Filter `performance` or Area = benchmarks |
| **Agents** | Table | Filter Area = agents |

## 4. Built-in Project workflows (enable in UI)

Project → **⋯** → **Workflows**:

1. **Auto-add to project** — issues and pull requests from `Best-Prime-Number-Function`
2. **Item closed** → set Status to **Done**
3. **Pull request merged** → set Status to **Done**

Optional: store classic PAT with `repo` + `project` as secret **`PROJECT_TOKEN`**, and set variable **`PROJECT_NUMBER`**, then **Project sync** re-runs the design/seed script on demand.

## 5. Release / quality checklist

Issues titled `[Quality] …` use:

| Label | Meaning |
|-------|---------|
| `quality/checklist` | Is a checklist item |
| `quality/todo` | Not started |
| `quality/partial` | Partial |
| `quality/done` | Complete |

## 6. Agent ops (fully autonomous)

**No “Needs human” column.**

| Label | Stage |
|-------|--------|
| `agent/triaged` | Intake complete |
| `agent/implementing` | Agent implementing |
| `agent/waiting-ci` | PR waiting on CI / determinism |
| `agent/done` | Pipeline complete |

## Extra labels

- **Area:** `area/core`, `area/tests`, `area/ci`, `area/docs`, `area/benchmarks`, `area/agents`
- **Priority:** `priority/p0` … `priority/p3`
- **Size:** `size/S`, `size/M`, `size/L`
- **Restriction risk:** `restriction-risk/low`, `restriction-risk/high`
- **Prime of the day:** `prime-of-the-day`

## Apply / refresh the design

```bash
# One-time (or when scopes missing):
gh auth refresh -h github.com -s read:project,project

# Design fields, README, link repo, seed all issues/PRs:
python3 scripts/design_github_project.py
```

Project number is written to [`.github/project-number.txt`](../.github/project-number.txt) for Actions.
