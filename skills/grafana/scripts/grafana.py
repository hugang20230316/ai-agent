#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
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


def config_path(value: Any, default: str) -> Path:
    return Path(str(value or default)).expanduser()


CONFIG = load_skill_config("grafana")
BASE_URL = str(CONFIG.get("baseUrl") or "https://grafana.example.com").rstrip("/")
DASHBOARD_UID = str(CONFIG.get("dashboardUid") or "replace-with-dashboard-uid")
DASHBOARD_SLUG = str(CONFIG.get("dashboardSlug") or "logs")
API_APP = str(CONFIG.get("apiApp") or "app-api")
BACKGROUND_APP = str(CONFIG.get("backgroundApp") or "app-backgroundtasks")
SERVICES_APP = str(CONFIG.get("servicesApp") or "app-services")
SAVE_WORK_ROUTE_PATTERN = str(CONFIG.get("saveWorkRoutePattern") or "")
STATE_DIR = config_path(CONFIG.get("localStateDir"), "~/.grafana-skill")
CACHE_DIR = STATE_DIR / "cache"
LOGIN_METADATA_PATH = STATE_DIR / "login.json"
AGENT_BROWSER_KEY_PATH = STATE_DIR / "agent-browser.key"
LOGIN_KEY_PATH = STATE_DIR / "login.key"
BROWSER_POLICY_PATH = Path(__file__).resolve().parent.parent / "assets" / "browser-policy.json"
LOGIN_KEYCHAIN_SERVICE = "codex.grafana.login"


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def add_no_proxy_host(env: dict[str, str], host: str) -> None:
    if not host:
        return
    for key in ("NO_PROXY", "no_proxy"):
        values = [item.strip() for item in env.get(key, "").split(",") if item.strip()]
        if not any(item == "*" or item == host or host.endswith(f".{item.lstrip('.')}") for item in values):
            values.append(host)
        env[key] = ",".join(values)
    env["AGENT_BROWSER_PROXY_BYPASS"] = env["NO_PROXY"]


def grafana_no_proxy_opener() -> request.OpenerDirector:
    parsed = parse.urlparse(BASE_URL)
    proxies = request.getproxies()
    if parsed.hostname:
        for scheme in ("http", "https", "all"):
            proxies.pop(scheme, None)
    return request.build_opener(request.ProxyHandler(proxies))


def json_request(method: str, url: str, *, headers: dict[str, str] | None = None, body: Any = None) -> Any:
    payload = None
    request_headers = dict(headers or {})
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    req = request.Request(url, data=payload, method=method.upper(), headers=request_headers)
    try:
        with grafana_no_proxy_opener().open(req, timeout=30) as response:
            raw = response.read()
            content = raw.decode("utf-8") if raw else ""
            return json.loads(content) if content else None
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(raw.strip() or exc.reason) from exc
    except error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def parse_time(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def key_path(name: str) -> Path:
    ensure_directory(STATE_DIR)
    return STATE_DIR / f"{name}.key"


def get_key_hex(name: str) -> str:
    path = key_path(name)
    if not path.exists():
        path.write_text(os.urandom(32).hex(), encoding="ascii")
    return path.read_text(encoding="ascii").strip()


def load_browser_policy() -> dict[str, Any]:
    policy = json.loads(BROWSER_POLICY_PATH.read_text(encoding="utf-8"))
    parsed = parse.urlparse(BASE_URL)
    policy["host"] = str(CONFIG.get("browserHost") or parsed.hostname or policy.get("host") or "")
    policy["sessionName"] = str(CONFIG.get("browserSession") or policy.get("sessionName") or "grafana-local")
    policy["maxOutput"] = int(CONFIG.get("browserMaxOutput") or policy.get("maxOutput") or 12000)
    policy.setdefault("allowedCommands", ["open", "back", "forward", "reload", "snapshot", "get", "find", "click", "fill", "type", "press", "scroll", "wait", "close", "cookies"])
    policy.setdefault("allowedOpenPathPrefixes", ["/", "/login", "/d", "/d-solo", "/dashboards", "/explore", "/goto"])
    return policy


def keychain_available() -> bool:
    return sys.platform == "darwin" and Path("/usr/bin/security").exists()


def keychain_set_password(username: str, password: str) -> None:
    if not keychain_available():
        return
    subprocess.run(
        ["security", "add-generic-password", "-U", "-a", username, "-s", LOGIN_KEYCHAIN_SERVICE, "-w", password],
        check=True,
        capture_output=True,
        text=True,
    )


def keychain_get_password(username: str) -> str | None:
    if not keychain_available():
        return None
    process = subprocess.run(
        ["security", "find-generic-password", "-a", username, "-s", LOGIN_KEYCHAIN_SERVICE, "-w"],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        return None
    return process.stdout.strip()


def save_login(username: str, password: str) -> dict[str, str]:
    ensure_directory(STATE_DIR)
    ensure_directory(CACHE_DIR)
    keychain_set_password(username, password)
    metadata = {"username": username, "savedAt": utc_iso(), "credentialStore": "keychain" if keychain_available() else "local-state"}
    if not keychain_available():
        metadata["password"] = password
    LOGIN_METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    agent_key = get_key_hex("agent-browser")
    login_key = get_key_hex("login")
    return {
        "credentialPath": str(LOGIN_METADATA_PATH),
        "credentialKeyPath": str(key_path("login")),
        "browserKeyPath": str(key_path("agent-browser")),
        "agentBrowserKeyLength": str(len(agent_key)),
        "loginKeyLength": str(len(login_key)),
    }


def get_login() -> tuple[str, str]:
    metadata = json.loads(LOGIN_METADATA_PATH.read_text(encoding="utf-8")) if LOGIN_METADATA_PATH.exists() else {}
    username = str(metadata.get("username") or CONFIG.get("username") or "").strip()
    if not username:
        raise RuntimeError("Grafana username is missing. Run save-login or configure grafana.local.json.")
    password = resolve_secret(str(CONFIG.get("passwordSource") or "")) or str(CONFIG.get("password") or "") or keychain_get_password(username) or str(metadata.get("password") or "")
    if not password:
        raise RuntimeError("Grafana password is missing. Run save-login or configure grafana.local.json.")
    return username, password


def find_agent_browser() -> str:
    names = ["agent-browser"]
    if os.name == "nt":
        names = ["agent-browser.cmd", "agent-browser.exe", "agent-browser.ps1", "agent-browser"]
    for name in names:
        path = shutil_which(name)
        if path:
            return path
    path = shutil_which("agent-browser")
    if not path:
        raise RuntimeError("agent-browser was not found. Install it first.")
    return path


def shutil_which(command: str) -> str | None:
    for directory in os.getenv("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def validate_open_url(policy: dict[str, Any], url: str) -> None:
    parsed = parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError("open requires an absolute URL.")
    if parsed.hostname != policy["host"]:
        raise RuntimeError(f"Only {policy['host']} is allowed.")
    path = parsed.path or "/"
    for prefix in policy["allowedOpenPathPrefixes"]:
        if prefix == "/" and path == "/":
            return
        if prefix != "/" and (path == prefix or path.startswith(prefix + "/")):
            return
    raise RuntimeError("The URL is outside the read-only allowlist.")


def run_agent_browser(args: list[str], *, headed: bool = False) -> str:
    policy = load_browser_policy()
    if not args:
        raise RuntimeError("Pass an agent-browser subcommand.")
    command = args[0].lower()
    if command not in policy["allowedCommands"]:
        raise RuntimeError(f"grafana-browser only allows: {', '.join(policy['allowedCommands'])}")
    if command == "open":
        if len(args) < 2:
            raise RuntimeError("open requires a URL.")
        validate_open_url(policy, args[1])

    agent_browser = find_agent_browser()
    env = os.environ.copy()
    env["AGENT_BROWSER_ENCRYPTION_KEY"] = get_key_hex("agent-browser")
    add_no_proxy_host(env, str(policy["host"]))
    base_args = [
        agent_browser,
        "--session-name",
        str(policy["sessionName"]),
        "--allowed-domains",
        str(policy["host"]),
        "--max-output",
        str(policy["maxOutput"]),
        "--proxy-bypass",
        env["AGENT_BROWSER_PROXY_BYPASS"],
    ]
    if headed:
        base_args.append("--headed")

    process = subprocess.run(base_args + args, check=False, capture_output=True, text=True, env=env)
    if process.returncode != 0:
        raise RuntimeError((process.stderr or process.stdout or f"agent-browser failed with exit code {process.returncode}").strip())
    return process.stdout.strip()


def try_agent_browser(args: list[str], *, headed: bool = False) -> bool:
    try:
        run_agent_browser(args, headed=headed)
        return True
    except Exception:  # noqa: BLE001
        return False


def ensure_session(*, headed: bool = False) -> str:
    run_agent_browser(["open", f"{BASE_URL}/"], headed=headed)
    run_agent_browser(["wait", "1500"], headed=headed)
    current_url = run_agent_browser(["get", "url"], headed=headed).strip()
    if "/login" not in current_url:
        return "Grafana session is ready."

    username, password = get_login()
    user_selectors = ["input[name=\"user\"]", "input[id=\"user\"]", "input[name=\"email\"]"]
    password_selectors = ["input[name=\"password\"]", "input[id=\"password\"]"]
    submit_selectors = ["button[type=\"submit\"]", "button[aria-label=\"Login button\"]"]

    if not any(try_agent_browser(["fill", selector, username], headed=headed) for selector in user_selectors):
        raise RuntimeError("Could not find the Grafana username input.")
    if not any(try_agent_browser(["fill", selector, password], headed=headed) for selector in password_selectors):
        raise RuntimeError("Could not find the Grafana password input.")
    submitted = any(try_agent_browser(["click", selector], headed=headed) for selector in submit_selectors)
    if not submitted:
        submitted = try_agent_browser(["find", "role", "button", "click", "--name", "Log in"], headed=headed) or try_agent_browser(
            ["find", "role", "button", "click", "--name", "Sign in"], headed=headed
        )
    if not submitted:
        raise RuntimeError("Could not find the Grafana login button.")

    run_agent_browser(["wait", "2500"], headed=headed)
    current_url = run_agent_browser(["get", "url"], headed=headed).strip()
    if "/login" in current_url:
        raise RuntimeError("Grafana stayed on the login page after submit. Check the credential or login flow.")
    return "Grafana session has been refreshed."


def grafana_cookie_from_agent_browser() -> str | None:
    output = run_agent_browser(["cookies", "get", "--json"])
    payload = json.loads(output)
    cookies = payload.get("data", {}).get("cookies", [])
    for cookie in cookies:
        if cookie.get("name") == "grafana_session":
            return str(cookie.get("value", ""))
    return None


def test_grafana_session_cookie(cookie: str) -> bool:
    try:
        req = request.Request(f"{BASE_URL}/api/dashboards/uid/{DASHBOARD_UID}", headers={"Cookie": f"grafana_session={cookie}"})
        with grafana_no_proxy_opener().open(req, timeout=15) as response:
            return response.status == 200
    except Exception:  # noqa: BLE001
        return False


def get_grafana_session_cookie() -> str:
    try:
        cookie = grafana_cookie_from_agent_browser()
    except Exception:  # noqa: BLE001
        cookie = None
    if cookie and test_grafana_session_cookie(cookie):
        return cookie
    ensure_session()
    cookie = grafana_cookie_from_agent_browser()
    if not cookie:
        raise RuntimeError("Could not read grafana_session cookie from agent-browser.")
    return cookie


def grafana_headers() -> dict[str, str]:
    cookie = get_grafana_session_cookie()
    return {"Cookie": f"grafana_session={cookie}", "Content-Type": "application/json"}


def resolve_time_value(value: str, now: datetime) -> int:
    if re.fullmatch(r"\d+", value):
        return int(value)
    if value == "now":
        return int(now.timestamp() * 1000)
    match = re.fullmatch(r"now([+-])(\d+)([smhdw])", value)
    if match:
        op, amount_text, unit = match.groups()
        amount = int(amount_text)
        delta = {
            "s": timedelta(seconds=amount),
            "m": timedelta(minutes=amount),
            "h": timedelta(hours=amount),
            "d": timedelta(days=amount),
            "w": timedelta(days=amount * 7),
        }[unit]
        target = now - delta if op == "-" else now + delta
        return int(target.timestamp() * 1000)
    return int(parse_time(value).timestamp() * 1000)


def resolve_time_range(from_value: str, to_value: str) -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    return resolve_time_value(from_value, now), resolve_time_value(to_value, now)


def dashboard_definition(refresh: bool = False) -> dict[str, Any]:
    ensure_directory(CACHE_DIR)
    cache_path = CACHE_DIR / f"{DASHBOARD_UID}-dashboard.json"
    if not refresh and cache_path.exists() and datetime.fromtimestamp(cache_path.stat().st_mtime, timezone.utc) > utc_now() - timedelta(minutes=30):
        return json.loads(cache_path.read_text(encoding="utf-8"))
    dashboard = json_request("GET", f"{BASE_URL}/api/dashboards/uid/{DASHBOARD_UID}", headers=grafana_headers())
    cache_path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    return dashboard


def teacher_ai_logs_target(dashboard: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    for panel in dashboard.get("dashboard", {}).get("panels", []):
        if panel.get("type") == "logs":
            targets = panel.get("targets", [])
            if targets:
                return panel, targets[0]
            break
    raise RuntimeError("Could not find a logs panel in the configured dashboard.")


def expand_expr(template: str, namespace: str, app: str, query_text: str) -> str:
    if not query_text.strip():
        return f"namespace: {namespace} AND app: {app}"
    return (
        template.replace("${namespace}", namespace)
        .replace("${app}", app)
        .replace("${query}", query_text)
        .replace("$namespace", namespace)
        .replace("$app", app)
        .replace("$query", query_text)
    )


def convert_frames(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for frame in frames:
        values = ((frame.get("data") or {}).get("values")) or []
        if len(values) < 2:
            continue
        times = values[0]
        lines = values[1]
        labels = values[2] if len(values) >= 3 else []
        for index, time_ms in enumerate(times):
            dt = datetime.fromtimestamp(int(time_ms) / 1000, timezone.utc).astimezone()
            results.append(
                {
                    "TimeMs": int(time_ms),
                    "Time": dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "Line": str(lines[index]) if index < len(lines) else "",
                    "Labels": labels[index] if index < len(labels) else None,
                }
            )
    return sorted(results, key=lambda item: item["TimeMs"])


def get_dashboard_body_text(dashboard_url: str) -> str:
    run_agent_browser(["open", dashboard_url])
    run_agent_browser(["wait", "2500"])
    text = run_agent_browser(["get", "text", "body"])
    if ".preloader" in text or "Panel Title" not in text:
        run_agent_browser(["wait", "2500"])
        text = run_agent_browser(["get", "text", "body"])
    return text


def invoke_logs_query(app: str, query: str = "", namespace: str = "prd", from_value: str = "now-2d", to_value: str = "now", limit: int = 200, refresh_dashboard: bool = False) -> dict[str, Any]:
    dashboard = dashboard_definition(refresh_dashboard)
    panel, target = teacher_ai_logs_target(dashboard)
    from_ms, to_ms = resolve_time_range(from_value, to_value)
    expr = expand_expr(str(target.get("expr", "")), namespace, app, query)
    ref_id = str(target.get("refId") or "A")
    query_type = str(target.get("queryType") or "instant")
    editor_mode = str(target.get("editorMode") or "code")
    datasource = target.get("datasource") or {}
    datasource_uid = str(datasource.get("uid", ""))
    datasource_type = str(datasource.get("type", ""))
    body = {
        "from": str(from_ms),
        "to": str(to_ms),
        "queries": [
            {
                "refId": ref_id,
                "datasource": {"uid": datasource_uid, "type": datasource_type},
                "editorMode": editor_mode,
                "expr": expr,
                "queryType": query_type,
                "maxLines": limit,
            }
        ],
    }
    query_uri = f"{BASE_URL}/api/ds/query?ds_type={datasource_type}&requestId=Q100"
    response = json_request("POST", query_uri, headers=grafana_headers(), body=body)
    frames: list[dict[str, Any]] = []
    for result_item in (response.get("results") or {}).values():
        frames.extend(result_item.get("frames") or [])
    dashboard_query = parse.quote(query)
    dashboard_url = f"{BASE_URL}/d/{DASHBOARD_UID}/{DASHBOARD_SLUG}?orgId=1&from={from_value}&to={to_value}&var-namespace={namespace}&var-app={app}&var-query={dashboard_query}"
    logs = convert_frames(frames)
    mode = "api"
    raw_text = None
    if not logs:
        raw_text = get_dashboard_body_text(dashboard_url)
        if query and query in raw_text:
            mode = "browser-fallback"
    return {
        "Mode": mode,
        "DashboardTitle": dashboard.get("dashboard", {}).get("title"),
        "DashboardUrl": dashboard_url,
        "PanelId": panel.get("id"),
        "PanelTitle": panel.get("title"),
        "DatasourceUid": datasource_uid,
        "DatasourceType": datasource_type,
        "QueryExpr": expr,
        "ApiUri": query_uri,
        "ResultCount": len(logs) if logs else (1 if query and raw_text and query in raw_text else 0),
        "Logs": logs,
        "RawText": raw_text,
    }


def convert_to_time_info(value: str | None) -> dict[str, Any]:
    if not value:
        return {"TimeMs": 0, "Time": ""}
    for fmt in ("%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            parsed = datetime.strptime(value, fmt)
            parsed = parsed.astimezone()
            return {"TimeMs": int(parsed.timestamp() * 1000), "Time": parsed.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}
        except ValueError:
            pass
    parsed = parse_time(value).astimezone()
    return {"TimeMs": int(parsed.timestamp() * 1000), "Time": parsed.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}


def to_grafana_time_string(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def workguid_seed_time(value: str) -> datetime | None:
    match = re.match(r"^(?P<date>\d{8})-(?P<time>\d{4})-", value)
    if not match:
        return None
    combined = f"{match.group('date')}{match.group('time')}+08:00"
    return datetime.strptime(combined, "%Y%m%d%H%M%z")


def meaningful_events(logs: list[dict[str, Any]], source: str, query_context: dict[str, Any], workguid: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    escaped = re.escape(workguid)
    for log in logs:
        line = str(log.get("Line", ""))
        if not line.strip() or re.match(r"^\s*\[Name\]:@", line):
            continue
        summary = None
        kind = None
        retry_index = None
        retry_match = re.search(r"准备第(\d+)次重试,延迟(\d+)毫秒", line)
        if source == API_APP and (not SAVE_WORK_ROUTE_PATTERN or SAVE_WORK_ROUTE_PATTERN in line) and re.search(escaped, line):
            kind = "save-work"
            summary = "保存作业成功"
        elif "消费者:TypesettingQueueMsgConsumer" in line and re.search(r'"status"\s*:\s*200', line) and re.search(escaped, line):
            kind = "typesetting-success"
            summary = "排版服务返回成功，PDF 已生成"
        elif "TypesettingQueueMsgHandler PDFium PDF转图片耗时" in line and re.search(escaped, line):
            kind = "pdf-to-image"
            summary = "PDF 转图片成功"
        elif "消费者:HomeworkMsgConsumer 内容:收到消息" in line and '"type":"workinfo_layout_completed"' in line and re.search(escaped, line):
            kind = "layout-completed"
            summary = "收到排版完成消息"
        elif retry_match and "OCR API" in line and re.search(escaped, line):
            kind = "ocr-retry"
            retry_index = int(retry_match.group(1))
            summary = f"OCR 调用失败，准备第{retry_match.group(1)}次重试，延迟{retry_match.group(2)}毫秒"
        elif "进入死信队列" in line and "重试次数超过限制" in line and re.search(escaped, line):
            kind = "dead-letter"
            summary = "OCR 连续失败，消息进入死信队列"
        elif "记录 info.json 失败状态" in line and re.search(escaped, line):
            kind = "final-failure"
            summary = "最终失败状态已回写到 info.json"
        elif ("RecognizeAsync" in line or "22222" in line) and re.search(escaped, line):
            kind = "ocr-start"
            summary = "开始 OCR 识别转出的图片"
        elif "EsWorkInfoSyncConsumer" in line and re.search(escaped, line):
            kind = "es-sync"
            summary = "ES 同步消费者收到作业消息"
        if not summary:
            continue
        key = f"{log['TimeMs']}|{kind}|{summary}|{retry_index}"
        if key in seen:
            continue
        seen.add(key)
        events.append(
            {
                "TimeMs": log["TimeMs"],
                "Time": log["Time"],
                "Source": source,
                "Kind": kind,
                "Summary": summary,
                "RetryIndex": retry_index,
                "Line": line.strip(),
                "QueryNode": query_context.get("Node"),
                "QueryApp": query_context.get("App"),
                "QueryExpr": query_context.get("QueryExpr"),
                "QueryFrom": query_context.get("From"),
                "QueryTo": query_context.get("To"),
                "DashboardUrl": query_context.get("DashboardUrl"),
            }
        )
    return sorted(events, key=lambda item: item["TimeMs"])


def event_query_priority(node: str | None) -> int:
    if not node:
        return 100
    if "primary-cycle-workGuid" in node:
        return 10
    if "primary-cycle-messageId" in node:
        return 20
    if "api/create-window" in node:
        return 30
    if "message-window" in node:
        return 40
    if "backgroundtasks/workGuid/window-" in node:
        return 50
    return 100


def merge_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(events, key=lambda item: (event_query_priority(item.get("QueryNode")), item["TimeMs"], item["Kind"]))
    merged: dict[str, dict[str, Any]] = {}
    for event in ordered:
        key = f"{event['TimeMs']}|{event['Kind']}|{event['Summary']}|{event['Line']}"
        merged.setdefault(key, event)
    return sorted(merged.values(), key=lambda item: (item["TimeMs"], item["Kind"]))


def select_first_event(events: list[dict[str, Any]], kind: str, after_time_ms: int = -1, retry_index: int = -1) -> dict[str, Any] | None:
    matches = [event for event in events if event["Kind"] == kind and event["TimeMs"] >= after_time_ms and (retry_index < 0 or event.get("RetryIndex") == retry_index)]
    matches.sort(key=lambda item: item["TimeMs"])
    return matches[0] if matches else None


def canonical_timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_event(event: dict[str, Any] | None) -> None:
        if not event:
            return
        key = f"{event['TimeMs']}|{event['Kind']}|{event['Summary']}"
        if key not in seen:
            seen.add(key)
            timeline.append(event)

    save_work = select_first_event(events, "save-work")
    add_event(save_work)
    typesetting_success = select_first_event(events, "typesetting-success")
    add_event(typesetting_success)
    pdf_search_start = typesetting_success["TimeMs"] if typesetting_success else -1
    pdf_to_image = select_first_event(events, "pdf-to-image", pdf_search_start)
    add_event(pdf_to_image)
    layout_search_start = pdf_to_image["TimeMs"] if pdf_to_image else (typesetting_success["TimeMs"] if typesetting_success else -1)
    layout_completed = select_first_event(events, "layout-completed", layout_search_start)
    add_event(layout_completed)
    chain_start = layout_completed["TimeMs"] if layout_completed else (pdf_to_image["TimeMs"] if pdf_to_image else (typesetting_success["TimeMs"] if typesetting_success else -1))
    add_event(select_first_event(events, "ocr-start", chain_start))
    for retry_index in range(1, 4):
        add_event(select_first_event(events, "ocr-retry", chain_start, retry_index))
    add_event(select_first_event(events, "dead-letter", chain_start))
    add_event(select_first_event(events, "final-failure", chain_start))
    return sorted(timeline, key=lambda item: item["TimeMs"]) if timeline else sorted(events, key=lambda item: item["TimeMs"])


def repeated_attempts(events: list[dict[str, Any]], primary_timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    terminal_events = [event for event in primary_timeline if event["Kind"] in {"final-failure", "dead-letter"}]
    terminal_events.sort(key=lambda item: item["TimeMs"], reverse=True)
    if not terminal_events:
        return []
    terminal_event = terminal_events[0]
    remaining = sorted([event for event in events if event["TimeMs"] > terminal_event["TimeMs"] + 60000], key=lambda item: item["TimeMs"])
    if not remaining:
        return []

    attempts: list[dict[str, Any]] = []
    cursor_time_ms = terminal_event["TimeMs"] + 60000
    while True:
        start_candidates = [event for event in remaining if event["Kind"] == "layout-completed" and event["TimeMs"] >= cursor_time_ms]
        start_candidates.sort(key=lambda item: item["TimeMs"])
        if not start_candidates:
            break
        start_event = start_candidates[0]
        candidate_events = [event for event in remaining if event["TimeMs"] >= start_event["TimeMs"]]
        cycle_terminals = [event for event in candidate_events if event["Kind"] in {"final-failure", "dead-letter"}]
        cycle_terminals.sort(key=lambda item: item["TimeMs"])
        cycle_terminal = cycle_terminals[0] if cycle_terminals else None
        cycle_events = [event for event in candidate_events if not cycle_terminal or event["TimeMs"] <= cycle_terminal["TimeMs"]]
        if not cycle_events:
            break
        cycle_dead_letter = select_first_event(cycle_events, "dead-letter", start_event["TimeMs"])
        cycle_final_failure = select_first_event(cycle_events, "final-failure", start_event["TimeMs"])
        cycle_ocr_start = select_first_event(cycle_events, "ocr-start", start_event["TimeMs"])
        retry_numbers = sorted({event["RetryIndex"] for event in cycle_events if event["Kind"] == "ocr-retry" and event.get("RetryIndex") is not None})
        retry_text = "/".join(str(number) for number in retry_numbers) if retry_numbers else "无"
        if cycle_final_failure:
            summary = f"同一 messageId 在 {start_event['Time']} 再次被消费，OCR 重试序列为 {retry_text}，并在 {cycle_final_failure['Time']} 再次回写最终失败。"
        elif cycle_dead_letter:
            summary = f"同一 messageId 在 {start_event['Time']} 再次被消费，OCR 重试序列为 {retry_text}，并在 {cycle_dead_letter['Time']} 再次进入死信队列。"
        elif cycle_ocr_start:
            summary = f"同一 messageId 在 {start_event['Time']} 再次被消费，并在 {cycle_ocr_start['Time']} 再次发起 OCR；当前查询窗口内未看到终态。"
        else:
            summary = f"同一 messageId 在 {start_event['Time']} 再次被消费，但当前查询窗口内没有足够证据还原完整终态。"
        attempts.append(
            {
                "StartTime": start_event["Time"],
                "Summary": summary,
                "RawEventCount": len(cycle_events),
                "Timeline": canonical_timeline(cycle_events),
                "ObservedKinds": sorted({event["Kind"] for event in cycle_events}),
            }
        )
        cursor_time_ms = cycle_terminal["TimeMs"] + 60000 if cycle_terminal else 2**63 - 1
    return attempts


def query_refs_for_kinds(events: list[dict[str, Any]], kinds: list[str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in sorted([event for event in events if event["Kind"] in kinds], key=lambda item: item["TimeMs"]):
        if not event.get("QueryNode"):
            continue
        key = f"{event['QueryNode']}|{event['QueryExpr']}|{event['QueryFrom']}|{event['QueryTo']}"
        if key in seen:
            continue
        seen.add(key)
        refs.append(
            {
                "Node": event["QueryNode"],
                "App": event["QueryApp"],
                "From": event["QueryFrom"],
                "To": event["QueryTo"],
                "QueryExpr": event["QueryExpr"],
                "DashboardUrl": event["DashboardUrl"],
            }
        )
    return refs


def evidence_gaps(has_api_save: bool, has_typesetting_success: bool, has_pdf_to_image: bool, has_layout_completed: bool, has_ocr_failure: bool, repeated: list[dict[str, Any]]) -> list[str]:
    gaps: list[str] = []
    if not has_api_save:
        gaps.append("当前 Grafana 没有提供入口 API 创建节点证据，入口只能按代码链路补充，不能按日志实证确认。")
    if not has_typesetting_success:
        gaps.append("当前结果没有实证命中排版服务成功日志。")
    if not has_pdf_to_image:
        gaps.append("当前结果没有实证命中 PDF 转图片成功日志。")
    if not has_layout_completed:
        gaps.append("当前结果没有实证命中 workinfo_layout_completed 消息。")
    if not has_ocr_failure:
        gaps.append("当前结果没有实证命中 OCR 失败终态，无法直接下失败阶段结论。")
    if repeated:
        gaps.append("重复消费的触发源仍未唯一确定，当前只能确认存在再次消费现象。")
    return gaps


def call_chain(has_api_save: bool, has_typesetting_success: bool, has_pdf_to_image: bool, has_layout_completed: bool, has_ocr_failure: bool, evidence_events: list[dict[str, Any]], repeated: list[dict[str, Any]]) -> dict[str, Any]:
    confirmed: list[dict[str, Any]] = []
    inferred: list[dict[str, Any]] = []
    if has_api_save:
        confirmed.append({"Summary": "入口 API 保存作业成功，生成 workGuid。", "Queries": query_refs_for_kinds(evidence_events, ["save-work"])})
    if has_typesetting_success:
        confirmed.append({"Summary": "后台任务服务的排版消费者成功收到排版结果，PDF 已生成。", "Queries": query_refs_for_kinds(evidence_events, ["typesetting-success"])})
    if has_pdf_to_image:
        confirmed.append({"Summary": "TypesettingQueueMsgHandler 使用 PDFium 转图片成功。", "Queries": query_refs_for_kinds(evidence_events, ["pdf-to-image"])})
    if has_layout_completed:
        confirmed.append({"Summary": "HomeworkMsgConsumer 收到 workinfo_layout_completed，进入排版后处理。", "Queries": query_refs_for_kinds(evidence_events, ["layout-completed"])})
    if has_ocr_failure:
        confirmed.append({"Summary": "HomeworkMsgHandler 调用 OcrService2.RecognizeAsync，底层 rpc/WorkImageOcr/layout-parsing 返回 500。", "Queries": query_refs_for_kinds(evidence_events, ["ocr-start", "ocr-retry"])})
        confirmed.append({"Summary": "消息按延迟队列重试 3 次后进入死信队列，并回写作业模板生成最终失败。", "Queries": query_refs_for_kinds(evidence_events, ["ocr-retry", "dead-letter", "final-failure"])})
        inferred.append({"Summary": "页面上的“排版失败”本质是排版完成后的 OCR 后处理失败。", "Queries": []})
    if repeated:
        inferred.append({"Summary": "后续重复消费更像是死信重放、人工重投或补偿任务再次触发；当前 Grafana 证据不足以唯一确定触发源。", "Queries": []})
    return {"Confirmed": confirmed, "Inferred": inferred}


def validation_report(used_queries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "ExecutedChecks": [
            {
                "Node": item["Node"],
                "App": item["App"],
                "From": item["From"],
                "To": item["To"],
                "Query": item["Query"],
                "LocalFilter": item["LocalFilter"],
                "QueryExpr": item["QueryExpr"],
                "DashboardUrl": item["DashboardUrl"],
                "ResultCount": item["ResultCount"],
            }
            for item in used_queries
        ]
    }


def analyze_workguid(workguid: str, namespace: str = "prd", from_value: str = "now-2d", to_value: str = "now", limit_per_query: int = 5000, include_services: bool = False, refresh_dashboard: bool = False) -> dict[str, Any]:
    used_queries: list[dict[str, Any]] = []

    def invoke_step_query(node: str, app: str, query: str = "", from_text: str = from_value, to_text: str = to_value, local_filter: str | None = None, limit: int = limit_per_query) -> dict[str, Any]:
        result = invoke_logs_query(app, query=query, namespace=namespace, from_value=from_text, to_value=to_text, limit=limit, refresh_dashboard=refresh_dashboard)
        filtered_logs = [log for log in result["Logs"] if not local_filter or re.search(local_filter, log["Line"])]
        used_queries.append(
            {
                "Node": node,
                "App": app,
                "Query": query or "<app-only>",
                "LocalFilter": local_filter,
                "From": from_text,
                "To": to_text,
                "Mode": result["Mode"],
                "DashboardUrl": result["DashboardUrl"],
                "QueryExpr": result["QueryExpr"],
                "ResultCount": len(filtered_logs),
            }
        )
        return {
            "Result": result,
            "Logs": filtered_logs,
            "QueryContext": {
                "Node": node,
                "App": app,
                "Query": query or "<app-only>",
                "From": from_text,
                "To": to_text,
                "QueryExpr": result["QueryExpr"],
                "DashboardUrl": result["DashboardUrl"],
            },
        }

    def find_app_window_hits(node_prefix: str, app: str, token: str, start: datetime, window_hours: int = 12, window_count: int = 4, limit: int = limit_per_query) -> dict[str, Any] | None:
        token_pattern = re.escape(token)
        for index in range(window_count):
            window_from = start + timedelta(hours=index * window_hours)
            window_to = window_from + timedelta(hours=window_hours)
            query = invoke_step_query(
                f"{node_prefix}/window-{index + 1}",
                app,
                from_text=to_grafana_time_string(window_from),
                to_text=to_grafana_time_string(window_to),
                local_filter=token_pattern,
                limit=limit,
            )
            if query["Logs"]:
                return query
        return None

    seed_time = workguid_seed_time(workguid)
    background_search_start = datetime(seed_time.year, seed_time.month, seed_time.day, tzinfo=seed_time.tzinfo) if seed_time else datetime.now().astimezone() - timedelta(days=2)
    background_result = find_app_window_hits("backgroundtasks/workGuid", BACKGROUND_APP, workguid, background_search_start)
    background_events = meaningful_events(background_result["Logs"], BACKGROUND_APP, background_result["QueryContext"], workguid) if background_result and background_result["Logs"] else []

    message_id = None
    layout_time = None
    for log in background_result["Logs"] if background_result else []:
        match = re.search(r'"type":"workinfo_layout_completed","id":"([^"]+)"', log["Line"])
        if match:
            message_id = match.group(1)
        match = re.search(r'"type":"workinfo_layout_completed","id":"[^"]+","time":"([^"]+)"', log["Line"])
        if match:
            layout_time = convert_to_time_info(match.group(1))

    primary_cycle_result = None
    primary_cycle_events: list[dict[str, Any]] = []
    message_result = None
    message_events: list[dict[str, Any]] = []
    if layout_time:
        layout_dt = datetime.fromtimestamp(layout_time["TimeMs"] / 1000, timezone.utc).astimezone()
        primary_cycle_result = invoke_step_query(
            "backgroundtasks/primary-cycle-workGuid",
            BACKGROUND_APP,
            from_text=to_grafana_time_string(layout_dt - timedelta(minutes=2)),
            to_text=to_grafana_time_string(layout_dt + timedelta(minutes=8)),
            local_filter=re.escape(workguid),
            limit=2000,
        )
        if primary_cycle_result["Logs"]:
            primary_cycle_events = meaningful_events(primary_cycle_result["Logs"], BACKGROUND_APP, primary_cycle_result["QueryContext"], workguid)
        primary_kinds = {event["Kind"] for event in primary_cycle_events}
        has_primary_chain = {"typesetting-success", "pdf-to-image", "layout-completed"}.issubset(primary_kinds) and bool(
            primary_kinds.intersection({"ocr-retry", "dead-letter", "final-failure"})
        )
        if message_id and not has_primary_chain:
            message_result = invoke_step_query(
                "backgroundtasks/primary-cycle-messageId",
                BACKGROUND_APP,
                from_text=to_grafana_time_string(layout_dt - timedelta(minutes=1)),
                to_text=to_grafana_time_string(layout_dt + timedelta(minutes=10)),
                local_filter=re.escape(message_id),
                limit=2000,
            )
            if message_result["Logs"]:
                message_events = meaningful_events(message_result["Logs"], BACKGROUND_APP, message_result["QueryContext"], workguid)

    api_window_from = to_grafana_time_string(seed_time - timedelta(minutes=30)) if seed_time else from_value
    api_window_to = to_grafana_time_string(seed_time + timedelta(hours=2)) if seed_time else to_value
    api_result = invoke_step_query("api/create-window", API_APP, from_text=api_window_from, to_text=api_window_to, local_filter=re.escape(workguid), limit=2000)
    api_events = meaningful_events(api_result["Logs"], API_APP, api_result["QueryContext"], workguid) if api_result["Logs"] else []

    if include_services or not background_result:
        find_app_window_hits("services/workGuid", SERVICES_APP, workguid, background_search_start)

    all_events = merge_events(api_events + background_events + primary_cycle_events + message_events)
    primary_events = merge_events(api_events + primary_cycle_events + message_events) or merge_events(api_events + background_events)
    timeline = canonical_timeline(primary_events)
    repeated = repeated_attempts(all_events, timeline)
    evidence_events = primary_events or all_events
    kinds = {event["Kind"] for event in evidence_events}
    has_api_save = "save-work" in kinds
    has_typesetting_success = "typesetting-success" in kinds
    has_pdf_to_image = "pdf-to-image" in kinds
    has_layout_completed = "layout-completed" in kinds
    has_ocr_failure = bool(kinds.intersection({"ocr-retry", "dead-letter", "final-failure"}))
    judgement = {
        "Confirmed": [
            item
            for item in [
                "排版服务返回 status=200，PDF 生成成功。" if has_typesetting_success else None,
                "PDF 转图片成功，说明失败点不在排版产物生成。" if has_pdf_to_image else None,
                "排版完成消息已经发出并被 HomeworkMsgConsumer 消费。" if has_layout_completed else None,
                "失败发生在 OCR 后处理阶段，且 rpc/WorkImageOcr/layout-parsing 返回了 500 Internal Server Error。" if has_ocr_failure else None,
                f"同一 messageId 在首次最终失败后仍至少出现 {len(repeated)} 轮重复消费。" if repeated else None,
            ]
            if item
        ],
        "Inferred": [
            item
            for item in [
                "页面上的“排版失败”本质是排版完成后的 OCR 后处理失败。" if has_ocr_failure else None,
                "后续重复消费更像是死信重放、人工重投或补偿任务再次触发；当前 Grafana 证据不足以唯一确定触发源。" if repeated else None,
            ]
            if item
        ],
    }
    return {
        "WorkGuid": workguid,
        "MessageId": message_id,
        "CallChain": call_chain(has_api_save, has_typesetting_success, has_pdf_to_image, has_layout_completed, has_ocr_failure, evidence_events, repeated),
        "Timeline": timeline,
        "RepeatedAttempts": repeated,
        "UsedQueries": used_queries,
        "Validation": validation_report(used_queries),
        "EvidenceGaps": evidence_gaps(has_api_save, has_typesetting_success, has_pdf_to_image, has_layout_completed, has_ocr_failure, repeated),
        "CurrentJudgement": judgement,
    }


def doctor() -> dict[str, Any]:
    return {
        "skillRoot": str(Path(__file__).resolve().parent.parent),
        "stateRoot": str(STATE_DIR),
        "configPath": str(CONFIG.get("_configPath") or ""),
        "python": sys.executable,
        "pythonVersion": sys.version.split()[0],
        "agentBrowser": find_agent_browser() if shutil_which("agent-browser") else "",
        "credentialStore": "keychain" if keychain_available() else "local-state",
        "browserPolicy": str(BROWSER_POLICY_PATH),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="grafana.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.set_defaults(handler=handle_doctor)

    save_login_parser = subparsers.add_parser("save-login")
    save_login_parser.add_argument("-Username", "--username", required=True)
    save_login_parser.add_argument("-Password", "--password", required=True)
    save_login_parser.set_defaults(handler=handle_save_login)

    ensure_parser = subparsers.add_parser("ensure-session")
    ensure_parser.add_argument("-Headed", "--headed", action="store_true")
    ensure_parser.set_defaults(handler=handle_ensure_session)

    browser_parser = subparsers.add_parser("browser")
    browser_parser.add_argument("-Headed", "--headed", action="store_true")
    browser_parser.add_argument("browser_args", nargs=argparse.REMAINDER)
    browser_parser.set_defaults(handler=handle_browser)

    query_parser = subparsers.add_parser("query-logs")
    query_parser.add_argument("-App", "--app", required=True)
    query_parser.add_argument("-Query", "--query", default="")
    query_parser.add_argument("-Namespace", "--namespace", default=str(CONFIG.get("defaultNamespace") or "default"))
    query_parser.add_argument("-From", "--from-value", default="now-2d")
    query_parser.add_argument("-To", "--to-value", default="now")
    query_parser.add_argument("-Limit", "--limit", type=int, default=200)
    query_parser.add_argument("-RefreshDashboard", "--refresh-dashboard", action="store_true")
    query_parser.set_defaults(handler=handle_query_logs)

    analyze_parser = subparsers.add_parser("analyze-workguid")
    analyze_parser.add_argument("-WorkGuid", "--workguid", required=True)
    analyze_parser.add_argument("-Namespace", "--namespace", default=str(CONFIG.get("defaultNamespace") or "default"))
    analyze_parser.add_argument("-From", "--from-value", default="now-2d")
    analyze_parser.add_argument("-To", "--to-value", default="now")
    analyze_parser.add_argument("-LimitPerQuery", "--limit-per-query", type=int, default=5000)
    analyze_parser.add_argument("-IncludeServices", "--include-services", action="store_true")
    analyze_parser.add_argument("-RefreshDashboard", "--refresh-dashboard", action="store_true")
    analyze_parser.set_defaults(handler=handle_analyze_workguid)

    return parser


def handle_doctor(args: argparse.Namespace) -> int:
    print(json.dumps(doctor(), ensure_ascii=False, indent=2))
    return 0


def handle_save_login(args: argparse.Namespace) -> int:
    result = save_login(args.username, args.password)
    print(f"Saved Grafana credential to: {result['credentialPath']}")
    print(f"Credential key file: {result['credentialKeyPath']}")
    print(f"Browser key file: {result['browserKeyPath']}")
    return 0


def handle_ensure_session(args: argparse.Namespace) -> int:
    print(ensure_session(headed=args.headed))
    return 0


def handle_browser(args: argparse.Namespace) -> int:
    browser_args = list(args.browser_args)
    if browser_args and browser_args[0] == "--":
        browser_args = browser_args[1:]
    print(run_agent_browser(browser_args, headed=args.headed))
    return 0


def handle_query_logs(args: argparse.Namespace) -> int:
    result = invoke_logs_query(
        args.app,
        query=args.query,
        namespace=args.namespace,
        from_value=args.from_value,
        to_value=args.to_value,
        limit=args.limit,
        refresh_dashboard=args.refresh_dashboard,
    )
    output = {
        "Mode": result["Mode"],
        "DashboardTitle": result["DashboardTitle"],
        "DashboardUrl": result["DashboardUrl"],
        "PanelId": result["PanelId"],
        "PanelTitle": result["PanelTitle"],
        "DatasourceUid": result["DatasourceUid"],
        "DatasourceType": result["DatasourceType"],
        "QueryExpr": result["QueryExpr"],
        "ApiUri": result["ApiUri"],
        "ResultCount": result["ResultCount"],
        "Logs": result["Logs"],
        "RawTextLength": len(result["RawText"]) if result["RawText"] else 0,
        "RawTextPreview": result["RawText"][:4000] if result["RawText"] else None,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def handle_analyze_workguid(args: argparse.Namespace) -> int:
    result = analyze_workguid(
        args.workguid,
        namespace=args.namespace,
        from_value=args.from_value,
        to_value=args.to_value,
        limit_per_query=args.limit_per_query,
        include_services=args.include_services,
        refresh_dashboard=args.refresh_dashboard,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
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
