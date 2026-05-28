# Hermes 规则

## 加载边界

- Hermes 原生会话启动后，SOUL/AGENTS 入口只负责接入公共规则；涉及 Hermes CLI、Dashboard、Gateway、MCP 或 cron 时再执行本文件。
- Hermes 本地目录、入口文件、skills 外部目录、MCP 和 Gateway 配置由本机 profile 或当前 Hermes 配置声明，公共规则不写具体路径。
- Hermes 本地目录不单独散写通用规则；通用行为回到公共规则，Hermes 专属行为写入本文件。

## 修改边界

- Hermes 官方源码或安装目录默认只读诊断，不直接修改或提交；除非用户明确要求维护该源码、本地 fork 或准备上游补丁。
- 发现 Hermes 官方问题时，默认给出复现命令、影响、临时绕过、配置或规则方案，以及上游 patch 建议；不要直接改官方文件。
- 不运行 `hermes update`、迁移、卸载、备份恢复、安装依赖、构建 Dashboard 或启动长期服务，除非用户明确授权。
- 不读取 `.env`、`config.yaml` 原文、sessions、memories、日志全文或凭据文件；需要状态时，使用 `hermes doctor`、`hermes status`、`hermes dump` 或日志摘要命令，并脱敏输出。

## 能力检查

- 用户要求测试、检查或排查 Hermes 能力时，目标是发现问题并给出修复或绕过方案；不要生成 spec、plan、报告文件，除非用户明确要求留档。
- 优先使用 Hermes 自带的只读状态、诊断、列表和日志摘要命令；具体命令以当前安装版本的 help 或本机配置为准。
- `hermes status` 可能展示脱敏 key 形态，最终答复只说明配置状态，不粘贴 key 片段。
- Dashboard 检查同时看 `hermes dashboard --status` 和端口监听或 HTTP 结果；`--skip-build` 缺少 web dist 时只报告，不自动构建。
- MCP 可用性以 `hermes mcp list` 的 server enabled 或 disabled 状态为准；`hermes tools list` 只能说明 tool filter，不替代 server 状态。

## 输出

- 最终答复只写问题、证据、已做的配置或规则变化、剩余风险和建议动作。
