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
| `review-candidate` | The user asks to approve, archive, delete, or move a candidate | Updated candidate status or target domain |
| `promote` | A candidate may become a reusable rule, skill, template, or checklist | Proposed rule or skill change after separate confirmation |
| `load-approved` | Future work needs reusable personal knowledge | Only approved, allowlisted, `agent_load: true` knowledge |

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
sensitivity: private
secret_policy: none
secret_refs: []
---
```

If Obsidian MCP, Local REST API, or write permission is unavailable, output the candidate summary in the reply and do not write through another path.

## Promotion Rules

Promote sparingly:

- Put durable behavior constraints in `rules/*.md`.
- Put reusable procedures, tools, or references in `skills/personal-knowledge/` or another existing domain skill.
- Do not promote one-off tasks, unverified guesses, private project facts, or sensitive operational details.
- Do not set `agent_load: true` unless the user explicitly approves future agent loading.
