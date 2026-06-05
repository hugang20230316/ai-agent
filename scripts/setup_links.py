#!/usr/bin/env python3
"""Create or print links from local agent tools to shared rules and selected skills.

Running this script without arguments auto-detects installed agent tools and
links the shared entry plus rules for each detected tool.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import shutil
import shlex
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("codex", "claude", "hermes", "openclaw")
TOOL_COMMANDS = {
    "codex": ("codex",),
    "claude": ("claude",),
    "hermes": ("hermes",),
    "openclaw": ("openclaw",),
}
TOOL_ENV_VARS = {
    "codex": ("CODEX_HOME",),
    "claude": ("CLAUDE_HOME",),
    "hermes": ("HERMES_HOME",),
    "openclaw": ("OPENCLAW_HOME", "OPENCLAW_WORKSPACE"),
}


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


@dataclass(frozen=True)
class TextPlan:
    tool: str
    label: str
    target: Path
    content: str
    required_text: str


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
        )
    raise ValueError(f"unknown tool: {name}")


def detect_tools() -> tuple[list[str], list[str]]:
    tools: list[str] = []
    notes: list[str] = []
    for tool in TOOLS:
        paths = tool_paths(tool)
        env_names = TOOL_ENV_VARS[tool]
        configured_env = [name for name in env_names if os.environ.get(name)]
        commands = TOOL_COMMANDS[tool]
        command = next((name for name in commands if shutil.which(name)), None)

        reason: str | None = None
        if configured_env:
            reason = "environment: " + ", ".join(configured_env)
        elif paths.home.exists():
            reason = f"home exists: {paths.home}"
        elif command:
            reason = f"command on PATH: {command}"

        if reason:
            tools.append(tool)
            notes.append(f"auto: detected {tool} ({reason})")
        else:
            notes.append(f"auto: skipped {tool} (tool home and command were not found)")
    return tools, notes


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


def native_reference_plan(tool: str) -> TextPlan | None:
    paths = tool_paths(tool)
    if tool == "claude":
        return TextPlan(tool, "native:CLAUDE.md", paths.home / "CLAUDE.md", "@AGENTS.md\n", "@AGENTS.md")
    if tool == "hermes":
        return TextPlan(tool, "native:SOUL.md", paths.home / "SOUL.md", "@AGENTS.md\n", "@AGENTS.md")
    return None


def build_plans(tools: list[str], include_rules: bool, selected_skills: list[str]) -> tuple[list[LinkPlan], list[TextPlan], list[str]]:
    plans: list[LinkPlan] = []
    text_plans: list[TextPlan] = []
    notes: list[str] = []
    for tool in tools:
        paths = tool_paths(tool)
        if include_rules:
            plans.append(LinkPlan(tool, "entry", ROOT / "AGENTS.md", paths.entry, False))
            for rule in managed_rules():
                plans.append(LinkPlan(tool, f"rule:{rule.name}", rule, paths.rules_dir / rule.name, False))
            native = native_reference_plan(tool)
            if native is not None:
                text_plans.append(native)

        if selected_skills:
            if paths.skill_mode == "symlink" and paths.skills_dir is not None:
                for skill in selected_skills:
                    plans.append(LinkPlan(tool, f"skill:{skill}", ROOT / "skills" / skill, paths.skills_dir / skill, True))
            else:
                skill_paths = ", ".join(str((ROOT / "skills" / skill).resolve()) for skill in selected_skills)
                notes.append(f"{tool}: configure selected skills locally instead of symlinking them: {skill_paths}")

        if paths.note:
            notes.append(f"{tool}: {paths.note}")
    return plans, text_plans, notes


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


def text_command(plan: TextPlan) -> str:
    if os.name == "nt":
        return f'powershell -NoProfile -Command "Set-Content -Path {quote(plan.target)} -Value {quote(plan.content.rstrip())}"'
    return f"mkdir -p {quote(plan.target.parent)} && printf '%s\\n' {quote(plan.content.rstrip())} > {quote(plan.target)}"


def text_target_references_plan(plan: TextPlan) -> bool:
    if not plan.target.exists():
        return False
    try:
        return plan.required_text in plan.target.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def backup_target(plan: LinkPlan, backup_id: str) -> Path:
    paths = tool_paths(plan.tool)
    try:
        relative_target = plan.target.relative_to(paths.home)
    except ValueError:
        relative_target = Path(plan.target.name)
    backup = paths.home / ".ai-agent-backups" / backup_id / relative_target
    backup.parent.mkdir(parents=True, exist_ok=True)
    os.replace(plan.target, backup)
    return backup


def restore_target(plan: LinkPlan, backup: Path) -> None:
    if backup.exists() and not plan.target.exists() and not plan.target.is_symlink():
        os.replace(backup, plan.target)


def backup_text_target(plan: TextPlan, backup_id: str) -> Path:
    paths = tool_paths(plan.tool)
    try:
        relative_target = plan.target.relative_to(paths.home)
    except ValueError:
        relative_target = Path(plan.target.name)
    backup = paths.home / ".ai-agent-backups" / backup_id / relative_target
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(plan.target, backup)
    return backup


def append_text_plan(plan: TextPlan) -> None:
    existing = plan.target.read_bytes()
    with plan.target.open("ab") as handle:
        if existing and not existing.endswith(b"\n"):
            handle.write(b"\n")
        handle.write(plan.content.encode("utf-8"))


def print_plan(plans: list[LinkPlan], text_plans: list[TextPlan], notes: list[str], replace_existing: bool = False) -> None:
    if not plans and not text_plans and not notes:
        print("Nothing to do.")
        return
    for plan in plans:
        print(f"# {plan.tool} {plan.label}")
        if same_link(plan.target, plan.source):
            print(f"# already linked: {plan.target}")
        elif plan.target.exists() or plan.target.is_symlink():
            if replace_existing:
                paths = tool_paths(plan.tool)
                print(f"# exists, will be backed up under: {paths.home / '.ai-agent-backups'}")
                print(link_command(plan))
            else:
                print(f"# exists, not changed: {plan.target}")
        else:
            print(link_command(plan))
    for plan in text_plans:
        print(f"# {plan.tool} {plan.label}")
        if text_target_references_plan(plan):
            print(f"# already references {plan.required_text}: {plan.target}")
        elif plan.target.is_symlink():
            print(f"# exists, not changed: {plan.target}")
            print(f"# add this line manually if it is safe for this machine: {plan.content.rstrip()}")
        elif plan.target.exists():
            paths = tool_paths(plan.tool)
            print(f"# exists, will be backed up under: {paths.home / '.ai-agent-backups'}")
            print(f"# append this line: {plan.content.rstrip()}")
        else:
            print(text_command(plan))
    for note in notes:
        print(f"# NOTE: {note}")


def apply_plan(plans: list[LinkPlan], text_plans: list[TextPlan], notes: list[str], replace_existing: bool = False) -> int:
    failures = 0
    backup_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    for plan in plans:
        backup: Path | None = None
        if same_link(plan.target, plan.source):
            print(f"OK: {plan.target} already linked")
            continue
        if plan.target.exists() or plan.target.is_symlink():
            if not replace_existing:
                print(f"SKIP: {plan.target} exists and was not changed")
                failures += 1
                continue
            try:
                backup = backup_target(plan, backup_id)
            except OSError as exc:
                failures += 1
                print(f"ERROR: could not back up {plan.target}: {exc}")
                continue
            print(f"BACKUP: {plan.target} -> {backup}")
        plan.target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(plan.source, plan.target, target_is_directory=plan.is_dir)
        except OSError as exc:
            if backup is not None:
                try:
                    restore_target(plan, backup)
                    print(f"RESTORE: {plan.target}")
                except OSError as restore_exc:
                    print(f"ERROR: could not restore {plan.target}: {restore_exc}")
            failures += 1
            print(f"ERROR: could not link {plan.target}: {exc}")
            print(f"Run manually if your platform requires elevated symlink permission: {link_command(plan)}")
            continue
        print(f"LINK: {plan.target} -> {plan.source}")

    for plan in text_plans:
        if text_target_references_plan(plan):
            print(f"OK: {plan.target} already references {plan.required_text}")
            continue
        if plan.target.is_symlink():
            print(f"SKIP: {plan.target} is a symlink and was not changed; add {plan.content.rstrip()} manually after reviewing it")
            failures += 1
            continue
        if plan.target.exists():
            if not plan.target.is_file():
                print(f"SKIP: {plan.target} exists and is not a regular file")
                failures += 1
                continue
            try:
                backup = backup_text_target(plan, backup_id)
                append_text_plan(plan)
            except OSError as exc:
                failures += 1
                print(f"ERROR: could not update {plan.target}: {exc}")
                continue
            print(f"BACKUP: {plan.target} -> {backup}")
            print(f"APPEND: {plan.target}")
            continue
        plan.target.parent.mkdir(parents=True, exist_ok=True)
        try:
            plan.target.write_text(plan.content, encoding="utf-8")
        except OSError as exc:
            failures += 1
            print(f"ERROR: could not create {plan.target}: {exc}")
            continue
        print(f"WRITE: {plan.target}")

    for note in notes:
        print(f"NOTE: {note}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--tool", action="append", choices=TOOLS, help="Tool to configure. Repeat as needed.")
    mode.add_argument("--auto", action="store_true", help="Detect local tools and configure shared rules. This is the default with no --tool.")
    parser.add_argument("--rules", action="store_true", help="Link AGENTS.md and rules/*.md.")
    parser.add_argument("--skills", action="append", help="Comma-separated managed skills to link or report for local config.")
    parser.add_argument("--apply", action="store_true", help="Create links. In auto mode this is the default unless --print-only is used.")
    parser.add_argument("--print-only", action="store_true", help="Print commands only. This is the default when --apply is omitted.")
    parser.add_argument("--replace-existing", action="store_true", help="Back up existing targets before linking. Auto mode enables this for shared rules.")
    args = parser.parse_args()

    selected_skills = validate_skills(split_csv(args.skills))
    if args.tool:
        selected_tools = args.tool
        include_rules = args.rules
        auto_notes: list[str] = []
        should_apply = args.apply and not args.print_only
        replace_existing = args.replace_existing
        if not include_rules and not selected_skills:
            parser.error("choose --rules and/or --skills <name>[,<name>]")
    else:
        selected_tools, auto_notes = detect_tools()
        include_rules = True
        should_apply = not args.print_only
        replace_existing = True
        if not selected_tools:
            for note in auto_notes:
                print(f"NOTE: {note}")
            print("ERROR: no supported agent tool was detected. Install a tool or pass --tool explicitly.", file=sys.stderr)
            return 1

    plans, text_plans, notes = build_plans(selected_tools, include_rules, selected_skills)
    notes = auto_notes + notes
    if should_apply:
        return apply_plan(plans, text_plans, notes, replace_existing=replace_existing)
    print_plan(plans, text_plans, notes, replace_existing=replace_existing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
