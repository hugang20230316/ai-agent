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


def logs_target(dashboard: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
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
    panel, target = logs_target(dashboard)
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
