#!/usr/bin/env python3
"""Block destructive removals of shared agent workflow files."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


PROTECTED_DELETIONS = {
    "AGENTS.md": "shared agent entry",
    "CODEOWNERS": "repository ownership map",
    "scripts/verify_agent_rules.py": "main verification script",
    ".github/workflows/verify.yml": "CI verification workflow",
}


PROTECTED_PREFIXES = (
    ("rules/", "shared rule file"),
    ("skills/", "managed skill file"),
    ("scripts/", "shared script"),
    (".github/", "GitHub repository automation"),
)


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def changed_files(base: str, head: str) -> list[tuple[str, str, str | None]]:
    output = run_git(["diff", "--name-status", "--find-renames", base, head])
    changes: list[tuple[str, str, str | None]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[1]
        new_path = parts[2] if status.startswith("R") and len(parts) > 2 else None
        changes.append((status, path, new_path))
    return changes


def is_delete(status: str) -> bool:
    return status.startswith("D")


def is_rename(status: str) -> bool:
    return status.startswith("R")


def dangerous_reason(path: str) -> str | None:
    if path in PROTECTED_DELETIONS:
        return PROTECTED_DELETIONS[path]
    if path.startswith("skills/") and path.endswith("/SKILL.md"):
        return "managed skill entry"
    for prefix, reason in PROTECTED_PREFIXES:
        if path.startswith(prefix):
            return reason
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base git revision")
    parser.add_argument("--head", required=True, help="Head git revision")
    args = parser.parse_args()

    if not args.base.strip() or not args.head.strip():
        print("Base and head revisions are required for dangerous deletion checks.", file=sys.stderr)
        return 2

    blocked: list[tuple[str, str]] = []
    for status, path, new_path in changed_files(args.base, args.head):
        if not is_delete(status) and not is_rename(status):
            continue
        reason = dangerous_reason(path)
        if reason:
            display_path = f"{path} -> {new_path}" if new_path else path
            blocked.append((display_path, reason))

    if not blocked:
        print("No dangerous deletions detected.")
        return 0

    print("Dangerous deletions detected:")
    for path, reason in blocked:
        print(f"- {path}: {reason}")
    print()
    print("Deprecate shared skills or rules first. Owner-reviewed removal should use an explicit exception workflow.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
