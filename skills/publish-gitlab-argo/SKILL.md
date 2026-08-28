---
name: publish-gitlab-argo
description: "Automate a configured development release through GitLab and Argo CD APIs. Use when the user asks to 发布 / 发版 / 同步 dev, or publish, release, sync dev applications, preview a release plan, or publish selected components."
---

# Publish GitLab Argo

## Tooling

Use the single Python entry point from the target repository working directory, or pass `-RepoPath` explicitly:

```console
python3 <skill-dir>/scripts/publish_gitlab_argo.py doctor
python3 <skill-dir>/scripts/publish_gitlab_argo.py resolve-plan -SourceRef <ref> -Scope default -Format json
python3 <skill-dir>/scripts/publish_gitlab_argo.py publish -SourceRef <ref> -Scope default -Format json
python3 <skill-dir>/scripts/publish_gitlab_argo.py publish -SourceRef <ref> -Scope default -Apps <app> -Format json
python3 <skill-dir>/scripts/publish_gitlab_argo.py publish -SourceRef <ref> -Scope all -Format json
```

Machine-specific API hosts, repo paths, app names, credentials, sessions, and release state must come from local config, environment variables, or explicit CLI arguments. Do not add platform-specific skill files or wrapper scripts.

The standard publish flow is pre-approved. Use the local persisted approval for this Python entry point for `doctor`, `resolve-plan`, and `publish`; do not interrupt a normal release with per-command permission questions. If the current environment lacks that approval, establish the persisted local approval before starting the release flow.

## Shared Workflow

1. Run `python3 <skill-dir>/scripts/publish_gitlab_argo.py doctor` before publishing. If credential or connectivity issues are detected (e.g., ArgoCD token expired, GitLab unreachable), resolve them before proceeding. Do not proceed to publish if doctor reports critical failures.
2. Before `resolve-plan` or `publish`, use local publish config to confirm and state the target repository. If the cwd repository differs from the configured publish repository, run the command from the single allowed readable repository directory, rerun `doctor`, and continue with the originally requested operation when repository checks pass and the user did not limit the request to the current repository, current changes, or current directory; run `publish` only when the user explicitly requested publishing. Otherwise stop and report the mismatch.
3. Resolve `-SourceRef` first, falling back only to local `sourceRef` config, and lock it to an immutable `sourceCommit` without changing the worktree. Source version and deployment scope are independent; never infer a Git ref from `Scope`, app names, or a dev environment.
4. Inspect the locked commit and its changed files to identify the affected components before choosing apps.
5. Resolve the requested publish scope: selected components from the change impact, explicit apps, all apps, preview only, or known-tag app update.
6. Use default apps only as a fallback when the changed components cannot be mapped more specifically.
7. On retry, interruption, or re-publish requests, rerun `resolve-plan`; reuse a lock or result only when `sourceRef`, `sourceCommit`, `effectiveTag`, and target apps all match.
8. Resolve or create the configured release tag through the GitLab API and verify that it points to the locked commit.
9. Wait only for the planned tag's configured pipeline/status gate within the end-to-end publish command budget; never switch to a newer tag while waiting.
10. Update only the configured deployment image tag through Argo CD APIs.
11. Verify the final app tag and sync/health state before reporting success or failure.

## Shared Guardrails

- Keep credentials in local config, environment variables, or local encrypted state only.
- Never publish a repository that is not explicitly listed in the local publish config; `-RepoPath` cannot override this allowlist.
- Do not publish apps outside the configured scope.
- Do not blindly publish the default apps when the change set points to different deployable components.
- Preview/check mode must not create tags or sync apps.
- Actual publish must stop before external writes when the source ref cannot be locked. During unresolved merge conflicts, reject `HEAD` or the current branch while allowing an explicit non-current ref that can be resolved without touching the worktree.
- When the user says optimization is limited to publishing, do not recommend GitLab, CI job, runner, or build-cache configuration changes as actionable fixes.
- A publish command must not stretch a normal pipeline-duration release into multiple stage timeouts. Use status reuse, an end-to-end timeout budget, and read-only progress observation instead.
- Do not use browser automation unless the configured APIs are unavailable and local policy allows a fallback.
- Timeout results require one read-only GitLab or Argo CD status refresh before reporting final failure.

## Output Contract

Any final publish success/failure summary must report the source ref and commit, planned tag, final release tag, GitLab pipeline status, updated apps with previous and deployed tags, publish start time, publish completion time, total publish elapsed time, and any timeout/status recheck performed, even after multi-turn status updates. Put the GitLab pipeline line immediately after the commit line. Show unchanged apps, failed apps, and timeout/status rechecks only when they are non-empty.

When a publish command actually runs, calculate the final total publish elapsed time from the user's publish request time to the last target Argo CD app reaching `Synced` with operation phase `Succeeded`. Prefer the latest exact Argo CD `finishedAt` or `deployedAt` timestamp across target apps as the publish completion time. If only the sync request/click time is available, use request time plus 5 seconds and label it estimated. If the user's request time is unavailable, fall back to the publish command start time and name that source. Do not use the publish command's `elapsedSeconds` as the final user-facing publish elapsed time unless it is the only available source and is labeled as command elapsed time. For preview-only resolve-plan output, state that no publish was executed and do not invent a publish elapsed time.
