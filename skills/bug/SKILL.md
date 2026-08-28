---
name: bug
description: "当用户提供缺陷编号、问题链接、截图、复现说明或报错信息，或要求分析、定位、修复缺陷时使用。"
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

Local config is loaded as a single authoritative `bug.local.json` by `scripts/local_config.py`: `$CODEX_SKILL_CONFIG_DIR/bug.local.json` when that environment variable is set, otherwise `~/.codex/local/bug.local.json`. Do not scan project `.codex/local/` directories for this skill. Project-specific entries should live under flat `projects.<project-name>` objects with fields such as `repoPath`, `webBaseUrl`, `apiBaseUrl`, `swaggerUrl`, `aliases`, and optional policy text. Project entries in `bug.local.json` stay flat. Do not add `resources` or `workflows`; unknown project fields are allowed but ignored by the skill except for alias matching and read-only project field groups. Treat project values as local-only secrets: use them during investigation, but do not copy internal hosts into public rules or committed docs. Diagnostics and tests must output only booleans, counts, and group names, never real local-only URL or path values. Final answers redact local-only values by default unless the user explicitly asks for exact values and the task needs them.

When a user explicitly asks to save or update project bug-investigation config, group related known layer addresses from the same conversation or project-local docs. Otherwise, use discovered addresses for the current investigation only and do not persist them.

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
   - If the user asks to check logs or runtime evidence without naming an environment, treat the target as the test environment by default.
   - For test environments, use the configured or known test-environment data source first. When TiDB or MongoDB MCP carries the relevant logs or data evidence, discover and execute the matching MCP query before any same-environment read-only fallback; record the MCP failure reason when blocked. Do not escalate test-environment evidence to Grafana, grey, or online sources unless the user explicitly changes the target environment or project evidence confirms that environment.
   - For grey environments, Grafana is the only data evidence source when data lookup is needed. Do not use TiDB or MongoDB MCP for grey data.
   - When the user names online, production, or online-equivalent environments, do not call a database MCP unless it is proven to map to that environment; if production data can only be queried by the user, provide SQL and wait for the result.
   - For online or production logs, use Grafana when log evidence is needed; if production data can only be queried by the user, follow the production SQL rules below.
   - When production relational-database evidence can only be queried by the user, stop at that evidence stage and provide exactly one directly executable, variable-free, read-only SQL statement per turn, limited to the business object and time window under investigation; wait for the result before continuing. If the safe business identifier or time window is missing, report the exact blocker and do not issue broad SQL. For logs or non-relational evidence, use the configured source instead of forcing SQL. Do not use variables, temporary tables, multiple result sets, bundled scripts, INSERT, UPDATE, DELETE, MERGE, DDL, write functions, or sensitive fields; do not add a usage explanation.
6. Do not call an API just because a URL exists. If code, logs, database rows, or user-provided response data already prove the point, avoid extra API calls. If API evidence is needed and a project API/services/upstream base URL is configured, choose the matching configured layer instead of browser/front-end routes that may disturb other users.
   - Before calling a project endpoint, confirm the target layer and authentication/context contract from local config or project rules.
   - Confirm the current layer contract before calling an endpoint. Fields added by another layer from login state, gateway context, or user tickets do not automatically exist on the target layer.
   - Include the complete request object required to reproduce the same result. If required context or identifiers are missing, report the blocker and do not treat the incomplete request's success or failure as valid evidence.
   - If the reported bug is not about authentication, login state, gateway mapping, or cross-layer field conversion, do not make extra calls to another layer just to fill the report.
7. For every boundary where data may be transformed, capture the endpoint or method name, key input, key output, and whether the value changed there. Include all request fields needed to reproduce the same result; mask only true secrets such as tokens, cookies, passwords, and session IDs.
8. Classify the issue as code defect, data issue, configuration issue, external dependency, frontend/UI ownership, or blocked evidence.
9. If the user needs to inspect a complete API response, save the raw response outside the target repo and, when a browser preview is useful, serve a read-only static view from a temp directory. Verify the preview page and its dependent JSON/resources before giving the link.
10. During long investigations, send short milestone updates after tracker fetch, missing-evidence requests, code-location discovery, fix-scope decisions, and verification. Do not leave the user guessing whether the work is stalled.

## 异步事件溯源排查

当问题语义涉及异步任务、作业、消息、回调、轮询、最终一致、延迟持久化、重试、重复投递或乱序处理时，使用本流程，不要求用户必须使用这些固定词语。同步请求、纯界面展示、认证或网络故障、单库静态数据问题不要启动本流程，除非后续代码或运行证据显示存在异步边界。

触发后：

1. 先阅读 [references/event-sourcing-investigation.md](references/event-sourcing-investigation.md)，按“事件生产 -> 消息投递 -> 消费者处理 -> 回调或后续事件 -> 持久化写入 -> 用户可见读取”重建时间线。这是一种排查方法，不表示系统一定存在不可变事件存储。
2. 对每一跳记录服务或日志源、业务标识，以及实际存在的任务/消息/Trace/回调标识、事件发生时间、处理时间、观测时间、输入输出变化和证据状态。逐跳映射标识；存在并发运行、租户、重试或重复消息时，不能只按业务标识关联。
3. 将历史证据与当前可变快照分开。当前记录、成功重试或空队列不能抹去之前的删除、失败或延迟消息；必须注明每个观察结果对应的时间和来源。
4. 使用当前代码解释历史行为前，先把日志时间窗与部署版本（提交、镜像标签或发布版本）绑定。无法绑定时报告证据缺口，不得下版本特定的根因结论。
5. 将查询 0 命中视为有范围限定的结果。宣称没有证据前，先检查服务或日志源、日期分片或集合、环境和时间窗映射；查错源或查错日期是证据阻塞，不是没有事件的证明。
6. 按参考文件逐项回答固定问题和状态字段，同时遵守现有的环境数据源、生产 SQL、最小数据量和默认不创建事故文件规则。

## Fast Online Investigation

When the user explicitly names an online, production, prod, live, or 正式 environment (or project evidence confirms it), use this short path unless the user requests a detailed report:

1. Locate the business object and the smallest production time window.
2. Check business invariants before analyzing downstream amplification. If an invariant is abnormal, trace upstream by data timeline to the first bad output, bad transform, or permission/evidence blocker. Reading an interface contract needed to define the invariant or confirm a transform is part of this step.
3. After the root-cause boundary is proven or blocked, inspect API and display/filter code only to explain how the downstream symptom was amplified. If an upstream invariant violation is proven, treat downstream filtering or omission as impact, not the root cause. Do not label a downstream symptom as the upstream root cause.
4. Run every other authorized read-only command yourself. Query only one minimum, independently observable source for the current evidence stage at a time. If it has no hit, is unavailable, or requires user permissions, record that blocker and request the next necessary evidence; do not broaden the search or continue dependent inference.
5. Keep each stage result to one sentence that states the current hit or blocker. Stop naturally once cause, downstream impact, evidence gap, and repair or unblocking direction are all explicit; do not fill a missing stage with a hypothesis.
6. Do not proactively create report files, reproduction scripts, or long process narratives. Create a named artifact only when the user explicitly asks for it.

## Fix Workflow

1. If the user asked to fix it, first identify the repair layer: network/client environment, DNS/proxy/VPN/certificate, gateway/routing, running service state, deployment/configuration, data, or code. Site access, connectivity, Swagger page, and URL reachability failures default to runtime/network repair; do not edit repository code or deployment configuration from that wording alone. If evidence points to code or deployment configuration and the latest user instruction has not explicitly authorized that write layer, state the evidence, exact write target, and impact, then wait for confirmation before editing.
2. After code editing is explicitly authorized, make the smallest code change and run the configured build or test command. For defects caused by stale persisted references, explicitly decide whether the fix is forward-only, data repair, read-side fallback, or a combination, and say which one was implemented.
    - Before editing, define the broken behavior as a workflow, not as one method or endpoint. Trace the places that use the same business rule, especially writes, reads, display and downstream effects, and decide whether each place needs a change or only a recorded risk.
    - Before reporting the fix as complete, re-check the workflow from entry to persisted state and back through user-visible reads. If any related path is not checked, call it out as remaining risk instead of implying the bug is fully fixed.
    - If verification exposes another fixable failure in the same authorized bug workflow, continue fixing and rerun verification. Stop to ask only when the next action needs new authorization, destructive data changes, credentials, or evidence the agent cannot access.
    - When adding or changing longer local variables, multi-line assignments, or important `if` conditions in the fix, add a short comment on the immediately preceding line that states the business meaning or reason for the branch.
    - Before renaming variables or adding comments, translate raw implementation signals into business meaning. Database sentinel values, enum values, SQL predicates, API fields, and UI wording are evidence, not final terminology.
    - Comments in bug fixes must describe the business meaning or decision reason. Do not use vague placeholders when the relationship is unclear; inspect the surrounding data flow first.
    - After the user corrects business terminology, update all variable names, helper names, comments, and final explanations touched by the fix to use that terminology.
    - When a fix changes one branch of a connected decision chain, review adjacent branches, helper names, and comments in the same chain. Necessary alignment is in scope; unrelated cleanup is not.
    - Do not make users identify every missing comment one by one. When one missing comment is pointed out, review the whole changed block for the same issue.
3. For destructive or data-changing bugs, scan same-class write paths first: deletes, updates, inserts, repository methods, consumers, and endpoints that mutate the same entity or persisted field. Treat read-only display or list paths as risks to mention, not automatic edit scope, unless they directly cause the reported bug or the user asks to change them.
4. Use the user's corrected and evidence-confirmed business terminology in conclusions, comments, and variable names touched by the fix. Do not keep misleading generic terms.
5. If the user only asked for analysis, stop after root cause, evidence, impact, and proposed fix. Do not edit files, start implementation work, or treat "look at this" as permission to patch code.
6. Before reporting the fix, scan the diff for unrelated formatting, whitespace, comments, renamed symbols, or files outside the bug scope. Revert your own unrelated edits and call out pre-existing unrelated edits separately.

## Skill Regression Gate

After editing this skill, verify both the rule text and the tracker fetch path:

```console
python3 scripts/diagnose_bug_config.py
python3 scripts/test_bug_skill_contract.py
python3 scripts/test_bug_skill_contract.py --live-bug <known-readable-bug-id>
python3 scripts/test_bug_skill_contract.py --live-url <known-readable-bug-url>
```

这些检查覆盖本机登录配置、必需输出章节、复现输入说明、异步事件溯源参考文件及其脱敏边界，以及不带内联凭据的禅道缺陷编号/链接抓取行为。

Keep bug-skill-specific test notes, fixtures, and cleanup guidance under this skill directory so they can be found and removed with the skill.

## Evidence and Output Gate

Before sending a bug analysis final answer, repair status summary, handoff, or complete conclusion, use the standard structured output below. For a normal follow-up, answer only the question asked; if the follow-up explicitly asks for cause, evidence, status, or a complete conclusion, include the corresponding fields instead of collapsing the answer to one sentence.

The default final answer is one sentence containing the proven main cause or exact blocker, known downstream impact, any remaining evidence gap, and the repair or unblocking direction.
For a detailed report with fix status or a next action, retain the remaining evidence fields below unless the user specifies another structure.
When the user explicitly asks for a detailed report, Use the six sections below unless the user specifies another structure.
Lead with `解决方案`, then `给测试的总结`, then `原因` whenever there is a fix status.
Compression means each required section keeps only facts that justify or verify the action, instead of forcing unrelated endpoints, fields, or code locations into the answer.
For an online investigation, the first summary sentence should contain the proven main cause or exact blocker, known downstream impact, any remaining evidence gap, and the repair or unblocking direction; the structured fields remain the authoritative detail.

1. `解决方案`: state whether code was changed and give the smallest executable action first. Separate immediate workaround, code fix, data repair, read-side fallback, and verification when more than one applies. Do not mix alternatives into one vague recommendation, and do not imply existing bad data is repaired unless a migration, repair script, or read-side compatibility path was actually added.
2. `给测试的总结`: write concise tester/product-readable notes from the product surface, including expected/actual, impact, and only verification that actually ran and any uncovered checks. Do not turn an API, database, log system, class, or method into a product reproduction entry unless interface/API regression is requested.
3. `原因`: start with one tester/product-readable conclusion, then separate the visible symptom, the direct trigger, and the proven root cause when they differ. If the issue is not reproduced, already recovered, or evidence is blocked, state that status and blocker first; unproven explanations must be marked as evidence-section hypotheses and must not replace the reason. Do not use "大概率/应该是/可能是" as the conclusion. For conflicting field, enum, or parameter meanings, base the conclusion on the current interface contract and measured data.
4. `接口与输入输出`: within this section, list only distinct boundaries that matter, then include all non-secret input fields/context needed to reproduce the result and the actual response status/message/data with its expected contract.
5. `证据`: cite tracker content, code location, database/log/API evidence, and what each piece proves. Separate verified facts, code inference, and blocked evidence.
6. `归属与影响`: classify as code defect, data issue, configuration issue, external dependency, frontend/UI ownership, or blocked evidence; include affected data shape or workflow.

If a requested detailed report has a different structure, follow that explicit request while retaining the fact/inference/blocker separation. Otherwise, revise the answer if the required default sentence or requested sections are missing.

## Shared Guardrails

- Never commit real tracker URLs, internal IPs, usernames, passwords, tokens, cookies, browser sessions, or machine paths.
- If the user pastes a password, token, cookie, or session value during a bug investigation, do not repeat it. Use it only as local evidence when necessary and remind the user to revoke or rotate it.
- Never leave bug-test artifacts in the target repository. Raw responses, screenshots, generated previews, logs, and caches belong in a temp/private location unless the user explicitly asks for a repo artifact.
- Do not present a POST/API endpoint as a Web preview. If a service must stay up so the user can inspect evidence, keep it running until the user confirms they are done, or clearly say it has been stopped.
- Do not stop at generic guesses. Words like "probably", "likely", or "大概率" are only allowed for explicitly marked hypotheses; a root-cause conclusion must cite the concrete request, response, code path, log row, or database row that proves it.
- When the user asks to trace the source, do not stop at an intermediate service that merely forwards or stores data. Continue upstream until the first bad output, the first bad transform, or a concrete blocker is identified.
- When adding long-term learning, update an existing rule first instead of appending duplicate guidance.
