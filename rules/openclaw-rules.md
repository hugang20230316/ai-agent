# OpenClaw 规则

## 启动入口

- OpenClaw 的 workspace 入口应是 `~/.openclaw/workspace/AGENTS.md`，并指向统一规则入口 `~/ai-agent/AGENTS.md`。
- OpenClaw 规则不要单独散写在 workspace 入口文件里；通用规则写入 `~/ai-agent/AGENTS.md`，OpenClaw 专属规则写入本文件。
- 个人 GitHub skill 只通过 `~/.openclaw/openclaw.json` 的 `skills.load.extraDirs` 逐个引入；不要把 `~/ai-agent/skills` 整个目录指向 workspace，也不要把 Codex、Claude、Hermes 的完整 skill 目录互相指向。
- 排查 OpenClaw 本机问题时，先按 `~/ai-agent/AGENTS.md` 的规则清单加载通用规则，再按本文件处理 OpenClaw 专属步骤。

## 输出与边界

- 默认中文简洁回复，先做事再总结；不要把可执行任务停在计划阶段。
- 最终答复只写实际变更、验证结果和剩余风险。
- 在 OpenClaw 原生会话中，消息带 `/hermes <message>` 时，可以调用 Hermes 本地 CLI 并只返回 Hermes 最终答复；具体 `HERMES_HOME` 使用本机私有配置或当前 profile 环境变量。
- `/hermes` 请求不得启动、停止、重启、安装、配置或登录 Hermes Gateway；如果 CLI 调用失败，只报告命令失败。
- 不执行破坏性命令，不外发消息，不上传私有数据，除非用户明确授权。

## 工作方式

- 先读本机上下文再编辑。
- 优先做最小、可验证的改动。
- 不碰无关文件，保留用户已有改动和本机秘密。
- 改完后运行最小相关验证；验证无法运行时说明具体原因。

## 长任务

- 命令或 RPC 5 分钟无进展时，报告已耗时、最后输出、可能原因和下一步。
- OpenClaw 命令表现异常时，先检查 gateway 健康、日志、残留进程和会话状态，再重试。

## 记忆

- 重要决策和经验写入可同步文件或明确的本机 memory，不依赖会话记忆。
- 长期记录要保持精简，不写入凭据或敏感信息。

- 处理 OpenClaw 打开后退出、无回复、卡住或提示 Gateway 不可达时，先区分 CLI 壳层、Gateway、运行时依赖、交互层和上游 API，不要先归因到用户输入内容。
- 启动类故障先收集版本、诊断、状态、健康检查和日志摘要证据；发现依赖缺失、锁、残留进程或版本兼容问题时，按安装完整性和运行时链路处理。
- 验证结论必须分别说明 CLI 是否能启动、Gateway 是否 ready、HTTP/端口是否可达、最小消息是否真的收到回复；沙箱内 loopback 失败需在宿主终端复核。
