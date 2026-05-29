---
name: personal-knowledge
description: Use when the user asks to record, summarize, review, approve, write to Obsidian, manage personal knowledge, handle agent logs, or promote a knowledge item into rules or skills.
---

# Personal Knowledge

## Scope

Use one skill for all personal knowledge work. Do not create separate knowledge skills such as capture, inbox, review, daily, or promotion skills. Add new capability here as a subfunction when it belongs to the Codex + Obsidian personal knowledge flow.

Follow the active personal knowledge, privacy, skill, and project-governance rules before writing or promoting anything.

For the current Obsidian vault layout, read `references/obsidian-structure.md` before changing vault structure, write paths, templates, Base views, or Canvas workspaces. If the reference does not exist yet, create it as part of the initial structure documentation or the structure change.

## Subfunctions

| Subfunction | Use When | Result |
| --- | --- | --- |
| `capture` | A task reaches a meaningful node or the user asks to summarize, record, or save knowledge | Private candidate summary |
| `write-candidate` | The user confirms writing a candidate to Obsidian, or explicitly asks for immediate candidate write | Candidate entry in `AgentKnowledge/Inbox/YYYY-MM-DD/<title>.md` |
| `scheduled-scan` | An external scheduler (launchd / cron) periodically reads CLI session logs and proposes candidates | Candidate entry written directly to vault `AgentKnowledge/Inbox/YYYY-MM-DD/<title>.md` with `source` set to the originating CLI and a real `session_id` for dedupe |
| `review-candidate` | The user asks to approve, archive, delete, or move a candidate | Updated candidate status or target domain |
| `promote` | A candidate may become a reusable rule, skill, template, or checklist | Proposed rule or skill change after separate confirmation |
| `load-approved` | Future work needs reusable personal knowledge | Only user-approved knowledge from the allowlist |

## CLI Sources

This skill can cover multiple agent CLIs. Each source has its own session log location declared by local private config, environment variables, or the scheduler; the in-session capture flow is identical.

| Source | In-session capture | Scanner log source |
| --- | --- | --- |
| `codex` | Codex CLI | Local private config |
| `claude` | Claude Code | Local private config |
| `hermes` | Hermes | Local private config |
| `openclaw` | OpenClaw | Local private config |

The scanner uses `source` to tag candidates and `session_id` (derived from the JSONL filename) to deduplicate against earlier scans and against Claude auto-memory.

## Workflow

1. Decide whether the content has long-term value.
2. Preserve useful private context for Obsidian by default. Only replace credential values that can directly grant access, such as production passwords, tokens, cookies, sessions, API keys, private keys, connection strings, recovery codes, verification codes, and seed phrases. Use `secret_ref` only as a reference name, never as a secret store.
3. Produce a candidate log with `status: 候选`.
4. If writing is confirmed and the Obsidian channel is available, write only to `AgentKnowledge/Inbox/YYYY-MM-DD/<title>.md`.
5. If the user approves a candidate, set `status: 已采纳`; the lifecycle step moves it to `AgentKnowledge/Daily/YYYY-MM-DD/<title>.md`.
6. If a candidate should affect future agent behavior, ask for separate confirmation before changing `rules/` or this skill.

Current-session rule corrections are a separate hotfix path, not candidate promotion. If the user explicitly says a rule missed, a rule is hard-coded, the same rule failure repeated, or the rule category is wrong, follow project-governance hotfix rules first; optionally capture the failure mode and verification result as an Obsidian candidate after the rule change.

AI must decide candidate `log_kind`, `domain`, `tags`, `related_issues`, and useful body sections from evidence. Do not create human tasks asking the user to review those fields, or to decide whether an item should become a rule, skill, or formal knowledge by default. Human review is reserved for explicit approval actions such as approve, archive, delete, merge, or a separate confirmed promotion to rules/skills.

## Candidate Body

Keep candidate entries short and readable, but do not drop key meaning, evidence, sources, or validation boundaries.

Every note has `log_kind` and `摘要`. After that, use only the sections that fit the log kind:

- `feedback`: `反馈`, `暴露的问题`, `处置`, `规则影响`, `关联`
- `incident`: `现象`, `原因`, `处理`, `验证`, `关联`
- `change`: `修改`, `验证`, `影响`, `关联`
- `decision`: `决策`, `依据`, `影响`, `关联`
- `workflow`: `流程`, `约束`, `触发条件`, `验证方式`, `关联`
- `research`: `结论`, `依据`, `适用边界`, `关联`
- `plan`: `方案`, `取舍`, `下一步`, `关联`

Do not force all notes into fixed fields such as `关键事实`, `证据与资料`, `具体问题`, `解决方案`, `验证情况`, and `关联判断`. Do not write a generic `待处理` section. A real follow-up belongs in `下一步`, and only for actionable work that will actually continue.

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
log_kind: feedback
domain: 01-Agent工作台
tags: []
source: codex
session_id: "real-session-id"
created_at: "2026-05-28T12:34:56+08:00"
reviewed_at: ""
review_count: 0
evidence_hash: "content-hash"
lifecycle_reason: ""
related_issues: []
duplicate_of: []
---
```

`log_kind` must be one of `feedback`, `incident`, `change`, `decision`, `workflow`, `research`, or `plan`. `source` is required and must be one of `codex`, `claude`, `hermes`, `openclaw`; it tags the originating CLI. Scanner-generated candidates must include a real `session_id` so the sync tool can dedupe and replace stale files.

`created_at` must include date and time, at least to seconds. Do not use date-only values such as `2026-05-28`.

`domain` is the note's single business home, not the storage folder. Use one of `01-Agent工作台`, `02-研发实现`, `03-排查与观测`, `04-需求与文档`, `05-交付与验证`. Notes may be stored under `AgentKnowledge/Inbox/YYYY-MM-DD/` while still having a non-Inbox `domain`.

Use short Chinese `tags` inferred from the session. Field names may stay English for machine stability, but values should be Chinese unless they are fixed source ids or code identifiers.

Use `related_issues` only for confirmed related notes. Do not use `pattern_candidate`, `repeat_key`, or `repeat_count`; suspected patterns belong in the appropriate body section such as `关联`, `依据`, or `规则影响`.

The generator must fill `domain`, `tags`, `related_issues`, and section content itself from available evidence. Empty related notes are acceptable; do not turn missing relations into a human review checkbox.

Only when the user explicitly corrects, complains, gets angry, insults, or otherwise gives a high-value feedback signal, add:

```yaml
feedback_signal: 纠正
feedback_target: 验证流程
```

Candidate logs do not put credential fields in frontmatter. If a sensitive configuration item matters to the conclusion, describe it in the body with a redacted Chinese phrase such as `测试环境只读账号`; do not include real secrets, connection strings, tokens, or values that can reveal them.

Human-facing bodies must not expose scanner tracking details. Keep `source_key`, raw evidence ids such as `turn_N`/`tool_N`, and sync markers such as `obsidian-log-sync` in scanner JSON, frontmatter, or reports only; candidate body evidence should be a readable natural-language summary.

The default schema must not include `agent_load`, `contexts`, `sensitivity`, `secret_policy`, `secret_refs`, `repeat_key`, `repeat_count`, `simple_tags`, `primary_home`, or `topics`. Do not emit deprecated fields such as `asset_type`, `source_key`, `session_date`, or use `type: knowledge-candidate` / `type: agent-log-candidate`.

Do not add version fields to personal knowledge notes. This is a new personal knowledge base, not a published versioned product.

The frontmatter field set above and the body section list are the single authoritative schema for scanner output. Adding a new default field requires updating this section first, then the scanner and tests — never the reverse.

`AgentKnowledge/Inbox/候选池.md` is a human guide, not a candidate note. Candidate Base views should exclude it.

Write channels:

- The scheduled scanner writes directly to `AgentKnowledge/Inbox/YYYY-MM-DD/<title>.md` files in the vault. Direct file write is the only supported channel for the scanner. New scanner output must not use flat paths such as `AgentKnowledge/Inbox/YYYY-MM-DD-title.md`.
- In-session captures may use the Obsidian MCP or Local REST API when available; otherwise they fall back to direct file write or output the candidate summary in the reply.
- If no channel is reachable, output the candidate summary in the reply and do not write through another path.
- Daily stores only approved candidate notes under `AgentKnowledge/Daily/YYYY-MM-DD/<title>.md`. Generated logs, timer output, quality-gate output, and pending files must not write Daily directly.
- Daily notes must not include candidate-index text such as `查看候选`, `进入 Inbox`, or `状态：候选`; they also must not include `source_key`, `session_id`, `obsidian-log-sync`, raw evidence ids, `会话ID`, `来源`, `你指出`, or `Agent 处理`.
- Scanner and writer code must block old-schema candidates before writing to Obsidian. If output contains `type: agent-log-candidate`, `status: candidate`, `agent_load`, `domain: Inbox`, `contexts`, `sensitivity`, `secret_policy`, or `secret_refs: []`, fix the generator instead of letting the file through.

## Vault Structure Maintenance

Keep the vault structure reference in `references/obsidian-structure.md` in sync with structural changes. Update it when changing `AgentKnowledge` top-level layout, the five business domains, `Inbox`, `Daily`, `Templates`, Base views, Canvas workspaces, template files, or supported write paths.

Do not update the structure reference for ordinary candidate notes, daily index pages, or single knowledge notes inside a business domain.

## Promotion Rules

Promote sparingly:

- Put durable behavior constraints in `rules/*.md`.
- Put reusable procedures, tools, or references in `skills/personal-knowledge/` or another existing domain skill.
- Do not promote one-off tasks, unverified guesses, private project facts, or sensitive operational details.
- Do not make a candidate affect future agent behavior unless the user explicitly approves the rule or skill change.
- Do not treat a current-session explicit rule correction as an Obsidian promotion; it is already user-approved rule hotfix work and should be verified through the rules test flow.
- When the current session already changed rules or skills, record the changed files, behavior boundary, and verification state if useful; do not ask again whether the same issue should be promoted.
