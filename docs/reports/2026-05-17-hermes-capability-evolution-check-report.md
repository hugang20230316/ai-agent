# Hermes 能力检查与进化闭环报告

## 摘要

Hermes 当前可用于本机 CLI 日常任务。基础环境、命令入口、规则软链接、skills/tools/plugins/MCP 列表、cron/gateway 状态检查都能正常执行。`doctor` 未发现 active security advisory，核心依赖正常。

本轮发现的主要问题集中在四类：

- Hermes 版本落后上游较多，且 Hermes 仓库已有未提交评估改动，不能直接更新。
- Dashboard 的 `--skip-build` 模式缺少已构建 Web 资产，短启动失败。
- `hermes tools --summary` 行为与 help 文案不一致。
- MCP 的 server 启用状态和 tools 展示状态口径不一致，容易误判某个 MCP server 是否可用。

本次没有执行更新、迁移、安装、卸载、真实平台投递或长期后台运行；没有读取敏感配置原文、sessions、memories 或日志全文。

## 能力矩阵

| 能力域 | 状态 | 证据摘要 | 风险 |
| --- | --- | --- | --- |
| 安装与版本 | 可用 | `hermes --version` 能返回版本；项目目录为 `$HERMES_HOME/hermes-agent` | 提示落后上游较多 |
| CLI 命令面 | 可用 | `hermes --help` 能列出 chat、model、gateway、cron、skills、tools、mcp、dashboard 等子命令 | 能力面很宽，需要任务边界 |
| 基础诊断 | 可用 | `hermes doctor` 核心环境正常，无 active security advisory | 多个可选 provider、平台和工具未配置 |
| 状态摘要 | 可用 | `hermes status` 能输出环境、provider、gateway、jobs、sessions 状态 | 会展示部分脱敏 key 形态，报告中不能原样粘贴 |
| Dump | 可用 | `hermes dump` 能输出紧凑支持信息 | 适合支持排查，但仍需脱敏审查 |
| Logs list | 可用 | `hermes logs list` 能列出日志文件和大小 | 不应在通用报告中展开日志全文 |
| 规则链路 | 正常 | `$HERMES_HOME/AGENTS.md` 指向个人规则入口；`$HERMES_HOME/rules/*.md` 软链接集合一致 | Hermes 不保证自动展开 AGENTS，依赖 SOUL 兜底 |
| Skills | 可列出 | `hermes skills list` 能列出 enabled skills，包含 builtin 和 local 来源 | 默认启用面较宽 |
| Tools | 可列出 | `hermes tools list --platform cli` 可输出 CLI 工具状态 | `tools --summary` 行为异常 |
| Plugins | 可列出 | 4 个 bundled plugin 均未启用 | 默认 opt-in，状态合理 |
| MCP | 可列出 | `hermes mcp list` 能列出若干已配置 server；其中一个 server 在 `mcp list` 中 disabled | `tools list` 与 `mcp list` 对同一 server 的状态展示不一致 |
| Cron | 可检查 | `hermes cron status/list` 显示 gateway 未运行、无 scheduled jobs | 未启动 gateway 时 cron 不会自动触发 |
| Gateway | 可检查 | `hermes gateway status/list` 显示本机 profile 均未运行 | 未做真实平台收发验证 |
| Dashboard | 部分可用 | `hermes dashboard --help/status` 可用；默认端口未监听；短启动 `--skip-build` 失败 | 缺少 Web dist；`status` 结果仍需结合端口监听验证 |

## 问题清单

| 严重度 | 分类 | 问题 | 影响 | 建议 |
| --- | --- | --- | --- | --- |
| 高 | 立即修复候选 | Hermes 仓库有未提交改动和未跟踪评估产物 | 更新、迁移或继续实验时容易混入无关变更 | 先确认这些改动归属；需要更新前先单独处理工作区 |
| 中 | 立即修复候选 | Dashboard `--skip-build` 缺少 Web dist，短启动失败 | 无法在无构建模式下打开 dashboard | 允许构建时运行 Web 构建；或沉淀检查，缺 dist 时提示改用自动构建 |
| 中 | 立即修复候选 | `hermes tools --summary` 与 help 文案不一致 | 自动化脚本按 help 调用会失败或进入交互 | 修 CLI 参数解析或修 help；短期用 `hermes tools list --platform cli` |
| 中 | 建议沉淀 | `hermes mcp list` 显示某个 server disabled，但 `tools list` 的 MCP 区域显示该 server 的 tools enabled | agent 容易误判 MCP server 可用 | 沉淀判定口径：server 状态以 `mcp list` 为准，tool 选择以 `tools list` 为准 |
| 中 | 建议沉淀 | Hermes 规则实际加载依赖 SOUL 中“每轮先读 AGENTS”的兜底 | 若某轮没有遵守 SOUL，可能只加载 persona，不加载完整规则 | 保留 SOUL 兜底；补一个只读规则链路审计 skill 或脚本 |
| 中 | 观察项 | `doctor` 显示多个可选包、provider、平台和工具未配置 | 不影响 CLI 基础使用，但会限制消息平台、部分 web/search/MCP/工具能力 | 按真实使用场景逐项配置，不建议一次性全开 |
| 中 | 观察项 | 当前版本落后上游较多 | 可能缺少新修复，也可能有升级风险 | 更新前先处理工作区、备份配置、看 release notes |
| 低 | 立即修复候选 | PATH 中 Hermes 可执行路径重复 | 排查实际入口时容易混淆 | 整理 shell 启动文件里的重复 PATH 注入 |
| 低 | 观察项 | 英文 README 和中文 README 对 Windows 原生支持表述不一致 | 中文用户可能被误导 | 若维护 Hermes 文档，后续同步两份 README |
| 低 | 建议沉淀 | Skills 默认启用面较宽 | 高权限能力较多，任务边界依赖规则约束 | 按 profile 或任务域沉淀最小启用策略 |

## 进化建议

### 个人规则

- 保留当前规则：涉及配置、凭据、日志、会话和外部平台时，默认不读取敏感原文，不执行写入型动作。
- 增补一条 Hermes 专用审计口径：判断 MCP 可用性时，server 启用状态以 `hermes mcp list` 为准，工具选择状态以 `hermes tools list` 为准。
- 增补一条 dashboard 检查口径：如果 `--skip-build` 缺少 Web dist，不自动执行构建，先报告缺口并征求是否允许构建。

### Hermes 本机配置

- 不建议为了“能力完整”一次性配置所有 provider 和平台。当前 CLI 基础能力正常，缺口主要是按需启用的外部集成。
- 如果需要消息平台和 cron 自动触发，再单独配置 gateway，并把真实平台收发作为独立验证任务。
- 如果需要 dashboard，先决定是否允许构建 Web 资产；构建动作可能写入 Hermes 项目目录，应单独确认。

### 自定义 skill

建议新增一个个人维护的 `hermes-capability-audit` skill，职责只包括：

- 检查 Hermes 版本、路径、doctor/status/dump 摘要。
- 检查 SOUL、AGENTS、rules 软链接链路。
- 检查 skills/tools/plugins/MCP/cron/gateway/dashboard 的只读状态。
- 输出问题分类和沉淀建议。

另可拆出更小的 `rules-chain-audit` skill，只检查规则入口和软链接，适合每次调整规则后快速验证。

### 自动化脚本

可写一个只读脚本复用本次流程：

- 输入：无，或指定 `$HERMES_HOME`。
- 输出：Markdown/JSON 摘要。
- 禁止：读取 `.env`、`config.yaml` 原文、sessions、memories、logs 全文。
- 检查项：版本、工作区状态、doctor 摘要、status 摘要、rules 链路、skills/tools/MCP/cron/gateway/dashboard 状态。

脚本应把命令结果分类为 OK/WARN/FAIL/SKIP，并保留“跳过原因”。

## 未覆盖项

- 未执行 `hermes update`，因为仓库已有未提交改动，且更新属于写入动作。
- 未执行 `doctor --fix`，因为它会自动修复并可能修改配置或安装依赖。
- 未执行 `hermes setup`、`login`、`auth add`、`tools enable/disable`、`plugins enable/disable`。
- 未运行 `hermes mcp test`，因为可能启动外部 MCP 进程、触发网络连接或认证流程。
- 未启动 gateway，也未做真实消息平台收发。
- 未构建 dashboard Web 资产。
- 未展开日志全文、sessions、memories 或配置原文。

## 下一步

推荐下一轮只做两个低风险动作：

1. 创建 `hermes-capability-audit` 自定义 skill 或只读脚本，把本次检查固化为可重复流程。
2. 修正规则：补充 MCP 状态判定口径和 dashboard 构建边界。

更高风险动作，如更新 Hermes、构建 dashboard、配置 gateway 或启用更多 provider，应分别走单独计划。
