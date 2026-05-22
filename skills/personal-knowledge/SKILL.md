---
name: personal-knowledge
description: Use when the user asks to record, summarize, review, approve, write to Obsidian, manage personal knowledge, handle agent logs, or promote a knowledge item into rules or skills.
---

# Personal Knowledge

## Scope

Use one skill for all personal knowledge work. Do not create separate knowledge skills such as capture, inbox, review, daily, or promotion skills. Add new capability here as a subfunction when it belongs to the Codex + Obsidian personal knowledge flow.

Follow the active personal knowledge, privacy, skill, and project-governance rules before writing or promoting anything.

## Subfunctions

| Subfunction | Use When | Result |
| --- | --- | --- |
| `capture` | A task reaches a meaningful node or the user asks to summarize, record, or save knowledge | Private candidate summary |
| `write-candidate` | The user confirms writing a candidate to Obsidian, or explicitly asks for immediate candidate write | Candidate entry in `AgentKnowledge/Inbox` or `AgentKnowledge/Daily` |
| `scheduled-scan` | An external scheduler (launchd / cron) periodically reads CLI session logs and proposes candidates | Candidate entry written directly to vault `AgentKnowledge/Inbox` or `AgentKnowledge/Daily` with `source` set to the originating CLI, `contexts` containing `scanner`, and a real `session_id` |
| `review-candidate` | The user asks to approve, archive, delete, or move a candidate | Updated candidate status or target domain |
| `promote` | A candidate may become a reusable rule, skill, template, or checklist | Proposed rule or skill change after separate confirmation |
| `load-approved` | Future work needs reusable personal knowledge | Only approved, allowlisted, `agent_load: true` knowledge |

## CLI Sources

This skill covers four CLIs. Each has its own session log location used by the scheduled scanner; the in-session capture flow is identical.

| Source | In-session capture | Session log root for the scanner |
| --- | --- | --- |
| `codex` | Codex CLI | `~/.codex/sessions/` |
| `claude` | Claude Code | `~/.claude/projects/-Users-hugang/*.jsonl` |
| `hermes` | Hermes | `$HERMES_HOME/sessions/` |
| `openclaw` | OpenClaw | `~/.claude/projects/-private-*-openclaw-*/*.jsonl` |

The scanner uses `source` to tag candidates and `session_id` (derived from the JSONL filename) to deduplicate against earlier scans and against Claude auto-memory.

## Workflow

1. Decide whether the content has long-term value.
2. Preserve useful private context for Obsidian by default. Only replace credential values that can directly grant access, such as production passwords, tokens, cookies, sessions, API keys, private keys, connection strings, recovery codes, verification codes, and seed phrases. Use `secret_ref` only as a reference name, never as a secret store.
3. Produce a candidate summary with `status: candidate` and `agent_load: false`.
4. If writing is confirmed and the Obsidian channel is available, write only to `AgentKnowledge/Inbox` or `AgentKnowledge/Daily`.
5. If the user approves a candidate, move it into the smallest matching business domain.
6. If a candidate should affect future agent behavior, ask for separate confirmation before changing `rules/` or this skill.

## Candidate Body

Keep candidate entries short and readable:

- `摘要`: what reusable knowledge was formed
- `决策`: user-confirmed preference or boundary
- `可复用经验`: workflow, test strategy, release lesson, or tool limit
- `待确认`: where it should live and whether it should become a rule or skill

Do not attach full chat, full command output, oversized logs, oversized interface responses, screenshots, or browser sessions as the body of the note.

Keep useful engineering context when it is needed to make the note actionable:

- file paths, repo names, module names, symbols, test commands, and verification results
- changed behavior, root cause category, implementation decision, and rollback or regression points
- bug, feature, release, environment, QA, and internal workflow context that makes the note useful later

Do not reject an otherwise useful private Obsidian note because it includes internal paths, internal URLs, project names, business fields, or debugging context. Keep those details when they make the note actionable. For credential-like content, replace only the secret value and keep the surrounding lesson.

Apply stricter redaction only at export boundaries: public rules, public docs, GitHub sync, commits, final user-facing excerpts, non-private tools, or promotion into reusable skills.

## Secret References

Use `secret_ref` when a private note needs to remember which production credential or configuration item was involved. It is a pointer for humans, not a value for agents to resolve automatically.

Rules:

- write stable reference names such as `prod-db-readonly`, not real usernames, passwords, tokens, cookies, connection strings, or URL parameters
- keep the incident context, root cause, rotation status, and verification result in the note
- do not fetch or expand a `secret_ref` unless the user explicitly asks and the lookup uses a private local secret source
- when exporting or promoting a note, keep only generalized wording unless the target is still private

## Obsidian Writes

Default metadata:

```yaml
---
type: agent-log-candidate
status: candidate
agent_load: false
domain: Inbox
contexts: []
source: codex
session_id: ""
sensitivity: private
secret_policy: none
secret_refs: []
---
```

`source` is required and must be one of `codex`, `claude`, `hermes`, `openclaw`; it tags the originating CLI. Scanner-generated candidates use the originating CLI as `source` and add `scanner` to `contexts`. `session_id` is required for scanner-generated candidates; in-session human captures may leave it empty.

The frontmatter field set above is the single authoritative schema for both scanner and in-session captures. Do not emit deprecated fields such as `asset_type`, `source_key`, `session_date`, or use `type: knowledge-candidate`; the canonical `type` value is `agent-log-candidate`. Adding a new field requires updating this section first, then the scanner — never the reverse.

`AgentKnowledge/Inbox/` directory listing IS the candidate index. Do not maintain a separate `候选池.md` or any other manual index file inside `Inbox/`; any such legacy file is out of the flow and should be ignored or removed.

Write channels:

- The scheduled scanner writes directly to `AgentKnowledge/Inbox/` or `AgentKnowledge/Daily/` files in the vault. Direct file write is the only supported channel for the scanner.
- In-session captures may use the Obsidian MCP or Local REST API when available; otherwise they fall back to direct file write or output the candidate summary in the reply.
- If no channel is reachable, output the candidate summary in the reply and do not write through another path.

## Promotion Rules

Promote sparingly:

- Put durable behavior constraints in `rules/*.md`.
- Put reusable procedures, tools, or references in `skills/personal-knowledge/` or another existing domain skill.
- Do not promote one-off tasks, unverified guesses, private project facts, or sensitive operational details.
- Do not set `agent_load: true` unless the user explicitly approves future agent loading.
