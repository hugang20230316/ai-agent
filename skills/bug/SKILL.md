---
name: bug
description: "Analyze and fix issue-tracker bugs from a configured tracker such as ZenTao. Use when the user provides a bug ID, issue URL, screenshot, reproduction note, or asks to analyze/fix a bug."
---

# Bug

## Tooling

Use the single Python entry point from this skill directory:

```console
python3 scripts/fetch_zentao_bug.py --help
python3 scripts/fetch_zentao_bug.py <bug-id-or-url>
python3 scripts/diagnose_bug_config.py
```

Machine-specific tracker URLs, accounts, passwords, download paths, repo paths, project API base URLs, and test-environment addresses must come from local config, environment variables, or explicit CLI arguments. Do not add platform-specific skill files or wrapper scripts.

Local config is loaded from `bug.local.json` by `scripts/local_config.py`. Project-specific service entries should use `projects.<project-name>.serviceBaseUrl` plus optional aliases/policy text. Treat those values as local-only secrets: use them during investigation, but do not copy internal hosts into public rules, committed docs, or final answers unless the user explicitly asks for that exact value.

When a user provides a test address for one layer of a project, update the local project config as a set: API layer, services layer, Swagger URLs, web base URL, and known upstream service URLs from the same conversation or project docs/config. Do not make the user repeat each related endpoint one by one.

## Trigger Contract

Invoke this skill, instead of answering ad hoc, when the user provides any of these inputs:

- A tracker URL or numeric bug ID, including ZenTao `bug-view-*.html` links.
- A screenshot, pasted response, stack trace, reproduction note, or "接口报错/页面异常/空引用/500/403" style symptom.
- A request to analyze, locate, summarize, or fix a bug, even if the user does not use the exact word "bug".

## Intent Gate

- A screenshot, link, reproduction note, pasted bug content, or "analyze this problem" is analysis-only unless the user explicitly asks to fix or modify code.
- For normal follow-up questions during the same investigation, answer only the question asked and omit unrelated sections such as QA notes unless the user explicitly requests them.
- When the user asks to fix, still produce bug analysis evidence before or alongside the code change.

## Login and Config Gate

When a tracker URL or bug ID is present:

1. Run `python3 scripts/fetch_zentao_bug.py <bug-id-or-url>` first with no inline credentials. Let the script load local config. Treat this as the first evidence gate before code search, database checks, API calls, or hypotheses.
2. If the fetch fails, run `python3 scripts/diagnose_bug_config.py`. It prints only booleans/counts: config paths found, base URL present, username present, password present, project config present. Do not print credentials, tokens, cookies, or internal URLs unless explicitly requested.
3. Only report a login blocker when the diagnostic proves credentials are missing, or when fetch still fails with an authentication/login error after local config was loaded.
4. If fetch succeeds, do not ask the user to configure ZenTao login and do not mention login as a blocker.

## Evidence Workflow

1. Fetch the bug details from the configured tracker whenever a tracker ID or URL is present. Do not skip tracker evidence or treat it as optional because screenshots, code, or user notes are also available.
2. Extract title, module, version, status, reproduction steps, actual result, expected result, attachments, comments, and hidden request parameters.
3. Search the configured repository for the precise route, DTO, method, message, enum, field, or business key from the bug.
4. Trace the shortest request chain that can prove the source by data timeline: visible symptom -> frontend/rendering entry -> service/API endpoint -> persisted data/logs -> upstream API -> first bad output, first bad transform, or blocked evidence.
5. Query only the minimum data source needed to prove the root cause. Use configured MCP tools, logs, database queries, API calls, or read-only CLI checks when they are the direct evidence source.
   - For grey environments, Grafana is the only data evidence source when data lookup is needed. Do not use TiDB or MongoDB MCP for grey data.
   - For test environments, use TiDB and MongoDB MCP tools when those databases are the direct evidence source.
   - When production data can only be queried by the user, provide one self-contained SQL script per request and consolidate related checks into that script when practical. Do not split into multiple scripts if one script can return the needed evidence.
   - If the user says production can run only one query or one statement at a time, provide exactly one directly executable SQL statement. Do not use variables, temporary tables, multiple result sets, or a bundled script. Wait for the result before giving the next statement.
6. Do not call an API just because a URL exists. If code, logs, database rows, or user-provided response data already prove the point, avoid extra API calls. If API evidence is needed and a project API/services/upstream base URL is configured, choose the matching configured layer instead of browser/front-end routes that may disturb other users.
   - For TeacherAI test-environment interface checks, default to the configured Services/RPC layer. Do not switch to the API layer, Web layer, or a similar environment to fill evidence unless the bug itself is about that layer or the user explicitly asks for it.
   - Confirm the current layer contract before calling an endpoint. Fields added by an API layer from login state, gateway context, or user tickets do not automatically exist for Services/RPC calls.
   - When calling TeacherAI Services/RPC endpoints directly, include the complete DTO `Input` business identifiers required to reproduce the same result. Examples include `teacherGuid`, `userGuid`, `schoolGuid`, `taskGuid`, `workGuid`, `paperGuid`, item GUIDs, tenant or school identifiers, depending on the endpoint. If a required field cannot be obtained, report the missing field as a blocker and do not treat the incomplete request's success or failure as valid Services/RPC evidence.
   - If the reported bug is not about API-layer authentication, login state, gateway mapping, or API-to-Services field conversion, do not make an extra unauthenticated API-layer call. Do not include expected no-token responses such as `401` or "not logged in" in the bug conclusion unless that layer is in scope.
7. For every boundary where data may be transformed, capture the endpoint or method name, key input, key output, and whether the value changed there. Include all request fields needed to reproduce the same result, including business scope/user/tenant/teacher/work identifiers when the interface requires them; mask only true secrets such as tokens, cookies, passwords, and session IDs.
8. Classify the issue as code defect, data issue, configuration issue, external dependency, frontend/UI ownership, or blocked evidence.
9. If the user needs to inspect a complete API response, save the raw response outside the target repo and, when a browser preview is useful, serve a read-only static view from a temp directory. Verify the preview page and its dependent JSON/resources before giving the link.
10. During long investigations, send short milestone updates after tracker fetch, missing-evidence requests, code-location discovery, fix-scope decisions, and verification. Do not leave the user guessing whether the work is stalled.

## Fix Workflow

1. If the user asked to fix it, make the smallest code change and run the configured build or test command. For defects caused by stale persisted references, explicitly decide whether the fix is forward-only, data repair, read-side fallback, or a combination, and say which one was implemented.
    - When adding or changing longer local variables, multi-line assignments, or important `if` conditions in the fix, add a short comment on the immediately preceding line that states the business meaning or reason for the branch.
    - Before renaming variables or adding comments, translate raw implementation signals into business meaning. Database sentinel values, enum values, SQL predicates, API fields, and UI wording are evidence, not final terminology.
    - Comments in bug fixes must describe the business meaning or decision reason. Do not use vague placeholders when the relationship is unclear; inspect the surrounding data flow first.
    - After the user corrects business terminology, update all variable names, helper names, comments, and final explanations touched by the fix to use that terminology.
    - When a fix changes one branch of a connected decision chain, review adjacent branches, helper names, and comments in the same chain. Necessary alignment is in scope; unrelated cleanup is not.
    - Do not make users identify every missing comment one by one. When one missing comment is pointed out, review the whole changed block for the same issue.
2. For destructive or data-changing bugs, scan same-class write paths first: deletes, updates, inserts, repository methods, consumers, and endpoints that mutate the same entity or persisted field. Treat read-only display or list paths as risks to mention, not automatic edit scope, unless they directly cause the reported bug or the user asks to change them.
3. Use the user's corrected business terminology in conclusions, comments, and variable names touched by the fix. Do not keep misleading generic terms such as "special page" when the evidence says "front/back side".
4. If the user only asked for analysis, stop after root cause, evidence, impact, and proposed fix. Do not edit files, start implementation work, or treat "look at this" as permission to patch code.
5. Before reporting the fix, scan the diff for unrelated formatting, whitespace, comments, renamed symbols, or files outside the bug scope. Revert your own unrelated edits and call out pre-existing unrelated edits separately.

## Skill Regression Gate

After editing this skill, verify both the rule text and the tracker fetch path:

```console
python3 scripts/diagnose_bug_config.py
python3 scripts/test_bug_skill_contract.py
python3 scripts/test_bug_skill_contract.py --live-bug <known-readable-bug-id>
python3 scripts/test_bug_skill_contract.py --live-url <known-readable-bug-url>
```

The checks cover local login config loading, required output sections, `teacherGuid`/`taskGuid` reproduction fields, and ZenTao bug ID/URL fetch behavior without inline credentials.

Keep bug-skill-specific test notes, fixtures, and cleanup guidance under this skill directory so they can be found and removed with the skill.

## Evidence and Output Gate

Before sending a bug analysis final answer, self-check that the answer contains these sections. Keep the heading even when blocked, and write the exact blocker under it.

1. `原因`: the first bad output, first bad transform, or exact code defect. Do not use "大概率/应该是/可能是" as the conclusion.
2. `接口`: list only distinct boundaries that matter: user-facing route/API, service-layer endpoint or method, upstream endpoint if actually called. Do not split "对外接口/服务接口/代码位置" into redundant headings when they describe the same boundary.
3. `输入参数`: include all fields needed to reproduce the same result. For TeacherAI service-layer calls, include required business identifiers such as `teacherGuid`, `taskGuid`, paper/work/item GUIDs, tenant/user/school identifiers when the interface requires them. Mask only true secrets.
4. `输出结果`: include the actual response status/message/data excerpt and the expected response or contract.
5. `证据`: cite tracker content, code location, database/log/API evidence, and what each piece proves. Separate verified facts, code inference, and blocked evidence.
6. `归属与影响`: classify as code defect, data issue, configuration issue, external dependency, frontend/UI ownership, or blocked evidence; include affected data shape or workflow.
7. `修复状态或建议`: state whether code was changed. If code is changed, distinguish forward-path fix, historical data repair, and query-side fallback. Do not imply existing bad data is repaired unless a migration, repair script, or read-side compatibility path was actually added. If not changed, give the smallest fix and the exact file/method if known.
8. `给测试的总结`: write concise QA notes from the tester's product surface, usually App, mini program, web page, or admin UI click paths. Do not make API names, database tables, log systems, class names, or method names the reproduction entry unless the user explicitly asks for interface/API regression. Include expected/actual, impact, and 1-3 regression points directly tied to this bug. Do not add generic smoke tests.

If any section is missing after self-check, revise the answer before sending it.

This full section set is for final bug reports, handoffs, or when the user asks for a complete conclusion. For normal follow-up questions during the same investigation, answer only the question asked and omit unrelated sections such as QA notes unless the user explicitly requests them.

## Shared Guardrails

- Never commit real tracker URLs, internal IPs, usernames, passwords, tokens, cookies, browser sessions, or machine paths.
- If the user pastes a password, token, cookie, or session value during a bug investigation, do not repeat it. Use it only as local evidence when necessary and remind the user to revoke or rotate it.
- Never leave bug-test artifacts in the target repository. Raw responses, screenshots, generated previews, logs, and caches belong in a temp/private location unless the user explicitly asks for a repo artifact.
- Do not present a POST/API endpoint as a Web preview. If a service must stay up so the user can inspect evidence, keep it running until the user confirms they are done, or clearly say it has been stopped.
- Do not stop at generic guesses. Words like "probably", "likely", or "大概率" are only allowed for explicitly marked hypotheses; a root-cause conclusion must cite the concrete request, response, code path, log row, or database row that proves it.
- When the user asks to trace the source, do not stop at an intermediate service that merely forwards or stores data. Continue upstream until the first bad output, the first bad transform, or a concrete blocker is identified.
- When adding long-term learning, update an existing rule first instead of appending duplicate guidance.
