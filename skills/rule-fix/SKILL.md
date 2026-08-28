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
   - 规则加载、诊断、验证或热修时，若存在已声明或已生效的规则入口，必须记录该入口及其真实目标；探测过的未声明规则路径只能作为加载失败证据，不得作为公共规则根继续使用。
   - Also read communication, skill, project governance, and testing rules when the task is a correction or hotfix.

2. **Choose mode**
   - For read-only explanation or review, diagnose and report findings only.
   - For behavior validation without edits, run the isolated validation gate without write steps.
   - For creating, modifying, or deleting rules, continue through the write and validation gates.

3. **Diagnose coverage**
   - Restate the behavior being constrained.
   - Classify intent semantically first: rule gap, existing-rule failure, rule conflict, or execution deviation; do not rely on fixed wording.
   - List existing rules that already cover it.
   - Classify the candidate as existing coverage failed, strengthening an existing rule, or a missing rule; when coverage failed, also classify the failure as trigger, loading, execution, validation, conflict, or missing rule.
   - Prefer fixing an existing rule over adding another rule.
   - If existing rules cover the issue, do not add a new rule; fix the trigger, execution, or validation gap.

4. **Filter the candidate before user-facing rule text**
   - Before drafting, list the semantic trigger, synonym intent, and reverse boundary; the draft must not depend on fixed wording.
   - 用户要求制定或修改行为约束、避免再犯、绝对禁止场景、规则方案或规则修改建议时，即使表达为“方案”或“建议”，也属于候选输出；本步通过前只能输出覆盖诊断、归属和方案边界。
   - 普通技术方案、产品方案、代码实现方案不因出现“方案”或“建议”进入本步；触发对象必须是 agent 行为约束或规则体系。
   - Candidate rule text may be drafted internally only for review; put reasons, background, examples, and explanation in the diagnosis, not the rule body.
   - Before semantic trigger, synonym intent, reverse boundary, and output-filter review pass, do not show proposed rule text, request approval, or enter the write plan; only report coverage diagnosis, placement, or a concrete blocker.
   - Run `multi-agent-workflow` with real isolated subagents to review the proposed rule for brevity, trigger reliability, clarity, duplication, conflicts, and hardcoded incident residue.
   - A pending review counts as not passed, and any blocking finding rejects the candidate. Do not show an edit plan or write until the revised candidate passes re-review, or the local fallback below explicitly passes when isolated review is unavailable.

5. **Show the edit plan before writing**
   - Enter this step only after the candidate passes the step 4 output-filter review.
   - List every file you intend to change.
   - For each file, state the purpose and the planned change.
   - State the related rules, skills, AGENTS files, docs, or config you will not change and why.
   - Do not include files unrelated to the rule fix in the plan.
   - Treat an exact plan as specific file paths, per-file purpose, planned rule effect, and excluded files; the write scope is limited to that plan.
   - Wait for user approval before modifying files, unless the user has already approved that exact plan.
   - A generic "continue" only approves writing when it directly follows an exact plan; otherwise continue diagnosis or planning without edits.

6. **Write the smallest rule change**
   - A rule body states one reusable constraint: keep only its trigger, required action, and the reverse boundary needed to prevent unsafe overreach; put all explanation in the diagnosis.
   - Do not write project names, one-off field names, endpoint names, people names, local paths, credentials, or tool-specific hacks into public rules.
   - If the rule belongs in a personal skill, place the source under `ai-agent/skills/<skill-name>/`; tool-side skill directories should be symlinks or config references.

7. **Self-check the diff**
   - Check `git diff --stat` and the relevant file diffs.
   - Verify no unrelated formatting, duplicate rules, conflicting rules, hardcoded scenario residue, or unnecessary files were added.
   - Verify `SKILL.md` stays concise; move long matrices to `references/`.

8. **Run isolated validation**
   - Use `multi-agent-workflow`.
   - Spawn real subagents with `fork_context: false`; same-chat roleplay does not count.
   - 用户确认规则修改后，隔离验证视为已授权且必须执行；不得以未单独授权多 agent 为由跳过。
   - 候选输出前审查工具超时或不可用时，按第 4 步执行同等 output-filter checks；未通过前仍不得展示规则正文、请求批准或进入写入计划。
   - 写入后验证工具一旦超时、卡住、关闭失败或无法确认状态，必须立即停止该工具链，改用本地最小复核并把隔离验证标为未覆盖风险；不得继续等待、关闭、恢复、重试或发送输入给同一个运行实例、会话、子 agent 或 reviewer。若清理工具不支持显式超时，不得把清理动作放入用户交付的关键路径。
   - Give validators only the minimal rule text, scenario prompts, and output contract needed for validation.
   - Follow `references/validation-matrix.md`.

9. **Fix and revalidate**
   - If validation finds a defect and the change is still in scope, fix it and rerun the failed scenarios.
   - Final status must separate facts, inferences, validation evidence, and uncovered risk.

## Output Requirements

- Before writing: changed files, reason, planned rule effect, and excluded files.
- 每项候选修改必须标注 `已有覆盖但失效`、`加强已有规则` 或 `新增缺口`；标为已有覆盖但失效时，还要写明触发、加载、执行、验证或冲突失效点。
- Do not propose rules before semantic intent classification, coverage conclusion, and failure-point analysis are complete.
- 只有规则候选通过输出前过滤后，才能提出目标文件和一句可执行规则；未通过时只报告归属诊断或具体阻塞。
- 规则修改方案必须短、硬、可执行；目标不明或有安全冲突时只报阻塞。
- After writing: changed files, diff summary, validation topology, scenario results, and remaining risk.
- For read-only review: existing coverage, gaps, recommendation, and whether a write workflow would be needed if the user approves edits.
- Never claim a rule is effective without naming the trigger, behavior, validation evidence, and uncovered boundary.
