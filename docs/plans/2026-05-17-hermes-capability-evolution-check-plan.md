# Hermes 能力检查与进化闭环实施计划

> **For Claude/Codex:** REQUIRED SUB-SKILL: Use `subagent-driven-development` to execute this plan task-by-task in this session.

**Goal:** 对本机 Hermes 做受控全面检查，并输出可沉淀的进化建议。

**Architecture:** 计划拆成只读审计、短生命周期运行验证、报告整合三类任务。子 agent 只负责独立审计和证据摘要，不修改文件、不读取敏感配置原文；主线程负责副作用控制、结果整合和最终报告。

**Tech Stack:** Hermes CLI、zsh、git、Markdown、macOS 本机环境。

---

## 全局边界

- 不执行 `hermes update`、迁移、卸载、备份恢复、安装类写入动作。
- 不读取 `.env`、`config.yaml` 原文、sessions、memories、token、cookie 或日志全文。
- 不真实发送外部平台消息。
- 不长期启动 gateway、dashboard、MCP server 或 cron worker。
- 临时输出只放系统临时目录；最终报告写入 `/Users/hugang/ai-agent/docs/reports/`。
- 输出命令结果时只摘关键行；敏感字段必须脱敏或省略。

## 任务 1：基线与命令面审计

**Owner:** 子 agent

**Files:**

- Read: `/Users/hugang/.hermes/SOUL.md`
- Read: `/Users/hugang/.hermes/hermes-agent/README.md`
- Read: `/Users/hugang/.hermes/hermes-agent/README.zh-CN.md`
- No write.

**Steps:**

1. 运行只读命令：`command -v hermes`、`which -a hermes`、`hermes --version`、`hermes --help`。
2. 检查 Hermes 项目 git 状态：`git -C /Users/hugang/.hermes/hermes-agent status --short`。
3. 汇总 CLI 子命令面：从 `hermes --help` 摘要出主要能力分类。
4. 输出基线结论：安装路径、版本、上游落后提示、当前工作区是否有未提交改动、命令面是否完整。

**Expected output:** 一段审计摘要，包含证据、风险、建议分类。

## 任务 2：规则加载链路审计

**Owner:** 子 agent

**Files:**

- Read: `/Users/hugang/.hermes/SOUL.md`
- Read: `/Users/hugang/.hermes/AGENTS.md`
- Read: `/Users/hugang/ai-agent/AGENTS.md`
- Read: `/Users/hugang/ai-agent/rules/*.md`
- No write.

**Steps:**

1. 检查 `$HERMES_HOME/AGENTS.md` 是否软链接到个人规则仓库入口。
2. 检查 `$HERMES_HOME/rules/*.md` 是否存在并指向个人规则源。
3. 核对 SOUL 是否要求 Hermes 每轮读取 AGENTS。
4. 判断规则入口是否存在断链、重复、平台差异或不可执行要求。
5. 给出可沉淀建议：规则、Hermes 本机配置、自定义 skill 或脚本。

**Expected output:** 规则链路状态、发现项、建议落点。

## 任务 3：Skills、tools、plugins、MCP 能力矩阵审计

**Owner:** 子 agent

**Files:**

- Read-only CLI output only.
- No write.

**Steps:**

1. 运行 `hermes skills --help`、`hermes tools --help`、`hermes plugins --help`、`hermes mcp --help`。
2. 如果对应命令有安全的 list/status 子命令，运行只读列表命令。
3. 不读取 `config.yaml` 原文；如命令输出包含敏感信息，摘要时省略。
4. 识别缺失、冲突、不可用、命名不一致、未正确引入的能力。
5. 把问题按“立即修复、建议沉淀、观察项、跳过项”分类。

**Expected output:** 能力矩阵表格草稿和问题清单。

## 任务 4：Cron、gateway、dashboard 短生命周期验证设计与执行

**Owner:** 主线程

**Files:**

- No repository writes.

**Steps:**

1. 先运行 help/status/list 类只读命令：`hermes cron --help`、`hermes gateway --help`、`hermes dashboard --help`。
2. 对 dashboard 只做本地短启动验证：确认端口、启动、HTTP 可访问、关闭进程。
3. 对 gateway 只做配置/帮助检查，不启动真实平台网关。
4. 对 cron 只做任务列表或 help 检查，不新增任务、不触发投递。
5. 记录未覆盖项和原因。

**Expected output:** 短生命周期验证结果和跳过项说明。

## 任务 5：报告整合与进化建议

**Owner:** 主线程

**Files:**

- Create: `/Users/hugang/ai-agent/docs/reports/2026-05-17-hermes-capability-evolution-check-report.md`

**Steps:**

1. 汇总任务 1-4 的证据。
2. 写最终报告，包含摘要、能力矩阵、问题清单、进化建议、未覆盖项。
3. 对每个问题写明证据、影响、分类和下一步建议。
4. 做 Markdown 自检：围栏闭合、表格完整、无敏感信息、正文不依赖聊天上下文。
5. 检查 git 状态，确认只新增计划和报告相关文档。

**Expected output:** 可复用的 Hermes 能力检查报告。

## 执行策略

- 任务 1、2、3 可并行委派给 fresh subagent。
- 任务 4 由主线程执行，因为涉及进程和端口控制。
- 任务 5 由主线程整合。
- 每个子 agent 返回后，主线程做事实核对；不要求子 agent 提交。
- 本计划不是代码变更计划，不做代码质量 review；改为证据一致性 review 和敏感信息 review。

## 验收标准

- 覆盖安装、诊断、规则加载、skills、tools、MCP、cron、gateway、dashboard。
- 未执行更新、迁移、卸载、真实外部平台投递或长期后台运行。
- 未读取或输出敏感配置原文。
- 报告中每个问题都有分类、证据、影响和下一步建议。
- 至少给出一项可沉淀的进化机会；如果没有发现，则明确说明。
