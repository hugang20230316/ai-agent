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
| `capture` | A task reaches a meaningful node or the user asks to summarize, record, or save knowledge | Redacted candidate summary |
| `write-candidate` | The user confirms writing a candidate to Obsidian, or explicitly asks for immediate candidate write | Candidate entry in `AgentKnowledge/Inbox` or `AgentKnowledge/Daily` |
| `review-candidate` | The user asks to approve, archive, delete, or move a candidate | Updated candidate status or target domain |
| `promote` | A candidate may become a reusable rule, skill, template, or checklist | Proposed rule or skill change after separate confirmation |
| `load-approved` | Future work needs reusable personal knowledge | Only approved, allowlisted, `agent_load: true` knowledge |

## Workflow

1. Decide whether the content has long-term value.
2. Filter secrets, raw logs, raw tool output, company details, internal URLs, accounts, tokens, cookies, and local absolute paths.
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

Do not attach full chat, command output, logs, interface responses, screenshots, credentials, or private project details.

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
sensitivity: redacted
---
```

If Obsidian MCP, Local REST API, or write permission is unavailable, output the candidate summary in the reply and do not write through another path.

## Promotion Rules

Promote sparingly:

- Put durable behavior constraints in `rules/*.md`.
- Put reusable procedures, tools, or references in `skills/personal-knowledge/` or another existing domain skill.
- Do not promote one-off tasks, unverified guesses, private project facts, or sensitive operational details.
- Do not set `agent_load: true` unless the user explicitly approves future agent loading.
