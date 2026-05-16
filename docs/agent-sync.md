# Agent 跨设备同步整理

范围只包含个人规则、个人维护 skill 和可拆分的跨平台约定；不包含任何公司项目仓库、Agent CLI 运行配置、会话、日志或凭据。

本仓库用 `AGENTS.md` 作为统一规则入口，用 `rules/` 存放规则正文，用 `skills/` 存放个人维护 skill。`docs/` 目录只保存同步说明和迁移说明，不参与规则加载。

## 全局规则

- 同步仓库内路径：`rules/*.md`
- Codex 生效路径：`~/.codex/rules/*.md`
- Claude 生效路径：`~/.claude/rules/*.md`
- Hermes 生效路径：`~/.hermes/rules/*.md` 和 profile 自己的 `rules/*.md`
- OpenClaw 生效路径：`~/.openclaw/workspace/rules/*.md`

规则文件：

- `communication-rules.md`：协作与回复规则
- `security-and-privacy-rules.md`：安全、隐私与同步边界规则
- `markdown-rules.md`：Markdown 写作与图表规则
- `coding-rules.md`：编码规则
- `testing-rules.md`：测试与验证规则
- `skill-rules.md`：skill 触发、加载和修改边界规则
- `openclaw-rules.md`：OpenClaw 排障规则
- `project-governance.md`：同步边界与治理规则
- `mcp-output-rules.md`：MCP 查询输出规则
- `requirements-and-prototype.md`：需求与原型规则

这些文件是个人 Agent 全局基线，适合跨项目、跨 Windows / Mac 共用。不要在这里写项目名、业务表、内部环境、发布链路、测试账号或项目专属构建例外。

统一入口文件是仓库根目录的 `AGENTS.md`。各工具只通过自己的原生入口加载它：

- Codex：`~/.codex/AGENTS.md -> ~/ai-agent/AGENTS.md`
- Claude：`~/.claude/CLAUDE.md` 引用 `~/.claude/AGENTS.md -> ~/ai-agent/AGENTS.md`
- Hermes：`$HERMES_HOME/SOUL.md` 要求读取 `$HERMES_HOME/AGENTS.md -> ~/ai-agent/AGENTS.md`
- OpenClaw：`~/.openclaw/workspace/AGENTS.md -> ~/ai-agent/AGENTS.md`

规则文件使用逐文件软链接暴露到各工具规则目录。不要把整个 `rules/` 目录软链接过去，因为有些工具目录里还会放本机生成文件或本机私有状态。

## AGENTS.md 模板

只维护一份共用 `AGENTS.md`。同步仓库不再维护任何分平台、分工具的公共入口模板。工具原生入口只负责引用这份 `AGENTS.md`。

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

## 说明文档

- `docs/file-map.md`：当前机器上的具体文件路径和同步分类
- `docs/do-not-sync.md`：明确禁止同步的本机配置、密钥、缓存和运行态文件
- `docs/symlink-design.md`：规则和 skill 的软链接设计

说明文档可以解释为什么同步、怎么安装、哪些文件不能同步，但不能新增 Agent 行为规则。需要新增行为规则时，必须放入 `rules/*.md` 并由 `AGENTS.md` 引用。

## Skill 同步

个人自定义 skill 放在本仓库的 `skills/<skill-name>/` 下。每个工具只软链接明确托管的 skill 目录。

不要软链接整个工具 skill 目录，这些目录混有系统 skill、插件 skill、缓存和本机安装态。

当前个人 GitHub skill 清单：

- `bug`
- `grafana`
- `hg-git`
- `publish-dev`
- `requirements-organizer`

Codex 和 Claude 通过逐个 skill 目录软链接加载这些 skill。Hermes 通过 `skills.external_dirs` 逐个列出这些目录。OpenClaw 通过 `skills.load.extraDirs` 逐个列出这些目录，不使用 workspace skill 软链接。

## 处理原则

- 各工具 CLI 配置文件不纳入同步包；每台机器单独配置
- 公共规则里不写 Windows 路径、Mac 路径、内网地址、账号、密码、token 或 cookie
- 平台相关路径、浏览器 profile、脚本绝对路径和本机状态只写进本机私有配置，不进入同步仓库
- `~/.codex/local` 只放本机私有配置，不同步
- `~/.codex/memories` 默认不进入这个同步仓库，只有明确无敏感信息、无机器路径的文件才可单独评估
- 当前整理不修改任何公司项目仓库
