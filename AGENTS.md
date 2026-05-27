# 个人 Agent 全局规则入口

本文件是个人 GitHub 仓库里的统一规则清单。Codex、Claude、OpenClaw、Hermes 都应通过各自会读取的原生入口加载本文件，再由本文件引用同一套 `rules/*.md`。

本机映射：

- Codex：`~/.codex/AGENTS.md`
- Claude：`~/.claude/AGENTS.md`，由 `~/.claude/CLAUDE.md` 引用
- OpenClaw：`~/.openclaw/workspace/AGENTS.md`
- Hermes：`$HERMES_HOME/AGENTS.md`，由 `$HERMES_HOME/SOUL.md` 要求读取

本文件只引用个人通用规则和少量工具专属边界；不引用任何工具的本机私有配置，也不引用项目仓库规则。

@rules/communication-rules.md
@rules/security-and-privacy-rules.md
@rules/markdown-rules.md
@rules/coding-rules.md
@rules/testing-rules.md
@rules/skill-rules.md
@rules/openclaw-rules.md
@rules/hermes-rules.md
@rules/project-governance.md
@rules/evidence-output-rules.md
@rules/mcp-output-rules.md
@rules/research-rules.md
@rules/requirements-and-prototype.md
@rules/personal-knowledge-rules.md

## 强制规则加载

- 看到上面的 `@rules/*.md` 清单不等于已经加载规则正文。执行任务前，必须按本节命中的场景读取对应规则文件。
- 普通协作、回复风格、任务边界或用户纠偏场景，读取 `@rules/communication-rules.md`。
- 涉及私有配置、凭据、同步边界、公司项目、上传、提交、发布或外部动作时，读取 `@rules/security-and-privacy-rules.md`。
- 涉及创建、修改或审阅 Markdown 文档时，必须在生成内容或编辑文件前读取 `@rules/markdown-rules.md`，并按其中的图表、围栏和自检要求执行。
- 涉及创建、修改、审阅、解释或重构代码时，必须在动手前读取 `@rules/coding-rules.md`；完成前必须检查新增或修改的方法位置、方法命名证据、方法注释、参数注释、返回值注释、字段注释、常量注释、配置项注释和私有辅助方法抽取价值是否符合当前文件既有风格。
- 涉及测试、验证、修复完成声明、回归检查或质量结论时，读取 `@rules/testing-rules.md`。
- 涉及规则没命中、同类错误复发、规则硬编码、规则分类混乱、规则热修、规则纠偏或验证规则是否生效时，必须同时读取 `@rules/communication-rules.md`、`@rules/project-governance.md`、`@rules/testing-rules.md` 和 `@rules/coding-rules.md`；若还涉及记录、候选或 Obsidian 证据，再读取 `@rules/personal-knowledge-rules.md`。
- 涉及长任务、多阶段排查、未完成收口、上下文压力或 `/compact` 时，必须同时读取 `@rules/communication-rules.md` 和 `@rules/testing-rules.md`。
- 涉及方法名过长、实现细节命名、字段语义、注释缺失、注释过长、泛词注释或无意义封装时，必须同时读取 `@rules/coding-rules.md` 和 `@rules/testing-rules.md`，并用最终 diff 复查命名、注释和辅助方法是否仍有同类问题。
- 用户点名 skill、插件或任务语义命中某个 skill 时，必须同时按 `@rules/skill-rules.md` 执行触发、加载、推荐筛选和修改边界规则。
- 涉及 OpenClaw 配置、SOUL、workspace、skills 或 OpenClaw 运行行为时，读取 `@rules/openclaw-rules.md`。
- 涉及 Hermes 配置、SOUL、AGENTS、rules、skills、CLI、Dashboard、Gateway、MCP、cron 或 Hermes 运行行为时，读取 `@rules/hermes-rules.md`。
- 涉及个人规则仓库、项目规则分层、同步设计、文件归类或规则沉淀时，读取 `@rules/project-governance.md`。
- 涉及工具输出、命令结果整理、日志、数据源查询、接口请求、接口排查、接口验证、联调参数、请求/响应比对、证据输出或长输出摘要时，读取 `@rules/evidence-output-rules.md`。
- 涉及 MCP 选择、MCP 调用、MCP 兜底、MCP 资源或连接来源时，读取 `@rules/mcp-output-rules.md`；若同时涉及查询结果呈现，也按 `@rules/evidence-output-rules.md` 执行。
- 涉及找资料、找方案、主流方案、推荐、选型、竞品/同类对比、技术调研、市场调研、资料综述或需要判断“什么更主流/更合适”时，读取 `@rules/research-rules.md`。
- 涉及需求、原型、PRD、验收标准、页面交互或产品说明时，读取 `@rules/requirements-and-prototype.md`。
- 涉及记录、总结、沉淀、复盘、写入 Obsidian、个人日志、知识库、规则候选或 skill 候选时，读取 `@rules/personal-knowledge-rules.md`。
- 如果任务涉及图表、流程、架构、部署、模块关系或方案说明，必须同时按 `@rules/markdown-rules.md` 的图表风格要求设计图表；不能只放一张默认样式 Mermaid 图敷衍复杂主题。
- Markdown 文档任务完成前，必须至少内部检查代码围栏是否闭合、Mermaid 语法是否使用保守写法、图表数量是否覆盖关键概念。只有复杂 Markdown 文档、含图表/代码围栏/渲染兼容风险的交付，或检查发现异常、跳过项时，才在最终答复里说明 Markdown 检查结果；纯规则条目、短列表、轻量文案修改不单独报告检查过程。

## 共用边界

- 全局规则以 `~/ai-agent/rules/*.md` 为源，各工具 home 下的 `rules/*.md` 只是逐文件软链接。
- 私有配置、敏感信息、同步边界、公司项目边界和平台差异遵循 `@rules/security-and-privacy-rules.md`。
- 项目规则只放在目标项目自己的规则入口和项目级规则目录里，不写回本仓库的全局规则。
