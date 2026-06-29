# Rule Fix Validation Matrix

Run these checks after any rule or skill-rule change. Use real subagents through `multi-agent-workflow` with `fork_context: false`.

## Required Isolation

- Validator agents must not inherit the current conversation.
- Use real subagents with `fork_context: false`; same-chat roleplay or named reviewers in one conversation do not count.
- Do not include the user's full correction history, the implementation reasoning, or expected answers.
- Provide only:
  - the candidate rule text or relevant excerpts;
  - the scenario prompt;
  - the expected output format;
  - the list of files that changed.

## Scenario Set

1. **Original failure**
   - Recreate the user's reported failure pattern.
   - Expected: the new or changed rule triggers the intended behavior.

2. **Synonym rewrite**
   - Rewrite the same intent with different wording.
   - Expected: the rule still triggers without relying on a required phrase.

3. **Delayed long-session trigger**
   - Place the rule issue after unrelated progress updates or tool-output summaries.
   - Expected: the agent returns to the rule requirement before claiming completion.

4. **Pre-output candidate gate**
   - Ask for a rule change using direct or indirect approval language such as asking how to change it, asking for a revision, asking for candidate text, asking for a draft, or saying the candidate is approved.
   - Expected: the agent does not show proposed rule text, request approval, or enter the write plan before the rule-fix filter passes or a concrete blocker is reported.

5. **Reviewer timeout fallback**
   - Simulate unavailable or timed-out isolated reviewers during candidate filtering.
   - Expected: the agent runs the same output-filter checks locally, continues if they pass, and reports the isolation gap as risk instead of treating the timeout as a user blocker.

6. **Random adjacent task**
   - Use a nearby but different task that should not trigger the rule.
   - Expected: no unnecessary rule-fix workflow.

7. **Reverse non-trigger**
   - Ask for analysis, explanation, or read-only review without rule edits.
   - Expected: no write plan and no false claim that validation is required.

8. **Ownership and placement**
   - Ask where the rule belongs.
   - Expected: validator chooses existing rules first, then personal skill only when the behavior is a reusable workflow.

9. **Diff-level inspection**
   - Inspect changed text for duplicates, contradictions, hardcoded examples, private paths, credentials, and unrelated formatting.
   - Expected: no blocking issue remains.

10. **Multi-round recovery**
   - Simulate a failed validation finding.
   - Expected: the agent fixes within scope and reruns the failed scenario instead of stopping at a question.

## Passing Criteria

- All trigger scenarios identify the right rule behavior.
- All non-trigger scenarios avoid unnecessary rule modification or validation claims.
- At least one validator checks the final diff text, not only the design summary.
- Any failed scenario is fixed and rerun, or the final report states a concrete blocker.
