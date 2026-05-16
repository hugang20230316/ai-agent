---
name: publish-dev
description: "Automate a configured development release through a Git provider API and Argo CD API. Use when the user asks to publish, release, sync dev applications, preview a release plan, or publish selected components."
---

# Publish Dev

## Tooling

Use the single Python entry point from this skill directory:

```console
python3 scripts/publish_dev.py doctor
python3 scripts/publish_dev.py resolve-plan -Scope default -Format json
python3 scripts/publish_dev.py publish -Scope default -Format json
python3 scripts/publish_dev.py publish -Scope default -Apps <app> -Format json
python3 scripts/publish_dev.py publish -Scope all -Format json
```

Machine-specific API hosts, repo paths, app names, credentials, sessions, and release state must come from local config, environment variables, or explicit CLI arguments. Do not add platform-specific skill files or wrapper scripts.

## Shared Workflow

1. Resolve the requested publish scope: default apps, selected components, all apps, preview only, or known-tag app update.
2. Reuse any in-flight publish result instead of creating duplicate tags or duplicate syncs.
3. Resolve or create the configured release tag through the Git provider API.
4. Wait for the configured release pipeline/status gate.
5. Update only the configured deployment image tag through Argo CD APIs.
6. Verify the final app tag and sync/health state before reporting success or failure.

## Shared Guardrails

- Keep credentials in local config, environment variables, or local encrypted state only.
- Do not publish apps outside the configured scope.
- Preview/check mode must not create tags or sync apps.
- Do not use browser automation unless the configured APIs are unavailable and local policy allows a fallback.
- Timeout results require one read-only Git provider or Argo CD status refresh before reporting final failure.

## Shared Output

Report the planned tag, final release tag, actual deployed tag, updated apps, unchanged apps, failed apps, and any timeout/status recheck performed.
