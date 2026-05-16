---
name: hg-git
description: Inspect, bootstrap, synchronize, commit, pull, and push Hugang's personal GitHub repositories. Use when the user explicitly names personal GitHub, hg-git, ai-agent, Codex rules/skills sync, encrypted/private personal data projects, personal private data, Postman sync, or personal repo update/commit/pull/push. Always list detected repo updates and show git-style change summaries before committing or pushing. Requires clear conflict reporting before resolving merge/rebase conflicts.
---

# HG Git

Use this skill to inspect, synchronize, commit, pull, and push the user's personal GitHub repositories safely.

## Activation Boundary

- This skill is only for personal Git repository maintenance.
- Do not inspect the known personal repo map unless the user explicitly mentions personal GitHub, `hg-git`, `ai-agent`, Codex rules/skills sync, encrypted/private personal data projects, personal private data, Postman sync, or personal repo commit/pull/push/update.

## Personal Repo Map

Known personal GitHub repositories:

- `github.com/hugang20230316/ai-agent`
- `github.com/hugang20230316/personal-private-data`

Resolve local paths from machine-specific configuration before inspecting:

- environment variables: `HG_GIT_AI_AGENT_REPO`,
  `HG_GIT_PERSONAL_PRIVATE_DATA_REPO`
- optional local config: `<codex-home>/local/hg-git.local.json`
- existing home-relative defaults such as `<home>/ai-agent`,
  `<codex-home>/ai-agent`, or `<home>/personal-private-data`

Treat any repo as personal only after `git remote -v` confirms a `github.com/hugang20230316/` remote. Do not copy, commit, or push company, cache, runtime, temporary, or third-party repo content to the user's personal GitHub.

## Workflow

1. Confirm the request is inside the Activation Boundary; otherwise stop this workflow.
2. Identify the target repo and verify its remote.
   - If the current working directory is inside a verified personal repo, use
     that repo first.
   - If the user gives only a short command such as `hg-git pull` or
     `hg-git push`, inspect known personal repo paths and route each repo by
     its type.
   - If a repo contains `.hg-git-private-data.json`, treat it as a
     private-data repo and use the shared helper instead of raw Git for
     pull/push/sync actions.
3. Run the update inventory before changing anything.
4. Run the live-source drift inventory for mapped files before saying any
   mapped repo is clean.
   - A clean `git status` in `ai-agent` is not enough. Compare
     `~/.codex/AGENTS.md` and `~/.codex/rules/*.md` with the `ai-agent`
     mirror files first.
   - A clean `git status` in `ai-agent` is not enough. Compare selected live
     `~/.codex/skills/<skill>/` folders with the matching
     `ai-agent/skills/<skill>` folders first.
   - If live sources differ from the repo mirror and the user asked to push or
     sync, copy only the allowed public files into the verified personal repo,
     then include those changes in the repo inventory.
5. Summarize what maps to personal GitHub before committing:
   - rules: `~/.codex/AGENTS.md` and `~/.codex/rules/*.md` map to `ai-agent`
   - skills: selected `~/.codex/skills/<skill>/` folders map to
     `ai-agent/skills`
   - private data: `personal-private-data` maps configured plaintext sync
     targets such as Postman plus encrypted secret files
6. Exclude local/private material:
   - credentials, tokens, cookies, sessions, sqlite databases, logs, caches
   - `config.toml`, `local/`, `default.rules`
   - company project files and internal environment details
7. Before commit, run focused checks:
   - `git diff --check`
   - `git diff --cached --check` when there are staged files
   - search staged files for common secret patterns when practical
8. Commit with a clear message when the user asked to commit.
9. Before push, fetch or pull the latest remote state.
10. Push only the confirmed personal repo branch.

## Private Data Encryption

Encryption/decryption belongs to this `hg-git` skill, not to individual
repositories. Private repositories declare encrypted files in
`.hg-git-private-data.json`; use the shared Python 3 tool:

```powershell
python ~/.codex/skills/hg-git/scripts/private_data.py status --repo <repo>
python ~/.codex/skills/hg-git/scripts/private_data.py doctor --repo <repo>
python ~/.codex/skills/hg-git/scripts/private_data.py pull --repo <repo>
python ~/.codex/skills/hg-git/scripts/private_data.py push --repo <repo> --message "Sync personal private data"
python ~/.codex/skills/hg-git/scripts/private_data.py pull-decrypt --repo <repo>
python ~/.codex/skills/hg-git/scripts/private_data.py sync-postman --repo <repo>
python ~/.codex/skills/hg-git/scripts/private_data.py install-postman --repo <repo>
python ~/.codex/skills/hg-git/scripts/private_data.py encrypt-push --repo <repo> --message "Sync personal private data"
```

Use the platform's Python 3 executable (`python` on Windows when available,
`python3` on macOS/Linux).

### Bootstrap Encrypted Private Repos

When the user asks on a new machine, especially macOS, to configure, pull, push,
or sync an encrypted/private personal data project:

1. Ensure this `hg-git` skill is present and current under `~/.codex/skills` on
   macOS or `%USERPROFILE%\.codex\skills` on Windows.
2. Ensure GitHub auth can access `github.com/hugang20230316/*`; complete auth
   once if needed, then continue.
3. Locate or clone the requested private repo. For `personal-private-data`, use
   `~/personal-private-data` on macOS when no path is specified.
4. Verify the repo remote is `github.com/hugang20230316/...` before operating.
5. If the repo has `.hg-git-private-data.json`, load it and use it as the source
   of truth for password files, encrypted files, plaintext sync targets, and
   Git add paths.
6. Ensure Python 3 can import `cryptography`; if not, install it for the active
   Python 3 environment and continue.
7. Ensure each configured local password file exists. On macOS for
   `personal-private-data`, the expected file is:

```text
~/.personal-private-data/backup-password.txt
```

   If a password file is missing, report the exact path and stop. Do not invent
   a password and do not commit the password file.
8. Read the target repo's `AGENTS.md` when present, then run the shared helper
   `doctor` command to validate local setup.
9. If `doctor` reports only fixable local setup issues, fix them when possible
   and rerun `doctor`. If it reports a missing password file, tell the user the
   exact expected local path and stop.
10. Run the shared helper for pull or push.

Do not require the user to remember helper commands. If they say `hg-git pull`
or `hg-git push`, bootstrap what is missing, then execute the matching helper
workflow.

Natural-language routing:

- If the user asks `hg-git pull`, `pull personal private data`, `sync Postman
  from GitHub`, or equivalent and the target/current/known repo contains
  `.hg-git-private-data.json`, run `private_data.py pull --repo <repo>`.
- If the user asks `hg-git push`, `push personal private data`, `sync Postman
  to GitHub`, or equivalent and the target/current/known repo contains
  `.hg-git-private-data.json`, run
  `private_data.py push --repo <repo> --message "<clear message>"`.
- Do not ask the user to run the helper manually when Codex can execute it.
- Only use raw `git pull`/`git push` for private-data repos when the user
  explicitly asks to bypass the private-data workflow.

Rules:

- Do not add repository-local encryption/decryption scripts.
- Keep plaintext secret paths ignored by Git.
- Store only encrypted secret files in Git.
- Treat configured `plaintext_sync` targets, such as Postman data, as normal Git
  plaintext. Do not encrypt them unless they are explicitly listed under
  `secrets`.
- Avoid needless encrypted-file churn. If a plaintext secret decrypts to the
  same content as the current encrypted file, leave the encrypted file
  unchanged.
- For each new personal private repository, add config only; reuse this tool.
- `pull`/`pull-decrypt` must pull Git, decrypt configured secrets, and install
  plaintext sync targets such as Postman onto the current machine when
  configured, so another machine can pull and use the updated local app data
  immediately.
- `push` must pull latest with `--ff-only`, sync configured plaintext targets
  such as Postman from the current machine into the repo, encrypt configured
  secrets, commit any resulting changes, and push.
- `encrypt-push` is a lower-level command for encrypted secret changes when the
  caller has already handled plaintext sync.

## Update Inventory

At the start of every invocation, inspect all known personal repos unless the user explicitly names one repo.

Before declaring `ai-agent` clean, collect live-source drift:

- `ai-agent`: compare `~/.codex/AGENTS.md` to `AGENTS.md`, and compare each
  public `~/.codex/rules/*.md` file to `rules/*.md`. Exclude
  `rules/default.rules`, backups, reports, local config, and generated cleanup
  files.
- `ai-agent` skills: compare each selected live `~/.codex/skills/<skill>/`
  folder to the corresponding `skills/<skill>/` folder. Exclude caches, local
  config, runtime state, credentials, and unselected skills.
- If drift exists, report it as pending sync even when repo `git status` is
  clean. Do not finish a push request until the drift is either synced,
  deliberately excluded, or explicitly blocked.

For each repo, collect:

- `git remote -v`
- `git branch --show-current`
- `git status --short`
- `git diff --stat`
- `git diff --name-status`
- `git diff --cached --stat`
- `git diff --cached --name-status`
- optional recent context: `git log --oneline -5 --decorate`

Show the user a git-tool-style summary before commit or push:

```text
仓库：<path>
远端：<owner/repo>
分支：<branch>
状态：<clean / staged / unstaged / untracked / mixed>

改动摘要：
<git diff --stat and/or git diff --cached --stat>

文件状态：
<git status --short or git diff --name-status output>

建议动作：
- <commit / stage / inspect / exclude / no action>
```

If a repo is clean, say it is clean. If multiple repos have changes, group the output by repo and ask before committing or pushing more than one repo in the same run unless the user already requested all personal repos.

When the user asks for "像 git 工具一样" or wants details, include the relevant `git diff -- <file>` snippets for small text files. For large, generated, binary, or sensitive-looking files, show only file status and explain why the full diff is omitted.

## Conflict Handling

If `git pull`, `git rebase`, `git merge`, or `git push` reports conflicts:

1. Stop automatic git operations.
2. Run `git status --short` and identify unmerged files.
3. Inspect the conflicted files enough to understand the conflict type.
4. Report before resolving unless the conflict is purely mechanical and obviously safe.

Use this report shape:

```text
冲突仓库：<path>
冲突来源：<pull/rebase/merge/push>
冲突文件：
- <file>: <原因判断>

建议解决：
- <file>: <保留本地 / 保留远端 / 手工合并 / 需要用户确认>

我可以继续处理的部分：
- <safe actions>

需要你确认的部分：
- <semantic or ownership questions>
```

For semantic conflicts in rules, skills, scripts, or public docs, prefer preserving user-authored local intent and integrating remote additions when compatible. Never discard local or remote changes silently.

## Sync Summary

When finished, report:

- repo path and remote
- branch
- commit hash and message, if committed
- pushed or not pushed
- files changed by category
- checks run
- any excluded files or unresolved risks
