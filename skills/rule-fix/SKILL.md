---
name: rule-fix
description: Use when creating, modifying, deleting, explaining, reviewing, or validating agent behavior rules. Read-only explanation or review stays in diagnosis mode; behavior validation runs isolated validation without writes; create, modify, or delete tasks enter the full write-plan, diff, and validation workflow.
---

# Rule Fix

Use this skill for creating, modifying, deleting, explaining, reviewing, or validating agent behavior rules. This includes `rules/*.md`, project `AGENTS.md`, project `.codex/rules/`, and personally maintained skill instructions that constrain agent behavior.

Do not treat rule changes as ordinary Markdown edits. The goal is to change behavior with evidence, not to add text. Read-only explanation or review stays in diagnosis mode and must not enter write steps unless the user authorizes edits.

## Workflow

1. **Load rules**
   - Read the relevant existing rule files and any affected `SKILL.md`.
   - Also read communication, skill, project governance, and testing rules when the task is a correction or hotfix.

2. **Choose mode**
   - For read-only explanation or review, diagnose and report findings only.
   - For behavior validation without edits, run the isolated validation gate without write steps.
   - For creating, modifying, or deleting rules, continue through the write and validation gates.

3. **Diagnose coverage**
   - Restate the behavior being constrained.
   - List existing rules that already cover it.
   - Classify the failure as trigger, loading, conflict, validation, or missing rule.
   - Prefer fixing an existing rule over adding another rule.

4. **Review the candidate before approval**
   - Before asking the user to approve a rule draft or rule-fix write plan, run `multi-agent-workflow` with real isolated subagents to review the proposed rule for brevity, trigger reliability, clarity, duplication, conflicts, and hardcoded incident residue.
   - Fix and re-review blocking findings; if real isolated subagents are unavailable, do not simulate them and report the blocker instead of asking approval of an unreviewed draft.

5. **Show the edit plan before writing**
   - List every file you intend to change.
   - For each file, state the purpose and the planned change.
   - State the related rules, skills, AGENTS files, docs, or config you will not change and why.
   - Do not include files unrelated to the rule fix in the plan.
   - Treat an exact plan as specific file paths, per-file purpose, planned rule effect, and excluded files; the write scope is limited to that plan.
   - Wait for user approval before modifying files, unless the user has already approved that exact plan.
   - A generic "continue" only approves writing when it directly follows an exact plan; otherwise continue diagnosis or planning without edits.

6. **Write the smallest rule change**
   - Keep rules short and reusable.
   - Do not write project names, one-off field names, endpoint names, people names, local paths, credentials, or tool-specific hacks into public rules.
   - If the rule belongs in a personal skill, place the source under `ai-agent/skills/<skill-name>/`; tool-side skill directories should be symlinks or config references.

7. **Self-check the diff**
   - Check `git diff --stat` and the relevant file diffs.
   - Verify no unrelated formatting, duplicate rules, conflicting rules, hardcoded scenario residue, or unnecessary files were added.
   - Verify `SKILL.md` stays concise; move long matrices to `references/`.

8. **Run isolated validation**
   - Use `multi-agent-workflow`.
   - Spawn real subagents with `fork_context: false`; same-chat roleplay does not count.
   - Give validators only the minimal rule text, scenario prompts, and output contract needed for validation.
   - Follow `references/validation-matrix.md`.

9. **Fix and revalidate**
   - If validation finds a defect and the change is still in scope, fix it and rerun the failed scenarios.
   - Final status must separate facts, inferences, validation evidence, and uncovered risk.

## Output Requirements

- Before writing: changed files, reason, planned rule effect, and excluded files.
- After writing: changed files, diff summary, validation topology, scenario results, and remaining risk.
- For read-only review: existing coverage, gaps, recommendation, and whether a write workflow would be needed if the user approves edits.
- Never claim a rule is effective without naming the trigger, behavior, validation evidence, and uncovered boundary.
