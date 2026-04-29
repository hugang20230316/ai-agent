# Mac 专属配置

本文件只记录 Mac 机器上应单独创建的 Codex 路径、脚本和本机配置。Mac 没有现成状态时，不要从 Windows 复制浏览器会话、绝对路径或 CLI 配置。

## Mac 目标路径

- Codex 根目录：`~/.codex`
- Codex 全局入口：`~/.codex/AGENTS.md`
- Codex 全局规则：`~/.codex/rules/*.md`
- 公共 memory 目录：`~/.codex/memories`
- 本机私有配置目录：`~/.codex/local`
- 本机脚本目录：`~/.codex/bin`
- Codex CLI 配置：`~/.codex/config.toml`
- Codex 命令审批规则：`~/.codex/rules/default.rules`

## Mac 需要单独创建

- `~/.codex/config.toml`
  - 由 Mac 本机 Codex CLI 生成或手工配置
  - 不从 Windows 覆盖
- `~/.codex/rules/default.rules`
  - Mac 本机审批历史
  - 不从 Windows 覆盖
- `~/.codex/local/*.local.json`
  - Mac 本机私有配置
  - 不从 Windows 覆盖
- `~/.codex/bin/lanhu-open.sh`
  - 如需蓝湖复用脚本，在 Mac 上单独实现
  - 不复用 Windows 的 `.ps1` 文件
- `~/.codex/memories/lanhu-login-reuse.mac.md`
  - 如需蓝湖登录态复用，在 Mac 上记录 Mac 专属浏览器 profile、状态文件和脚本路径

## Mac 可直接复用

- `.codex/AGENTS.md`
- `.codex/AGENTS-mac.md`
- `.codex/rules/*.md`
- 公共外链预检规则
- 公共同步边界规则
- 不含机器路径、不含账号密码、不含 token 的 memory

## Mac 不应复用

- Windows 盘符路径
- PowerShell 脚本
- Windows 浏览器 profile
- Windows agent-browser state 文件
- Windows 的 `config.toml`
- Windows 的 `default.rules`

## Mac 建议同步包结构

```text
codex-sync/
  common/
    common-rules.md
    external-link-preflight.md
  windows/
    windows-config.md
  mac/
    mac-config.md
    lanhu-login-reuse.mac.md
    bin/
      lanhu-open.sh
```
