#!/usr/bin/env python3
"""Fail if the tree introduces forbidden patterns (stochastic MR, prime libs, etc.)."""
from __future__ import annotations

import argparse
import re
import sys
import tokenize
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Patterns that violate project restrictions in implementation code
FORBIDDEN = [
    (re.compile(r"\brandom\.(random|randint|choice|getrandbits)\b"), "use of random.* (non-deterministic)"),
    (re.compile(r"\bnumpy\.random\b"), "numpy.random (non-deterministic)"),
    (re.compile(r"\bsympy\.isprime\b"), "sympy.isprime forbidden as engine"),
    (re.compile(r"\bprimesieve\b"), "primesieve forbidden"),
    (re.compile(r"\bprobab(le|ilistic)?\s*prime\b", re.I), "probabilistic prime wording in code"),
    (re.compile(r"\bmiller[_-]?rabin\b", re.I), "Miller-Rabin (stochastic / forbidden as engine)"),
    (re.compile(r"\bmillerrabin\b", re.I), "MillerRabin forbidden as engine"),
]

# Allow in docs / comments in tests describing why we reject MR
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", ".eggs"}
SKIP_FILES = {"check_restrictions.py"}  # this file
ALLOW_PATH_SUBSTRINGS = (
    "README",
    "CONTRIBUTING",
    "PROJECT_BOARD",
    "ALGORITHM_HISTORY",
    "docs/wiki",
    "docs/guide",
    "docs/theme",
    "mkdocs.yml",
    ".readthedocs.yaml",
    "copilot-instructions",
    "AGENT_BRIEFING",
    "test_is_prime.py",  # may mention Carmichael / MR context
    "test_properties.py",
    "benchmarks/",
    ".github/workflows/",  # policy text in agents / potd / auto-merge
    "ISSUE_TEMPLATE",
    "PULL_REQUEST_TEMPLATE",
    "CODE_OF_CONDUCT",
    "SECURITY.md",
)


def allowed(path: Path) -> bool:
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    if path.name in SKIP_FILES:
        return True
    return any(s in rel for s in ALLOW_PATH_SUBSTRINGS)


def code_only_text(path: Path, text: str) -> str:
    """For .py files, blank out comments and string/docstring literals so docs may mention bans."""
    if path.suffix != ".py":
        return text
    try:
        tokens = list(tokenize.tokenize(BytesIO(text.encode("utf-8")).readline))
    except tokenize.TokenError:
        return text
    out = bytearray(text.encode("utf-8"))
    for tok in tokens:
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            # Preserve newlines so line numbers stay aligned
            start = tok.start[0], tok.start[1]
            # Map (line, col) to byte offset via line starts
            pass
    # Rebuild from tokens: keep non-comment/non-string as-is, replace others with spaces/newlines
    lines = text.splitlines(keepends=True)
    if not lines:
        return text
    # Character offsets
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    chars = list(text)
    for tok in tokens:
        if tok.type not in (tokenize.COMMENT, tokenize.STRING):
            continue
        sline, scol = tok.start
        eline, ecol = tok.end
        start = offsets[sline - 1] + scol
        end = offsets[eline - 1] + ecol
        for i in range(start, min(end, len(chars))):
            if chars[i] not in "\r\n":
                chars[i] = " "
    return "".join(chars)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root: Path = args.root
    bad = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(p in SKIP_DIRS for p in path.parts):
            continue
        if path.suffix not in {".py", ".yml", ".yaml", ".md", ".toml", ".sh"}:
            continue
        if allowed(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scan = code_only_text(path, text)
        for rx, why in FORBIDDEN:
            for m in rx.finditer(scan):
                line_no = text.count("\n", 0, m.start()) + 1
                # Prefer matched text from original for display
                snippet = text[m.start() : m.end()]
                bad.append((path.relative_to(root), line_no, why, snippet or m.group(0)))

    if bad:
        print("Restriction linter FAILED:")
        for rel, ln, why, g in bad:
            print(f"  {rel}:{ln}: {why}  (matched {g!r})")
        print("\nSee docs/PROJECT_BOARD.md and Project restrictions.")
        return 1
    print("Restriction linter PASSED (no forbidden patterns in implementation paths).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
