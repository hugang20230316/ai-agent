#!/usr/bin/env python3
"""Inspect local setup for the shared agent workflow without changing files."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import platform
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("codex", "claude", "hermes", "openclaw")


@dataclass(frozen=True)
class ToolPaths:
    name: str
    home: Path
    entry: Path
    rules_dir: Path
    skills_dir: Path | None
    skill_mode: str
    native_entry_note: str | None = None


@dataclass
class Check:
    level: str
    area: str
    message: str


def display_path(path: Path) -> str:
    home = Path.home()
    absolute = path.expanduser().absolute()
    try:
        return "~/" + str(absolute.relative_to(home.resolve()))
    except ValueError:
        return str(absolute)


def split_csv(values: list[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        result.extend(item.strip() for item in value.split(",") if item.strip())
    return result


def managed_rules() -> list[Path]:
    return sorted((ROOT / "rules").glob("*.md"))


def managed_skills() -> list[str]:
    return sorted(path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md"))


def env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else default


def tool_paths(name: str) -> ToolPaths:
    home = Path.home()
    if name == "codex":
        tool_home = env_path("CODEX_HOME", home / ".codex")
        return ToolPaths(name, tool_home, tool_home / "AGENTS.md", tool_home / "rules", tool_home / "skills", "symlink")
    if name == "claude":
        tool_home = env_path("CLAUDE_HOME", home / ".claude")
        return ToolPaths(
            name,
            tool_home,
            tool_home / "AGENTS.md",
            tool_home / "rules",
            tool_home / "skills",
            "symlink",
            native_entry_note="~/.claude/CLAUDE.md should reference ~/.claude/AGENTS.md",
        )
    if name == "hermes":
        tool_home = env_path("HERMES_HOME", home / ".hermes")
        return ToolPaths(
            name,
            tool_home,
            tool_home / "AGENTS.md",
            tool_home / "rules",
            None,
            "local-config",
            native_entry_note="$HERMES_HOME/SOUL.md should reference $HERMES_HOME/AGENTS.md",
        )
    if name == "openclaw":
        openclaw_home = env_path("OPENCLAW_HOME", home / ".openclaw")
        workspace = env_path("OPENCLAW_WORKSPACE", openclaw_home / "workspace")
        return ToolPaths(
            name,
            workspace,
            workspace / "AGENTS.md",
            workspace / "rules",
            None,
            "local-config",
            native_entry_note="OpenClaw skills should be listed in local skills.load.extraDirs",
        )
    raise ValueError(f"unknown tool: {name}")


def same_link(target: Path, source: Path) -> bool:
    if not target.is_symlink():
        return False
    return target.resolve(strict=False) == source.resolve(strict=False)


def check_repo_structure(checks: list[Check]) -> None:
    required = [
        ROOT / "AGENTS.md",
        ROOT / "rules",
        ROOT / "skills",
        ROOT / "scripts" / "verify_agent_rules.py",
        ROOT / "scripts" / "check_dangerous_deletions.py",
    ]
    for path in required:
        if path.exists():
            checks.append(Check("OK", "repo", f"{path.relative_to(ROOT)} exists"))
        else:
            checks.append(Check("ERROR", "repo", f"{path.relative_to(ROOT)} is missing"))

    if not managed_rules():
        checks.append(Check("ERROR", "repo", "rules/*.md is empty"))
    if not managed_skills():
        checks.append(Check("WARN", "repo", "skills/*/SKILL.md is empty"))


def check_link(checks: list[Check], area: str, target: Path, source: Path) -> None:
    if same_link(target, source):
        checks.append(Check("OK", area, f"{display_path(target)} -> {source.relative_to(ROOT)}"))
        return
    if not target.exists() and not target.is_symlink():
        checks.append(Check("WARN", area, f"{display_path(target)} is not linked"))
        return
    checks.append(Check("WARN", area, f"{display_path(target)} exists but does not point to {source.relative_to(ROOT)}"))


def check_tool_links(checks: list[Check], selected_tools: list[str], selected_skills: list[str]) -> None:
    for name in selected_tools:
        paths = tool_paths(name)
        check_link(checks, name, paths.entry, ROOT / "AGENTS.md")
        for rule in managed_rules():
            check_link(checks, name, paths.rules_dir / rule.name, rule)

        if selected_skills and paths.skill_mode == "symlink" and paths.skills_dir is not None:
            for skill in selected_skills:
                check_link(checks, name, paths.skills_dir / skill, ROOT / "skills" / skill)
        elif selected_skills:
            checks.append(
                Check(
                    "INFO",
                    name,
                    f"skills are configured through local config; selected skills: {', '.join(selected_skills)}",
                )
            )

        if paths.native_entry_note:
            checks.append(Check("INFO", name, paths.native_entry_note))


def validate_selected_skills(skills: list[str], checks: list[Check]) -> list[str]:
    available = set(managed_skills())
    selected: list[str] = []
    for skill in skills:
        if skill.lower() == "all":
            checks.append(Check("ERROR", "skills", "do not use 'all'; choose only the skills needed on this machine"))
        elif skill not in available:
            checks.append(Check("ERROR", "skills", f"unknown managed skill: {skill}"))
        else:
            selected.append(skill)
    if not selected:
        checks.append(Check("INFO", "skills", "no skills selected; shared skills are opt-in"))
    else:
        checks.append(Check("INFO", "skills", "selected skills: " + ", ".join(selected)))
    return selected


def run_verify(checks: list[Check]) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_agent_rules.py")],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0:
        checks.append(Check("OK", "verify", "scripts/verify_agent_rules.py passed"))
    else:
        checks.append(Check("ERROR", "verify", "scripts/verify_agent_rules.py failed"))
        if result.stderr.strip():
            checks.append(Check("INFO", "verify", result.stderr.strip().splitlines()[-1]))
        elif result.stdout.strip():
            checks.append(Check("INFO", "verify", result.stdout.strip().splitlines()[-1]))


def print_checks(checks: list[Check]) -> None:
    width = max((len(check.level) for check in checks), default=4)
    for check in checks:
        print(f"{check.level:<{width}}  {check.area}: {check.message}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", action="append", choices=TOOLS, help="Tool to inspect. Repeat or omit for all tools.")
    parser.add_argument("--skills", action="append", help="Comma-separated managed skills to inspect. Skills are opt-in.")
    parser.add_argument("--no-verify", action="store_true", help="Skip scripts/verify_agent_rules.py.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when warnings are present.")
    args = parser.parse_args()

    checks: list[Check] = [
        Check("INFO", "system", f"{platform.system()} {platform.release()}"),
        Check("INFO", "repo", display_path(ROOT)),
    ]
    selected_tools = args.tool or list(TOOLS)

    check_repo_structure(checks)
    selected_skills = validate_selected_skills(split_csv(args.skills), checks)
    check_tool_links(checks, selected_tools, selected_skills)
    if not args.no_verify:
        run_verify(checks)

    print_checks(checks)

    has_errors = any(check.level == "ERROR" for check in checks)
    has_warnings = any(check.level == "WARN" for check in checks)
    if has_errors or (args.strict and has_warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
