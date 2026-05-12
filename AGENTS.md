# Codex 全局规则入口

本文件是 Windows 和 Mac 共用的 Codex 全局入口模板。复制到每台机器的 Codex home：

- Windows：`%USERPROFILE%\.codex\AGENTS.md`
- Mac：`~/.codex/AGENTS.md`

本文件只引用个人 Codex 通用规则；不引用 Claude 配置，也不引用任何项目仓库规则。

@rules/communication-rules.md
@rules/security-and-privacy-rules.md
@rules/markdown-rules.md
@rules/coding-rules.md
@rules/testing-rules.md
@rules/skill-rules.md
@rules/openclaw-rules.md
@rules/project-governance.md
@rules/mcp-output-rules.md
@rules/requirements-and-prototype.md

## 强制规则加载

- 涉及创建、修改或审阅 Markdown 文档时，必须在生成内容或编辑文件前读取 `@rules/markdown-rules.md`，并按其中的图表、围栏和自检要求执行。
- 涉及创建、修改或审阅代码时，必须在动手前读取 `@rules/coding-rules.md`；完成前必须检查新增或修改的方法位置、方法注释、参数注释、返回值注释、字段注释、常量注释和配置项注释是否符合当前文件既有风格。
- 用户点名 skill、插件或任务语义命中某个 skill 时，必须同时按 `@rules/skill-rules.md` 执行触发、加载、推荐筛选和修改边界规则。
- 如果任务涉及图表、流程、架构、部署、模块关系或方案说明，必须同时按 `@rules/markdown-rules.md` 的图表风格要求设计图表；不能只放一张默认样式 Mermaid 图敷衍复杂主题。
- Markdown 文档任务完成前，必须至少检查代码围栏是否闭合、Mermaid 语法是否使用保守写法、图表数量是否覆盖关键概念，并在最终答复里说明已完成 Markdown 规则检查。

## 共用边界

- 全局规则放在当前机器 Codex home 的 `rules/*.md` 下。
- 私有配置、敏感信息、同步边界、公司项目边界和平台差异遵循 `@rules/security-and-privacy-rules.md`。
- 项目规则只放在目标项目自己的 `AGENTS.md` 和 `.codex/rules/`。
