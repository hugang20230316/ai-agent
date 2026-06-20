# publish-gitlab-argo 健壮性改进设计

## 背景

2026-05-29 发布 teacher-ai 时，实际耗时 15 分钟，其中有效发布仅 90 秒。时间浪费在：

1. Keychain 写入失败（sandbox 环境 `security add-generic-password` 被拒绝，exit 161）
2. 总超时预算不足（pipeline 280s + ArgoCD sync，300s 预算用完）
3. ArgoCD 认证需要手动绕路（keychain 失败后无降级路径）
4. -Apps 逗号分隔被当成单个 app 名（404 错误）

## 改进范围

脚本 `publish_gitlab_argo.py` + `SKILL.md` agent 调用策略 + 项目 local config。

## 改动 1：Keychain 静默降级

位置：`keychain_set_password()` 和 `save_cached_credential()`

当前：`subprocess.run(..., check=True)` — 写入失败直接抛异常中断发布。

改后：
- `keychain_set_password` 改为 `check=False`，返回布尔值表示是否成功
- `save_cached_credential` 在 keychain 写入失败时，把密码写入本地 credential JSON
- stderr 输出一行警告，不中断流程

影响：只影响凭据持久化路径。下次发布时如果 keychain 仍不可用，从 JSON 读密码重新登录。

## 改动 2：总超时预算改为阶段叠加

位置：`execute_publish()` 第 1037-1040 行

当前：`max(gitLabWaitTimeout, syncTimeout)` = 300s

改后：`gitLabWaitTimeout + syncTimeout` = 600s

如果 config 里显式写了 `totalTimeoutSeconds`，仍以 config 为准。对 teacher-ai（pipeline 4-5 分钟 + sync 1-2 分钟），600s 预算足够。

## 改动 3：-Apps 支持逗号分隔

位置：`execute_publish()` 中解析 apps 列表处

当前：argparse `nargs="*"` 直接使用，`-Apps "a,b"` 得到 `["a,b"]`。

改后：对每个元素做 `split(",")` 展开并去空白：

```python
raw_apps = args.apps or []
apps = []
for item in raw_apps:
    apps.extend(a.strip() for a in item.split(",") if a.strip())
```

兼容空格分隔和逗号分隔两种写法。

## 改动 4：SKILL.md 加 doctor 前置检查

位置：`SKILL.md` Shared Workflow

在现有步骤 1 之前加：

> 0. Run `doctor` before publishing. If credential or connectivity issues are detected, resolve them before proceeding. Do not proceed to publish if doctor reports critical failures.

agent 在调用 publish 前先确认环境就绪，避免在 publish 过程中才发现认证失败浪费整个超时预算。

## 不做的事

- 超时后自动 recheck（留作后续迭代）
- Pipeline 已 passed 时跳过等待的智能重试（当前 reuse 逻辑已部分覆盖）
- GitLab CI/CD 或 runner 配置优化（SKILL.md guardrail 明确排除）

## 预期效果

正常发布流程从 15 分钟降到 2-3 分钟（pipeline 等待 + sync），无需人工介入。
