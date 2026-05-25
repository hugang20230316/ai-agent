# Hermes 规则

## 启动入口

- Hermes 原生入口是 `$HERMES_HOME/SOUL.md`；涉及 Hermes 时，先确认它会读取 `$HERMES_HOME/AGENTS.md`。
- `$HERMES_HOME/AGENTS.md` 应指向统一规则入口 `~/ai-agent/AGENTS.md`，不要在 Hermes home 里单独散写通用规则。
- `$HERMES_HOME/rules/*.md` 只做逐文件软链接，源文件放在 `~/ai-agent/rules/*.md`。
- 个人 GitHub skill 只通过 `$HERMES_HOME/config.yaml` 的 `skills.external_dirs` 逐个引入具体 skill 目录；不要指向整个 `~/ai-agent/skills`，也不要指向其他工具的完整 skill 目录。

## 修改边界

- `$HERMES_HOME/hermes-agent` 是 Hermes 官方源码或安装目录，默认只读诊断，不直接修改或提交；除非用户明确要求维护该源码、本地 fork 或准备上游补丁。
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
