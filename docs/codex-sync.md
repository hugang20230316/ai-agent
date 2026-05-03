# Codex 跨设备同步整理

范围只包含 Codex 个人规则和可拆分的跨平台约定；不包含任何公司项目仓库、Claude 配置、Codex CLI 运行配置、会话、日志或凭据。

## 全局规则

- 同步仓库内路径：`rules/*.md`
- Windows 实际生效路径：`%USERPROFILE%\.codex\rules\*.md`
- Mac 实际生效路径：`~/.codex/rules/*.md`

规则文件：

- `communication-rules.md`：协作与回复规则
- `coding-rules.md`：编码规则
- `testing-rules.md`：测试与验证规则
- `openclaw-rules.md`：OpenClaw 排障规则
- `project-governance.md`：同步边界与治理规则
- `mcp-output-rules.md`：MCP 查询输出规则
- `requirements-and-prototype.md`：需求与原型规则

这些文件是个人 Codex 全局基线，适合跨项目、跨 Windows / Mac 共用。不要在这里写项目名、业务表、内部环境、发布链路、测试账号或项目专属构建例外。

Codex 全局入口文件在 Windows 放到 `%USERPROFILE%\.codex\AGENTS.md`，在 Mac 放到 `~/.codex/AGENTS.md`，两个平台都复制同一份同步仓库里的 `AGENTS.md`。入口文件使用 `@rules/*.md` 引用实际生效路径下的规则文件。

## AGENTS.md 模板

只维护一份共用 `AGENTS.md`，Windows 和 Mac 都从它复制生成实际入口。同步仓库不再维护 `AGENTS-mac.md`、`AGENTS-windows.md` 或任何分平台公共入口文件。

平台差异只允许存在于本机私有配置、环境变量、用户 home 路径解析或跨平台脚本的运行时检测中，不进入公共规则入口。

## 项目规则位置

项目规则只放在目标项目仓库内：

```text
<project>/
  AGENTS.md
  .codex/
    rules/
      *.md
```

项目根 `AGENTS.md` 负责引用项目内 `.codex/rules/*.md`。项目规则可以追加业务约束，但不要反向改写个人全局规则。

## 本目录其他文件

- `docs/common-rules.md`：Windows 和 Mac 都可复用的公共规则
- `docs/file-map.md`：当前机器上的具体文件路径和同步分类
- `docs/do-not-sync.md`：明确禁止同步的本机配置、密钥、缓存和运行态文件

## 处理原则

- `config.toml` 是 Codex CLI 配置文件，不纳入同步包；每台机器单独配置
- 公共规则里不写 Windows 路径、Mac 路径、内网地址、账号、密码、token 或 cookie
- 平台相关路径、浏览器 profile、脚本绝对路径和本机状态只写进本机私有配置，不进入同步仓库
- `~/.codex/local` 只放本机私有配置，不同步
- `~/.codex/memories` 默认不进入这个同步仓库，只有明确无敏感信息、无机器路径的文件才可单独评估
- 当前整理不修改任何公司项目仓库
