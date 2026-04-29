# Codex Mac 差异说明

本文件只记录 Mac 相对共用 `AGENTS.md` 的差异，不替代 `AGENTS.md`。

## Mac 安装位置

- Codex home：`~/.codex`
- 全局入口：`~/.codex/AGENTS.md`
- 全局规则：`~/.codex/rules/*.md`
- 本机私有配置：`~/.codex/local/`
- Codex CLI 配置：`~/.codex/config.toml`
- 命令审批历史：`~/.codex/rules/default.rules`

## Mac 迁移口径

- 将同步仓库的 `.codex/AGENTS.md` 复制为 `~/.codex/AGENTS.md`。
- 将同步仓库的 `.codex/rules/*.md` 复制到 `~/.codex/rules/`。
- 不从 Windows 复制 `config.toml`、`default.rules`、`local/`、浏览器状态、PowerShell 脚本或绝对路径。
- Mac 需要的 shell 脚本、浏览器 profile 和本机凭据在 Mac 上单独创建。
