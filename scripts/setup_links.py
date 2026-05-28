#!/usr/bin/env python3
"""Create or print links from local agent tools to shared rules and selected skills."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shlex
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
    note: str | None = None


@dataclass(frozen=True)
class LinkPlan:
    tool: str
    label: str
    source: Path
    target: Path
    is_dir: bool


def split_csv(values: list[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        result.extend(item.strip() for item in value.split(",") if item.strip())
    return result


def env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else default


def managed_rules() -> list[Path]:
    return sorted((ROOT / "rules").glob("*.md"))


def managed_skills() -> list[str]:
    return sorted(path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md"))


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
            "Add a local ~/.claude/CLAUDE.md reference to ~/.claude/AGENTS.md when needed.",
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
            "Add selected skills to local skills.external_dirs. This script does not edit Hermes config.",
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
            "Add selected skills to local skills.load.extraDirs. This script does not edit OpenClaw config.",
        )
    raise ValueError(f"unknown tool: {name}")


def validate_skills(selected: list[str]) -> list[str]:
    if not selected:
        return []
    available = set(managed_skills())
    valid: list[str] = []
    errors: list[str] = []
    for skill in selected:
        if skill.lower() == "all":
            errors.append("Do not use --skills all. Choose only the skills needed on this machine.")
        elif skill not in available:
            errors.append(f"Unknown managed skill: {skill}")
        else:
            valid.append(skill)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
    return valid


def build_plans(tools: list[str], include_rules: bool, selected_skills: list[str]) -> tuple[list[LinkPlan], list[str]]:
    plans: list[LinkPlan] = []
    notes: list[str] = []
    for tool in tools:
        paths = tool_paths(tool)
        if include_rules:
            plans.append(LinkPlan(tool, "entry", ROOT / "AGENTS.md", paths.entry, False))
            for rule in managed_rules():
                plans.append(LinkPlan(tool, f"rule:{rule.name}", rule, paths.rules_dir / rule.name, False))

        if selected_skills:
            if paths.skill_mode == "symlink" and paths.skills_dir is not None:
                for skill in selected_skills:
                    plans.append(LinkPlan(tool, f"skill:{skill}", ROOT / "skills" / skill, paths.skills_dir / skill, True))
            else:
                skill_paths = ", ".join(str((ROOT / "skills" / skill).resolve()) for skill in selected_skills)
                notes.append(f"{tool}: configure selected skills locally instead of symlinking them: {skill_paths}")

        if paths.note:
            notes.append(f"{tool}: {paths.note}")
    return plans, notes


def same_link(target: Path, source: Path) -> bool:
    if not target.is_symlink():
        return False
    return target.resolve(strict=False) == source.resolve(strict=False)


def quote(path: Path) -> str:
    return shlex.quote(str(path))


def link_command(plan: LinkPlan) -> str:
    if os.name == "nt":
        flag = " /D" if plan.is_dir else ""
        return f'cmd /c mklink{flag} "{plan.target}" "{plan.source}"'
    return f"ln -s {quote(plan.source)} {quote(plan.target)}"


def print_plan(plans: list[LinkPlan], notes: list[str]) -> None:
    if not plans and not notes:
        print("Nothing to do.")
        return
    for plan in plans:
        print(f"# {plan.tool} {plan.label}")
        if same_link(plan.target, plan.source):
            print(f"# already linked: {plan.target}")
        elif plan.target.exists() or plan.target.is_symlink():
            print(f"# exists, not changed: {plan.target}")
        else:
            print(link_command(plan))
    for note in notes:
        print(f"# NOTE: {note}")


def apply_plan(plans: list[LinkPlan], notes: list[str]) -> int:
    failures = 0
    for plan in plans:
        if same_link(plan.target, plan.source):
            print(f"OK: {plan.target} already linked")
            continue
        if plan.target.exists() or plan.target.is_symlink():
            print(f"SKIP: {plan.target} exists and was not changed")
            failures += 1
            continue
        plan.target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(plan.source, plan.target, target_is_directory=plan.is_dir)
        except OSError as exc:
            failures += 1
            print(f"ERROR: could not link {plan.target}: {exc}")
            print(f"Run manually if your platform requires elevated symlink permission: {link_command(plan)}")
            continue
        print(f"LINK: {plan.target} -> {plan.source}")

    for note in notes:
        print(f"NOTE: {note}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", action="append", choices=TOOLS, required=True, help="Tool to configure. Repeat as needed.")
    parser.add_argument("--rules", action="store_true", help="Link AGENTS.md and rules/*.md.")
    parser.add_argument("--skills", action="append", help="Comma-separated managed skills to link or report for local config.")
    parser.add_argument("--apply", action="store_true", help="Create links. Without this flag the script only prints the plan.")
    parser.add_argument("--print-only", action="store_true", help="Print commands only. This is the default when --apply is omitted.")
    args = parser.parse_args()

    selected_skills = validate_skills(split_csv(args.skills))
    if not args.rules and not selected_skills:
        parser.error("choose --rules and/or --skills <name>[,<name>]")

    plans, notes = build_plans(args.tool, args.rules, selected_skills)
    if args.apply and not args.print_only:
        return apply_plan(plans, notes)
    print_plan(plans, notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
