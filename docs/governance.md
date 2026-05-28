# Governance

The repository is public so anyone can use or fork it. Trusted members can help maintain it. Private configuration stays on each member's machine.

## Organization Model

Target organization:

```text
team-agent-workflow
```

Target repository:

```text
team-agent-workflow/ai-agent
```

Recommended teams:

- `owners`: organization owners and repository admins.
- `maintainers`: trusted maintainers for rules, skills, scripts, and docs.
- `contributors`: regular contributors who work through pull requests.

## Permissions

- Public users can read, clone, fork, and open pull requests.
- Contributors use pull requests.
- Maintainers can review and merge routine changes when branch rules allow it.
- Owners manage repository settings, rulesets, permissions, and destructive operations.

Deleting the repository, changing security settings, disabling branch protection, and bypassing dangerous-deletion checks should stay with owners.

## Transfer Order

Use this order when moving the current personal repository into the organization:

1. Create the `team-agent-workflow` organization.
2. Create `owners`, `maintainers`, and `contributors` teams.
3. Transfer the repository to `team-agent-workflow/ai-agent`.
4. Update the local `origin` remote on existing machines.
5. Enable branch protection and CODEOWNERS review on `main`.
6. Confirm CI runs on a test pull request.
7. Invite trusted members into the right teams.

Existing local directories and symlinks do not need to move if the repository path stays the same. Only the Git remote changes.

Detailed GitHub UI steps and official references are in `docs/github-transfer-checklist.md`.

## Branch Protection

Protect `main` with these rules:

- No direct pushes to `main`.
- Pull requests required.
- Review required before merge.
- CODEOWNERS review required for protected paths.
- CI checks required.
- Force push disabled.
- Branch deletion disabled.

Protected paths include:

- `AGENTS.md`
- `rules/**`
- `skills/**`
- `scripts/**`
- `.github/**`

## Dangerous Changes

Deleting a skill package can break members who have local symlinks to that skill. Treat deletion as an owner-reviewed change.

Prefer deprecation:

```text
skills/<name>/DEPRECATED.md
skills/<name>/SKILL.md keeps a short compatibility note
docs/deprecations.md records replacement guidance
```

The CI dangerous-deletion check blocks direct removal of protected files, shared scripts, GitHub automation, rule files, and managed skill files.

## Private Configuration Boundary

The shared repository contains only portable rules, skills, scripts, and docs. It must not contain:

- Tokens, cookies, passwords, private keys, or browser sessions.
- Local CLI config.
- Command approval history.
- Logs, sqlite databases, caches, or generated runtime state.
- Company project files, internal hosts, internal account data, or internal deployment details.

Each user owns their local configuration.
