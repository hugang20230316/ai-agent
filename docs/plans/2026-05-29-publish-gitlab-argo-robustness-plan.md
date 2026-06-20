# publish-gitlab-argo 健壮性改进实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 publish-gitlab-argo 在 sandbox 环境下无需人工介入即可完成发布，正常耗时从 15 分钟降到 2-3 分钟。

**Architecture:** 四项独立改动，互不依赖：keychain 写入降级为本地 JSON、总超时改为阶段叠加、-Apps 参数支持逗号分隔、SKILL.md 加 doctor 前置步骤。

**Tech Stack:** Python 3, argparse, subprocess, macOS keychain (graceful degradation)

---

### Task 1: Keychain 写入静默降级

**Files:**
- Modify: `skills/publish-gitlab-argo/scripts/publish_gitlab_argo.py:592-601`
- Modify: `skills/publish-gitlab-argo/scripts/publish_gitlab_argo.py:644-658`

**Step 1: 修改 `keychain_set_password` 返回布尔值，写入失败不抛异常**

将第 592-601 行替换为：

```python
def keychain_set_password(base_url: str, username: str, password: str, service: str = KEYCHAIN_SERVICE) -> bool:
    if not keychain_available():
        return False
    account = keychain_account(base_url, username)
    result = subprocess.run(
        ["security", "add-generic-password", "-U", "-a", account, "-s", service, "-w", password],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Warning: keychain write failed (rc={result.returncode}), falling back to local credential store", file=sys.stderr)
        return False
    return True
```

**Step 2: 修改 `save_cached_credential` 在 keychain 失败时把密码写入 JSON**

将第 644-658 行替换为：

```python
def save_cached_credential(base_url: str, username: str, password: str, session_path: Path) -> None:
    keychain_ok = keychain_set_password(base_url, username, password)
    metadata = {
        "baseUrl": base_url.rstrip("/"),
        "username": username,
        "credentialStore": "keychain" if keychain_ok else "local-state",
        "updatedAt": utc_iso(),
    }
    if keychain_ok:
        metadata["keychainService"] = KEYCHAIN_SERVICE
        metadata["legacyKeychainService"] = LEGACY_KEYCHAIN_SERVICE
        metadata["keychainAccount"] = keychain_account(base_url, username)
    else:
        metadata["password"] = password
    write_json_file(credential_metadata_path(session_path), metadata)
```

**Step 3: 验证**

```console
python3 skills/publish-gitlab-argo/scripts/publish_gitlab_argo.py doctor
```

Expected: 正常输出 JSON，无异常。

**Step 4: Commit**

```console
git add skills/publish-gitlab-argo/scripts/publish_gitlab_argo.py
git commit -m "publish-gitlab-argo: keychain 写入失败时静默降级为本地 JSON 存储"
```

---

### Task 2: 总超时预算改为阶段叠加

**Files:**
- Modify: `skills/publish-gitlab-argo/scripts/publish_gitlab_argo.py:1037-1040`

**Step 1: 修改默认值计算逻辑**

将第 1037-1040 行：

```python
    total_timeout_seconds = args.total_timeout_seconds or config_int(
        "totalTimeoutSeconds",
        max(args.gitlab_wait_timeout_seconds, args.sync_timeout_seconds),
    )
```

替换为：

```python
    total_timeout_seconds = args.total_timeout_seconds or config_int(
        "totalTimeoutSeconds",
        args.gitlab_wait_timeout_seconds + args.sync_timeout_seconds,
    )
```

**Step 2: 验证**

```console
python3 -c "
import sys; sys.argv = ['test', 'publish', '-Scope', 'default', '-WhatIf', '-Format', 'json']
exec(open('skills/publish-gitlab-argo/scripts/publish_gitlab_argo.py').read().split('if __name__')[0])
print('default total timeout:', 300 + 300, '= 600s')
"
```

逻辑验证：默认 gitLabWaitTimeout=300 + syncTimeout=300 = 600s。

**Step 3: Commit**

```console
git add skills/publish-gitlab-argo/scripts/publish_gitlab_argo.py
git commit -m "publish-gitlab-argo: 总超时默认值改为 gitLabWait + syncTimeout 叠加"
```

---

### Task 3: -Apps 参数支持逗号分隔

**Files:**
- Modify: `skills/publish-gitlab-argo/scripts/publish_gitlab_argo.py:878-879`

**Step 1: 在 `argocd_publish` 中展开逗号分隔的 app 名**

将第 878-879 行：

```python
    if args.apps:
        resolved_apps = sorted({app for app in args.apps if app})
```

替换为：

```python
    if args.apps:
        resolved_apps = sorted({a.strip() for item in args.apps for a in item.split(",") if a.strip()})
```

**Step 2: 验证解析逻辑**

```console
python3 -c "
apps_input = ['app-a,app-b', 'app-c']
resolved = sorted({a.strip() for item in apps_input for a in item.split(',') if a.strip()})
assert resolved == ['app-a', 'app-b', 'app-c'], f'Got: {resolved}'
print('OK: comma and space separation both work')
"
```

Expected: `OK: comma and space separation both work`

**Step 3: Commit**

```console
git add skills/publish-gitlab-argo/scripts/publish_gitlab_argo.py
git commit -m "publish-gitlab-argo: -Apps 参数支持逗号分隔"
```

---

### Task 4: SKILL.md 加 doctor 前置检查步骤

**Files:**
- Modify: `skills/publish-gitlab-argo/SKILL.md`

**Step 1: 在 Shared Workflow 第 1 步前插入 doctor 检查**

在 `## Shared Workflow` 的编号列表开头加入：

```markdown
0. Run `python3 scripts/publish_gitlab_argo.py doctor` before publishing. If credential or connectivity issues are detected (e.g., ArgoCD token expired, GitLab unreachable), resolve them before proceeding. Do not proceed to publish if doctor reports critical failures.
```

**Step 2: 在 Tooling 示例中把 doctor 放在第一位并加注释**

确认 `doctor` 已在示例列表第一行（当前已是）。

**Step 3: Commit**

```console
git add skills/publish-gitlab-argo/SKILL.md
git commit -m "publish-gitlab-argo: SKILL.md 加 doctor 前置检查步骤"
```

---

### Task 5: 最终验证

**Step 1: 运行 doctor 确认脚本无语法错误**

```console
cd <ai-agent-repo>
python3 skills/publish-gitlab-argo/scripts/publish_gitlab_argo.py doctor
```

Expected: JSON 输出，包含配置、连接状态和凭据状态。

**Step 2: 运行 resolve-plan 确认计划解析正常**

```console
python3 skills/publish-gitlab-argo/scripts/publish_gitlab_argo.py resolve-plan -Scope default -Format json
```

Expected: JSON 输出，包含 nextTag、sourceCommit、targetApps。

**Step 3: 确认 git 状态干净**

```console
git status --short
git log --oneline -5
```
