# Agent 个人知识库沉淀规则

## 触发范围

- 用户要求记录、总结、沉淀、复盘、写入 Obsidian、整理个人日志、整理规则或整理 skill 时，读取本规则。
- 长任务到达明确节点时，可以判断是否有可记录内容；例如方案确认、排查闭环、实现完成、发布完成、测试结论明确或用户明确做出长期偏好选择。
- 系统定时扫描器读取各 CLI 会话日志时按本规则筛选可沉淀节点；扫描器范围覆盖 Codex、Claude、Hermes、OpenClaw 的会话产物，落地仍走候选与人工确认流程。
- 普通寒暄、低信息问答、一次性命令、未验证猜测和纯过程汇报不进入知识库。

## 沉淀原则

- Obsidian 是人工可读的个人知识库，不是 CLI 原始会话归档。
- Claude 自带 auto-memory（`~/.claude/projects/-Users-hugang/memory/`）作为 in-session 快路径，记录 user、feedback、project、reference 四类即时偏好；Obsidian 候选属于长期沉淀。扫描器写入 Obsidian 候选时按 `source` 与 `session_id` 去重，不重复记录 auto-memory 已覆盖的同一条目。
- Obsidian 默认按私有知识库处理，保留能帮助后续复盘和继续工作的上下文；代码位置、仓库名、模块名、方法名、改动范围、测试命令、验证结论、问题编号、环境名称和必要的内部业务上下文可以进入知识库。
- 敏感处理采用出口管控：写入私有 Obsidian 时默认不做脱敏；当内容要同步到个人 GitHub、写入公开规则、升级为 skill、进入提交记录、对外回复或交给非私有环境时，再按安全规则做脱敏、改写或删除。
- 只有能直接登录、调用、越权访问或恢复身份的凭据类内容默认处理，例如生产账号密码、token、cookie、session、API key、私钥、连接串、验证码、恢复码和助记词；处理时只替换凭据值，尽量保留问题背景和操作结论。
- 生产凭据值不写入 Obsidian；如果记录确实需要关联某个凭据或配置，使用 `secret_ref` 记录安全引用名。`secret_ref` 只能指向密钥管理器、本机私有配置、Keychain、环境变量或云厂商 Secret Manager 中的条目，不得包含真实凭据、账号密码、token 片段或可反推出密钥的值。
- `secret_ref` 只用于定位、复盘和轮换记录；agent 默认不得根据 `secret_ref` 自动读取真实密钥。需要读取时，必须由用户明确授权，并通过本机私有配置或专用密钥工具完成。
- 不把完整对话、完整工具输出、超长日志原文、超长接口响应原文或浏览器会话当作知识库主体；这类内容不是因为敏感，而是因为可读性和复用价值低。确实需要保留证据时，只摘取关键片段或记录本机私有位置。
- 默认生成候选条目，状态为 `candidate`，`agent_load` 必须为 `false`。
- 即使用户要求写入 Obsidian，也默认先生成候选摘要并等待确认；除非用户明确要求立即写入候选区。
- 只有用户明确确认后，候选条目才可以进入正式业务域；只有 `status: approved` 且 `agent_load: true` 且位于 allowlist 的内容，未来才可以被 agent 当作可加载知识。
- 规则和 skill 的执行源仍然是个人规则仓库。Obsidian 中的候选内容只用于整理、复盘和人工确认，不直接改变 agent 行为。
- 知识库自动化只维护一个 `personal-knowledge` skill；候选生成、候选写入、审批、Daily 索引、规则或 skill 升级都作为它的子功能，不再拆多个知识库 skill。
- 方案、总结和知识库条目不要按发布编号命名；只有正式稳定并准备对外分发时，才考虑编号。
- 单个 session 默认产出 ≤1 个候选；只有用户在该 session 中明确确认了 ≥2 个相互独立的知识点（不同决策、不同工作流、不同坑点），才允许拆分；同一主题的不同视角应合并为一条。
- 含具体业务字段名、表名、方法名、bug 编号、接口名或人员名的内容只能进项目仓库；个人知识库只保留去场景化后的规则、工作流、坑点。

## 有意义判断

满足下列任一条件时，才算可沉淀：

- 用户明确表达了长期偏好、协作方式、输出格式或安全边界。
- 形成了可复用的工作流、排查路径、测试策略或发布经验。
- 做出了明确技术决策，并有适用条件或反例。
- 产出了可复用的规则、skill、模板、检查清单或分类方法。
- 发现了会反复影响后续任务的问题、限制、坑点或工具边界。

下列内容默认不沉淀：

- 单次执行结果、临时路径、临时 URL、临时日志、一次性错误码。
- 未完成验证的猜测。
- 无长期复用价值的公司项目、内部环境、业务字段、人员信息、账号和测试数据。
- 用户没有确认的偏好推断。

## 采集排除清单

扫描器默认排除以下会话，不写入 Daily，也不产候选；人工捕获前同样要先比对本清单：

- `session_id` 匹配 `api-*`：CLI 内部 LLM 辅助调用（标题生成、tag 生成、follow-up 生成等），不是用户与 agent 的真实协作会话。
- 没有 assistant 回复的会话：只有 user 消息、只有错误码、只有连接中断或仅工具日志。
- 以 `ECONNRESET`、API 错误、连接失败、立即 `/exit` 或会话夭折结束的会话。
- 单轮寒暄会话：user 首条消息长度 ≤ 20 字符，且没有后续语义内容。
- 单次执行结果、临时路径、临时 URL、临时日志、一次性错误码、一次性业务排查结论。

排除掉的会话不需要在 Daily 留索引条目；如果用户事后要求追溯，再按需补记。

## 业务域

个人知识库的顶层业务域保持最小集合：

- `01-Agent工作台`：Codex、Claude、Hermes、OpenClaw、gstack、规则、skill、Obsidian 接入。
- `02-研发实现`：代码实现、重构、后端、前端、浏览器自动化和工程实践。
- `03-排查与观测`：bug、日志、Grafana、MCP 数据查询、链路追踪、根因判断。
- `04-需求与文档`：需求、原型、PRD、技术调研、方案文档和写作规范。
- `05-交付与验证`：测试、QA、发布、GitHub 同步、dev 发布和回归。

不要因为单次任务新增顶层域。新主题先放 `Inbox`，累计出现稳定复用价值后再归入已有域或拆分。

## 候选条目格式

候选条目至少包含：

```yaml
---
type: agent-log-candidate
status: candidate
agent_load: false
domain: Inbox
contexts: []
source: codex
session_id: ""
sensitivity: private
secret_policy: none
secret_refs: []
---
```

`source` 必填，取值为 `codex`、`claude`、`hermes` 或 `openclaw`，表示候选所对应的 CLI 会话来源；扫描器产出的候选仍按 CLI 来源填写 `source`，并在 `contexts` 中加入 `scanner` 以区分人工捕获。`session_id` 用来定位原始会话，会话内人工生成可留空，扫描器生成必须填会话 JSONL 文件名或会话标识。

私有 Obsidian 候选默认使用 `sensitivity: private`；只有已经为公开同步或外部输出处理过的条目才使用 `sensitivity: redacted`。

若条目关联生产凭据或生产配置，设置 `secret_policy: reference-only` 并只填写稳定引用名，例如 `prod-db-readonly`；不要在 `secret_refs` 写真实账号、密码、token、cookie、连接串、URL 参数或可直接访问生产系统的值。

正文写摘要、决策、可复用经验、待确认项和建议归档位置。不要把原始聊天当附件或引用块粘进去。

候选标题与文件名由正文语义生成，不得直接截取 user 首条消息、会话起始内容或 CLI 自动会话标题。只能拿到首条消息（极短会话、未展开会话）时，整体不进候选。

## 扫描器写入红线

- 扫描器以直接文件写入 vault 的 `AgentKnowledge/Inbox/` 或 `AgentKnowledge/Daily/` 作为标准通道；MCP 与 Local REST API 仅用于会话内人工写入。
- 扫描器读取会话 JSONL 时，若工具输出含密码、token、cookie、session、连接串、API key 明文（包括 `~/.claude/mcp.json` 这类配置文件原文），必须以 `secret_ref` 占位，原始值不能进入候选正文。
- 扫描器写入失败时只在自身日志记录失败原因，不改写到非 vault 路径，不把候选塞进任何 agent 上下文。
- 扫描器只读会话日志和已知 vault 目录，不读 `~/.claude/projects/*/memory/`、`~/.codex/local/`、Hermes sessions、OpenClaw workspace 私有目录等其他位置。
- 扫描器每跑完一批必须在自身日志输出本批自检统计：写入文件数、frontmatter schema 校验失败数、排除清单命中数、单 session 候选数分布、主题与正文语义脱节告警数。自检异常时本批整体回退或标红，不依赖人工事后审计发现 schema drift 或采集偏差。

## 写入流程

1. 先判断是否有可沉淀价值。
2. 私有 Obsidian 写入默认保留上下文；仅处理生产级账号密码、token、cookie、session、API key、私钥、连接串、验证码、恢复码和助记词等凭据值。需要保留关联关系时，用 `secret_ref` 替代真实值。
3. 生成候选摘要。
4. 用户确认后写入 Obsidian 候选区或对应业务域。
5. 如果候选内容要升级成规则、skill、公开文档或同步到个人 GitHub，先按出口管控做脱敏和泛化，再说明会影响的文件和行为，并等待用户确认。

如果 Obsidian MCP、Local REST API 或写入权限不可用，只输出候选摘要，不尝试绕过权限写文件。
