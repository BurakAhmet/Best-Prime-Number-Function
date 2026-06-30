#!/usr/bin/env python3
"""Design GitHub Projects (v2) for Best-Prime-Number-Function.

Requires: gh auth with read:project + project scopes
  gh auth refresh -h github.com -s read:project,project
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

OWNER = os.environ.get("OWNER", "BurakAhmet")
REPO = os.environ.get("REPO", "Best-Prime-Number-Function")
TITLE = os.environ.get("PROJECT_TITLE", "Best-Prime-Number-Function")

STATUS_OPTIONS = [
    ("Backlog", "YELLOW", "Queued / intake — status/backlog"),
    ("Ready", "GREEN", "Ready for implement — status/ready"),
    ("In progress", "BLUE", "Agent implementing — status/in-progress"),
    ("In review", "PURPLE", "PR open / CI — status/in-review"),
    ("Done", "GRAY", "Closed or merged — status/done"),
]

EXTRA_FIELDS = {
    "Priority": [
        ("P0", "RED", "Critical — priority/p0"),
        ("P1", "ORANGE", "High — priority/p1"),
        ("P2", "YELLOW", "Normal — priority/p2"),
        ("P3", "GRAY", "Low — priority/p3"),
    ],
    "Size": [
        ("S", "GREEN", "Small — size/S"),
        ("M", "YELLOW", "Medium — size/M"),
        ("L", "ORANGE", "Large — size/L"),
    ],
    "Area": [
        ("core", "PURPLE", "area/core"),
        ("tests", "BLUE", "area/tests"),
        ("ci", "ORANGE", "area/ci"),
        ("docs", "PURPLE", "area/docs"),
        ("benchmarks", "GREEN", "area/benchmarks"),
        ("agents", "RED", "area/agents"),
    ],
    "Restriction risk": [
        ("Low", "GREEN", "restriction-risk/low"),
        ("High", "RED", "restriction-risk/high"),
    ],
    "Agent stage": [
        ("Triaged", "BLUE", "agent/triaged"),
        ("Implementing", "BLUE", "agent/implementing"),
        ("Waiting CI", "YELLOW", "agent/waiting-ci"),
        ("Done", "GREEN", "agent/done"),
    ],
}

STATUS_FROM_LABEL = {
    "status/backlog": "Backlog",
    "status/ready": "Ready",
    "status/in-progress": "In progress",
    "status/in-review": "In review",
    "status/done": "Done",
}
PRIORITY_FROM_LABEL = {f"priority/p{i}": f"P{i}" for i in range(4)}
SIZE_FROM_LABEL = {"size/S": "S", "size/M": "M", "size/L": "L"}
AREA_FROM_LABEL = {
    "area/core": "core",
    "area/tests": "tests",
    "area/ci": "ci",
    "area/docs": "docs",
    "area/benchmarks": "benchmarks",
    "area/agents": "agents",
}
RISK_FROM_LABEL = {
    "restriction-risk/low": "Low",
    "restriction-risk/high": "High",
}
AGENT_FROM_LABEL = {
    "agent/triaged": "Triaged",
    "agent/implementing": "Implementing",
    "agent/waiting-ci": "Waiting CI",
    "agent/done": "Done",
}

README = """# Best-Prime-Number-Function — Project board

Fully **autonomous** board for the deterministic primality project.

## Columns (Status)

| Status | Meaning | Labels |
|--------|---------|--------|
| **Backlog** | Intake / queued | `status/backlog`, `agent/triaged` |
| **Ready** | Ready for agent implement | `status/ready` |
| **In progress** | Being implemented | `status/in-progress`, `agent/implementing` |
| **In review** | PR open / CI running | `status/in-review`, `agent/waiting-ci` |
| **Done** | Closed / merged | `status/done`, `agent/done` |

**No “Needs human” column.** Agents and Actions move work end-to-end.

## Views (create in UI once fields exist)

1. **Kanban** — Board layout, group by **Status**, hide Done optional
2. **Agent ops** — Board or table, group by **Agent stage**
3. **Quality checklist** — Filter items whose title starts with `[Quality]` or label `quality/checklist`
4. **Bugs** — Filter label `bug`
5. **Enhancements** — Filter label `enhancement`
6. **Restrictions** — Filter `restrictions` or **Restriction risk** = High
7. **Performance** — Filter label `performance` or **Area** = benchmarks
8. **Agents / automation** — Filter **Area** = agents

## Built-in Project workflows (enable in Project → ⋯ → Workflows)

- **Auto-add to project**: issues and PRs in `BurakAhmet/Best-Prime-Number-Function`
- **Item closed** → Status = Done
- **Pull request merged** → Status = Done

Label automation: workflow **Project autonomy** in the repo.
Re-run this script anytime: `python3 scripts/design_github_project.py`

Restrictions: no stochastic Miller–Rabin; no prime libraries; deterministic for all naturals.
"""


def run(cmd: list[str], check: bool = True) -> str:
    r = subprocess.run(cmd, text=True, capture_output=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"cmd failed: {cmd}\n{r.stderr or r.stdout}")
    return (r.stdout or "").strip()


def gql(query: str, variables: dict | None = None) -> dict:
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    if variables is not None:
        args += ["-f", f"variables={json.dumps(variables)}"]
    out = run(args)
    data = json.loads(out)
    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"], indent=2))
    return data["data"]


def need_scope() -> None:
    try:
        gql("query { viewer { projectsV2(first: 1) { nodes { id } } } }")
    except Exception as e:
        print(
            "ERROR: token missing project scopes.\n"
            "  Run: gh auth refresh -h github.com -s read:project,project\n"
            f"  Detail: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


def list_projects() -> list[dict]:
    out = run(["gh", "project", "list", "--owner", OWNER, "--limit", "50", "--format", "json"])
    data = json.loads(out)
    if isinstance(data, list):
        return data
    return data.get("projects") or data.get("items") or []


def resolve_project() -> tuple[int, str, str]:
    projects = list_projects()
    match = [p for p in projects if p.get("title") == TITLE]
    if not match:
        match = [
            p
            for p in projects
            if "prime" in (p.get("title") or "").lower()
            or "Best-Prime" in (p.get("title") or "")
        ]
    if not match and projects:
        # Prefer most recently updated user project if only one open
        open_ps = [p for p in projects if not p.get("closed")]
        if len(open_ps) == 1:
            match = open_ps
            print(f"Using sole open project: {match[0].get('title')}")
    if not match:
        print(f"Creating project {TITLE!r}…")
        out = run(["gh", "project", "create", "--owner", OWNER, "--title", TITLE, "--format", "json"])
        p = json.loads(out)
        number = int(p["number"])
    else:
        number = int(match[0]["number"])
        print(f"Using existing project #{number}: {match[0].get('title')}")

    meta = json.loads(run(["gh", "project", "view", str(number), "--owner", OWNER, "--format", "json"]))
    return number, meta["id"], meta.get("url") or ""


def link_repo(number: int) -> None:
    for args in (
        ["gh", "project", "link", str(number), "--owner", OWNER, "--repo", f"{OWNER}/{REPO}"],
        ["gh", "project", "link", str(number), "--owner", OWNER, "--repo", REPO],
    ):
        r = subprocess.run(args, text=True, capture_output=True)
        if r.returncode == 0:
            print("Linked repository to project")
            return
    print("Note: project link skipped (may already be linked)")


def update_meta(project_id: str) -> None:
    gql(
        """mutation($projectId: ID!, $desc: String!, $readme: String!) {
          updateProjectV2(input: {
            projectId: $projectId
            shortDescription: $desc
            readme: $readme
          }) { projectV2 { id } }
        }""",
        {
            "projectId": project_id,
            "desc": "Autonomous kanban for deterministic is_prime — labels drive Status; no human-only column.",
            "readme": README,
        },
    )
    print("Updated short description + project README")


def get_fields(project_id: str) -> dict[str, dict]:
    data = gql(
        """query($id: ID!) {
          node(id: $id) {
            ... on ProjectV2 {
              fields(first: 50) {
                nodes {
                  __typename
                  ... on ProjectV2Field { id name dataType }
                  ... on ProjectV2SingleSelectField {
                    id name dataType
                    options { id name }
                  }
                }
              }
            }
          }
        }""",
        {"id": project_id},
    )
    out: dict[str, dict] = {}
    for f in data["node"]["fields"]["nodes"]:
        if not f or not f.get("name"):
            continue
        out[f["name"]] = {
            "id": f["id"],
            "options": {o["name"]: o["id"] for o in (f.get("options") or [])},
            "typename": f.get("__typename"),
        }
    return out


def create_single_select(project_id: str, name: str, options: list[tuple[str, str, str]]) -> None:
    opts = ", ".join(
        f'{{name: "{n}", color: {c}, description: "{d}"}}' for n, c, d in options
    )
    gql(
        f"""mutation($projectId: ID!) {{
          createProjectV2Field(input: {{
            projectId: $projectId
            dataType: SINGLE_SELECT
            name: "{name}"
            singleSelectOptions: [{opts}]
          }}) {{
            projectV2Field {{ ... on ProjectV2SingleSelectField {{ id name }} }}
          }}
        }}""",
        {"projectId": project_id},
    )
    print(f"Created field: {name}")


def ensure_status(project_id: str, fields: dict) -> dict:
    """Align Status options with our kanban names."""
    if "Status" not in fields:
        create_single_select(project_id, "Status", STATUS_OPTIONS)
        return get_fields(project_id)

    status = fields["Status"]
    existing_names = set(status["options"])
    desired = {n for n, _, _ in STATUS_OPTIONS}

    # If options already match, done
    if desired <= existing_names:
        print("Status options already include design set")
        return fields

    # Replace/update: pass full option list; include ids for existing when renaming defaults
    # Map common defaults → our names
    rename_map = {
        "Todo": "Backlog",
        "To Do": "Backlog",
        "In Progress": "In progress",
        "Done": "Done",
    }
    option_inputs = []
    used_ids = set()
    name_to_id = status["options"]

    # Prefer rename existing defaults
    for old, new in rename_map.items():
        if old in name_to_id and new not in name_to_id:
            oid = name_to_id[old]
            color = next(c for n, c, _ in STATUS_OPTIONS if n == new)
            desc = next(d for n, _, d in STATUS_OPTIONS if n == new)
            option_inputs.append(
                {"id": oid, "name": new, "color": color, "description": desc}
            )
            used_ids.add(oid)

    for name, color, desc in STATUS_OPTIONS:
        # already covered by rename?
        if any(x.get("name") == name for x in option_inputs):
            continue
        if name in name_to_id:
            option_inputs.append(
                {
                    "id": name_to_id[name],
                    "name": name,
                    "color": color,
                    "description": desc,
                }
            )
            used_ids.add(name_to_id[name])
        else:
            option_inputs.append({"name": name, "color": color, "description": desc})

    # Keep unused existing options with their ids to avoid API wipe errors (optional drop)
    for n, oid in name_to_id.items():
        if oid in used_ids:
            continue
        # drop unused default options by not including them

    # Build GraphQL inline — mutation with variables is cleaner
    # GitHub expects ProjectV2SingleSelectFieldOptionInput
    gql(
        """mutation($fieldId: ID!, $options: [ProjectV2SingleSelectFieldOptionInput!]!) {
          updateProjectV2Field(input: {
            fieldId: $fieldId
            singleSelectOptions: $options
          }) {
            projectV2Field {
              ... on ProjectV2SingleSelectField { id name options { id name } }
            }
          }
        }""",
        {"fieldId": status["id"], "options": option_inputs},
    )
    print("Updated Status options:", [o.get("name") for o in option_inputs])
    return get_fields(project_id)


def ensure_extra_fields(project_id: str, fields: dict) -> dict:
    for name, options in EXTRA_FIELDS.items():
        if name in fields:
            print(f"Field exists: {name}")
            continue
        try:
            create_single_select(project_id, name, options)
        except Exception as e:
            print(f"Warn create {name}: {e}")
    return get_fields(project_id)


def content_id(kind: str, number: int) -> str:
    data = gql(
        f"""query {{
          repository(owner: "{OWNER}", name: "{REPO}") {{
            {kind}(number: {number}) {{ id }}
          }}
        }}"""
    )
    return data["repository"][kind]["id"]


def add_item(project_id: str, content_id: str) -> str:
    data = gql(
        """mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item { id }
          }
        }""",
        {"projectId": project_id, "contentId": content_id},
    )
    return data["addProjectV2ItemById"]["item"]["id"]


def set_select(project_id: str, item_id: str, fields: dict, field_name: str, option_name: str) -> None:
    f = fields.get(field_name)
    if not f or option_name not in f["options"]:
        return
    gql(
        """mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: { singleSelectOptionId: $optionId }
          }) { projectV2Item { id } }
        }""",
        {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": f["id"],
            "optionId": f["options"][option_name],
        },
    )


def apply_labels(project_id: str, item_id: str, fields: dict, labels: list) -> None:
    names = [l["name"] if isinstance(l, dict) else l for l in labels]
    for mapping, field in (
        (STATUS_FROM_LABEL, "Status"),
        (PRIORITY_FROM_LABEL, "Priority"),
        (SIZE_FROM_LABEL, "Size"),
        (AREA_FROM_LABEL, "Area"),
        (RISK_FROM_LABEL, "Restriction risk"),
        (AGENT_FROM_LABEL, "Agent stage"),
    ):
        for lab, val in mapping.items():
            if lab in names:
                set_select(project_id, item_id, fields, field, val)
                break


def seed_items(project_id: str, fields: dict) -> int:
    issues = json.loads(
        run(
            [
                "gh",
                "issue",
                "list",
                "-R",
                f"{OWNER}/{REPO}",
                "-L",
                "100",
                "--state",
                "all",
                "--json",
                "number,title,labels,state",
            ]
        )
    )
    prs = json.loads(
        run(
            [
                "gh",
                "pr",
                "list",
                "-R",
                f"{OWNER}/{REPO}",
                "-L",
                "50",
                "--state",
                "all",
                "--json",
                "number,title,labels,state",
            ]
        )
    )
    n = 0
    for issue in issues:
        try:
            iid = add_item(project_id, content_id("issue", issue["number"]))
            apply_labels(project_id, iid, fields, issue.get("labels") or [])
            if issue.get("state") == "CLOSED":
                set_select(project_id, iid, fields, "Status", "Done")
                set_select(project_id, iid, fields, "Agent stage", "Done")
            print(f"  + issue #{issue['number']}: {issue['title'][:70]}")
            n += 1
        except Exception as e:
            print(f"  ! issue #{issue['number']}: {e}")
    for pr in prs:
        try:
            iid = add_item(project_id, content_id("pullRequest", pr["number"]))
            apply_labels(project_id, iid, fields, pr.get("labels") or [])
            if pr.get("state") in ("CLOSED", "MERGED"):
                set_select(project_id, iid, fields, "Status", "Done")
            print(f"  + PR #{pr['number']}: {pr['title'][:70]}")
            n += 1
        except Exception as e:
            print(f"  ! PR #{pr['number']}: {e}")
    return n


def main() -> int:
    need_scope()
    number, project_id, url = resolve_project()
    print(f"Project ID: {project_id}\nURL: {url}")
    link_repo(number)
    update_meta(project_id)
    fields = get_fields(project_id)
    print("Existing fields:", sorted(fields))
    fields = ensure_status(project_id, fields)
    fields = ensure_extra_fields(project_id, fields)
    print("Final fields:", sorted(fields))
    for name, f in fields.items():
        if f["options"]:
            print(f"  {name}: {list(f['options'])}")
    added = seed_items(project_id, fields)
    # Persist for docs
    path = os.path.join(os.path.dirname(__file__), "..", ".github", "project-number.txt")
    path = os.path.normpath(path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"{number}\n")
    print(f"\nSeeded/updated {added} items.")
    print(f"Wrote {path} with project number {number}")
    print(f"\nOpen: {url}")
    print(
        "In Project UI: enable Workflows → Auto-add issues/PRs from this repo; "
        "create saved views (Kanban by Status, Quality, Bugs, …)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
