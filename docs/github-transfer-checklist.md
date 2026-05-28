# GitHub Transfer Checklist

Use this checklist when moving the repository from the personal account to `team-agent-workflow/ai-agent`.

Official references:

- GitHub repository transfer docs: https://docs.github.com/en/enterprise-cloud@latest/repositories/creating-and-managing-repositories/transferring-a-repository
- GitHub delete or transfer permission docs: https://docs.github.com/en/organizations/managing-organization-settings/setting-permissions-for-deleting-or-transferring-repositories
- GitHub branch protection docs: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- GitHub rulesets docs: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets

## Before Transfer

1. Create the organization `team-agent-workflow`.
2. Confirm the target organization has no existing `ai-agent` repository.
3. Create teams:
   - `owners`
   - `maintainers`
   - `contributors`
4. Keep organization repository deletion and transfer limited to owners.
5. Confirm this repository has no private config, credentials, sessions, logs, or local-only files in Git.

## Transfer

1. Open the current repository on GitHub.
2. Go to repository settings.
3. Use the transfer action in the danger zone.
4. Set the new owner to `team-agent-workflow`.
5. Keep the repository name `ai-agent`.
6. Complete the GitHub confirmation flow.

GitHub redirects the old repository URL after transfer, but local clones should still update `origin`:

```bash
git remote set-url origin https://github.com/team-agent-workflow/ai-agent.git
```

## After Transfer

1. Confirm `CODEOWNERS` recognizes `@team-agent-workflow/owners` and `@team-agent-workflow/maintainers`.
2. Enable protection for `main`:
   - Require pull requests.
   - Require reviews.
   - Require CODEOWNERS review.
   - Require the `Verify` workflow.
   - Block force pushes.
   - Block branch deletion.
3. Keep destructive repository actions limited to owners.
4. Open a small test pull request and confirm:
   - `python3 scripts/verify_agent_rules.py` runs in CI.
   - `scripts/check_dangerous_deletions.py` runs in CI.
   - CODEOWNERS review is requested on protected paths.
5. Invite trusted members into the right teams.

Existing local agent symlinks do not need to change if the local checkout path stays the same.
