---
name: timer
description: Manage local scheduled jobs and timer-like background tasks across macOS and Windows, with an AI-workflow-focused default view. Use when the user asks to list, inspect, create, update, delete, enable, disable, start, run, launch, restart, stop, or check status of timers, scheduled tasks, launchd jobs, LaunchAgents, LaunchDaemons, cron jobs, at jobs, Windows Task Scheduler tasks, schtasks, or AI workflow background jobs such as Codex, OpenClaw, Hermes, Claude, Obsidian sync, MCP services, local AI gateways, browser automation daemons, agent automation, knowledge sync, or log sync.
---

# Timer

Use this skill to manage local scheduled jobs through one Python entry point.
Default views show jobs with strong AI workflow evidence; use `--all` for full inventory.

## Entry Point

From a terminal on this machine, use:

```bash
timer <command>
```

Agents can also call the Python entry point directly:

```bash
python3 ~/.codex/skills/timer/scripts/timer_manager.py <command>
```

Prefer `--json` when another tool or agent will consume the result.

## Commands

Read commands:

```bash
timer list
timer list --all
timer get <id>
timer status <id>
```

Write commands:

```bash
timer create --file timer.json
timer create --file timer.json --apply
timer update <id> --file timer.json
timer update <id> --file timer.json --apply
timer delete <id>
timer delete <id> --confirm <stable-id>
timer enable <id> --apply
timer disable <id> --apply
timer start <id> --apply
timer launch <id> --apply
timer restart <id> --apply
timer stop <id> --apply
```

`run` is an alias of `launch`. `lunch` is accepted as a typo alias of `launch`.
Chinese aliases are accepted for common operations: `开启`, `执行`, `停止`, `状态`.

## Safety Rules

- Start with `list`, `get`, or `status` before changing a timer.
- `list` uses strong evidence for default visibility: AI tool names, AI workflow directories, or both weak terms and strong local evidence. Broad words like `sync` or `agent` alone are not enough.
- `list --all` always bypasses default visibility filtering. It does not relax write protections.
- All state-changing commands are preview-first. `create`, `update`, `enable`, `disable`, `start`, `launch`, `restart`, and `stop` need `--apply`; `delete` needs `--confirm <stable-id>`.
- Non-AI timers shown by `--all` are still protected. Use `--allow-non-ai` only after reviewing the preview.
- Do not edit system-level jobs unless the user explicitly asks for that scope and has reviewed the preview. Use `--allow-system` only after explaining administrator/root risk.
- Do not convert cron, at, or package-manager services into launchd or Windows tasks unless the user explicitly asks for migration.
- Follow `capabilities`. If a backend reports an operation as unsupported, explain the limitation instead of forcing a different backend.

## Normalized Fields

The manager returns `TimerJob` objects with these stable fields:

- `id`, `native_id`, `name`, `platform`, `backend`, `scope`
- `category`, `visible_by_default`, `filter_reasons`, `tags`
- `source`, `enabled`, `loaded`, `running`, `pid`
- `trigger`, `action`, `logs`, `health`, `capabilities`

Use stable `id` for follow-up commands. Native ids are accepted only when they match one job.

## Platform Coverage

macOS:

- Primary backend: `launchd` LaunchAgents and LaunchDaemons.
- Read-only supplemental backends: user `crontab`, `atq`, and `brew services`.
- Create/update/delete support is limited to current-user LaunchAgents managed under `~/Library/LaunchAgents`.

Windows:

- Primary backend: Task Scheduler through PowerShell `ScheduledTasks`.
- Create/update/delete uses `schtasks` for user-scope tasks; run/stop/enable/disable uses PowerShell `ScheduledTasks`.
- Write support is limited by current user permissions and task scope. If running on non-Windows, treat Windows paths as unverified.

Unsupported or privileged operations must return a clear error and must not silently fallback to destructive commands.
