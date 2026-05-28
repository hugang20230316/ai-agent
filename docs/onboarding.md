# Onboarding

This repository gives each user the same shared agent rules and maintained skills. It does not provide private configuration. Each member configures their own tools, accounts, MCP servers, tokens, cookies, and local paths.

## Setup Flow

1. Clone the repository.

```bash
git clone https://github.com/team-agent-workflow/ai-agent.git
cd ai-agent
```

Before the repository is transferred to the organization, use the current repository URL.

If you already have a local checkout, keep its directory in place and only update the Git remote after transfer:

```bash
git remote set-url origin https://github.com/team-agent-workflow/ai-agent.git
```

This does not change local agent symlinks, private config, tokens, sessions, or MCP settings.

Repository owners can follow `docs/github-transfer-checklist.md` for the transfer and protection setup.

2. Verify the repository files.

```bash
python3 scripts/verify_agent_rules.py
```

3. Inspect local setup.

```bash
python3 scripts/doctor.py
```

`doctor.py` is read-only. It reports missing links and selected skill status, but it does not install tools, write private config, or create links.

4. Link the shared entry and rules into your agent tool home.

Recommended shape:

```text
<tool-home>/AGENTS.md -> <repo>/AGENTS.md
<tool-home>/rules/*.md -> <repo>/rules/*.md
```

Use per-file symlinks for `rules/*.md`. Do not symlink the whole `rules/` directory because some tools keep private local files in their rules directory.

To print commands without changing files:

```bash
python3 scripts/setup_links.py --tool codex --rules --print-only
python3 scripts/setup_links.py --tool claude --rules --print-only
```

Add `--apply` only after reviewing the printed plan.

5. Expose only the maintained skills you need.

Codex and Claude can use per-skill symlinks:

```text
<tool-home>/skills/<skill-name> -> <repo>/skills/<skill-name>
```

Hermes and OpenClaw should use their local config to list the shared skill directories. OpenClaw should use `skills.load.extraDirs`, not workspace skill symlinks that escape the workspace.

Skills are not installed by default. Some skills depend on company issue trackers, monitoring, release systems, or personal repositories. Select them explicitly:

```bash
python3 scripts/setup_links.py --tool codex --skills multi-agent-workflow,personal-knowledge --print-only
```

Do not use an all-skills setup for a shared team machine.

6. Add private configuration locally.

Keep private files outside Git:

```text
~/.codex/local/*.local.json
<tool-home>/config.*
<tool-home>/auth*
<tool-home>/sessions/
<tool-home>/logs/
```

Never commit tokens, cookies, browser sessions, sqlite databases, command approval history, or company project configuration.

## First Validation

Run:

```bash
python3 scripts/doctor.py --skills multi-agent-workflow,personal-knowledge
python3 scripts/verify_agent_rules.py
python3 scripts/check_dangerous_deletions.py --base HEAD --head HEAD
git status --short
```

`git status --short` should not show local config, sessions, logs, caches, or generated files.

## When Something Does Not Work

- If a rule did not load, check the `AGENTS.md` symlink or native tool entry.
- If a skill did not load, check whether the skill is linked or listed in the tool config.
- If private config is missing, create it in your local tool directory, not in this repository.
- If the shared behavior rule is wrong, follow `docs/rule-fix-workflow.md`.
