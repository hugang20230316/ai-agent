# Windows 专属配置

本文件只记录 Windows 机器上的 Codex 相关路径、脚本和本机配置归属。不要把这些内容合并进公共规则。

## Windows 路径模板

- Codex 根目录：`%USERPROFILE%\.codex`
- 公共 memory 目录：`%USERPROFILE%\.codex\memories`
- 本机私有配置目录：`%USERPROFILE%\.codex\local`
- 本机脚本目录：`%USERPROFILE%\.codex\bin`
- Codex CLI 配置：`%USERPROFILE%\.codex\config.toml`
- Codex 命令审批规则：`%USERPROFILE%\.codex\rules\default.rules`

## 可参考但不直接同步

- `%USERPROFILE%\.codex\config.toml`
  - Codex CLI 配置
  - 每台机器单独配置
  - 不进入共享包
- `%USERPROFILE%\.codex\rules\default.rules`
  - 命令审批 allowlist
  - 含大量本机路径和历史命令
  - 不进入共享包
- `%USERPROFILE%\.codex\local\*.local.json`
  - 本机私有发布配置
  - 不进入共享包

## Windows 可迁移内容

- `%USERPROFILE%\.codex\memories\external-link-preflight.md`
  - 内容偏公共，可整理进公共规则
- `%USERPROFILE%\.codex\memories\lanhu-login-reuse.md`
  - 含 Windows 路径和 `.ps1` 脚本引用
  - 只能作为 Windows 专属规则迁移
- `%USERPROFILE%\.codex\bin\lanhu-open.ps1`
  - Windows 专属脚本
  - 若要迁移，只放到 Windows 专属目录

## Windows 建议同步包结构

```text
codex-sync/
  common/
    common-rules.md
    external-link-preflight.md
  windows/
    windows-config.md
    lanhu-login-reuse.windows.md
    bin/
      lanhu-open.ps1
  mac/
    mac-config.md
```

## Windows 恢复口径

- 公共规则恢复到：`%USERPROFILE%\.codex\memories`
- Windows 专属 memory 恢复到：`%USERPROFILE%\.codex\memories`
- Windows 专属脚本恢复到：`%USERPROFILE%\.codex\bin`
- 私有配置重新创建到：`%USERPROFILE%\.codex\local`
- `config.toml` 由 Codex CLI 或用户手工配置，不从同步包覆盖
