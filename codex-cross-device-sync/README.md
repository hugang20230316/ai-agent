# Codex 跨设备同步整理

范围只包含 Codex 个人规则、公开 memory 和可拆分的跨平台约定；不包含任何公司项目仓库、Claude 配置、Codex CLI 运行配置、会话、日志或凭据。

## 本目录文件

- `common-rules.md`：Windows 和 Mac 都可复用的公共规则
- `windows-config.md`：只适用于 Windows 的路径、脚本和本机状态说明
- `mac-config.md`：Mac 需要单独创建或迁移的路径、脚本和本机状态说明
- `file-map.md`：当前 Windows 机器上的具体文件路径和同步分类
- `do-not-sync.md`：明确禁止同步的本机配置、密钥、缓存和运行态文件

## 处理原则

- `config.toml` 是 Codex CLI 配置文件，不纳入同步包；每台机器单独配置
- 公共规则里不写 Windows 路径、Mac 路径、内网地址、账号、密码、token 或 cookie
- 平台相关路径只写进 `windows-config.md` 或 `mac-config.md`
- `.codex/local` 只放本机私有配置，不同步
- `.codex/memories` 只有明确无敏感信息、无机器路径的文件才可同步
- 当前整理不修改任何公司项目仓库
