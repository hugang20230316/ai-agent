---
name: publish-gitlab-argo
description: "Automate a configured development release through GitLab and Argo CD APIs. Use when the user asks to publish, release, sync dev applications, preview a release plan, or publish selected components."
---

# Publish GitLab Argo

## Tooling

Use the single Python entry point from this skill directory:

```console
python3 scripts/publish_gitlab_argo.py doctor
python3 scripts/publish_gitlab_argo.py resolve-plan -Scope default -Format json
python3 scripts/publish_gitlab_argo.py publish -Scope default -Format json
python3 scripts/publish_gitlab_argo.py publish -Scope default -Apps <app> -Format json
python3 scripts/publish_gitlab_argo.py publish -Scope all -Format json
```

Machine-specific API hosts, repo paths, app names, credentials, sessions, and release state must come from local config, environment variables, or explicit CLI arguments. Do not add platform-specific skill files or wrapper scripts.

## Shared Workflow

1. Inspect the commits/files being published and identify the affected components before choosing apps.
2. Resolve the requested publish scope: selected components from the change impact, explicit apps, all apps, preview only, or known-tag app update.
3. Use default apps only as a fallback when the changed components cannot be mapped more specifically.
4. Reuse any in-flight publish result instead of creating duplicate tags or duplicate syncs.
5. Resolve or create the configured release tag through the GitLab API.
6. Wait for the configured release pipeline/status gate within the end-to-end publish command budget, not by adding independent full timeouts for each stage.
7. Update only the configured deployment image tag through Argo CD APIs.
8. Verify the final app tag and sync/health state before reporting success or failure.

## Shared Guardrails

- Keep credentials in local config, environment variables, or local encrypted state only.
- Do not publish apps outside the configured scope.
- Do not blindly publish the default apps when the change set points to different deployable components.
- Preview/check mode must not create tags or sync apps.
- When the user says optimization is limited to publishing, do not recommend GitLab, CI job, runner, or build-cache configuration changes as actionable fixes.
- A publish command must not stretch a normal pipeline-duration release into multiple stage timeouts. Use status reuse, an end-to-end timeout budget, and read-only progress observation instead.
- Do not use browser automation unless the configured APIs are unavailable and local policy allows a fallback.
- Timeout results require one read-only GitLab or Argo CD status refresh before reporting final failure.

## Output Contract

Any final publish success/failure summary must report the planned tag, final release tag, actual deployed tag, updated apps, unchanged apps, failed apps, and any timeout/status recheck performed, even after multi-turn status updates. When a publish command actually runs, also report the total publish elapsed time. Prefer the publish command's `elapsedSeconds`; if it is unavailable, report the measured wall-clock time and name that source. For preview-only resolve-plan output, state that no publish was executed and do not invent a publish elapsed time.
