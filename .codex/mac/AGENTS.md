# Codex Mac 全局规则入口

将本文件复制到 Mac 机器的 `~/.codex/AGENTS.md`。

本文件只引用个人 Codex 通用规则；不引用 Claude 配置，也不引用任何项目仓库规则。

@rules/communication-rules.md
@rules/coding-rules.md
@rules/testing-rules.md
@rules/project-governance.md
@rules/mcp-output-rules.md
@rules/requirements-and-prototype.md

## Mac 边界

- 全局规则实际生效位置：`~/.codex/rules/*.md`
- 命令审批历史：`~/.codex/rules/default.rules`，不上传、不引用
- Codex CLI 配置：`~/.codex/config.toml`，不上传、不覆盖
- 本机私有配置：`~/.codex/local/`，不上传
- 项目规则只放在目标项目自己的 `AGENTS.md` 和 `.codex/rules/`
