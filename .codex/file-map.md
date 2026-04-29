# Codex 文件路径分类

以下路径使用通用模板表示。只整理 Codex 相关内容，不包含公司项目仓库。

## 公共可同步

- `%USERPROFILE%\.codex\memories\external-link-preflight.md`
  - 可同步
  - 内容不依赖具体系统路径
- `%USERPROFILE%\.codex\memories\codex-cross-device-sync\README.md`
  - 可同步
- `%USERPROFILE%\.codex\memories\codex-cross-device-sync\common-rules.md`
  - 可同步
- `%USERPROFILE%\.codex\memories\codex-cross-device-sync\file-map.md`
  - 可同步
- `%USERPROFILE%\.codex\memories\codex-cross-device-sync\do-not-sync.md`
  - 可同步

## Windows 专属

- `%USERPROFILE%\.codex\memories\lanhu-login-reuse.md`
  - Windows 专属
  - 含 Windows 状态文件路径和 `.ps1` 脚本路径
- `%USERPROFILE%\.codex\bin\lanhu-open.ps1`
  - Windows 专属
  - 只放 Windows 同步目录
- `%USERPROFILE%\.codex\memories\codex-cross-device-sync\windows-config.md`
  - Windows 专属说明

## Mac 专属

- `~/.codex/memories/lanhu-login-reuse.mac.md`
  - Mac 上单独创建
- `~/.codex/bin/lanhu-open.sh`
  - Mac 上单独创建
- `~/.codex/memories/codex-cross-device-sync/mac-config.md`
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
