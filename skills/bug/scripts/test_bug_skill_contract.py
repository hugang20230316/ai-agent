#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归检查 bug skill 的触发、登录配置和输出契约。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_DIR / "SKILL.md"
FETCH_SCRIPT = SKILL_DIR / "scripts" / "fetch_zentao_bug.py"
DIAGNOSE_SCRIPT = SKILL_DIR / "scripts" / "diagnose_bug_config.py"
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from local_config import load_skill_config, resolve_secret  # noqa: E402


REQUIRED_PHRASES = {
    "trigger_contract": "## Trigger Contract",
    "intent_gate": "## Intent Gate",
    "evidence_workflow": "## Evidence Workflow",
    "fix_workflow": "## Fix Workflow",
    "evidence_and_output_gate": "## Evidence and Output Gate",
    "skill_regression_gate": "## Skill Regression Gate",
    "login_gate": "## Login and Config Gate",
    "no_inline_credentials_first": "with no inline credentials",
    "diagnose_config": "python3 scripts/diagnose_bug_config.py",
    "no_login_blocker_after_success": "If fetch succeeds, do not ask the user to configure ZenTao login",
    "teacher_guid_required": "teacherGuid",
    "task_guid_required": "taskGuid",
    "output_self_check": "If any section is missing after self-check, revise the answer before sending it.",
    "qa_summary": "`给测试的总结`",
    "live_url_test": "--live-url <known-readable-bug-url>",
    "forward_historical_split": "distinguish forward-path fix, historical data repair, and query-side fallback",
    "stale_reference_decision": "stale persisted references",
    "tracker_first_evidence_gate": "first evidence gate before code search",
    "tracker_always_fetch_when_present": "whenever a tracker ID or URL is present",
    "tracker_not_optional": "Do not skip tracker evidence or treat it as optional",
    "single_sql_statement": "exactly one directly executable SQL statement",
    "no_variables_temp_tables": "Do not use variables, temporary tables, multiple result sets, or a bundled script",
    "grey_only_grafana": "For grey environments, Grafana is the only data evidence source",
    "grey_no_tidb_mongodb": "Do not use TiDB or MongoDB MCP for grey data",
    "test_uses_tidb_mongodb": "For test environments, use TiDB and MongoDB MCP tools",
    "production_user_sql": "When production data can only be queried by the user",
    "production_consolidate_script": "consolidate related checks into that script when practical",
    "no_split_scripts": "Do not split into multiple scripts if one script can return the needed evidence",
    "write_paths_first": "scan same-class write paths first",
    "read_only_not_auto_scope": "read-only display or list paths as risks to mention, not automatic edit scope",
    "milestone_updates": "send short milestone updates",
    "rotate_pasted_secret": "remind the user to revoke or rotate it",
    "corrected_business_terminology": "Use the user's corrected business terminology",
    "business_meaning_translation": "translate raw implementation signals into business meaning",
    "vague_placeholders": "Do not use vague placeholders when the relationship is unclear",
    "decision_chain": "review adjacent branches, helper names, and comments in the same chain",
    "normal_follow_up": "For normal follow-up questions during the same investigation",
}


REQUIRED_HEADINGS = [
    "`原因`",
    "`接口`",
    "`输入参数`",
    "`输出结果`",
    "`证据`",
    "`归属与影响`",
    "`修复状态或建议`",
    "`给测试的总结`",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查 bug skill 契约")
    parser.add_argument("--live-bug", default="", help="用可读取的真实 BUG 编号执行抓取回归")
    parser.add_argument("--live-url", default="", help="用可读取的真实 BUG URL 执行抓取回归")
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_skill_text() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    for key, phrase in REQUIRED_PHRASES.items():
        if phrase not in text:
            fail(f"missing phrase {key}: {phrase}")

    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            fail(f"missing required output heading: {heading}")

    for forbidden in [
        "## Shared Output",
        "## Final Output Contract",
    ]:
        if forbidden in text:
            fail(f"legacy or conflicting section heading detected: {forbidden}")

    print("PASS: skill text contract")


def check_local_config() -> None:
    completed = subprocess.run(
        [sys.executable, str(DIAGNOSE_SCRIPT)],
        cwd=str(Path.cwd()),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if completed.returncode != 0:
        fail(f"diagnose config failed: {completed.stderr.strip() or completed.stdout.strip()}")

    diagnose_output = completed.stdout
    if "has_username=True" not in diagnose_output or "has_password=True" not in diagnose_output:
        fail("diagnose config did not confirm local credentials")

    config = load_skill_config("bug")
    config_paths = config.get("_configPaths") or []
    if not config_paths:
        fail("bug.local.json was not loaded")
    if not config.get("zentaoBaseUrl"):
        fail("zentaoBaseUrl is missing")
    if not (config.get("username") or resolve_secret(config.get("usernameSource"))):
        fail("username is missing")
    if not (config.get("password") or resolve_secret(config.get("passwordSource"))):
        fail("password is missing")

    projects = config.get("projects")
    if not isinstance(projects, dict) or not projects:
        fail("project service config is missing")

    print(f"PASS: local config loaded paths={len(config_paths)} projects={len(projects)}")


def run_fetch(bug_ref: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="bug-skill-contract-") as temp_dir:
        output_path = Path(temp_dir) / "bug.json"
        command = [
            sys.executable,
            str(FETCH_SCRIPT),
            bug_ref,
            "--out",
            str(output_path),
        ]
        completed = subprocess.run(
            command,
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
            timeout=40,
            check=False,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            fail(f"fetch failed for {bug_ref}: {stderr or completed.stdout.strip()}")

        if not output_path.exists():
            fail(f"fetch did not write output for {bug_ref}")

        data = json.loads(output_path.read_text(encoding="utf-8"))
        if not data.get("bug_id"):
            fail(f"fetch output missing bug_id for {bug_ref}")
        if not data.get("title"):
            fail(f"fetch output missing title for {bug_ref}")
        if not data.get("steps_text"):
            fail(f"fetch output missing steps_text for {bug_ref}")

        return data


def check_live_fetch(live_bug: str, live_url: str) -> None:
    if live_bug:
        data = run_fetch(live_bug)
        print(f"PASS: live bug id fetch {data['bug_id']} {data['title']}")

    if live_url:
        data = run_fetch(live_url)
        print(f"PASS: live bug url fetch {data['bug_id']} {data['title']}")


def main() -> None:
    args = parse_args()
    check_skill_text()
    check_local_config()
    check_live_fetch(args.live_bug, args.live_url)


if __name__ == "__main__":
    main()
