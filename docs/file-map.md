# Codex 文件路径分类

以下路径使用通用模板表示。只整理 Codex 个人规则和跨平台说明，不包含公司项目仓库。

## 公共可同步

- `AGENTS.md`
  - 可同步
  - Windows 和 Mac 共用的 Codex 全局入口模板
- `rules/*.md`
  - 可同步
  - 仅包含个人通用规则；排除 `<codex-home>/rules/default.rules`
- `docs/common-rules.md`
  - 可同步
- `docs/codex-sync.md`
  - 可同步
- `docs/file-map.md`
  - 可同步
- `docs/do-not-sync.md`
  - 可同步
- `README.md`
  - 可同步
- `.gitignore`
  - 可同步

## 平台差异

- 不在同步仓库中维护分平台公共入口、分平台规则文件或分平台配置说明。
- 平台差异通过本机私有配置、环境变量、用户 home 路径解析或跨平台脚本运行时检测处理。

## 本机私有，不同步

- `<codex-home>/config.toml`
- `<codex-home>/config.toml.*`
- `<codex-home>/rules/default.rules`
- `<codex-home>/local/`
- `<codex-home>/auth.json`
- `<codex-home>/cap_sid`
- `<codex-home>/installation_id`
- `<codex-home>/.codex-global-state.json`
- `<codex-home>/.codex-global-state.json.bak`
- `<codex-home>/history.jsonl`
- `<codex-home>/session_index.jsonl`
- `<codex-home>/logs_*.sqlite*`
- `<codex-home>/state_*.sqlite*`
- `<codex-home>/sandbox.log`
- `<codex-home>/sessions/`
- `<codex-home>/archived_sessions/`
- `<codex-home>/shell_snapshots/`
- `<codex-home>/log/`
- `<codex-home>/tmp/`
- `<codex-home>/.tmp/`
- `<codex-home>/.sandbox*`
- `<codex-home>/mcp_venvs/`
- `<codex-home>/mcp_servers/`
- `<codex-home>/skills/`
- `<codex-home>/memories/`
- `<codex-home>/AGENTS-mac.md`
- `<codex-home>/AGENTS-windows.md`

## 需要剔除或重写

- `<codex-home>/memories/<company-project>-*.md`
  - 公司项目和内部环境相关
  - 不进入个人跨设备公共同步包
- `<codex-home>/memories/<defect-platform>_auth.py`
  - 登录脚本和内部平台相关
  - 不进入公共同步包
- `<codex-home>/memories/<defect-platform>_auth_state.json`
  - 登录状态或认证信息
  - 不同步
