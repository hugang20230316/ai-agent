#!/usr/bin/env python3
"""Cross-platform timer inventory and control for AI workflow jobs."""

from __future__ import annotations

import argparse
import json
import os
import platform
import plistlib
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


AI_ROOTS = (
    ".codex",
    ".openclaw",
    ".claude",
    ".hermes",
    ".agents",
    ".agent-browser",
    "ai-agent",
)

STRONG_AI_TERMS = (
    "codex",
    "openclaw",
    "hermes",
    "claude",
    "obsidian",
    "mcp",
)

WEAK_AI_TERMS = (
    "agent",
    "automation",
    "browser",
    "gateway",
    "knowledge",
    "log-sync",
    "sync",
)

COMMON_NOISE_TERMS = (
    "apple.",
    "chrome",
    "google",
    "keystone",
    "microsoft autoupdate",
    "softwareupdate",
    "updater",
    "update",
)

USER_LAUNCH_AGENTS = Path.home() / "Library/LaunchAgents"
SUPPORTED_WRITE_BACKENDS = {"launchd", "windows-task-scheduler"}


@dataclass
class TimerTrigger:
    """Normalized trigger metadata."""

    type: str = "manual"
    interval_seconds: int | None = None
    calendar: Any = None
    run_at_load: bool = False
    watch_paths: list[str] = field(default_factory=list)
    schedule: str | None = None


@dataclass
class TimerAction:
    """Normalized command metadata."""

    command: str | None = None
    args: list[str] = field(default_factory=list)
    working_directory: str | None = None
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class TimerLogs:
    """Normalized log metadata."""

    stdout: str | None = None
    stderr: str | None = None
    history: str | None = None


@dataclass
class TimerHealth:
    """Normalized runtime health metadata."""

    last_run_at: str | None = None
    next_run_at: str | None = None
    last_exit_code: int | None = None
    last_error: str | None = None


@dataclass
class TimerCapabilities:
    """Supported operations for the current backend and scope."""

    can_create: bool = False
    can_update: bool = False
    can_delete: bool = False
    can_start: bool = False
    can_stop: bool = False
    can_restart: bool = False
    can_enable: bool = False
    can_disable: bool = False
    can_report_pid: bool = False
    can_report_logs: bool = False


@dataclass
class TimerJob:
    """Normalized timer record used by all platform backends."""

    id: str
    native_id: str
    name: str
    platform: str
    backend: str
    scope: str
    category: str
    visible_by_default: bool
    filter_reasons: list[str]
    tags: list[str]
    source: str | None
    enabled: bool | None
    loaded: bool | None
    running: bool | None
    pid: int | None
    trigger: TimerTrigger
    action: TimerAction
    logs: TimerLogs
    health: TimerHealth
    capabilities: TimerCapabilities


class TimerError(RuntimeError):
    """User-facing command error."""


def run_command(args: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    """Run a command and capture text output."""

    try:
        return subprocess.run(
            args,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise TimerError(f"command not found: {args[0]}") from exc
    except PermissionError as exc:
        raise TimerError(f"permission denied: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise TimerError(f"command timed out: {' '.join(args)}") from exc


def normalize_text(value: Any) -> str:
    """Return a lowercase searchable string for metadata matching."""

    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return " ".join(normalize_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{k} {normalize_text(v)}" for k, v in value.items())
    return str(value).lower()


def stable_id(backend: str, scope: str, native_id: str) -> str:
    """Build a stable cross-backend timer id."""

    return f"{backend}:{scope}:{native_id}"


def humanize_label(label: str) -> str:
    """Create a short display name from a timer identifier."""

    base = re.sub(r"^com\.hugang\.", "", label)
    base = re.sub(r"^ai\.", "ai.", base)
    words = re.split(r"[._:/\\-]+", base)
    return " ".join(word.upper() if word in {"ai", "mcp"} else word.capitalize() for word in words if word)


def infer_tags(*parts: Any) -> list[str]:
    """Infer tags from strong and weak AI workflow metadata."""

    haystack = normalize_text(parts)
    tags: list[str] = []
    for keyword in (*STRONG_AI_TERMS, *WEAK_AI_TERMS):
        if keyword in haystack and keyword not in tags:
            tags.append(keyword)
    return tags


def ai_visibility(*parts: Any) -> tuple[bool, list[str]]:
    """Decide default AI workflow visibility from strong evidence."""

    haystack = normalize_text(parts)
    reasons: list[str] = []
    for root in AI_ROOTS:
        if f"/{root}/" in haystack or f"\\{root}\\" in haystack or root in haystack.split():
            reasons.append(f"ai-root:{root}")
    for term in STRONG_AI_TERMS:
        if term in haystack:
            reasons.append(f"strong-term:{term}")
    weak_hits = [term for term in WEAK_AI_TERMS if term in haystack]
    if weak_hits and reasons:
        reasons.extend(f"weak-term:{term}" for term in weak_hits)
    if not reasons and any(term in haystack for term in COMMON_NOISE_TERMS):
        reasons.append("hidden-noise")
    visible = any(reason.startswith(("ai-root:", "strong-term:")) for reason in reasons)
    return visible, reasons


def timer_to_dict(job: TimerJob) -> dict[str, Any]:
    """Convert a timer object to plain JSON-safe data."""

    return asdict(job)


def print_result(payload: Any, as_json: bool) -> None:
    """Print JSON or compact human-readable output."""

    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if isinstance(payload, list):
        for item in payload:
            schedule = item.get("trigger", {}).get("schedule") or item.get("trigger", {}).get("type")
            state = "running" if item.get("running") else "stopped"
            enabled = "enabled" if item.get("enabled") else "disabled"
            print(f"{item['id']}\t{state}\t{enabled}\t{item['backend']}\t{schedule}")
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def launchd_paths() -> list[tuple[Path, str]]:
    """Return launchd search paths and their normalized scopes."""

    return [
        (USER_LAUNCH_AGENTS, "user"),
        (Path("/Library/LaunchAgents"), "system"),
        (Path("/Library/LaunchDaemons"), "system"),
    ]


def launchctl_domain(scope: str) -> str:
    """Return the launchctl domain for a timer scope."""

    if scope == "system":
        return "system"
    return f"gui/{os.getuid()}"


def parse_launchd_trigger(plist: dict[str, Any]) -> TimerTrigger:
    """Normalize launchd trigger fields."""

    watch_paths = [str(item) for item in plist.get("WatchPaths", [])]
    if "StartInterval" in plist:
        interval = int(plist["StartInterval"])
        return TimerTrigger(
            type="interval",
            interval_seconds=interval,
            run_at_load=bool(plist.get("RunAtLoad", False)),
            watch_paths=watch_paths,
            schedule=f"every {interval}s",
        )
    if "StartCalendarInterval" in plist:
        calendar = plist["StartCalendarInterval"]
        return TimerTrigger(
            type="calendar",
            calendar=calendar,
            run_at_load=bool(plist.get("RunAtLoad", False)),
            watch_paths=watch_paths,
            schedule=f"calendar {calendar}",
        )
    if watch_paths:
        return TimerTrigger(
            type="watch_path",
            run_at_load=bool(plist.get("RunAtLoad", False)),
            watch_paths=watch_paths,
            schedule=f"watch {', '.join(watch_paths)}",
        )
    if plist.get("RunAtLoad"):
        return TimerTrigger(type="login", run_at_load=True, schedule="run at load")
    return TimerTrigger(type="manual", schedule="manual")


def build_launchd_trigger(definition: dict[str, Any]) -> dict[str, Any]:
    """Build launchd trigger keys from a normalized definition."""

    trigger = definition.get("trigger", {})
    output: dict[str, Any] = {}
    trigger_type = trigger.get("type", "manual")
    if trigger.get("run_at_load"):
        output["RunAtLoad"] = True
    if trigger_type == "interval":
        interval = int(trigger["interval_seconds"])
        if interval < 1:
            raise TimerError("trigger.interval_seconds must be positive")
        output["StartInterval"] = interval
    elif trigger_type == "calendar":
        output["StartCalendarInterval"] = trigger["calendar"]
    elif trigger_type == "watch_path":
        output["WatchPaths"] = [str(item) for item in trigger.get("watch_paths", [])]
    elif trigger_type in {"manual", "login"}:
        pass
    else:
        raise TimerError(f"unsupported launchd trigger type: {trigger_type}")
    return output


def parse_launchd_action(plist: dict[str, Any]) -> TimerAction:
    """Normalize launchd action fields."""

    args = [str(item) for item in plist.get("ProgramArguments", [])]
    program = str(plist.get("Program") or (args[0] if args else ""))
    return TimerAction(
        command=program or None,
        args=args[1:] if args else [],
        working_directory=plist.get("WorkingDirectory"),
        env={str(k): str(v) for k, v in plist.get("EnvironmentVariables", {}).items()},
    )


def build_launchd_plist(definition: dict[str, Any], existing_label: str | None = None) -> dict[str, Any]:
    """Build a user-level launchd plist from a normalized timer definition."""

    label = str(definition.get("native_id") or definition.get("label") or definition.get("id") or existing_label or "")
    if label.startswith("launchd:"):
        label = label.split(":", 2)[-1]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]+", label):
        raise TimerError("launchd label must contain only letters, numbers, dot, underscore, and dash")
    action = definition.get("action", {})
    command = action.get("command")
    if not command:
        raise TimerError("action.command is required")
    program_args = [str(command), *[str(arg) for arg in action.get("args", [])]]
    plist: dict[str, Any] = {
        "Label": label,
        "ProgramArguments": program_args,
    }
    plist.update(build_launchd_trigger(definition))
    if action.get("working_directory"):
        plist["WorkingDirectory"] = str(action["working_directory"])
    if action.get("env"):
        plist["EnvironmentVariables"] = {str(k): str(v) for k, v in action["env"].items()}
    logs = definition.get("logs", {})
    if logs.get("stdout"):
        plist["StandardOutPath"] = str(logs["stdout"])
    if logs.get("stderr"):
        plist["StandardErrorPath"] = str(logs["stderr"])
    return plist


def parse_launchd_job(path: Path, scope: str) -> TimerJob | None:
    """Read a launchd plist and return a normalized timer job."""

    try:
        with path.open("rb") as handle:
            plist = plistlib.load(handle)
    except Exception:
        return None
    label = str(plist.get("Label") or path.stem)
    action = parse_launchd_action(plist)
    trigger = parse_launchd_trigger(plist)
    logs = TimerLogs(
        stdout=plist.get("StandardOutPath"),
        stderr=plist.get("StandardErrorPath"),
    )
    visible, reasons = ai_visibility(label, path, action.command, action.args, action.working_directory, action.env)
    tags = infer_tags(label, path, action.command, action.args, action.working_directory, action.env)
    user_owned_source = scope == "user" and path.parent == USER_LAUNCH_AGENTS and os.access(path, os.W_OK)
    caps = TimerCapabilities(
        can_create=scope == "user",
        can_update=user_owned_source,
        can_delete=user_owned_source,
        can_start=scope == "user",
        can_stop=scope == "user",
        can_restart=scope == "user",
        can_enable=scope == "user",
        can_disable=scope == "user",
        can_report_pid=True,
        can_report_logs=bool(logs.stdout or logs.stderr),
    )
    return TimerJob(
        id=stable_id("launchd", scope, label),
        native_id=label,
        name=humanize_label(label),
        platform="macos",
        backend="launchd",
        scope=scope,
        category="ai-workflow" if visible else "system-or-app",
        visible_by_default=visible,
        filter_reasons=reasons,
        tags=tags,
        source=str(path),
        enabled=True,
        loaded=None,
        running=None,
        pid=None,
        trigger=trigger,
        action=action,
        logs=logs,
        health=TimerHealth(),
        capabilities=caps,
    )


def enrich_launchd_status(job: TimerJob) -> TimerJob:
    """Attach runtime status from launchctl when available."""

    domain = launchctl_domain(job.scope)
    result = run_command(["launchctl", "print", f"{domain}/{job.native_id}"], timeout=10)
    output = result.stdout + result.stderr
    if result.returncode != 0:
        job.loaded = False
        job.running = False
        job.health.last_error = output.strip() or None
        return job
    job.loaded = True
    pid_match = re.search(r"\bpid\s*=\s*(\d+)", output)
    if not pid_match:
        service_match = re.search(r"^\s*(\d+)\s+[-\d]+\s+" + re.escape(job.native_id), output, re.MULTILINE)
        pid_match = service_match
    if pid_match:
        pid = int(pid_match.group(1))
        job.pid = pid if pid > 0 else None
    job.running = job.pid is not None
    exit_match = re.search(r"last exit code\s*=\s*(-?\d+)", output, re.IGNORECASE)
    if exit_match:
        job.health.last_exit_code = int(exit_match.group(1))
    return job


def list_launchd_jobs(include_all: bool) -> list[TimerJob]:
    """List launchd jobs from local plist search paths."""

    jobs: list[TimerJob] = []
    for directory, scope in launchd_paths():
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.plist")):
            job = parse_launchd_job(path, scope)
            if job and (include_all or job.visible_by_default):
                jobs.append(enrich_launchd_status(job))
    return jobs


def readonly_caps() -> TimerCapabilities:
    """Return read-only capabilities for supplemental backends."""

    return TimerCapabilities()


def list_crontab_jobs(include_all: bool) -> list[TimerJob]:
    """List current user crontab entries as read-only timer jobs."""

    if shutil.which("crontab") is None:
        return []
    try:
        result = run_command(["crontab", "-l"], timeout=10)
    except TimerError:
        return []
    if result.returncode != 0:
        return []
    jobs: list[TimerJob] = []
    for index, line in enumerate(result.stdout.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 5)
        if len(parts) < 6:
            continue
        schedule = " ".join(parts[:5])
        command = parts[5]
        native_id = str(index)
        visible, reasons = ai_visibility(command)
        if not include_all and not visible:
            continue
        jobs.append(
            TimerJob(
                id=stable_id("cron", "user", native_id),
                native_id=native_id,
                name=f"Crontab {index}",
                platform="macos",
                backend="cron",
                scope="user",
                category="ai-workflow" if visible else "system-or-app",
                visible_by_default=visible,
                filter_reasons=reasons,
                tags=infer_tags(command),
                source="user crontab",
                enabled=True,
                loaded=True,
                running=None,
                pid=None,
                trigger=TimerTrigger(type="calendar", schedule=schedule),
                action=TimerAction(command=command),
                logs=TimerLogs(),
                health=TimerHealth(),
                capabilities=readonly_caps(),
            )
        )
    return jobs


def list_at_jobs(include_all: bool) -> list[TimerJob]:
    """List at queue entries as read-only timer jobs."""

    if shutil.which("atq") is None:
        return []
    try:
        result = run_command(["atq"], timeout=10)
    except TimerError:
        return []
    if result.returncode != 0:
        return []
    jobs: list[TimerJob] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        native_id = parts[0]
        visible, reasons = ai_visibility(stripped)
        if not include_all and not visible:
            continue
        jobs.append(
            TimerJob(
                id=stable_id("at", "user", native_id),
                native_id=native_id,
                name=f"At {native_id}",
                platform="macos",
                backend="at",
                scope="user",
                category="ai-workflow" if visible else "system-or-app",
                visible_by_default=visible,
                filter_reasons=reasons,
                tags=infer_tags(stripped),
                source="at queue",
                enabled=True,
                loaded=True,
                running=False,
                pid=None,
                trigger=TimerTrigger(type="calendar", schedule=stripped),
                action=TimerAction(),
                logs=TimerLogs(),
                health=TimerHealth(),
                capabilities=readonly_caps(),
            )
        )
    return jobs


def list_brew_services(include_all: bool) -> list[TimerJob]:
    """List Homebrew services as read-only timer jobs."""

    brew = shutil.which("brew")
    if brew is None:
        return []
    try:
        result = run_command([brew, "services", "list", "--json"], timeout=20)
    except TimerError:
        return []
    if result.returncode != 0:
        return []
    try:
        services = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    jobs: list[TimerJob] = []
    for item in services:
        name = str(item.get("name", ""))
        visible, reasons = ai_visibility(name, item)
        if not include_all and not visible:
            continue
        status = str(item.get("status", "unknown"))
        scope = str(item.get("user") or "user")
        jobs.append(
            TimerJob(
                id=stable_id("brew-services", scope, name),
                native_id=name,
                name=f"Brew {humanize_label(name)}",
                platform="macos",
                backend="brew-services",
                scope=scope,
                category="ai-workflow" if visible else "system-or-app",
                visible_by_default=visible,
                filter_reasons=reasons,
                tags=infer_tags(name, item),
                source=item.get("file"),
                enabled=status != "none",
                loaded=status != "none",
                running=status == "started",
                pid=None,
                trigger=TimerTrigger(type="service", schedule=status),
                action=TimerAction(command=name),
                logs=TimerLogs(),
                health=TimerHealth(last_error=item.get("error")),
                capabilities=readonly_caps(),
            )
        )
    return jobs


def powershell_json(command: str) -> Any:
    """Run PowerShell and parse JSON output."""

    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        raise TimerError("PowerShell is required for Windows scheduled task support")
    result = run_command([executable, "-NoProfile", "-Command", command], timeout=30)
    if result.returncode != 0:
        raise TimerError(result.stderr.strip() or result.stdout.strip())
    text = result.stdout.strip()
    if not text:
        return []
    return json.loads(text)


def windows_list_tasks(include_all: bool) -> list[TimerJob]:
    """List Windows Scheduled Tasks."""

    ps = (
        "Get-ScheduledTask | Select-Object TaskName,TaskPath,State,"
        "@{Name='Actions';Expression={$_.Actions | ConvertTo-Json -Compress}},"
        "@{Name='Triggers';Expression={$_.Triggers | ConvertTo-Json -Compress}} "
        "| ConvertTo-Json -Depth 6"
    )
    data = powershell_json(ps)
    if isinstance(data, dict):
        data = [data]
    jobs: list[TimerJob] = []
    for item in data:
        path = str(item.get("TaskPath") or "\\")
        name = str(item.get("TaskName") or "")
        native_id = f"{path}{name}"
        visible, reasons = ai_visibility(native_id, item)
        if not include_all and not visible:
            continue
        state = str(item.get("State") or "Unknown")
        scope = "system" if path.lower().startswith("\\microsoft\\") else "user"
        caps = TimerCapabilities(
            can_create=scope == "user",
            can_update=scope == "user",
            can_delete=scope == "user",
            can_start=scope == "user",
            can_stop=scope == "user",
            can_restart=scope == "user",
            can_enable=scope == "user",
            can_disable=scope == "user",
            can_report_pid=False,
            can_report_logs=True,
        )
        jobs.append(
            TimerJob(
                id=stable_id("windows-task-scheduler", scope, native_id),
                native_id=native_id,
                name=humanize_label(name),
                platform="windows",
                backend="windows-task-scheduler",
                scope=scope,
                category="ai-workflow" if visible else "system-or-app",
                visible_by_default=visible,
                filter_reasons=reasons,
                tags=infer_tags(native_id, item),
                source=path,
                enabled=state.lower() != "disabled",
                loaded=True,
                running=state.lower() == "running",
                pid=None,
                trigger=TimerTrigger(type="scheduled-task", schedule=str(item.get("Triggers"))),
                action=TimerAction(command=str(item.get("Actions") or "")),
                logs=TimerLogs(history="Task Scheduler History"),
                health=TimerHealth(),
                capabilities=caps,
            )
        )
    return jobs


def list_jobs(include_all: bool) -> list[TimerJob]:
    """List timers for the current platform."""

    system = platform.system()
    if system == "Darwin":
        jobs = list_launchd_jobs(include_all)
        jobs.extend(list_crontab_jobs(include_all))
        jobs.extend(list_at_jobs(include_all))
        jobs.extend(list_brew_services(include_all))
        return sorted(jobs, key=lambda job: (job.backend, job.scope, job.native_id))
    if system == "Windows":
        return sorted(windows_list_tasks(include_all), key=lambda job: job.id)
    raise TimerError(f"unsupported platform: {system}")


def find_job(timer_id: str, include_all: bool = True) -> TimerJob:
    """Find a timer by stable id or native id."""

    matches = [job for job in list_jobs(include_all=include_all) if job.id == timer_id or job.native_id == timer_id]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        ids = ", ".join(job.id for job in matches)
        raise TimerError(f"ambiguous timer id {timer_id}; use one of: {ids}")
    raise TimerError(f"timer not found: {timer_id}")


def capability_name(operation: str) -> str:
    """Return the capability field for an operation."""

    return {
        "run": "can_start",
        "launch": "can_start",
        "start": "can_start",
        "stop": "can_stop",
        "restart": "can_restart",
        "enable": "can_enable",
        "disable": "can_disable",
        "delete": "can_delete",
        "update": "can_update",
        "unload": "can_delete",
    }.get(operation, f"can_{operation}")


def require_capability(
    job: TimerJob,
    operation: str,
    allow_system: bool = False,
    allow_non_ai: bool = False,
) -> None:
    """Reject unsupported or protected operations with a clear message."""

    if job.backend not in SUPPORTED_WRITE_BACKENDS:
        raise TimerError(f"{operation} is not supported for backend {job.backend}; this backend is read-only")
    if job.scope == "system" and not allow_system:
        raise TimerError(f"{operation} refused for system-scope timer {job.id}; pass --allow-system after review")
    if not job.visible_by_default and not allow_non_ai:
        raise TimerError(f"{operation} refused for non-AI timer {job.id}; pass --allow-non-ai after review")
    cap = capability_name(operation)
    if not getattr(job.capabilities, cap, False):
        raise TimerError(f"{operation} is not supported for timer {job.id}")


def preview_operation(job: TimerJob, operation: str) -> dict[str, Any]:
    """Return dry-run details for a state-changing operation."""

    return {
        "operation": operation,
        "id": job.id,
        "native_id": job.native_id,
        "backend": job.backend,
        "scope": job.scope,
        "source": job.source,
        "dry_run": True,
        "note": "No local state changed. Re-run with --apply after reviewing backend, scope, source, and command.",
    }


def launchd_control(job: TimerJob, operation: str, allow_system: bool, allow_non_ai: bool) -> dict[str, Any]:
    """Run a launchctl operation for a launchd timer."""

    require_capability(job, operation, allow_system=allow_system, allow_non_ai=allow_non_ai)
    if not job.source:
        raise TimerError(f"timer has no source plist: {job.id}")
    domain = launchctl_domain(job.scope)
    label = job.native_id
    source = job.source
    if operation == "enable":
        args = ["launchctl", "enable", f"{domain}/{label}"]
    elif operation == "disable":
        args = ["launchctl", "disable", f"{domain}/{label}"]
    elif operation == "start":
        if not job.loaded:
            bootstrap = run_command(["launchctl", "bootstrap", domain, source], timeout=20)
            if bootstrap.returncode != 0 and "already bootstrapped" not in bootstrap.stderr.lower():
                return {
                    "id": job.id,
                    "operation": operation,
                    "returncode": bootstrap.returncode,
                    "stderr": bootstrap.stderr.strip(),
                }
        args = ["launchctl", "kickstart", "-k", f"{domain}/{label}"]
    elif operation in {"launch", "run"}:
        args = ["launchctl", "kickstart", "-k", f"{domain}/{label}"]
    elif operation == "stop":
        args = ["launchctl", "kill", "TERM", f"{domain}/{label}"]
    elif operation == "restart":
        stop = run_command(["launchctl", "kill", "TERM", f"{domain}/{label}"], timeout=10)
        start = run_command(["launchctl", "kickstart", "-k", f"{domain}/{label}"], timeout=10)
        return {
            "id": job.id,
            "operation": operation,
            "stop_returncode": stop.returncode,
            "start_returncode": start.returncode,
            "stderr": (stop.stderr + start.stderr).strip(),
        }
    elif operation == "unload":
        args = ["launchctl", "bootout", domain, source]
    else:
        raise TimerError(f"unsupported launchd operation: {operation}")
    result = run_command(args, timeout=20)
    return {
        "id": job.id,
        "operation": operation,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def split_windows_native_id(native_id: str) -> tuple[str, str]:
    """Split a Windows task native id into path and name."""

    normalized = native_id if native_id.startswith("\\") else f"\\{native_id}"
    task_name = normalized.rstrip("\\").split("\\")[-1]
    task_path = normalized[: -len(task_name)]
    return task_path or "\\", task_name


def windows_control(job: TimerJob, operation: str, allow_system: bool, allow_non_ai: bool) -> dict[str, Any]:
    """Run a PowerShell ScheduledTasks operation."""

    require_capability(job, operation, allow_system=allow_system, allow_non_ai=allow_non_ai)
    task_path, task_name = split_windows_native_id(job.native_id)
    operation_map = {
        "enable": "Enable-ScheduledTask",
        "disable": "Disable-ScheduledTask",
        "start": "Start-ScheduledTask",
        "launch": "Start-ScheduledTask",
        "run": "Start-ScheduledTask",
        "stop": "Stop-ScheduledTask",
    }
    if operation == "restart":
        stop_result = windows_control(job, "stop", allow_system=allow_system, allow_non_ai=allow_non_ai)
        start_result = windows_control(job, "start", allow_system=allow_system, allow_non_ai=allow_non_ai)
        return {"id": job.id, "operation": operation, "stop": stop_result, "start": start_result}
    cmdlet = operation_map.get(operation)
    if cmdlet is None:
        raise TimerError(f"unsupported Windows operation: {operation}")
    ps = f"{cmdlet} -TaskPath {json.dumps(task_path)} -TaskName {json.dumps(task_name)} | Out-Null"
    powershell_json(f"{ps}; @{{ ok = $true }} | ConvertTo-Json")
    return {"id": job.id, "operation": operation, "returncode": 0}


def control_job(
    timer_id: str,
    operation: str,
    apply: bool,
    allow_system: bool,
    allow_non_ai: bool,
) -> dict[str, Any]:
    """Control a timer through the correct platform backend."""

    job = find_job(timer_id)
    require_capability(job, operation, allow_system=allow_system, allow_non_ai=allow_non_ai)
    if not apply:
        return preview_operation(job, operation)
    if job.backend == "launchd":
        return launchd_control(job, operation, allow_system=allow_system, allow_non_ai=allow_non_ai)
    if job.backend == "windows-task-scheduler":
        return windows_control(job, operation, allow_system=allow_system, allow_non_ai=allow_non_ai)
    raise TimerError(f"unsupported backend: {job.backend}")


def load_timer_file(path: str) -> dict[str, Any]:
    """Load a JSON timer definition file."""

    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def launchd_source_for_label(label: str) -> Path:
    """Return the managed user LaunchAgent source path for a label."""

    return USER_LAUNCH_AGENTS / f"{label}.plist"


def write_launchd_plist(path: Path, plist: dict[str, Any]) -> None:
    """Write a launchd plist atomically enough for local skill usage."""

    USER_LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        plistlib.dump(plist, handle, sort_keys=False)


def windows_task_identity(definition: dict[str, Any], existing_native_id: str | None = None) -> tuple[str, str, str]:
    """Return native id, task path, and task name for a Windows task definition."""

    native_id = str(definition.get("native_id") or definition.get("task") or definition.get("id") or existing_native_id or "")
    if native_id.startswith("windows-task-scheduler:"):
        native_id = native_id.split(":", 2)[-1]
    if not native_id:
        raise TimerError("native_id or task is required for Windows Task Scheduler")
    task_path, task_name = split_windows_native_id(native_id)
    return f"{task_path}{task_name}", task_path, task_name


def windows_trigger_command(definition: dict[str, Any]) -> list[str]:
    """Build schtasks trigger arguments for simple create/update operations."""

    trigger = definition.get("trigger", {})
    trigger_type = trigger.get("type", "manual")
    if trigger_type == "interval":
        minutes = max(1, int(trigger["interval_seconds"]) // 60)
        return ["/SC", "MINUTE", "/MO", str(minutes)]
    if trigger_type == "calendar":
        schedule = str(trigger.get("schedule") or "DAILY").upper()
        return ["/SC", schedule]
    if trigger_type in {"login", "startup"}:
        return ["/SC", "ONLOGON" if trigger_type == "login" else "ONSTART"]
    if trigger_type == "manual":
        return ["/SC", "ONCE", "/ST", "23:59"]
    raise TimerError(f"unsupported Windows trigger type: {trigger_type}")


def windows_task_command(definition: dict[str, Any]) -> str:
    """Build the Windows task action command string."""

    action = definition.get("action", {})
    command = action.get("command")
    if not command:
        raise TimerError("action.command is required")
    parts = [str(command), *[str(arg) for arg in action.get("args", [])]]
    return subprocess.list2cmdline(parts) if platform.system() == "Windows" else shlex.join(parts)


def create_windows_task(definition: dict[str, Any], apply: bool, allow_non_ai: bool) -> dict[str, Any]:
    """Create a user-level Windows Scheduled Task through schtasks."""

    native_id, _task_path, _task_name = windows_task_identity(definition)
    scope = "system" if native_id.lower().startswith("\\microsoft\\") else "user"
    if scope != "user":
        raise TimerError("create refused for system-scope Windows task; use a user task path")
    command = windows_task_command(definition)
    visible, reasons = ai_visibility(native_id, definition, command)
    if not visible and not allow_non_ai:
        raise TimerError("create refused for non-AI timer; pass --allow-non-ai after review")
    args = ["schtasks", "/Create", "/TN", native_id, "/TR", command, *windows_trigger_command(definition)]
    preview = {
        "operation": "create",
        "id": stable_id("windows-task-scheduler", scope, native_id),
        "native_id": native_id,
        "dry_run": not apply,
        "command": args,
        "filter_reasons": reasons,
        "rollback": f"schtasks /Delete /TN {native_id} /F",
    }
    if not apply:
        preview["note"] = "No local state changed. Re-run with --apply after reviewing the schtasks command."
        return preview
    result = run_command(args, timeout=30)
    preview["returncode"] = result.returncode
    preview["stdout"] = result.stdout.strip()
    preview["stderr"] = result.stderr.strip()
    return preview


def update_windows_task(job: TimerJob, file_path: str, apply: bool, allow_non_ai: bool) -> dict[str, Any]:
    """Update a Windows Scheduled Task by delete/create preview semantics."""

    definition = load_timer_file(file_path)
    native_id, _task_path, _task_name = windows_task_identity(definition, existing_native_id=job.native_id)
    if native_id != job.native_id:
        raise TimerError("update cannot rename a Windows task; create a new task instead")
    command = windows_task_command(definition)
    visible, reasons = ai_visibility(native_id, definition, command)
    if not visible and not allow_non_ai:
        raise TimerError("update refused for non-AI timer; pass --allow-non-ai after review")
    create_args = ["schtasks", "/Create", "/F", "/TN", native_id, "/TR", command, *windows_trigger_command(definition)]
    preview = {
        "operation": "update",
        "id": job.id,
        "native_id": native_id,
        "dry_run": not apply,
        "command": create_args,
        "filter_reasons": reasons,
        "rollback": "restore the previous scheduled task definition",
    }
    if not apply:
        preview["note"] = "No local state changed. Re-run with --apply after reviewing the schtasks command."
        return preview
    result = run_command(create_args, timeout=30)
    preview["returncode"] = result.returncode
    preview["stdout"] = result.stdout.strip()
    preview["stderr"] = result.stderr.strip()
    return preview


def create_job(file_path: str, apply: bool, allow_non_ai: bool) -> dict[str, Any]:
    """Create a managed user-level launchd timer from a JSON definition."""

    definition = load_timer_file(file_path)
    backend = definition.get("backend", "launchd" if platform.system() == "Darwin" else "windows-task-scheduler")
    scope = definition.get("scope", "user")
    if scope != "user":
        raise TimerError("create currently supports only user-scope timers")
    if platform.system() == "Windows" and backend == "windows-task-scheduler":
        return create_windows_task(definition, apply=apply, allow_non_ai=allow_non_ai)
    if backend != "launchd" or platform.system() != "Darwin":
        raise TimerError("create supports macOS launchd or Windows Task Scheduler timers on their native platforms")
    plist = build_launchd_plist(definition)
    label = plist["Label"]
    source = launchd_source_for_label(label)
    visible, reasons = ai_visibility(label, source, plist)
    if not visible and not allow_non_ai:
        raise TimerError("create refused for non-AI timer; pass --allow-non-ai after review")
    if source.exists():
        raise TimerError(f"timer already exists: {stable_id('launchd', 'user', label)}")
    preview = {
        "operation": "create",
        "id": stable_id("launchd", "user", label),
        "source": str(source),
        "dry_run": not apply,
        "filter_reasons": reasons,
        "plist": plist,
        "rollback": f"launchctl bootout {launchctl_domain('user')} {source}; rm {source}",
    }
    if not apply:
        preview["note"] = "No local state changed. Re-run with --apply after reviewing source and plist."
        return preview
    write_launchd_plist(source, plist)
    bootstrap = run_command(["launchctl", "bootstrap", launchctl_domain("user"), str(source)], timeout=20)
    preview["bootstrap_returncode"] = bootstrap.returncode
    preview["stderr"] = bootstrap.stderr.strip()
    return preview


def update_job(
    timer_id: str,
    file_path: str,
    apply: bool,
    allow_system: bool,
    allow_non_ai: bool,
) -> dict[str, Any]:
    """Update a managed user-level launchd timer from a JSON definition."""

    job = find_job(timer_id)
    require_capability(job, "update", allow_system=allow_system, allow_non_ai=allow_non_ai)
    if job.backend == "windows-task-scheduler":
        return update_windows_task(job, file_path, apply=apply, allow_non_ai=allow_non_ai)
    if job.backend != "launchd" or job.scope != "user":
        raise TimerError("update currently supports only macOS user launchd timers")
    if not job.source:
        raise TimerError(f"timer has no source plist: {job.id}")
    definition = load_timer_file(file_path)
    plist = build_launchd_plist(definition, existing_label=job.native_id)
    if plist["Label"] != job.native_id:
        raise TimerError("update cannot rename a timer; create a new timer instead")
    visible, reasons = ai_visibility(job.native_id, job.source, plist)
    if not visible and not allow_non_ai:
        raise TimerError("update refused for non-AI timer; pass --allow-non-ai after review")
    preview = {
        "operation": "update",
        "id": job.id,
        "source": job.source,
        "dry_run": not apply,
        "filter_reasons": reasons,
        "plist": plist,
        "rollback": f"restore previous plist at {job.source} and bootstrap it again",
    }
    if not apply:
        preview["note"] = "No local state changed. Re-run with --apply after reviewing source and plist."
        return preview
    launchd_control(job, "unload", allow_system=allow_system, allow_non_ai=allow_non_ai)
    write_launchd_plist(Path(job.source), plist)
    bootstrap = run_command(["launchctl", "bootstrap", launchctl_domain("user"), job.source], timeout=20)
    preview["bootstrap_returncode"] = bootstrap.returncode
    preview["stderr"] = bootstrap.stderr.strip()
    return preview


def delete_job(timer_id: str, confirm: str | None, allow_system: bool, allow_non_ai: bool) -> dict[str, Any]:
    """Delete a timer only when confirmation matches the stable id."""

    job = find_job(timer_id)
    require_capability(job, "delete", allow_system=allow_system, allow_non_ai=allow_non_ai)
    if confirm != job.id:
        return {
            "operation": "delete",
            "id": job.id,
            "native_id": job.native_id,
            "dry_run": True,
            "source": job.source,
            "note": f"No local state changed. Re-run with --confirm {job.id} to delete.",
        }
    if job.backend == "launchd":
        if not job.source:
            raise TimerError(f"timer has no source plist: {job.id}")
        unload = launchd_control(job, "unload", allow_system=allow_system, allow_non_ai=allow_non_ai)
        source = Path(job.source)
        source.unlink()
        return {"operation": "delete", "id": job.id, "unload": unload, "deleted": str(source)}
    if job.backend == "windows-task-scheduler":
        result = run_command(["schtasks", "/Delete", "/TN", job.native_id, "/F"], timeout=30)
        return {
            "operation": "delete",
            "id": job.id,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    raise TimerError(f"delete is not implemented for backend {job.backend}")


def build_parser() -> argparse.ArgumentParser:
    """Build command-line parser."""

    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--json", action="store_true", help="print JSON output")

    parser = argparse.ArgumentParser(description="Manage AI workflow timers")
    parser.add_argument("--json", action="store_true", help="print JSON output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", aliases=["ls"], parents=[common_parser])
    list_parser.add_argument("--all", action="store_true", help="include non-AI workflow jobs")

    get_parser = subparsers.add_parser("get", aliases=["show", "inspect"], parents=[common_parser])
    get_parser.add_argument("id")

    status_parser = subparsers.add_parser("status", aliases=["状态"], parents=[common_parser])
    status_parser.add_argument("id")

    create_parser = subparsers.add_parser("create", aliases=["add"], parents=[common_parser])
    create_parser.add_argument("--file", required=True)
    create_parser.add_argument("--apply", action="store_true")
    create_parser.add_argument("--allow-non-ai", action="store_true")

    update_parser = subparsers.add_parser("update", aliases=["edit"], parents=[common_parser])
    update_parser.add_argument("id")
    update_parser.add_argument("--file", required=True)
    update_parser.add_argument("--apply", action="store_true")
    update_parser.add_argument("--allow-system", action="store_true")
    update_parser.add_argument("--allow-non-ai", action="store_true")

    delete_parser = subparsers.add_parser("delete", aliases=["remove", "rm"], parents=[common_parser])
    delete_parser.add_argument("id")
    delete_parser.add_argument("--confirm")
    delete_parser.add_argument("--allow-system", action="store_true")
    delete_parser.add_argument("--allow-non-ai", action="store_true")

    for command, aliases in {
        "enable": [],
        "disable": [],
        "start": ["开启"],
        "launch": ["run", "lunch", "执行"],
        "restart": [],
        "stop": ["停止"],
    }.items():
        action_parser = subparsers.add_parser(command, aliases=aliases, parents=[common_parser])
        action_parser.add_argument("id")
        action_parser.add_argument("--apply", action="store_true")
        action_parser.add_argument("--allow-system", action="store_true")
        action_parser.add_argument("--allow-non-ai", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command
    as_json = bool(getattr(args, "json", False))
    if argv is None and "--json" in sys.argv[1:]:
        as_json = True
    try:
        if command in {"list", "ls"}:
            print_result([timer_to_dict(job) for job in list_jobs(include_all=args.all)], as_json)
        elif command in {"get", "show", "inspect"}:
            print_result(timer_to_dict(find_job(args.id)), True)
        elif command in {"status", "状态"}:
            print_result(timer_to_dict(find_job(args.id)), True)
        elif command in {"create", "add"}:
            print_result(create_job(args.file, args.apply, args.allow_non_ai), True)
        elif command in {"update", "edit"}:
            print_result(update_job(args.id, args.file, args.apply, args.allow_system, args.allow_non_ai), True)
        elif command in {"delete", "remove", "rm"}:
            print_result(delete_job(args.id, args.confirm, args.allow_system, args.allow_non_ai), True)
        else:
            normalized = {"run": "launch", "lunch": "launch", "执行": "launch", "开启": "start", "停止": "stop"}.get(
                command,
                command,
            )
            print_result(control_job(args.id, normalized, args.apply, args.allow_system, args.allow_non_ai), True)
        return 0
    except TimerError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
