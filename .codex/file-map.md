# Codex 文件路径分类

以下路径使用通用模板表示。只整理 Codex 相关内容，不包含公司项目仓库。

## 当前本机生效路径

- `%USERPROFILE%\.codex\AGENTS.md`
  - Codex 全局入口
  - 当前机器实际生效文件
- `%USERPROFILE%\.codex\rules\*.md`
  - Codex 全局规则
  - 当前机器实际生效规则目录
- `%USERPROFILE%\.codex\rules\default.rules`
  - 命令审批历史
  - 本机私有，不同步

## GitHub 同步仓库路径

- `%USERPROFILE%\.codex\ai-agent\.codex\AGENTS.md`
  - 可同步
  - Windows / Mac 共用的 Codex 全局入口模板
- `%USERPROFILE%\.codex\ai-agent\.codex\AGENTS-mac.md`
  - 可同步
  - Mac 相对共用入口的差异说明
- `%USERPROFILE%\.codex\ai-agent\.codex\rules\*.md`
  - 可同步
  - Windows / Mac 共用的 Codex 全局规则模板
- `%USERPROFILE%\.codex\ai-agent\.codex\common-rules.md`
  - 可同步
  - 跨平台公共约定
- `%USERPROFILE%\.codex\ai-agent\.codex\config-windows.md`
  - 可同步
  - Windows 专属路径和配置说明
- `%USERPROFILE%\.codex\ai-agent\.codex\config-mac.md`
  - 可同步
  - Mac 专属路径和配置说明
- `%USERPROFILE%\.codex\ai-agent\.codex\do-not-sync.md`
  - 可同步
  - 不同步清单
- `%USERPROFILE%\.codex\ai-agent\.codex\file-map.md`
  - 可同步
  - 本文件

## Windows 专属

- `%USERPROFILE%\.codex\AGENTS.md`
  - 从同步仓库 `.codex\AGENTS.md` 复制生成
- `%USERPROFILE%\.codex\rules\*.md`
  - 从同步仓库 `.codex\rules\*.md` 复制生成
- `%USERPROFILE%\.codex\ai-agent\.codex\config-windows.md`
  - Windows 专属说明

## Mac 专属

- `~/.codex/AGENTS.md`
  - 从同步仓库 `.codex/AGENTS.md` 复制生成
- `~/.codex/rules/*.md`
  - 从同步仓库 `.codex/rules/*.md` 复制生成
- `~/.codex/ai-agent/.codex/config-mac.md`
  - Mac 专属说明

## 本机私有，不同步

- `%USERPROFILE%\.codex\config.toml`
- `%USERPROFILE%\.codex\config.toml.*`
- `%USERPROFILE%\.codex\rules\default.rules`
- `%USERPROFILE%\.codex\local\`
- `%USERPROFILE%\.codex\auth.json`
- `%USERPROFILE%\.codex\cap_sid`
- `%USERPROFILE%\.codex\installation_id`
- `%USERPROFILE%\.codex\.codex-global-state.json`
- `%USERPROFILE%\.codex\.codex-global-state.json.bak`
- `%USERPROFILE%\.codex\history.jsonl`
- `%USERPROFILE%\.codex\session_index.jsonl`
- `%USERPROFILE%\.codex\logs_*.sqlite*`
- `%USERPROFILE%\.codex\state_*.sqlite*`
- `%USERPROFILE%\.codex\sandbox.log`
- `%USERPROFILE%\.codex\sessions\`
- `%USERPROFILE%\.codex\archived_sessions\`
- `%USERPROFILE%\.codex\log\`
- `%USERPROFILE%\.codex\tmp\`
- `%USERPROFILE%\.codex\.tmp\`
- `%USERPROFILE%\.codex\.sandbox*`

## 需要剔除或重写

- `%USERPROFILE%\.codex\memories\<company-project>-*.md`
  - 公司项目和内部环境相关
  - 不进入个人跨设备公共同步包
- `%USERPROFILE%\.codex\memories\<defect-platform>_auth.py`
  - 登录脚本和内部平台相关
  - 不进入公共同步包
- `%USERPROFILE%\.codex\memories\<defect-platform>_auth_state.json`
  - 登录状态或认证信息
  - 不同步
- `<project>\.claude\`
  - Claude 本地 MCP、settings、logs、node_modules 和报告
  - 不进入公开项目规则模板
- `<project>\.codex\local\`
  - 项目本机私有配置和任务状态
  - 不同步
- `<project>\scripts\publish\config.env*`
  - 发布配置、token 或环境变量
  - 不同步
