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
| `scheduled-scan` | An external scheduler (launchd / cron) periodically reads CLI session logs and proposes candidates | Candidate entry written directly to vault `AgentKnowledge/Inbox` or `AgentKnowledge/Daily` with `source` set to the originating CLI and a real `session_id` for dedupe |
| `review-candidate` | The user asks to approve, archive, delete, or move a candidate | Updated candidate status or target domain |
| `promote` | A candidate may become a reusable rule, skill, template, or checklist | Proposed rule or skill change after separate confirmation |
| `load-approved` | Future work needs reusable personal knowledge | Only user-approved knowledge from the allowlist |

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
3. Produce a candidate log with `status: 候选`.
4. If writing is confirmed and the Obsidian channel is available, write only to `AgentKnowledge/Inbox` or `AgentKnowledge/Daily`.
5. If the user approves a candidate, move it into the smallest matching business domain.
6. If a candidate should affect future agent behavior, ask for separate confirmation before changing `rules/` or this skill.

Current-session rule corrections are a separate hotfix path, not candidate promotion. If the user explicitly says a rule missed, a rule is hard-coded, the same rule failure repeated, or the rule category is wrong, follow project-governance hotfix rules first; optionally capture the failure mode and verification result as an Obsidian candidate after the rule change.

## Candidate Body

Keep candidate entries short and readable, but do not drop key meaning, evidence, sources, or validation boundaries.

- `摘要`: what reusable knowledge was formed
- `关键事实`: the facts needed to understand the note later
- `证据与资料`: evidence refs, source material, or a short readable evidence summary
- `具体问题`: the user feedback, bug, decision gap, or observed issue
- `解决方案`: what changed or should change
- `验证情况`: what was verified and what remains unverified
- `关联判断`: home domain, confirmed related notes, suspected pattern, orphan/repeat judgement
- `待处理`: review checklist or follow-up items

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
type: agent-log
status: 候选
domain: 01-Agent工作台
tags: []
source: codex
related_issues: []
pattern_candidate: ""
---
```

`source` is required and must be one of `codex`, `claude`, `hermes`, `openclaw`; it tags the originating CLI. Scanner-generated candidates may add `session_id` so the sync tool can dedupe and replace stale files; in-session human captures may omit it.

`domain` is the note's single business home, not the storage folder. Use one of `01-Agent工作台`, `02-研发实现`, `03-排查与观测`, `04-需求与文档`, `05-交付与验证`. Notes may be stored under `AgentKnowledge/Inbox/` while still having a non-Inbox `domain`.

Use short Chinese `tags` inferred from the session. Field names may stay English for machine stability, but values should be Chinese unless they are fixed source ids or code identifiers.

Use `related_issues` for confirmed related notes and `pattern_candidate` for a human-readable suspected pattern. Do not use `repeat_key` or `repeat_count`; repeated issues are too fuzzy for a stable key in the default log format.

In `关联判断`, link the home domain to a semantic hub page such as `[[01-Agent工作台/01-Agent工作台|01-Agent工作台]]`. Do not link candidate logs to directory `README.md` files as their home; README links make Obsidian Graph centrality reflect folder documentation instead of meaningful knowledge domains.

Only when the user explicitly corrects, complains, gets angry, insults, or otherwise gives a high-value feedback signal, add:

```yaml
feedback_signal: 纠正
feedback_target: 验证流程
```

Candidate logs do not put credential fields in frontmatter. If a sensitive configuration item matters to the conclusion, describe it in the body with a redacted Chinese phrase such as `测试环境只读账号`; do not include real secrets, connection strings, tokens, or values that can reveal them.

Human-facing bodies must not expose scanner tracking details. Keep `source_key`, raw evidence ids such as `turn_N`/`tool_N`, and sync markers such as `obsidian-log-sync` in scanner JSON, frontmatter, or reports only; candidate body evidence should be a readable natural-language summary.

The default schema must not include `agent_load`, `contexts`, `sensitivity`, `secret_policy`, `secret_refs`, `repeat_key`, `repeat_count`, `simple_tags`, `primary_home`, or `topics`. Do not emit deprecated fields such as `asset_type`, `source_key`, `session_date`, or use `type: knowledge-candidate` / `type: agent-log-candidate`.

The frontmatter field set above and the body section list are the single authoritative schema for both scanner and in-session captures. Adding a new default field requires updating this section first, then the scanner and tests — never the reverse.

`AgentKnowledge/Inbox/候选池.md` is a human guide, not a candidate note. Candidate Base views should exclude it.

Write channels:

- The scheduled scanner writes directly to `AgentKnowledge/Inbox/` or `AgentKnowledge/Daily/` files in the vault. Direct file write is the only supported channel for the scanner.
- In-session captures may use the Obsidian MCP or Local REST API when available; otherwise they fall back to direct file write or output the candidate summary in the reply.
- If no channel is reachable, output the candidate summary in the reply and do not write through another path.
- Daily is a readable date index only. Do not write sessions with no assistant handling, fix, verification, or clear conclusion; Daily body must not include `source_key`, `session_id`, `obsidian-log-sync`, raw evidence ids, `会话ID`, `来源`, `你指出`, or `Agent 处理`.
- Scanner and writer code must block old-schema candidates before writing to Obsidian. If output contains `type: agent-log-candidate`, `status: candidate`, `agent_load`, `domain: Inbox`, `contexts`, `sensitivity`, `secret_policy`, or `secret_refs: []`, fix the generator instead of letting the file through.

## Promotion Rules

Promote sparingly:

- Put durable behavior constraints in `rules/*.md`.
- Put reusable procedures, tools, or references in `skills/personal-knowledge/` or another existing domain skill.
- Do not promote one-off tasks, unverified guesses, private project facts, or sensitive operational details.
- Do not make a candidate affect future agent behavior unless the user explicitly approves the rule or skill change.
- Do not treat a current-session explicit rule correction as an Obsidian promotion; it is already user-approved rule hotfix work and should be verified through the rules test flow.
