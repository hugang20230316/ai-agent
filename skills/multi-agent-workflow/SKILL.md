---
name: multi-agent-workflow
description: Use when the user asks for multi-agent collaboration, agent orchestration, multiple agents to plan/do/review, or a coordinator-driven workflow in Codex without building a separate orchestration system.
---

# Multi Agent Workflow

Choose the orchestration topology first. Codex native subagents are one option, not the whole workflow. Do not build a custom external orchestrator unless the user explicitly asks for one.

## Core Rules

- Treat the current assistant as the coordinator by default: split the task, assign bounded work, pass only the needed context to each agent, wait only when blocked, integrate results, verify, and report the final state.
- If a dedicated coordinator CLI/session is launched, that session becomes the coordinator and the current assistant should describe the handoff clearly.
- Treat `ma_*` agent files as reusable role profiles, not singletons. Spawn multiple instances of the same profile when the work has independent evidence areas, implementation slices, or review surfaces.
- Spawn real subagents only when independent work can run in parallel or a separate review context matters.
- Use `ma_researcher` for evidence gathering and tool capability checks.
- Use `ma_planner` for options and implementation plans.
- Use `ma_worker` only after the user has authorized implementation or the current request clearly asks for execution.
- Use `ma_reviewer` for independent review before claiming completion.
- Same-chat roleplay is not real multi-agent work.
- Do not call work "independent" unless the subagents run in separate contexts, sessions, threads, or worktrees provided by the runtime.
- Do not create files, skills, commands, scripts, or persistent configuration unless the user explicitly asks for configuration or implementation.

## Topology Selection

Pick the least heavy topology that provides the needed isolation:

1. **Current-session subagents**: use when the task fits one coordinator session and needs isolated subagent context, parallel evidence gathering, or independent review. The parent agent stays as coordinator.
2. **Multi-CLI or multi-session team**: use when the user asks for separate CLIs, wants visible independent terminals, needs long-running workers, or wants a lead/coordinator CLI dispatching worker CLIs. Each worker CLI/session gets a distinct task, working directory or worktree, context packet, and output contract.
3. **Worktree-isolated execution**: use when multiple workers may edit code in parallel. Each worker gets a separate branch/worktree or otherwise disjoint write scope, and the coordinator integrates the result.

Do not describe work as "multi-CLI" unless separate CLI processes or sessions are actually started. Do not describe work as "worktree-isolated" unless separate worktrees or equivalent filesystem isolation are actually used.

## Coordinator Pattern

The coordinator is the parent agent in the current Codex session unless a dedicated coordinator CLI/session has been launched. It must:

1. Define the user goal, read scope, write scope, and completion criteria.
2. Decide which work belongs on the critical path and which work can run in parallel.
3. Create non-overlapping subagent assignments with concrete inputs, forbidden areas, and expected outputs.
4. Keep parallel agents separated by topic, file ownership, evidence source, or review angle.
5. Merge results into facts, inferences, decisions, and unresolved risks.
6. Verify important claims independently instead of trusting subagent status messages.

## Multiple Instances

Use multiple instances of one role when breadth matters:

- Spawn multiple `ma_researcher` instances for separate evidence areas, such as official docs, local CLI behavior, competing tools, and community practice.
- Spawn multiple `ma_worker` instances only when write ownership is disjoint by file, module, or worktree.
- Spawn multiple `ma_reviewer` instances when review angles differ, such as correctness, tests, security, and evidence quality.
- Give each instance a distinct question and output contract. Do not ask several agents to answer the same broad prompt.
- For multi-CLI mode, "multiple instances" means multiple actual CLI processes or sessions, not several role labels in one conversation.

## Default Flows

For方案 or tool-capability questions:

1. The coordinator chooses current-session subagents or multi-CLI research based on the requested isolation.
2. Spawn one or more `ma_researcher` instances for objective evidence across distinct evidence areas.
3. Spawn `ma_planner` for options if the answer involves tradeoffs.
4. Spawn `ma_reviewer` to challenge unsupported claims for high-impact decisions.
5. The coordinator returns facts, inferences, recommendation, and evidence gaps, including which topology was actually used.

For implementation:

1. The coordinator defines task boundary, write scope, and verification target.
2. Choose topology: current-session worker for small scoped edits, multi-CLI for visible independent sessions, or worktree isolation for parallel code edits.
3. Spawn `ma_researcher` or built-in `explorer` for codebase discovery when needed.
4. Spawn one or more `ma_worker` instances for scoped implementation tasks only when their write scopes do not overlap.
5. Spawn `ma_reviewer` or run Codex review on the resulting diff.
6. The coordinator integrates results, verifies, and reports changed files, actual topology, and residual risk.

For "continue":

- Continue the same goal until a natural boundary: evidence gathered, plan reviewed, implementation verified, or a real blocker appears.
- Do not stop after a small sub-step if safe non-blocking work remains.

## Output Contract

Every coordinator summary should distinguish:

- facts with sources;
- inferences from those facts;
- recommendation or next action;
- unresolved risks or missing evidence.
