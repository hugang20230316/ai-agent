# 个人 Agent 全局规则入口

本文件是公共规则入口。Codex、Claude、OpenClaw、Hermes 等工具应通过各自原生入口、本机 profile、软链接或配置引用加载本文件，再由本文件引用同一套公共 `rules/*.md`。

本文件只放公共规则索引和加载门槛。工具专属规则按当前运行工具或任务语义触发加载；本机路径、工具本地目录、账号、内部环境、项目仓库规则和私有启动方式不写入本文件。

## 公共规则索引

下面的 `@rules/*.md` 只是公共规则索引，不等于规则正文已经加载。执行任务前，必须按后面的触发规则读取对应文件。

@rules/communication-rules.md
@rules/security-and-privacy-rules.md
@rules/markdown-rules.md
@rules/coding-rules.md
@rules/testing-rules.md
@rules/skill-rules.md
@rules/project-governance.md
@rules/evidence-output-rules.md
@rules/mcp-output-rules.md
@rules/research-rules.md
@rules/requirements-and-prototype.md
@rules/personal-knowledge-rules.md

## 规则加载原则

- 解析 `@rules/*` 时，以当前生效 `AGENTS.md` 的真实文件所在目录为根。
- 若入口是软链接，先解析软链接真实目标，再从真实目标所在目录加载 `rules/*.md`。
- 不得按当前工作目录、用户名目录、工具 home 或历史记忆猜测公共规则源。
- 同一任务同时命中多个规则文件时，读取全部命中的文件；不得用单个 skill、单条规则或工具默认行为覆盖更具体的公共规则。

## 基础触发

- 普通协作、回复风格、任务边界或用户纠偏：读取 `@rules/communication-rules.md`。
- 私有配置、凭据、同步边界、公司项目、上传、提交、发布或外部动作：读取 `@rules/security-and-privacy-rules.md`。
- Markdown 文档创建、修改或审阅：先读取 `@rules/markdown-rules.md`，再生成内容或编辑文件。
- 代码创建、修改、审阅、解释或重构：先读取 `@rules/coding-rules.md`。
- 代码任务完成前，按当前文件风格检查方法位置、命名、注释、参数、返回值、字段、常量、配置项和新增私有辅助方法的保留价值。
- 本轮产生代码改动后，最终答复、提交或创建 PR 前，先读取 `@rules/skill-rules.md` 并执行 `review-coding`。
- 用户主动要求审查当前改动、未提交代码或指定提交记录时，也必须执行 `review-coding`，并先确定目标仓库。`review-coding` 是代码合规门禁，不替代需求验收、spec review 或功能测试。
- 测试、验证、修复完成声明、回归检查或质量结论：读取 `@rules/testing-rules.md`。
- 用户点名 skill、插件，或任务语义命中某个 skill：读取 `@rules/skill-rules.md`，按其中的触发、加载、推荐筛选和修改边界执行。

## 组合触发

- 涉及规则没命中、同类错误复发、规则硬编码、规则分类混乱、规则热修、规则纠偏或验证规则是否生效时，必须同时读取 `@rules/communication-rules.md`、`@rules/project-governance.md`、`@rules/testing-rules.md` 和 `@rules/coding-rules.md`；若还涉及记录、候选或 Obsidian 证据，再读取 `@rules/personal-knowledge-rules.md`。
- 涉及长任务、多阶段排查、未完成收口、上下文压力或 `/compact` 时，同时读取 `@rules/communication-rules.md` 和 `@rules/testing-rules.md`。
- 方法名过长、实现细节命名、字段语义、注释缺失、注释过长、泛词注释或无意义封装：同时读取 `@rules/coding-rules.md` 和 `@rules/testing-rules.md`，并用最终 diff 复查命名、注释和辅助方法是否仍有同类问题。
- 图表、流程、架构、部署、模块关系或方案说明：同时读取 `@rules/markdown-rules.md`，按图表风格要求设计图表。
- 工具输出、命令结果整理、日志、数据源查询、接口请求、接口排查、接口验证、联调参数、请求/响应比对、证据输出或长输出摘要：读取 `@rules/evidence-output-rules.md`。
- MCP 选择、MCP 调用、MCP 兜底、MCP 资源或连接来源：读取 `@rules/mcp-output-rules.md`。若同时呈现查询结果，再叠加 `@rules/evidence-output-rules.md`。
- 找资料、找方案、主流方案、推荐、选型、竞品或同类对比、技术调研、市场调研、资料综述，或需要判断“什么更主流/更合适”：读取 `@rules/research-rules.md`。
- 需求、原型、PRD、验收标准、页面交互或产品说明：读取 `@rules/requirements-and-prototype.md`。
- 记录、总结、沉淀、复盘、写入 Obsidian、个人日志、知识库、规则候选或 skill 候选：读取 `@rules/personal-knowledge-rules.md`。

## 工具专属触发

- 当前 agent 运行在 OpenClaw 原生会话中时，即使用户任务没有提到 OpenClaw，也读取 `@rules/openclaw-rules.md`。
- 当前 agent 运行在 Hermes 原生会话中时，即使用户任务没有提到 Hermes，也读取 `@rules/hermes-rules.md`。
- 涉及 OpenClaw 配置、OpenClaw SOUL、workspace、skills 或 OpenClaw 运行行为：读取 `@rules/openclaw-rules.md`。
- 涉及 Hermes 配置、Hermes SOUL、AGENTS、rules、skills、CLI、Dashboard、Gateway、MCP、cron 或 Hermes 运行行为：读取 `@rules/hermes-rules.md`。

## 治理触发

- 个人规则仓库、项目规则分层、同步设计、文件归类或规则沉淀：读取 `@rules/project-governance.md`。

## 收口检查

- Markdown 文档任务完成前，至少内部检查代码围栏是否闭合、Mermaid 语法是否保守、图表数量是否覆盖关键概念。
- 只有复杂 Markdown 文档、含图表/代码围栏/渲染兼容风险的交付、用户要求说明验证过程，或检查发现异常、跳过项时，才在最终答复里说明 Markdown 检查结果。
- 纯规则条目、短列表、轻量文案修改只做内部检查，不单独报告检查过程。

## 共用边界

- 公共规则以本仓库 `rules/*.md` 为源；工具侧通过各自原生入口、本机 profile、软链接或配置引用加载。
- 私有配置、敏感信息、同步边界、公司项目边界和平台差异遵循 `@rules/security-and-privacy-rules.md`。
- 项目规则只放在目标项目自己的规则入口和项目级规则目录里，不写回本仓库的全局规则。
