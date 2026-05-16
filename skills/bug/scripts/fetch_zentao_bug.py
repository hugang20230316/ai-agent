#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取禅道 BUG 详情。

优先使用旧版 JSON 认证链路：
1. 读取 /bug-view-{id}.json
2. 若返回登录跳转，则调用 /api-getsessionid.json
3. 使用 /user-login.json 完成登录
4. 重新拉取目标 BUG 的 JSON 数据
"""

from __future__ import annotations

import argparse
import html
import json
import re
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import HTTPSHandler, HTTPCookieProcessor, Request, build_opener

from local_config import load_skill_config, resolve_secret


DEFAULT_BASE_URL = "https://zentao.example.com/zentao"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取禅道 BUG 详情")
    parser.add_argument("bug_ref", help="BUG 编号或 bug-view 链接")
    parser.add_argument("--base-url", default="", help="禅道基础地址；默认读取 bug.local.json 的 zentaoBaseUrl")
    parser.add_argument("--username", default="", help="禅道账号")
    parser.add_argument("--password", default="", help="禅道密码")
    parser.add_argument("--raw", action="store_true", help="输出完整 payload")
    parser.add_argument("--out", default="", help="将结果写入文件")
    return parser.parse_args()


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def extract_bug_id(bug_ref: str) -> str:
    match = re.search(r"bug-view-(\d+)", bug_ref)
    if match:
        return match.group(1)
    match = re.fullmatch(r"\d+", bug_ref.strip())
    if match:
        return match.group(0)
    raise SystemExit(f"无法解析 BUG 编号: {bug_ref}")


def build_opener_with_cookies():
    ssl_context = ssl.create_default_context()
    opener = build_opener(HTTPCookieProcessor(), HTTPSHandler(context=ssl_context))
    return opener, ssl_context


def request_json(opener, ssl_context: ssl.SSLContext, url: str) -> Any:
    req = Request(
        url,
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with opener.open(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def unwrap_payload(payload: Any) -> Any:
    current = payload
    while isinstance(current, dict) and "data" in current and isinstance(current["data"], str):
        data_text = current["data"]
        try:
            current = json.loads(data_text)
        except json.JSONDecodeError:
            break
    return current


def login_if_needed(opener, ssl_context: ssl.SSLContext, base_url: str, username: str, password: str, bug_id: str) -> Any:
    bug_payload = request_json(opener, ssl_context, f"{base_url}/bug-view-{bug_id}.json")
    bug_data = unwrap_payload(bug_payload)

    if not isinstance(bug_data, dict) or "locate" not in bug_data:
        return bug_data

    if not username or not password:
        raise SystemExit("BUG 详情需要登录，但未提供 --username / --password")

    session_payload = request_json(opener, ssl_context, f"{base_url}/api-getsessionid.json")
    session_data = unwrap_payload(session_payload)
    if not isinstance(session_data, dict):
        raise SystemExit(f"无法解析 session 信息: {session_payload}")

    session_name = session_data.get("sessionName")
    session_id = session_data.get("sessionID")
    if not session_name or not session_id:
        raise SystemExit(f"session 数据不完整: {session_data}")

    query = urlencode(
        {
            "account": username,
            "password": password,
            session_name: session_id,
        }
    )
    login_payload = request_json(opener, ssl_context, f"{base_url}/user-login.json?{query}")
    if not isinstance(login_payload, dict) or login_payload.get("status") != "success":
        raise SystemExit(f"登录失败: {login_payload}")

    final_payload = request_json(opener, ssl_context, f"{base_url}/bug-view-{bug_id}.json?{session_name}={session_id}")
    final_data = unwrap_payload(final_payload)
    if isinstance(final_data, dict) and "locate" in final_data:
        raise SystemExit(f"登录后仍未拿到 BUG 数据: {final_data}")
    return final_data


def clean_html(raw_html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_attachments(steps_html: str, base_url: str) -> list[str]:
    result = []
    origin_match = re.match(r"^https?://[^/]+", base_url)
    origin = origin_match.group(0) if origin_match else base_url
    for src in re.findall(r'src="([^"]+)"', steps_html):
        if src.startswith("http://") or src.startswith("https://"):
            result.append(src)
            continue
        if src.startswith("/"):
            result.append(f"{origin}{src}")
    return result


def normalize_actions(actions: Any) -> list[dict[str, Any]]:
    if not isinstance(actions, dict):
        return []
    rows = list(actions.values())
    rows.sort(key=lambda item: (item.get("date", ""), item.get("id", "")))
    return [
        {
            "id": item.get("id"),
            "actor": item.get("actor"),
            "action": item.get("action"),
            "date": item.get("date"),
            "comment": clean_html(item.get("comment", "")) if item.get("comment") else "",
        }
        for item in rows
    ]


def build_summary(payload: dict[str, Any], bug_id: str, base_url: str) -> dict[str, Any]:
    bug = payload.get("bug") if isinstance(payload, dict) else {}
    if not isinstance(bug, dict):
        raise SystemExit(f"BUG 数据格式异常: {payload}")

    steps_html = bug.get("steps") or ""
    module_path = payload.get("modulePath") or []
    return {
        "bug_id": bug_id,
        "url": f"{base_url}/bug-view-{bug_id}.html",
        "title": bug.get("title", ""),
        "product": payload.get("product", {}).get("name", "") if isinstance(payload.get("product"), dict) else "",
        "module_path": [item.get("name", "") for item in module_path if isinstance(item, dict)],
        "execution": bug.get("executionName", ""),
        "opened_build": bug.get("openedBuild", ""),
        "resolved_build": bug.get("resolvedBuild", ""),
        "status": bug.get("status", ""),
        "resolution": bug.get("resolution", ""),
        "severity": bug.get("severity", ""),
        "priority": bug.get("pri", ""),
        "type": bug.get("type", ""),
        "opened_by": bug.get("openedBy", ""),
        "opened_date": bug.get("openedDate", ""),
        "assigned_to": bug.get("assignedTo", ""),
        "resolved_by": bug.get("resolvedBy", ""),
        "resolved_date": bug.get("resolvedDate", ""),
        "last_edited_by": bug.get("lastEditedBy", ""),
        "last_edited_date": bug.get("lastEditedDate", ""),
        "steps_text": clean_html(steps_html),
        "attachments": extract_attachments(steps_html, normalize_base_url(base_url)),
        "actions": normalize_actions(payload.get("actions")),
    }


def main() -> None:
    args = parse_args()
    config = load_skill_config("bug")
    base_url = normalize_base_url(args.base_url or str(config.get("zentaoBaseUrl") or DEFAULT_BASE_URL))
    username = args.username or resolve_secret(config.get("usernameSource")) or str(config.get("username") or "")
    password = args.password or resolve_secret(config.get("passwordSource")) or str(config.get("password") or "")
    bug_id = extract_bug_id(args.bug_ref)

    opener, ssl_context = build_opener_with_cookies()
    payload = login_if_needed(opener, ssl_context, base_url, username, password, bug_id)
    result = payload if args.raw else build_summary(payload, bug_id, base_url)

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
