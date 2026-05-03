# 不同步清单

以下内容不进入 Windows / Mac 公共同步包。

## Codex CLI 配置

- `~/.codex/config.toml`
- `~/.codex/config.toml.*`

原因：这是 agent CLI 本机配置，包含模型、供应商、MCP、插件、本机 trusted projects 和路径。每台机器单独配置。

## 命令审批历史

- `~/.codex/rules/default.rules`

原因：这是本机审批规则和历史命令集合，混有平台命令、绝对路径、历史任务和可能的敏感片段。

## 私有配置

- `~/.codex/local/`

原因：用于保存本机私有地址、凭据、测试环境、Swagger 地址、发布配置和脚本状态。

## 认证与会话

- `~/.codex/auth.json`
- `~/.codex/cap_sid`
- `~/.codex/installation_id`
- `~/.codex/shell_snapshots/`
- `~/.codex/sessions/`
- `~/.codex/archived_sessions/`
- `~/.codex/session_index.jsonl`
- `~/.codex/history.jsonl`

原因：包含账号、会话、历史上下文或设备标识。

## 日志与数据库

- `~/.codex/log/`
- `~/.codex/sandbox.log`
- `~/.codex/logs_*.sqlite*`
- `~/.codex/state_*.sqlite*`
- `~/.codex/sqlite/`

原因：运行态数据，不具备跨机器复用价值。

## 缓存与临时目录

- `~/.codex/tmp/`
- `~/.codex/.tmp/`
- `~/.codex/.sandbox/`
- `~/.codex/.sandbox-bin/`
- `~/.codex/.sandbox-secrets/`
- `~/.codex/plugins/`
- `~/.codex/vendor_imports/`
- `~/.codex/mcp_venvs/`
- `~/.codex/mcp_servers/`
- `~/.codex/skills/`

原因：缓存、运行时产物或平台专属依赖，应由本机重建。

## 公司项目和内部环境

- 任何公司项目仓库路径
- 任何内网 IP、内部域名、测试账号、发布 token、缺陷平台会话
- `~/.codex/memories/`
- `~/.codex/memories/<company-project>-*.md`
- `~/.codex/memories/<defect-platform>_auth.py`
- `~/.codex/memories/<defect-platform>_auth_state.json`

原因：与个人跨设备 Codex 规则无关，且可能包含公司环境或认证信息。
