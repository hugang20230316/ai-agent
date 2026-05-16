# Bug Skill Evolution Template

Use this shared template after a bug task ends.

## 1. What reusable rule did this task expose?

Write one stable action rule. Avoid one-off bug details, internal URLs, credentials, IDs, or table names.

## 2. Should it become part of the skill?

Only promote the rule if it saves meaningful time, avoids repeated wrong attribution, or applies to a repeated environment/tooling issue.

## 3. Where should it live?

- Common behavior: update `SKILL.md`
- Machine-specific behavior: keep it in local config or environment variables
- Repeated mechanical work: update or add the unified Python script

## 4. Cleanup rule

Prefer editing an existing rule over appending another similar rule. Delete stale rules when they are replaced.
