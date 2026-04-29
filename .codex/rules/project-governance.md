# Codex 项目治理规则

- 公共同步仓库只保存通用规则、说明和无敏感信息的 memory。
- `config.toml` 是 Codex CLI 本机配置，不同步，不放入公开仓库。
- `.codex/local/` 保存本机私有配置，不同步。
- `default.rules` 是本机命令审批历史，不同步。
- 会话、日志、sqlite、缓存、浏览器状态、token、cookie、账号密码和内部环境配置一律不同步。
- Windows 专属路径、PowerShell 脚本和浏览器状态只放 Windows 文件；Mac 专属路径、shell 脚本和状态只放 Mac 文件。
- 公共规则不得混入平台路径、公司项目路径、内部域名、内网 IP 或个人账号。
- 上传公开仓库前必须做敏感扫描，至少检查 token、password、cookie、内网 IP、公司域名和个人绝对路径。
- 发现 token 或密码已经进入聊天、日志、审批规则或提交记录时，先删除本地残留，再提示用户在平台撤销该凭据。
