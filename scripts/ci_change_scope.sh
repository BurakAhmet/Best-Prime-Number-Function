#!/usr/bin/env bash
# Emit code= / full= for GitHub Actions $GITHUB_OUTPUT.
# - push to main → full matrix + all heavy jobs
# - pull_request with engine/tooling paths → PR-lite suite
# - pull_request docs/meta only → required check stubs only
set -euo pipefail

out="${1:-${GITHUB_OUTPUT:-/dev/stdout}}"
event="${GITHUB_EVENT_NAME:-}"

write() {
  echo "$1" >>"$out"
}

# Paths that need the primality / packaging suite.
CODE_RE='^(best_prime/|is_prime_data/|tests/|scripts/|native/|include/|benchmarks/|examples/|pkgconfig/|pyproject\.toml|setup\.py|MANIFEST\.in|Dockerfile|\.github/workflows/|\.github/dependabot\.yml)'

if [[ "$event" == "push" ]]; then
  write "code=true"
  write "full=true"
  exit 0
fi

# pull_request (and anything else): never run the full multi-OS matrix.
write "full=false"

base_ref="${GITHUB_BASE_REF:-main}"
# Shallow PR checkouts need the merge base; fetch base branch tip.
git fetch --no-tags --depth=1 origin "$base_ref" 2>/dev/null || true

if git rev-parse --verify "origin/${base_ref}" >/dev/null 2>&1; then
  files=$(git diff --name-only "origin/${base_ref}...HEAD" || true)
else
  files=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || true)
fi

if [[ -z "${files//[$'\n']/}" ]]; then
  # Empty diff: treat as code so we never silently skip on broken fetch.
  write "code=true"
  exit 0
fi

if echo "$files" | grep -qE "$CODE_RE"; then
  write "code=true"
else
  write "code=false"
fi
