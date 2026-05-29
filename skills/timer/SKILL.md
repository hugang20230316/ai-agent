---
name: timer
description: Manage personal AI-workflow timers across macOS and Windows through one Python entry point. Use when the user names the timer skill or command, asks about AI workflow timers such as Codex, OpenClaw, Hermes, Claude, Obsidian sync, MCP, local AI gateways, browser automation, agent automation, knowledge sync, or log sync, or explicitly asks for a full local timer inventory. Do not use by default for generic system or vendor scheduled jobs such as browser updates, Google or Chrome updates, system wake jobs, or unrelated launchd, cron, Task Scheduler, or schtasks items.
---

# Timer

Use this skill to inspect and manage personal AI-workflow timers through one Python entry point.
Default views show jobs with strong AI workflow evidence; use `--all` only for explicit full-inventory requests.

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
Human-readable `list` output uses Chinese headers by default; pass `--lang en` for English headers.

## Commands

Read commands:

```bash
timer list
timer list --all
timer list --lang en
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

CLI commands are English-only. Chinese operation words are agent-only intent terms, not terminal subcommands:

- `列出`, `查看全部`: use `timer list`
- `查看`, `状态`: use `timer status <id>` or `timer get <id>`
- `新增`, `创建`: use `timer create --file timer.json`
- `修改`, `更新`: use `timer update <id> --file timer.json`
- `删除`: use `timer delete <id>`
- `开启`, `启动`: use `timer start <id>`
- `执行`, `运行`: use `timer launch <id>`
- `重启`: use `timer restart <id>`
- `停止`: use `timer stop <id>`

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
