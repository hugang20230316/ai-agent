#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


def load_skill_config(skill_name: str) -> dict[str, Any]:
    candidates: list[Path] = []
    config_dir = os.environ.get("CODEX_SKILL_CONFIG_DIR")
    if config_dir:
        candidates.append(Path(config_dir).expanduser() / f"{skill_name}.local.json")

    home = Path.home()
    candidates.append(home / ".codex" / "local" / f"{skill_name}.local.json")

    current = Path.cwd().resolve()
    for parent in [current, *current.parents]:
        candidates.append(parent / ".codex" / "local" / f"{skill_name}.local.json")

    for candidate in candidates:
        if candidate.exists():
            value = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                value["_configPath"] = str(candidate)
                return value
    return {}


def resolve_secret(source: str | None) -> str:
    if not source:
        return ""
    if source.startswith("env:"):
        return os.environ.get(source[4:], "")
    return source


PUBLISH_CONFIG = load_skill_config("publish-dev")
DEFAULT_SCOPE = "default"
DEFAULT_BASE_URL = str(PUBLISH_CONFIG.get("argocdBaseUrl") or "https://argocd.example.com").rstrip("/")
DEFAULT_PROJECT = str(PUBLISH_CONFIG.get("argocdProject") or "project-dev")
DEFAULT_DEFAULT_APPS = [str(item) for item in PUBLISH_CONFIG.get("defaultApps", []) if item]
DEFAULT_ALL_APPS_NAME_FILTER = str(PUBLISH_CONFIG.get("allAppsNameFilter") or "")
DEFAULT_RELEASE_TAG_PATTERN = re.compile(str(PUBLISH_CONFIG.get("releaseTagPattern") or r"^v0\.0\.\d+$"))
KEYCHAIN_SERVICE = "codex.publish-dev.argocd"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(value: datetime | None = None) -> str:
    return (value or utc_now()).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def user_home() -> Path:
    return Path.home()


def expand_user_path(path: str | None) -> Path | None:
    if not path:
        return None
    return Path(path).expanduser()


def resolve_existing_path(path: str | Path | None) -> Path | None:
    if path is None:
        return None
    candidate = Path(path).expanduser()
    if candidate.exists():
        return candidate.resolve()
    return None


def to_home_relative(path: str | Path | None) -> str:
    if path is None:
        return ""
    candidate = Path(path).expanduser()
    try:
        return "~/" + str(candidate.resolve().relative_to(user_home()))
    except Exception:
        return str(candidate)


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_env_style_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        values[key] = value
    return values


def configured_repo_markers() -> list[str]:
    markers = PUBLISH_CONFIG.get("repoMarkers")
    if isinstance(markers, list):
        return [str(item) for item in markers if item]
    return []


def is_configured_repo(path: Path) -> bool:
    if not path.is_dir() or not (path / ".git").is_dir():
        return False
    markers = configured_repo_markers()
    if not markers:
        return True
    return any((path / marker).exists() for marker in markers)


def repo_search_roots() -> list[Path]:
    roots: list[Path] = []
    cwd = Path.cwd()
    roots.append(cwd)
    roots.append(user_home())
    for segments in [
        ("Works",),
        ("Works", "7Day"),
        ("Projects",),
        ("Code",),
        ("src",),
        ("workspace",),
        ("workspaces",),
        ("dev",),
        ("repos",),
        ("git",),
    ]:
        roots.append(user_home().joinpath(*segments))
    return list(dict.fromkeys(root for root in roots if root))


def resolve_repo_path(requested_path: str | None) -> Path:
    if requested_path:
        candidate = expand_user_path(requested_path)
        assert candidate is not None
        if is_configured_repo(candidate):
            return candidate.resolve()
        raise RuntimeError(f"RepoPath {to_home_relative(candidate)} 不存在，或不是可识别的发布仓库。")

    env_candidates = [os.getenv("PUBLISH_DEV_REPO_PATH")]
    candidates: list[Path] = []
    for value in env_candidates:
        if value:
            candidates.append(Path(value).expanduser())
    repo_directory_name = str(PUBLISH_CONFIG.get("repoDirectoryName") or "").strip()
    for root in repo_search_roots():
        candidates.append(root)
        if repo_directory_name:
            candidates.append(root / repo_directory_name)
        if root.exists():
            try:
                for child in root.iterdir():
                    if child.is_dir() and repo_directory_name:
                        candidates.append(child / repo_directory_name)
            except OSError:
                pass

    deduped: list[Path] = list(dict.fromkeys(candidates))
    for candidate in deduped:
        if is_configured_repo(candidate):
            return candidate.resolve()

    displayed = ", ".join(to_home_relative(candidate) for candidate in deduped[:10])
    raise RuntimeError(f"未找到发布仓库。已检查常见位置: {displayed}。请通过 -RepoPath 指定仓库根目录。")


def publish_state_directory(create_default: bool = False) -> Path | None:
    configured = PUBLISH_CONFIG.get("publishStateDir") or PUBLISH_CONFIG.get("stateDir")
    if configured:
        candidate = expand_user_path(str(configured))
        assert candidate is not None
        if create_default:
            return ensure_directory(candidate).resolve()
        return candidate.resolve() if candidate.exists() else candidate
    if not create_default:
        return None
    return ensure_directory(user_home() / ".codex" / "memories" / "publish-dev").resolve()


def run_git(repo_path: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", "-c", f"safe.directory={repo_path}", "-C", str(repo_path), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise RuntimeError((process.stdout + process.stderr).strip())
    return process.stdout.strip()


def json_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: Any = None,
    capture_headers: bool = False,
) -> Any:
    payload = None
    request_headers = dict(headers or {})
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    req = request.Request(url, data=payload, method=method.upper(), headers=request_headers)
    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read()
            content = raw.decode("utf-8") if raw else ""
            parsed = json.loads(content) if content else None
            if capture_headers:
                return parsed, dict(response.headers)
            return parsed
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        message = raw.strip() or exc.reason
        raise RuntimeError(message) from exc
    except error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


@dataclass
class GitLabConnection:
    base_url: str
    project_id: str
    token: str
    config_path: str | None


def gitlab_connection_info(repo_path: Path, args: argparse.Namespace) -> GitLabConnection:
    candidate_paths: list[Path] = []
    configured_gitlab_config_path = getattr(args, "gitlab_config_path", None) or PUBLISH_CONFIG.get("gitlabConfigPath")
    if configured_gitlab_config_path:
        config_path = expand_user_path(str(configured_gitlab_config_path))
        if config_path:
            candidate_paths.append(config_path)
    candidate_paths.append(repo_path / "scripts" / "publish" / "config.env.local")
    candidate_paths.append(repo_path / "scripts" / "publish" / "config.env")

    resolved_config_path: Path | None = None
    for candidate in candidate_paths:
        if candidate.exists():
            resolved_config_path = candidate.resolve()
            break

    config_values = read_env_style_config(resolved_config_path) if resolved_config_path else {}
    base_url = getattr(args, "gitlab_base_url", None) or PUBLISH_CONFIG.get("gitlabBaseUrl") or config_values.get("GITLAB_URL", "")
    project_id = getattr(args, "gitlab_project_id", None) or PUBLISH_CONFIG.get("gitlabProjectId") or config_values.get("GITLAB_PROJECT_ID", "")
    token_source = getattr(args, "gitlab_token", None) or PUBLISH_CONFIG.get("gitlabToken") or config_values.get("GITLAB_TOKEN", "")
    token = resolve_secret(str(token_source))
    if not base_url or not project_id or not token:
        raise RuntimeError("GitLab API 配置不完整。请提供 BaseUrl、ProjectId、Token，或确保脚本可读取 scripts/publish/config.env.local。")

    return GitLabConnection(base_url=base_url.rstrip("/"), project_id=project_id, token=token, config_path=str(resolved_config_path) if resolved_config_path else None)


def tag_version_parts(tag: str) -> list[int]:
    parts = re.findall(r"\d+", tag)
    if not parts:
        raise RuntimeError(f"无法从 tag {tag} 中提取版本号")
    return [int(part) for part in parts]


def compare_tag_version(left: str, right: str) -> int:
    left_parts = tag_version_parts(left)
    right_parts = tag_version_parts(right)
    length = max(len(left_parts), len(right_parts))
    for index in range(length):
        lv = left_parts[index] if index < len(left_parts) else 0
        rv = right_parts[index] if index < len(right_parts) else 0
        if lv > rv:
            return 1
        if lv < rv:
            return -1
    return 0


def gitlab_request(connection: GitLabConnection, method: str, path: str, *, query: dict[str, Any] | None = None, body: Any = None, capture_headers: bool = False) -> Any:
    url = connection.base_url + path
    if query:
        url = f"{url}?{parse.urlencode(query)}"
    headers = {"PRIVATE-TOKEN": connection.token}
    return json_request(method, url, headers=headers, body=body, capture_headers=capture_headers)


def gitlab_release_tag_catalog(connection: GitLabConnection, release_pattern: re.Pattern[str] = DEFAULT_RELEASE_TAG_PATTERN) -> list[dict[str, str]]:
    page = 1
    tags: list[dict[str, str]] = []
    while True:
        body, headers = gitlab_request(
            connection,
            "GET",
            f"/api/v4/projects/{connection.project_id}/repository/tags",
            query={"per_page": 100, "page": page},
            capture_headers=True,
        )
        for item in body or []:
            name = str(item.get("name", ""))
            if not release_pattern.match(name):
                continue
            commit = str(item.get("commit", {}).get("id") or item.get("target") or "")
            tags.append({"name": name, "commit": commit})
        next_page = headers.get("X-Next-Page", "") or headers.get("x-next-page", "")
        if not next_page:
            break
        page = int(next_page)
    if not tags:
        raise RuntimeError("GitLab API 没有返回可用于发布的 v0.0.N tag")
    return tags


def gitlab_latest_release_tag(connection: GitLabConnection, release_pattern: re.Pattern[str] = DEFAULT_RELEASE_TAG_PATTERN) -> dict[str, Any]:
    latest: dict[str, str] | None = None
    catalog = gitlab_release_tag_catalog(connection, release_pattern)
    for tag in catalog:
        if latest is None or compare_tag_version(tag["name"], latest["name"]) > 0:
            latest = tag
    assert latest is not None
    return {"latestTag": latest["name"], "latestTagCommit": latest["commit"], "tagCount": len(catalog)}


def gitlab_create_tag(connection: GitLabConnection, tag_name: str, ref: str, message: str) -> dict[str, str]:
    try:
        response = gitlab_request(
            connection,
            "POST",
            f"/api/v4/projects/{connection.project_id}/repository/tags",
            body={"tag_name": tag_name, "ref": ref, "message": message},
        )
        return {"action": "created", "tag": str(response.get("name", tag_name))}
    except RuntimeError as exc:
        if "already exists" in str(exc):
            return {"action": "exists", "tag": tag_name}
        raise


def gitlab_pipeline_status(connection: GitLabConnection, tag: str) -> dict[str, str] | None:
    response = gitlab_request(
        connection,
        "GET",
        f"/api/v4/projects/{connection.project_id}/pipelines",
        query={"ref": tag, "per_page": 1},
    )
    pipelines = response or []
    if not pipelines:
        return None
    pipeline = pipelines[0]
    status = str(pipeline.get("status", ""))
    normalized = {
        "success": "passed",
        "failed": "failed",
        "canceled": "canceled",
        "skipped": "skipped",
        "running": "running",
        "pending": "running",
        "created": "running",
        "preparing": "running",
        "waiting_for_resource": "running",
    }.get(status, status)
    return {
        "id": str(pipeline.get("id", "")),
        "status": status,
        "webUrl": str(pipeline.get("web_url", "")),
        "updatedAt": str(pipeline.get("updated_at", "")),
        "createdAt": str(pipeline.get("created_at", "")),
        "normalized": normalized,
    }


def wait_gitlab_latest_release_tag_passed(connection: GitLabConnection, timeout_seconds: int, poll_interval_seconds: int) -> dict[str, Any]:
    deadline = utc_now() + timedelta(seconds=timeout_seconds)
    observations: list[dict[str, str]] = []
    while utc_now() < deadline:
        latest = gitlab_latest_release_tag(connection)
        pipeline = gitlab_pipeline_status(connection, latest["latestTag"])
        normalized = pipeline["normalized"] if pipeline else "none"
        observations.append(
            {
                "tag": latest["latestTag"],
                "commit": latest["latestTagCommit"],
                "status": normalized,
                "pipeline": pipeline["id"] if pipeline else "",
            }
        )
        if normalized == "passed":
            return {
                "latestTag": latest["latestTag"],
                "latestTagCommit": latest["latestTagCommit"],
                "pipelineStatus": normalized,
                "pipelineId": pipeline["id"] if pipeline else "",
                "observations": observations,
            }
        if normalized in {"failed", "canceled", "skipped", "none"}:
            raise RuntimeError(f"最新 tag {latest['latestTag']} 的流水线状态为 {normalized}，停止发布")
        time.sleep(poll_interval_seconds)
    raise RuntimeError(f"最新 tag 流水线在 {timeout_seconds} 秒内仍未通过")


def next_tag(tag: str) -> str:
    match = re.match(r"^(.*?)(\d+)$", tag)
    if not match:
        raise RuntimeError(f"无法从最新 tag {tag} 中识别末尾数字")
    prefix, digits = match.groups()
    next_number = str(int(digits) + 1).zfill(len(digits))
    return f"{prefix}{next_number}"


def resolve_publish_plan(args: argparse.Namespace) -> dict[str, Any]:
    repo_path = resolve_repo_path(args.repo_path or PUBLISH_CONFIG.get("repoPath"))
    connection = gitlab_connection_info(repo_path, args)
    source_commit = run_git(repo_path, "rev-parse", "HEAD")
    commit_subject = run_git(repo_path, "log", "-1", "--pretty=%s")
    tag_description = run_git(repo_path, "log", "-1", "--pretty=%B")
    current_branch = run_git(repo_path, "branch", "--show-current")
    remote_url = run_git(repo_path, "remote", "get-url", "origin")
    latest = gitlab_latest_release_tag(connection)
    latest_tag = latest["latestTag"]
    latest_tag_commit = latest["latestTagCommit"]
    next_release_tag = next_tag(latest_tag)
    should_create = latest_tag_commit != source_commit
    effective_tag = next_release_tag if should_create else latest_tag
    tag_action = "create" if should_create else "reuse-latest"
    reason = (
        f"远端最新 tag {latest_tag} 未指向当前提交 {source_commit}，需要创建 {next_release_tag}"
        if should_create
        else f"远端最新 tag {latest_tag} 已指向当前提交 {source_commit}，跳过创建"
    )
    return {
        "repoPath": str(repo_path),
        "scope": args.scope,
        "gitLabConfigPath": connection.config_path,
        "remoteUrl": remote_url,
        "releaseTagPattern": DEFAULT_RELEASE_TAG_PATTERN.pattern,
        "currentBranch": current_branch,
        "latestTag": latest_tag,
        "latestTagCommit": latest_tag_commit,
        "nextTag": next_release_tag,
        "shouldCreateTag": should_create,
        "effectiveTag": effective_tag,
        "tagAction": tag_action,
        "tagDecisionReason": reason,
        "sourceCommit": source_commit,
        "tagDescription": tag_description,
        "lastCommit": {"sha": source_commit, "subject": commit_subject, "message": tag_description},
        "targetApps": DEFAULT_DEFAULT_APPS if args.scope == DEFAULT_SCOPE else [],
        "appSelectionRule": "发布 local config 中的 defaultApps" if args.scope == DEFAULT_SCOPE else "执行阶段从 Argo CD API 按 allAppsNameFilter 筛选全部应用",
        "urls": {
            "gitlabTags": f"{connection.base_url}/-/tags",
            "argocdApplications": f"{DEFAULT_BASE_URL}/applications",
        },
        "_connection": connection,
    }


def credential_metadata_path(session_path: Path) -> Path:
    return session_path.parent / "argocd-credential.json"


def session_path_from_arg(value: str | None) -> Path:
    configured = value or PUBLISH_CONFIG.get("argocdSessionPath")
    if configured:
        path = expand_user_path(str(configured))
        assert path is not None
        return path
    state_dir = publish_state_directory(create_default=True)
    assert state_dir is not None
    return state_dir / "argocd-session.json"


def read_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def keychain_account(base_url: str, username: str) -> str:
    return f"{base_url.rstrip('/')}|{username}"


def keychain_available() -> bool:
    return sys.platform == "darwin" and Path("/usr/bin/security").exists()


def keychain_set_password(base_url: str, username: str, password: str) -> None:
    if not keychain_available():
        return
    account = keychain_account(base_url, username)
    subprocess.run(
        ["security", "add-generic-password", "-U", "-a", account, "-s", KEYCHAIN_SERVICE, "-w", password],
        check=True,
        capture_output=True,
        text=True,
    )


def keychain_get_password(base_url: str, username: str) -> str | None:
    if not keychain_available():
        return None
    account = keychain_account(base_url, username)
    process = subprocess.run(
        ["security", "find-generic-password", "-a", account, "-s", KEYCHAIN_SERVICE, "-w"],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        return None
    return process.stdout.strip()


def read_cached_credential(base_url: str, session_path: Path) -> dict[str, str] | None:
    metadata = read_json_file(credential_metadata_path(session_path))
    if not metadata:
        return None
    if str(metadata.get("baseUrl", "")).rstrip("/") != base_url.rstrip("/"):
        return None
    username = str(metadata.get("username", ""))
    if not username:
        return None
    password = keychain_get_password(base_url, username)
    if not password:
        password = str(metadata.get("password") or "")
    if not password:
        return None
    return {"username": username, "password": password, "authSource": "credential-cache"}


def save_cached_credential(base_url: str, username: str, password: str, session_path: Path) -> None:
    keychain_set_password(base_url, username, password)
    metadata = {
        "baseUrl": base_url.rstrip("/"),
        "username": username,
        "credentialStore": "keychain" if keychain_available() else "local-state",
        "updatedAt": utc_iso(),
    }
    if keychain_available():
        metadata["keychainService"] = KEYCHAIN_SERVICE
        metadata["keychainAccount"] = keychain_account(base_url, username)
    else:
        metadata["password"] = password
    write_json_file(credential_metadata_path(session_path), metadata)


def argocd_request(method: str, base_url: str, path: str, *, headers: dict[str, str] | None = None, body: Any = None) -> Any:
    return json_request(method, base_url.rstrip("/") + path, headers=headers, body=body)


def argocd_auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_argocd_session_token(base_url: str, token: str, project: str | None) -> bool:
    query = f"?project={parse.quote(project)}" if project else ""
    try:
        argocd_request("GET", base_url, f"/api/v1/applications{query}", headers=argocd_auth_headers(token))
        return True
    except RuntimeError:
        return False


def get_argocd_access_token(args: argparse.Namespace) -> dict[str, str]:
    session_path = session_path_from_arg(args.session_path)
    session_state = read_json_file(session_path)
    base_url = args.base_url.rstrip("/")
    if session_state and session_state.get("baseUrl") == base_url and session_state.get("token"):
        token = str(session_state["token"])
        if test_argocd_session_token(base_url, token, args.project):
            return {
                "token": token,
                "authSource": "cache",
                "sessionPath": str(session_path),
                "username": str(session_state.get("username", "")),
            }

    username = args.username or resolve_secret(str(PUBLISH_CONFIG.get("argocdUsername") or PUBLISH_CONFIG.get("argocdUsernameSource") or ""))
    password = args.password or resolve_secret(str(PUBLISH_CONFIG.get("argocdPassword") or PUBLISH_CONFIG.get("argocdPasswordSource") or ""))
    auth_source = "input"
    if not (username and password):
        cached = read_cached_credential(base_url, session_path)
        if cached:
            username = cached["username"]
            password = cached["password"]
            auth_source = cached["authSource"]
    if not (username and password):
        raise RuntimeError(
            f"ArgoCD API 需要有效登录态。当前 token 已失效，且本机未找到可用的已保存账号密码。请提供一次账号密码，后续会把凭据缓存到 {credential_metadata_path(session_path)} 并自动续登。"
        )

    response = argocd_request("POST", base_url, "/api/v1/session", body={"username": username, "password": password})
    token = str(response.get("token", ""))
    if not token:
        raise RuntimeError("ArgoCD 登录成功，但未返回 token")
    write_json_file(
        session_path,
        {"baseUrl": base_url, "token": token, "username": username, "updatedAt": utc_iso()},
    )
    save_cached_credential(base_url, username, password, session_path)
    return {
        "token": token,
        "authSource": "credential-cache-login" if auth_source == "credential-cache" else "login",
        "sessionPath": str(session_path),
        "username": username,
    }


def argocd_application_list(base_url: str, token: str, project: str | None) -> list[dict[str, Any]]:
    query = f"?project={parse.quote(project)}" if project else ""
    response = argocd_request("GET", base_url, f"/api/v1/applications{query}", headers=argocd_auth_headers(token))
    return list(response.get("items", []))


def argocd_application(base_url: str, token: str, name: str, project: str | None) -> dict[str, Any]:
    query = f"?project={parse.quote(project)}" if project else ""
    encoded_name = parse.quote(name, safe="")
    return argocd_request("GET", base_url, f"/api/v1/applications/{encoded_name}{query}", headers=argocd_auth_headers(token))


def argocd_image_tag_state(application: dict[str, Any]) -> dict[str, Any] | None:
    single_source = application.get("spec", {}).get("source")
    parameters = (((single_source or {}).get("helm") or {}).get("parameters")) if single_source else None
    if isinstance(parameters, list):
        for index, parameter in enumerate(parameters):
            if str(parameter.get("name", "")) == "image.tag":
                return {"sourceMode": "single", "sourceIndex": -1, "parameterIndex": index, "currentTag": str(parameter.get("value", ""))}
    multi_sources = application.get("spec", {}).get("sources") or []
    if isinstance(multi_sources, list):
        for source_index, source in enumerate(multi_sources):
            parameters = (((source or {}).get("helm") or {}).get("parameters")) or []
            if not isinstance(parameters, list):
                continue
            for parameter_index, parameter in enumerate(parameters):
                if str(parameter.get("name", "")) == "image.tag":
                    return {
                        "sourceMode": "multi",
                        "sourceIndex": source_index,
                        "parameterIndex": parameter_index,
                        "currentTag": str(parameter.get("value", "")),
                    }
    return None


def updated_argocd_parameters(parameters: list[dict[str, Any]], parameter_index: int, target_tag: str) -> list[dict[str, Any]]:
    cloned = json.loads(json.dumps(parameters))
    cloned[parameter_index]["value"] = target_tag
    return cloned


def set_argocd_image_tag(base_url: str, token: str, application: dict[str, Any], tag_state: dict[str, Any], target_tag: str, project: str | None) -> None:
    spec = application["spec"]
    if tag_state["sourceMode"] == "single":
        updated_source = json.loads(json.dumps(spec["source"]))
        updated_source["helm"]["parameters"] = updated_argocd_parameters(updated_source["helm"]["parameters"], tag_state["parameterIndex"], target_tag)
        updated_spec = {"destination": json.loads(json.dumps(spec["destination"])), "project": spec["project"], "source": updated_source}
    else:
        updated_sources = json.loads(json.dumps(spec["sources"]))
        source_index = tag_state["sourceIndex"]
        updated_sources[source_index]["helm"]["parameters"] = updated_argocd_parameters(
            updated_sources[source_index]["helm"]["parameters"],
            tag_state["parameterIndex"],
            target_tag,
        )
        updated_spec = {"destination": json.loads(json.dumps(spec["destination"])), "project": spec["project"], "sources": updated_sources}

    body = {
        "metadata": {"name": application["metadata"]["name"], "namespace": application["metadata"]["namespace"]},
        "spec": updated_spec,
    }
    encoded_name = parse.quote(application["metadata"]["name"], safe="")
    query = f"?project={parse.quote(project)}" if project else ""
    argocd_request("PUT", base_url, f"/api/v1/applications/{encoded_name}{query}", headers=argocd_auth_headers(token), body=body)


def start_argocd_sync(base_url: str, token: str, name: str, project: str | None) -> None:
    encoded_name = parse.quote(name, safe="")
    query = f"?project={parse.quote(project)}" if project else ""
    argocd_request("POST", base_url, f"/api/v1/applications/{encoded_name}/sync{query}", headers=argocd_auth_headers(token), body={})


def wait_argocd_sync(base_url: str, token: str, name: str, project: str | None, timeout_seconds: int, poll_interval_seconds: int, sync_requested_at_utc: datetime) -> dict[str, Any]:
    deadline = utc_now() + timedelta(seconds=timeout_seconds)
    observed_requested_operation = False
    while True:
        application = argocd_application(base_url, token, name, project)
        status_obj = application.get("status", {}) or {}
        operation_state = status_obj.get("operationState")
        top_level_operation = application.get("operation")
        sync_obj = status_obj.get("sync", {}) or {}
        health_obj = status_obj.get("health", {}) or {}
        history_items = status_obj.get("history") or []
        sync_status = str(sync_obj.get("status", ""))
        health_status = str(health_obj.get("status", ""))
        phase = str((operation_state or {}).get("phase", ""))
        message = str((operation_state or {}).get("message", ""))
        started_at = parse_datetime((operation_state or {}).get("startedAt"))
        finished_at = parse_datetime((operation_state or {}).get("finishedAt"))
        latest_history = history_items[-1] if history_items else None
        history_started_at = parse_datetime((latest_history or {}).get("deployStartedAt"))

        fresh_operation = started_at and started_at >= sync_requested_at_utc - timedelta(seconds=5)
        fresh_finished_operation = finished_at and finished_at >= sync_requested_at_utc - timedelta(seconds=5)
        fresh_history = history_started_at and history_started_at >= sync_requested_at_utc - timedelta(seconds=5)

        if not operation_state and top_level_operation:
            observed_requested_operation = True
            time.sleep(poll_interval_seconds)
            continue

        if fresh_operation or fresh_finished_operation or fresh_history:
            observed_requested_operation = True

        if (observed_requested_operation or fresh_operation or fresh_finished_operation or fresh_history) and phase == "Succeeded" and sync_status == "Synced":
            return {
                "phase": phase,
                "message": message,
                "syncStatus": sync_status,
                "healthStatus": health_status,
                "startedAt": (operation_state or {}).get("startedAt"),
                "finishedAt": (operation_state or {}).get("finishedAt"),
                "historyId": (latest_history or {}).get("id"),
                "deployedAt": (latest_history or {}).get("deployedAt"),
            }

        if (fresh_operation or fresh_finished_operation) and phase in {"Failed", "Error"}:
            raise RuntimeError(f"应用 {name} 同步失败: {message}")

        if utc_now() >= deadline:
            break
        time.sleep(poll_interval_seconds)

    raise RuntimeError(f"应用 {name} 在 {timeout_seconds} 秒内未完成同步")


def argocd_publish(args: argparse.Namespace, target_tag: str) -> dict[str, Any]:
    session = get_argocd_access_token(args)
    token = session["token"]
    if args.apps:
        resolved_apps = sorted({app for app in args.apps if app})
    elif args.scope == DEFAULT_SCOPE:
        resolved_apps = list(DEFAULT_DEFAULT_APPS)
    else:
        name_filter = DEFAULT_ALL_APPS_NAME_FILTER
        resolved_apps = sorted(
            {
                str(item.get("metadata", {}).get("name", ""))
                for item in argocd_application_list(args.base_url, token, args.project)
                if not name_filter or name_filter in str(item.get("metadata", {}).get("name", ""))
            }
        )

    updated_and_synced: list[dict[str, Any]] = []
    no_change: list[dict[str, Any]] = []
    planned_updates: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    stage_deadline = utc_now() + timedelta(seconds=args.sync_timeout_seconds)

    for app_name in resolved_apps:
        try:
            remaining_sync_seconds = max(int((stage_deadline - utc_now()).total_seconds()), 0)
            if not args.what_if and remaining_sync_seconds <= 0:
                failed.append({"appName": app_name, "reason": f"ArgoCD 发布阶段超过 {args.sync_timeout_seconds} 秒，停止继续等待后续应用"})
                continue

            application = argocd_application(args.base_url, token, app_name, args.project)
            tag_state = argocd_image_tag_state(application)
            if not tag_state:
                failed.append({"appName": app_name, "reason": "未找到 PARAMETERS 里的 image.tag"})
                continue
            if tag_state["currentTag"] == target_tag:
                no_change.append(
                    {
                        "appName": app_name,
                        "currentTag": tag_state["currentTag"],
                        "targetTag": target_tag,
                        "sourceMode": tag_state["sourceMode"],
                        "sourceIndex": tag_state["sourceIndex"],
                    }
                )
                continue
            if args.what_if:
                planned_updates.append(
                    {
                        "appName": app_name,
                        "currentTag": tag_state["currentTag"],
                        "targetTag": target_tag,
                        "sourceMode": tag_state["sourceMode"],
                        "sourceIndex": tag_state["sourceIndex"],
                    }
                )
                continue

            sync_requested_at = utc_now()
            poll_interval = min(5, max(1, remaining_sync_seconds))
            set_argocd_image_tag(args.base_url, token, application, tag_state, target_tag, args.project)
            start_argocd_sync(args.base_url, token, app_name, args.project)
            sync_state = wait_argocd_sync(args.base_url, token, app_name, args.project, remaining_sync_seconds, poll_interval, sync_requested_at)
            updated_and_synced.append(
                {
                    "appName": app_name,
                    "previousTag": tag_state["currentTag"],
                    "targetTag": target_tag,
                    "syncStatus": sync_state["syncStatus"],
                    "healthStatus": sync_state["healthStatus"],
                    "phase": sync_state["phase"],
                    "finishedAt": sync_state["finishedAt"],
                }
            )
        except Exception as exc:  # noqa: BLE001
            failed.append({"appName": app_name, "reason": str(exc)})

    return {
        "scope": args.scope,
        "targetTag": target_tag,
        "whatIf": bool(args.what_if),
        "resolvedApps": resolved_apps,
        "auth": {
            "authSource": session["authSource"],
            "sessionPath": session["sessionPath"],
            "username": session.get("username", ""),
        },
        "updatedAndSynced": updated_and_synced,
        "noChange": no_change,
        "plannedUpdates": planned_updates,
        "failed": failed,
    }


def publish_result_to_text(result: dict[str, Any]) -> str:
    updated = ", ".join(item["appName"] for item in result["argocd"]["updatedAndSynced"]) or "(无)"
    unchanged = ", ".join(item["appName"] for item in result["argocd"]["noChange"]) or "(无)"
    failed = "; ".join(f"{item['appName']}: {item['reason']}" for item in result["argocd"]["failed"]) or "(无)"
    return "\n".join(
        [
            f"scope: {result['scope']}",
            f"whatIf: {result['whatIf']}",
            f"plan.latestTag: {result['plan']['latestTag']}",
            f"plan.nextTag: {result['plan']['nextTag']}",
            f"plan.shouldCreateTag: {result['plan']['shouldCreateTag']}",
            f"plan.effectiveTag: {result['plan']['effectiveTag']}",
            f"gitlab.createAction: {result['gitlab']['createAction']}",
            f"gitlab.finalTag: {result['gitlab']['finalTag']}",
            f"gitlab.pipelineStatus: {result['gitlab']['pipelineStatus']}",
            f"gitlab.pipelineId: {result['gitlab']['pipelineId']}",
            f"gitlab.switchReason: {result['gitlab']['switchReason']}",
            f"argocd.updatedAndSynced: {updated}",
            f"argocd.noChange: {unchanged}",
            f"argocd.failed: {failed}",
        ]
    )


def plan_to_text(plan: dict[str, Any]) -> str:
    target_apps = ", ".join(plan["targetApps"]) if plan["targetApps"] else "(由 ArgoCD 动态筛选)"
    return "\n".join(
        [
            f"repoPath: {plan['repoPath']}",
            f"scope: {plan['scope']}",
            f"currentBranch: {plan['currentBranch']}",
            f"releaseTagPattern: {plan['releaseTagPattern']}",
            f"latestTag: {plan['latestTag']}",
            f"latestTagCommit: {plan['latestTagCommit']}",
            f"nextTag: {plan['nextTag']}",
            f"shouldCreateTag: {plan['shouldCreateTag']}",
            f"effectiveTag: {plan['effectiveTag']}",
            f"tagAction: {plan['tagAction']}",
            f"tagDecisionReason: {plan['tagDecisionReason']}",
            f"sourceCommit: {plan['sourceCommit']}",
            f"tagDescription: {plan['tagDescription']}",
            f"targetApps: {target_apps}",
            f"appSelectionRule: {plan['appSelectionRule']}",
            f"gitlabTags: {plan['urls']['gitlabTags']}",
            f"argocdApplications: {plan['urls']['argocdApplications']}",
        ]
    )


def execute_publish(args: argparse.Namespace) -> dict[str, Any]:
    resolve_args = argparse.Namespace(**vars(args))
    plan = resolve_publish_plan(resolve_args)
    connection: GitLabConnection = plan.pop("_connection")
    state_dir = publish_state_directory(create_default=True)
    assert state_dir is not None
    lock_path = state_dir / "publish-dev.lock.json"
    result_path = state_dir / "publish-dev.last-result.json"
    lock_token = os.urandom(8).hex()

    if not args.what_if:
        while True:
            if lock_path.exists():
                existing_lock = read_json_file(lock_path)
                if existing_lock and existing_lock.get("processId"):
                    try:
                        os.kill(int(existing_lock["processId"]), 0)
                        timeout_seconds = max(args.gitlab_wait_timeout_seconds, args.sync_timeout_seconds) + 60
                        deadline = time.time() + timeout_seconds
                        while time.time() < deadline:
                            try:
                                os.kill(int(existing_lock["processId"]), 0)
                                time.sleep(5)
                            except OSError:
                                break
                        if result_path.exists():
                            existing_result = read_json_file(result_path)
                            if existing_result:
                                return existing_result
                        raise RuntimeError(f"检测到已有发布进程 {existing_lock['processId']} 已完成，但没有产出结果文件，停止重复发布")
                    except OSError:
                        lock_path.unlink(missing_ok=True)
                        continue
                lock_path.unlink(missing_ok=True)
                continue

            result_path.unlink(missing_ok=True)
            write_json_file(
                lock_path,
                {"token": lock_token, "processId": os.getpid(), "repoPath": plan["repoPath"], "scope": args.scope, "startedAt": utc_iso()},
            )
            stored = read_json_file(lock_path)
            if stored and stored.get("token") == lock_token:
                break
            time.sleep(1)

    try:
        if args.what_if:
            create_action = "planned" if plan["shouldCreateTag"] else "skipped"
            wait_result = {
                "latestTag": plan["effectiveTag"],
                "latestTagCommit": plan["sourceCommit"] if plan["shouldCreateTag"] else plan["latestTagCommit"],
                "pipelineStatus": "not-started" if plan["shouldCreateTag"] else "passed",
                "pipelineId": "",
            }
            final_tag = wait_result["latestTag"]
            switch_reason = ""
        else:
            create_action = gitlab_create_tag(connection, plan["nextTag"], plan["sourceCommit"], plan["tagDescription"])["action"] if plan["shouldCreateTag"] else "skipped"
            wait_result = wait_gitlab_latest_release_tag_passed(connection, args.gitlab_wait_timeout_seconds, args.gitlab_poll_interval_seconds)
            final_tag = wait_result["latestTag"]
            switch_reason = f"GitLab 等待期间检测到更新的最新 tag，发布目标自动切换为 {final_tag}" if final_tag != plan["effectiveTag"] else ""

        argocd_result = argocd_publish(args, final_tag)
        result = {
            "scope": args.scope,
            "whatIf": bool(args.what_if),
            "plan": {
                key: plan[key]
                for key in [
                    "latestTag",
                    "latestTagCommit",
                    "nextTag",
                    "shouldCreateTag",
                    "effectiveTag",
                    "sourceCommit",
                    "tagDescription",
                ]
            },
            "gitlab": {
                "configPath": connection.config_path,
                "createAction": create_action,
                "finalTag": final_tag,
                "finalTagCommit": wait_result["latestTagCommit"],
                "pipelineStatus": wait_result["pipelineStatus"],
                "pipelineId": wait_result["pipelineId"],
                "switchReason": switch_reason,
            },
            "argocd": argocd_result,
        }
        if not args.what_if:
            write_json_file(result_path, result)
        return result
    finally:
        if not args.what_if:
            current_lock = read_json_file(lock_path)
            if current_lock and current_lock.get("token") == lock_token:
                lock_path.unlink(missing_ok=True)


def doctor() -> dict[str, Any]:
    state_dir = publish_state_directory(create_default=False)
    repo_candidates: list[str] = []
    repo_directory_name = str(PUBLISH_CONFIG.get("repoDirectoryName") or "").strip()
    for root in repo_search_roots():
        candidate = root / repo_directory_name if repo_directory_name else root
        repo_candidates.append(to_home_relative(candidate))
    return {
        "python": sys.executable,
        "pythonVersion": sys.version.split()[0],
        "configPath": str(PUBLISH_CONFIG.get("_configPath") or ""),
        "stateDirectory": str(state_dir) if state_dir else "",
        "defaultRepoCandidates": repo_candidates[:10],
        "credentialStore": "keychain" if keychain_available() else "local-state",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="publish_dev.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-RepoPath", "--repo-path")
    common.add_argument("-GitLabConfigPath", "--gitlab-config-path")
    common.add_argument("-GitLabBaseUrl", "--gitlab-base-url")
    common.add_argument("-GitLabProjectId", "--gitlab-project-id")
    common.add_argument("-GitLabToken", "--gitlab-token")
    common.add_argument("-Scope", "--scope", choices=["default", "all"], default=DEFAULT_SCOPE)
    common.add_argument("-Format", "--format", choices=["json", "text"], default="json")

    resolve_parser = subparsers.add_parser("resolve-plan", parents=[common])
    resolve_parser.set_defaults(handler=handle_resolve_plan)

    publish_parser = subparsers.add_parser("publish", parents=[common])
    publish_parser.add_argument("-BaseUrl", "--base-url", default=DEFAULT_BASE_URL)
    publish_parser.add_argument("-Project", "--project", default=DEFAULT_PROJECT)
    publish_parser.add_argument("-Apps", "--apps", nargs="*")
    publish_parser.add_argument("-SessionPath", "--session-path")
    publish_parser.add_argument("-Username", "--username")
    publish_parser.add_argument("-Password", "--password")
    publish_parser.add_argument("-GitLabWaitTimeoutSeconds", "--gitlab-wait-timeout-seconds", type=int, default=300)
    publish_parser.add_argument("-GitLabPollIntervalSeconds", "--gitlab-poll-interval-seconds", type=int, default=15)
    publish_parser.add_argument("-SyncTimeoutSeconds", "--sync-timeout-seconds", type=int, default=300)
    publish_parser.add_argument("-WhatIf", "--what-if", action="store_true")
    publish_parser.set_defaults(handler=handle_publish)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.set_defaults(handler=handle_doctor)
    return parser


def handle_resolve_plan(args: argparse.Namespace) -> int:
    plan = resolve_publish_plan(args)
    plan.pop("_connection", None)
    if args.format == "text":
        print(plan_to_text(plan))
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


def handle_publish(args: argparse.Namespace) -> int:
    result = execute_publish(args)
    if args.format == "text":
        print(publish_result_to_text(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def handle_doctor(args: argparse.Namespace) -> int:
    print(json.dumps(doctor(), ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
