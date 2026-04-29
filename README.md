# ai-agent

Personal AI agent rules and migration notes.

This repository stores portable Codex agent guidance that can be shared between Windows and macOS machines. It intentionally excludes local CLI configuration, credentials, sessions, logs, caches, and company/project-specific files.

## Contents

- `codex-cross-device-sync/common-rules.md`: rules shared by Windows and macOS
- `codex-cross-device-sync/windows-config.md`: Windows-only paths and setup notes
- `codex-cross-device-sync/mac-config.md`: macOS-only paths and setup notes
- `codex-cross-device-sync/file-map.md`: file classification and migration map
- `codex-cross-device-sync/do-not-sync.md`: files and directories that must never be synced

## Security

Do not commit:

- `~/.codex/config.toml`
- `~/.codex/local/`
- auth files, tokens, cookies, browser sessions
- command approval history
- logs, sqlite databases, caches, temporary files
- company or internal project configuration

Each machine should keep its own Codex CLI configuration and private local files.
