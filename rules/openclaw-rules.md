# OpenClaw 规则

## 启动入口

- OpenClaw 的 workspace 入口应是 `~/.openclaw/workspace/AGENTS.md`，并指向统一规则入口 `~/ai-agent/AGENTS.md`。
- OpenClaw 规则不要单独散写在 workspace 入口文件里；通用规则写入 `~/ai-agent/AGENTS.md`，OpenClaw 专属规则写入本文件。
- 个人 GitHub skill 只通过 `~/.openclaw/openclaw.json` 的 `skills.load.extraDirs` 逐个引入；不要把 `~/ai-agent/skills` 整个目录指向 workspace，也不要把 Codex、Claude、Hermes 的完整 skill 目录互相指向。
- 排查 OpenClaw 本机问题时，先按 `~/ai-agent/AGENTS.md` 的规则清单加载通用规则，再按本文件处理 OpenClaw 专属步骤。

## 输出与边界

- 默认中文简洁回复，先做事再总结；不要把可执行任务停在计划阶段。
- 最终答复只写实际变更、验证结果和剩余风险。
- 消息带 `/hermes <message>` 时，调用 Hermes 本地 CLI 并只返回 Hermes 最终答复；具体 `HERMES_HOME` 使用本机私有配置或当前 profile 环境变量。
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

- 处理 `openclaw` 打开后退出、无回复、卡住或提示 Gateway 不可达时，先判断是 CLI 壳层问题、Gateway 连接问题，还是运行时依赖损坏；不要先把原因归到用户输入内容。
- 首轮固定先查 4 项：`openclaw --version`、`openclaw doctor --fix`、`openclaw status --all`、Gateway 日志；没有这 4 项证据前，不下“配置错了”或“消息触发异常”的结论。
- 若 `doctor --fix` 或启动日志出现 bundled runtime deps 缺失、`ENOENT`、依赖锁超时、模块找不到或类似报错，优先按“安装损坏 / 运行时依赖未铺完整”处理，不要继续围绕业务消息反复复现。
- 若本地端口已监听、HTTP 健康检查可通，但 TUI 仍提示 Gateway 不可达，要把问题收窄为 CLI 到本地 WebSocket 的连接链路，不要再把重点放回 Gateway 是否启动。
- 同一版本连续出现运行时依赖缺失、channel 初始化异常、缺模块或 `doctor` 修复后仍反复损坏时，优先升级到最新稳定版，再继续排查；不要长期困在旧版本上补洞。
- 若修复流程被旧进程、锁目录或残留安装任务卡住，先清掉卡住的 OpenClaw 进程和锁，再重跑 `doctor --fix`；不要在锁未释放的状态下重复执行同一命令。
- 对 OpenClaw 这类本地工具，验证结论必须分别说明：CLI 是否能启动、Gateway 是否 ready、HTTP/端口是否可达、发送一条最小消息后是否真的收到回复。
- 若升级后 Gateway 已 ready、HTTP 已通，但 `openclaw` / `openclaw chat` 仍报告本地 `ws://127.0.0.1` 不可达，要优先怀疑 TUI 与本地 WebSocket 的连接链路或包版本兼容问题，而不是继续判定为“服务没启动”。
- 若在 Codex 沙箱里复测 OpenClaw，本地 Node 进程访问 `127.0.0.1` 可能因沙箱限制报 `connect EPERM`；这类结果不能直接当作宿主机故障结论，必须在真实终端再跑一次 `openclaw status --all` 或 `openclaw gateway status --json` 复核。
- `openclaw status --all` 的 `stderr` 若还残留旧时间点的 channel 缺模块日志，要区分“历史日志残留”和“当前状态异常”；判断当前是否恢复，以 Overview 的 Gateway reachable、Channel issues、以及一条最小消息实测回复为准。
- Gateway 正常但“发消息无回复”时，优先补做 `openclaw agent --agent main --message "hi" --json` 这类最小调用；若能回复，问题更可能在 TUI 展示或交互层；若不能回复，再转向模型鉴权、默认模型和上游 API 连通性。
