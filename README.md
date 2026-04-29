# ai-agent

Personal AI agent rules and migration notes.

This repository stores portable Codex agent guidance that can be shared between Windows and macOS machines. It intentionally excludes local CLI configuration, credentials, sessions, logs, caches, and company/project-specific files.

## Contents

Global Codex rules:

- `.codex/rules/communication-rules.md`: collaboration and response rules
- `.codex/rules/coding-rules.md`: coding rules
- `.codex/rules/testing-rules.md`: testing and verification rules
- `.codex/rules/project-governance.md`: sync and governance rules
- `.codex/rules/mcp-output-rules.md`: MCP result output rules
- `.codex/rules/requirements-and-prototype.md`: requirements and prototype rules

On each machine, install these rule files into the Codex home rules directory:

```text
~/.codex/rules/*.md
```

The Codex global entry file should live at `~/.codex/AGENTS.md` and reference:

```text
@rules/communication-rules.md
@rules/coding-rules.md
@rules/testing-rules.md
@rules/project-governance.md
@rules/mcp-output-rules.md
@rules/requirements-and-prototype.md
```

Platform-specific `AGENTS.md` templates:

- `.codex/windows/AGENTS.md`: copy to `%USERPROFILE%\.codex\AGENTS.md`
- `.codex/mac/AGENTS.md`: copy to `~/.codex/AGENTS.md`

Cross-device notes:

- `.codex/common-rules.md`: rules shared by Windows and macOS
- `.codex/windows-config.md`: Windows-only paths and setup notes
- `.codex/mac-config.md`: macOS-only paths and setup notes
- `.codex/file-map.md`: file classification and migration map
- `.codex/do-not-sync.md`: files and directories that must never be synced

Project rules do not live in this global repository. Put them inside the target project:

```text
<project>/
  AGENTS.md
  .codex/
    rules/
      *.md
```

## Security

Do not commit:

- `~/.codex/config.toml`
- `~/.codex/local/`
- auth files, tokens, cookies, browser sessions
- command approval history
- logs, sqlite databases, caches, temporary files
- company or internal project configuration

Each machine should keep its own Codex CLI configuration and private local files.
