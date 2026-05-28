# Rule Fix Workflow

Use this workflow when an agent behavior rule or skill instruction fails. The goal is to change behavior with evidence, not to add more text.

## When To Use It

Use this flow for:

- A rule did not trigger.
- The same mistake happened again after a rule was added.
- A rule is too specific to one project, interface, field, or incident.
- A rule belongs in the wrong file.
- A rule conflicts with another rule.
- A skill instruction changes agent behavior and needs review.

Do not use it for ordinary documentation edits that do not change agent behavior.

## Process

1. Restate the failed behavior.

Write the behavior in reusable terms. Do not start from the exact project name, endpoint name, field name, or one-off incident.

2. Load existing coverage.

Check:

- `AGENTS.md`
- Relevant `rules/*.md`
- Relevant `skills/<name>/SKILL.md`
- Any referenced validation files

3. Classify the failure.

Use one category:

- Trigger problem: the right rule exists but the scenario did not load it.
- Loading problem: the rule file or skill was not read.
- Conflict problem: another rule pushed the agent the other way.
- Validation problem: the test did not catch the behavior.
- Missing rule: no existing rule covers the reusable behavior.

4. Choose the smallest fix.

Prefer editing an existing rule. Add a new rule only when the behavior is reusable and uncovered.

Rules should be short. Avoid project names, internal paths, people names, table names, field names, endpoint names, credentials, or temporary incident details.

5. Validate.

Cover at least:

- Original failure scenario.
- Synonym or paraphrase scenario.
- Reverse scenario that should not trigger.
- Random adjacent scenario.
- Diff review for duplicate, conflicting, or hardcoded wording.

If a skill changed, also run the skill's own focused checks when available.

6. Open a pull request.

The PR should include:

- Failed behavior.
- Existing rule coverage and gap classification.
- Files changed.
- Files intentionally not changed.
- Validation commands and results.
- Remaining risk.

## Review Standard

A rule-fix PR should be rejected if it:

- Adds a long rule without diagnosing existing coverage.
- Hardcodes one project, field, endpoint, person, or incident.
- Duplicates a rule that already exists.
- Changes unrelated rules or skills.
- Claims the rule works without validation evidence.
