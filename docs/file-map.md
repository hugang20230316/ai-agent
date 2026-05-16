# Agent 文件路径分类

以下路径使用通用模板表示。只整理个人 Agent 规则、个人维护 skill 和跨平台说明，不包含公司项目仓库。

## 公共可同步

- `AGENTS.md`
  - 可同步
  - Codex、Claude、Hermes、OpenClaw 共用的统一规则入口
- `rules/*.md`
  - 可同步
  - 仅包含个人通用规则；通过逐文件软链接暴露到 `<codex-home>/rules/*.md`
  - 排除 `<codex-home>/rules/default.rules`
- `docs/agent-sync.md`
  - 可同步
  - 同步布局和安装说明，不参与规则加载
- `docs/file-map.md`
  - 可同步
  - 文件分类说明，不参与规则加载
- `docs/do-not-sync.md`
  - 可同步
  - 禁止同步清单，不参与规则加载
- `docs/symlink-design.md`
  - 可同步
  - 规则和 skill 软链接设计，不参与规则加载
- `README.md`
  - 可同步
- `.gitignore`
  - 可同步

## 平台差异

- 不在同步仓库中维护分平台公共入口、分平台规则文件或分平台配置说明。
- 平台差异通过本机私有配置、环境变量、用户 home 路径解析或跨平台脚本运行时检测处理。
- `docs/` 目录不承载平台差异规则；需要约束行为时写入 `rules/*.md`，需要记录同步说明时写入 `docs/*.md`。

## 本机私有，不同步

- `<tool-home>/config.*`
- `<tool-home>/settings*.json`
- `<tool-home>/rules/default.rules`
- `<tool-home>/local/`
- `<tool-home>/auth.json`
- `<tool-home>/installation_id`
- `<tool-home>/*state*.json`
- `<tool-home>/history.jsonl`
- `<tool-home>/session_index.jsonl`
- `<tool-home>/logs_*.sqlite*`
- `<tool-home>/state_*.sqlite*`
- `<tool-home>/sessions/`
- `<tool-home>/archived_sessions/`
- `<tool-home>/shell_snapshots/`
- `<tool-home>/log/`
- `<tool-home>/logs/`
- `<tool-home>/tmp/`
- `<tool-home>/.tmp/`
- `<tool-home>/.sandbox*`
- `<tool-home>/mcp_venvs/`
- `<tool-home>/mcp_servers/`
- `<tool-home>/skills/`
  - 整体不同步；只允许把明确托管的单个 skill 目录软链接到 `ai-agent/skills`
- `<tool-home>/memories/`

## 需要剔除或重写

- `<tool-home>/memories/<company-project>-*.md`
  - 公司项目和内部环境相关
  - 不进入个人跨设备公共同步包
- `<tool-home>/memories/<defect-platform>_auth.py`
  - 登录脚本和内部平台相关
  - 不进入公共同步包
- `<tool-home>/memories/<defect-platform>_auth_state.json`
  - 登录状态或认证信息
  - 不同步
