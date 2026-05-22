# Codex + Obsidian 个人日志设计

## 背景

目标不是把 Codex 的每次对话都存进 Obsidian，而是把有长期价值的信息沉淀成个人知识。原始会话、工具输出和日志仍然属于运行态私有数据，不进入 Obsidian，不进入个人 GitHub 仓库。

这套设计采用“候选式沉淀”：Codex 在关键节点生成私有摘要，先进入候选区；用户确认后，再进入业务域、规则或 skill。私有 Obsidian 默认保留可复用上下文，只有对外、同步或升级为可执行规则时才做严格脱敏。

## 设计依据

- OpenAI Agents SDK 的 memory 设计强调摘要、索引和按需恢复，而不是把完整历史长期塞进上下文。
- LangChain 将记忆分成短期记忆和长期记忆，并进一步区分 semantic、episodic、procedural。Obsidian 适合保存 semantic 和 episodic；规则与 skill 属于 procedural，应该留在个人规则仓库。
- MCP 工具规范强调用户确认和安全边界。写入 Obsidian、升级规则或修改 skill 都应走人工确认。
- Obsidian 的 Properties、Daily Notes、Templates 和 Local REST API 能支撑结构化候选条目、每日索引和后续自动化写入。

参考：

- OpenAI Agents SDK Memory: https://openai.github.io/openai-agents-python/sandbox/memory/
- OpenAI Cookbook Session Memory: https://developers.openai.com/cookbook/examples/agents_sdk/session_memory
- LangChain Memory: https://docs.langchain.com/oss/python/concepts/memory
- MCP Tools Specification: https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- Obsidian Properties: https://obsidian.md/help/properties
- Obsidian Local REST API: https://github.com/coddingtonbear/obsidian-local-rest-api

## 范围

本设计覆盖：

- Codex 会话到达明确节点时生成个人知识候选，例如方案确认、排查闭环、实现完成、测试结论明确或用户确认了长期偏好。
- 候选摘要写入 Obsidian。
- Obsidian 内容按最小业务域整理。
- 经用户确认后，将稳定知识迁移到个人规则或 skill。

本设计不覆盖：

- 全量会话备份。
- 自动读取整个 Obsidian vault 作为上下文。
- 自动把候选内容升级成规则或 skill。
- 用发布编号描述内部方案。
- 把完整会话、完整日志、完整接口响应或浏览器会话当作知识库主体。
- 自动归档生产账号密码、token、cookie、session、API key、私钥、连接串、验证码、恢复码和助记词等可直接授予访问权限的凭据值。
- 让 agent 根据 Obsidian 中的 `secret_ref` 自动读取真实生产密钥。

## 总体流程

```mermaid
flowchart TD
  A[Codex 会话] --> B[明确节点]
  B --> C{有长期价值?}
  C -- 否 --> D[不记录]
  C -- 是 --> E[凭据值处理]
  E --> F[候选摘要]
  F --> G[Obsidian Inbox 或 Daily]
  G --> H{用户确认?}
  H -- 否 --> I[保留候选或删除]
  H -- 是 --> J[归入业务域]
  J --> K{需要变成规则或 skill?}
  K -- 否 --> L[只作为知识保存]
  K -- 是 --> M[人工评审后改规则库]
```

## Obsidian 结构

```text
AgentKnowledge/
  Daily/
  Inbox/
  01-Agent工作台/
  02-研发实现/
  03-排查与观测/
  04-需求与文档/
  05-交付与验证/
Templates/
  Agent日志候选.md
  Agent每日索引.md
```

业务域保持 5 个，不按单次任务继续拆。弱证据主题先进入 `Inbox`，只有长期重复出现并且难以归入现有域时，才考虑新增顶层域。

## 业务域定义

| 业务域 | 放什么 | 不放什么 |
| --- | --- | --- |
| `01-Agent工作台` | Codex、Claude、Hermes、OpenClaw、gstack、规则、skill、Obsidian 接入 | 单个业务项目的临时处理 |
| `02-研发实现` | 代码实现、重构、工程实践、浏览器自动化 | 未验证想法和一次性命令 |
| `03-排查与观测` | bug、Grafana、日志链路、MCP 数据查询、根因判断 | 原始日志、接口响应和内部标识 |
| `04-需求与文档` | 需求、原型、PRD、技术调研、方案文档 | 纯过程汇报 |
| `05-交付与验证` | 测试、QA、发布、GitHub 同步、dev 发布和回归 | 临时发布地址和凭据 |

## 候选条目模型

候选条目使用 Obsidian Properties：

```yaml
---
type: agent-log-candidate
status: candidate
agent_load: false
domain: Inbox
contexts: []
source: codex
session_date: YYYY-MM-DD
sensitivity: private
secret_policy: none
secret_refs: []
target: ""
---
```

字段含义：

| 字段 | 含义 |
| --- | --- |
| `type` | 条目类型，候选日志固定为 `agent-log-candidate` |
| `status` | `candidate`、`approved`、`archived` |
| `agent_load` | 是否允许未来 agent 加载，候选必须为 `false` |
| `domain` | 目标业务域 |
| `contexts` | 低敏上下文标签，例如 `codex`、`testing`、`grafana` |
| `source` | 来源工具 |
| `session_date` | 产生日期 |
| `sensitivity` | 私有或已脱敏状态，私有 Obsidian 候选默认 `private` |
| `secret_policy` | 凭据处理策略；无凭据关联时为 `none`，只保留引用时为 `reference-only` |
| `secret_refs` | 生产凭据或配置的安全引用名，不保存真实值 |
| `target` | 如果未来要升级，写目标规则或 skill 名称 |

正文只保存四类内容：

- 摘要：这次形成了什么可复用信息。
- 决策：用户明确确认了什么偏好或边界。
- 证据：能支撑结论的关键上下文，不粘贴完整原始输出。
- 待处理：是否需要迁移到规则或 skill。

## 有意义判断

进入 Obsidian 的最低门槛：

- 它能减少后续重复沟通。
- 它能指导未来 agent 行为。
- 它描述了稳定偏好、规则、流程、排查经验或技术决策。
- 它不依赖原始会话才能看懂。

不进入 Obsidian 的内容：

- 低信息聊天。
- 单次命令输出。
- 没有长期复用价值的临时路径、临时 URL 和临时环境。
- 未确认的主观推断。
- 无长期复用价值的公司项目细节。
- 生产账号密码、token、cookie、session、API key、私钥、连接串、验证码、恢复码和助记词等凭据值。

## 生产凭据引用

生产凭据值不进入 Obsidian。需要记录某次排查、发布或回滚关联了哪个凭据时，使用 `secret_ref`。

```yaml
secret_policy: reference-only
secret_refs:
  - prod-db-readonly
```

`secret_ref` 的边界：

- 它是给人看的引用名，不是密钥、不包含密钥片段，也不是自动取密钥的开关。
- 真实凭据留在 1Password、Keychain、环境变量、云厂商 Secret Manager 或本机私有配置中。
- Obsidian 记录用途、影响范围、轮换状态、处理结论和验证结果。
- Agent 默认不能根据 `secret_ref` 自动读取真实密钥；只有用户明确要求，并且通过本机私有密钥源时才允许查找。

## 触发节点

只在这些节点生成候选：

- 用户明确说记录、总结、沉淀、写入 Obsidian。
- 一个方案被确认。
- 一个排查或修复闭环。
- 一个测试、发布或回归结论明确。
- 上下文过长，需要 compact 或换会话。
- 用户表达了稳定偏好或纠正了长期规则。

不做每轮自动记录，也不做后台持续扫描。

## GitHub 规则库接入

个人 GitHub 仓库继续作为执行源：

```text
AGENTS.md
rules/
skills/
docs/
```

Obsidian 和 GitHub 的边界：

- Obsidian 保存候选、复盘、知识索引。
- `rules/*.md` 保存会直接影响 agent 行为的通用规则。
- `skills/<name>/` 保存明确可复用的操作能力。
- 知识库相关能力只维护一个 `skills/personal-knowledge/`。候选生成、候选写入、审批、Daily 索引和升级规则都作为这个 skill 的子功能。
- `docs/*.md` 只解释同步、设计和迁移，不参与 agent 规则加载。

候选升级成规则或 skill 前，需要人工判断：

- 是否足够通用。
- 是否适合从私有 Obsidian 升级到公开规则或 skill。
- 是否会和现有规则冲突。
- 是否应该写规则、skill、模板，还是继续留在 Obsidian。

## 自动化边界

默认不修改 Codex 私有配置，不直接启用 hooks，也不读取历史会话做回填。

候选生成、候选写入、审批、Daily 索引和升级规则都收敛到 `personal-knowledge` skill 内，不再拆分多个知识库 skill。

后续如果启用自动写入，应满足：

- 只读取当前会话的模型生成摘要，不读取完整历史库。
- 写入私有 Obsidian 时默认保留上下文，仅处理可直接授予访问权限的凭据值；需要关联生产凭据时只写 `secret_ref`。
- 默认写入 `AgentKnowledge/Inbox` 或 `AgentKnowledge/Daily`。
- 写入条目保持 `status: candidate` 和 `agent_load: false`。
- 写入失败时只报告失败原因，不改用不受控路径。

## 验收标准

- Obsidian 有最小目录、候选模板和每日索引模板。
- 个人规则库有明确的个人知识库沉淀规则。
- 规则说明清楚禁止全量会话归档和自动规则升级。
- README 或同步说明能指到这套设计。
- 没有把本机私有配置、会话、完整日志、生产账号密码、token、cookie、连接串和无法泛化的公司项目细节写入公共仓库。

## 启用顺序

1. 维护一个 `personal-knowledge` skill，先支持候选摘要和人工确认。
2. 用户要求沉淀时，由 agent 生成候选摘要，人工确认后写入 Obsidian。
3. 在任务完成、compact 前、方案确认后，agent 可以主动给出候选摘要。
4. 确认 Obsidian Local REST API 和 MCP 可用后，再在同一个 skill 内启用候选写入和 Daily 索引。
5. 对 approved 条目做人工评审，少量迁移到 `rules/` 或现有 skill。

---

> 注：本设计是 2026-05-17 的初版快照，原本只覆盖 Codex。后续扩展为多 CLI（Codex、Claude、Hermes、OpenClaw）方案，并加入系统定时扫描器作为可选触发方式。最新行为约束以 `~/ai-agent/rules/personal-knowledge-rules.md` 和 `~/ai-agent/skills/personal-knowledge/SKILL.md` 为准。
