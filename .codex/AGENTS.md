# Codex 全局规则入口

本文件是 Windows 和 Mac 共用的 Codex 全局入口模板。复制到每台机器的 Codex home：

- Windows：`%USERPROFILE%\.codex\AGENTS.md`
- Mac：`~/.codex/AGENTS.md`

本文件只引用个人 Codex 通用规则；不引用 Claude 配置，也不引用任何项目仓库规则。

@rules/communication-rules.md
@rules/coding-rules.md
@rules/testing-rules.md
@rules/project-governance.md
@rules/mcp-output-rules.md
@rules/requirements-and-prototype.md

## 共用边界

- 全局规则放在当前机器 Codex home 的 `rules/*.md` 下。
- `rules/default.rules` 是本机命令审批历史，不是沟通或开发规则，不上传、不引用。
- `config.toml`、`local/`、会话、日志、缓存和凭据都是本机私有配置，不同步。
- 项目规则只放在目标项目自己的 `AGENTS.md` 和 `.codex/rules/`。
- 未经用户明确点名授权，不要读取、修改、复制或上传公司项目仓库内的规则文件。
- 平台差异不要复制一整份入口文件；Mac 差异写在同步仓库的 `.codex/AGENTS-mac.md`。
