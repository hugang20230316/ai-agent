---
name: dev-tool
description: Local development CLI for configured .NET and Node.js projects. Use when the user asks Codex to build, compile, test, start, stop, restart, inspect status, view logs, or locally debug a configured project; also use when the user explicitly mentions dev-tool or wants local debugging to use the configured dev-tool workflow instead of ad hoc commands.
---

# dev-tool

Use `dev-tool` as the default local workflow for configured .NET and Node.js projects.

## Command Entry

Run commands through the stable launcher:

```bash
dev-tool <command> [project] [service]
```

Do not require a project-local `dev-tool.json`. Machine-specific project config lives in local private config; `references/projects.json` is only a public example. Runtime logs and PID files live outside project repositories.

## Command Mapping

| User intent | Command |
| --- | --- |
| List configured projects | `dev-tool list` |
| Build/compile | `dev-tool build <project> [service]` |
| Diagnose slow build | `dev-tool diagnose-build <project> [service]` |
| Run tests | `dev-tool test <project> [service]` |
| Start local service | `dev-tool run <project> [service]` |
| Watch local service | `dev-tool watch <project> [service]` |
| Stop local service | `dev-tool stop <project> [service]` |
| Restart local service | `dev-tool restart <project> [service]` |
| Status | `dev-tool status [project]` |
| Logs | `dev-tool logs <project> <service> [lines]` |
| Clean build outputs | `dev-tool clean <project> [service]` |

For a configured Node.js project, `build` runs `npm run lint`, `test` runs `npm test`, and `run/restart` runs `npm start` after lint succeeds. Node projects do not use `dotnet clean`, `watch`, or `diagnose-build`.

`start` is accepted as an alias for `run`.

## Run Health Contract

For services with a configured port, `dev-tool run` is only successful when the service process is alive and the port is listening on `127.0.0.1`.

- Startup waits are bounded by `DEV_TOOL_STARTUP_TIMEOUT_SECONDS` or 30 seconds.
- Startup prints periodic progress while waiting for the port.
- If startup times out, `dev-tool` prints the log tail, terminates the process group it started, removes the PID file, and exits non-zero.
- A tracked PID with a closed configured port is treated as unhealthy and is restarted by the next `run` command.

## Build Modes

`dev-tool build` defaults to the native-aligned local path:

- same rebuild semantics as `dotnet build <target> --configuration Debug --verbosity minimal`
- implicit restore remains enabled by default, matching native `dotnet build`
- explicit `dotnet restore` followed by `dotnet build --no-restore` when `--restore` is passed
- `--no-restore` only when the user intentionally wants a hot local build without package restore
- `Debug` configuration
- bounded by `DEV_TOOL_TIMEOUT_SECONDS` or `--timeout`

Use `--stable` when a build appears stuck or affected by build-server/process state. Stable mode runs serialized isolated MSBuild, disables build servers, shared compilation, analyzers, and XML documentation.

If the native build path times out and local `project.assets.json` exists, `dev-tool build` automatically retries a stable `--no-restore` build after printing diagnostics and shutting down build servers. If assets are missing, the timeout still returns exit code 124.

Use `dev-tool diagnose-build <project> [service]` when compile time is abnormal. It separates restore, native build without restore, and stable build without restore, then prints elapsed time and timeout diagnostics. A timeout prints build-related processes, NuGet sources, and shuts down dotnet build servers before returning exit code 124.

Use plain `dev-tool run <project> <service>` for the normal local loop. It must build first, start the configured service, and only return success after the configured port is listening. Use `--restore` when package references changed and you want an explicit restore step. Use `--no-restore` only for an intentional hot local build. Do not claim `dev-tool` is faster than native `dotnet` unless a same-scope benchmark proves it.

Use `dev-tool watch <project> <service>` for the hot local edit loop. Watch mode starts `dotnet watch run` for the configured service, tracks its PID and log file through `dev-tool`, and returns success only after the configured port is listening. It does not change `dev-tool build` semantics and does not run a separate pre-build; `dotnet watch` handles source changes with Hot Reload when possible and restarts the child app when needed.

## Required Workflow

1. Resolve the project and service from the user request and private project configuration. If omitted and only one project is relevant, use that project; do not infer a service's source root from a similarly named repository.
2. Use the command mapping above. Prefer `dev-tool` over direct `dotnet` for configured projects.
3. Run `build`, `test`, and `diagnose-build` in the foreground with the execution tool's wait window set to at least 30 seconds and pass `--timeout 30`. Never use a short wait to move these commands into the background intentionally. If the execution tool still returns a running handle, observe it immediately under the bounded wait rules and never leave it unattended.
4. Read the command output and exit code before reporting status.
5. For build/start/restart, include the git freshness summary from `dev-tool`; do not auto-pull code.
6. If the command fails, report the failing command, exit code, and the key error lines.
7. Do same-scope speed comparisons against the default command users actually run, not against `--restore` or other troubleshooting flags.
8. If this turn changed code and a build succeeds, run the normal `review-coding` gate before final completion.

## Output Contract

Final responses for dev-tool actions must include:

```text
命令：dev-tool <command> ...
结果：成功 / 失败（退出码 N）
关键证据：<build/start/status/log summary>
```

Do not claim a service is running unless `dev-tool` reports a live PID or a verified listening port.
