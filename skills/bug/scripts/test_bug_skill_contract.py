#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归检查 bug skill 的触发、登录配置和输出契约。"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_DIR / "SKILL.md"
EVENT_SOURCING_REFERENCE = SKILL_DIR / "references" / "event-sourcing-investigation.md"
FETCH_SCRIPT = SKILL_DIR / "scripts" / "fetch_zentao_bug.py"
DIAGNOSE_SCRIPT = SKILL_DIR / "scripts" / "diagnose_bug_config.py"
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from local_config import find_project_config, group_project_fields, load_skill_config, resolve_config_secret  # noqa: E402


REQUIRED_PHRASES = {
    "trigger_contract": "## Trigger Contract",
    "intent_gate": "## Intent Gate",
    "evidence_workflow": "## Evidence Workflow",
    "fix_workflow": "## Fix Workflow",
    "evidence_and_output_gate": "## Evidence and Output Gate",
    "skill_regression_gate": "## Skill Regression Gate",
    "login_gate": "## Login and Config Gate",
    "single_authoritative_config": "single authoritative `bug.local.json`",
    "no_project_local_scan": "Do not scan project `.codex/local/` directories",
    "no_inline_credentials_first": "with no inline credentials",
    "diagnose_config": "python3 scripts/diagnose_bug_config.py",
    "no_login_blocker_after_success": "If fetch succeeds, do not ask the user to configure ZenTao login",
    "complete_reproduction_request": "complete request object required to reproduce the same result",
    "missing_context_blocker": "required context or identifiers are missing",
    "output_self_check": "revise the answer if the required default sentence or requested sections are missing.",
    "qa_summary": "`给测试的总结`",
    "reason_tester_readable": "tester/product-readable conclusion",
    "reason_not_reproduced_recovered_blocked": "not reproduced, already recovered, or evidence is blocked",
    "reason_hypotheses_under_evidence": "evidence-section hypotheses",
    "solution_first": "Lead with `解决方案`, then `给测试的总结`, then `原因` whenever there is a fix status",
    "compression_keeps_sections": "Compression means each required section keeps only facts",
    "no_forced_details": "instead of forcing unrelated endpoints, fields, or code locations",
    "async_event_workflow": "## 异步事件溯源排查",
    "async_trigger_synonyms": "异步任务、作业、消息、回调、轮询",
    "async_reverse_boundary": "同步请求、纯界面展示、认证或网络故障",
    "event_reference_link": "references/event-sourcing-investigation.md",
    "fast_online_investigation": "## Fast Online Investigation",
    "online_environment_synonyms": "online, production, prod, live, or 正式",
    "business_object_time_window": "business object and the smallest production time window",
    "business_invariant_first": "Check business invariants before analyzing downstream amplification",
    "downstream_not_root_cause": "Do not label a downstream symptom as the upstream root cause",
    "proven_invariant_downstream_impact": "treat downstream filtering or omission as impact, not the root cause",
    "production_sql_one_statement": "exactly one directly executable, variable-free, read-only SQL statement per turn",
    "production_sql_no_usage": "do not add a usage explanation",
    "missing_sql_scope_blocker": "If the safe business identifier or time window is missing, report the exact blocker and do not issue broad SQL",
    "non_relational_source": "For logs or non-relational evidence, use the configured source instead of forcing SQL",
    "agent_runs_read_only": "Run every other authorized read-only command yourself",
    "stage_result_one_sentence": "one sentence that states the current hit or blocker",
    "online_final_one_sentence": "one sentence containing the proven main cause or exact blocker",
    "online_output_required_parts": "known downstream impact, any remaining evidence gap, and the repair or unblocking direction",
    "no_default_artifacts": "Do not proactively create report files, reproduction scripts, or long process narratives",
    "detailed_report_opt_in": "When the user explicitly asks for a detailed report",
    "detailed_report_default_structure": "Use the six sections below unless the user specifies another structure",
    "qa_no_fabricated_verification": "only verification that actually ran and any uncovered checks",
    "facts_inference_blocker_split": "Separate verified facts, code inference, and blocked evidence",
    "live_url_test": "--live-url <known-readable-bug-url>",
    "solution_executable_action": "smallest executable action first",
    "solution_no_vague_recommendation": "Do not mix alternatives into one vague recommendation",
    "solution_forward_historical_split": "code fix, data repair, read-side fallback, and verification",
    "reason_symptom_trigger_root_cause": "visible symptom, the direct trigger, and the proven root cause",
    "current_contract_precedence": "base the conclusion on the current interface contract and measured data",
    "stale_reference_decision": "stale persisted references",
    "tracker_first_evidence_gate": "first evidence gate before code search",
    "tracker_always_fetch_when_present": "whenever a tracker ID or URL is present",
    "tracker_not_optional": "Do not skip tracker evidence or treat it as optional",
    "single_sql_statement": "exactly one directly executable, variable-free, read-only SQL statement per turn",
    "no_variables_temp_tables": "Do not use variables, temporary tables, multiple result sets, bundled scripts, INSERT, UPDATE, DELETE, MERGE, DDL, write functions, or sensitive fields",
    "grey_only_grafana": "For grey environments, Grafana is the only data evidence source",
    "grey_no_tidb_mongodb": "Do not use TiDB or MongoDB MCP for grey data",
    "test_uses_tidb_mongodb": "When TiDB or MongoDB MCP carries the relevant logs or data evidence",
    "test_no_grafana_escalation": "Do not escalate test-environment evidence to Grafana, grey, or online sources",
    "production_user_sql": "When production relational-database evidence can only be queried by the user",
    "write_paths_first": "scan same-class write paths first",
    "read_only_not_auto_scope": "read-only display or list paths as risks to mention, not automatic edit scope",
    "milestone_updates": "send short milestone updates",
    "rotate_pasted_secret": "remind the user to revoke or rotate it",
    "corrected_business_terminology": "Use the user's corrected and evidence-confirmed business terminology",
    "business_meaning_translation": "translate raw implementation signals into business meaning",
    "vague_placeholders": "Do not use vague placeholders when the relationship is unclear",
    "decision_chain": "review adjacent branches, helper names, and comments in the same chain",
    "normal_follow_up": "For normal follow-up questions during the same investigation",
    "continue_fix_after_verification_gap": "verification exposes another fixable failure in the same authorized bug workflow",
    "rerun_verification_after_fix": "continue fixing and rerun verification",
    "ask_only_new_authorization": "Stop to ask only when the next action needs new authorization",
    "flat_project_config": "Project entries in `bug.local.json` stay flat",
    "read_only_project_groups": "read-only project field groups",
    "no_resources_workflows": "Do not add `resources` or `workflows`",
}


REQUIRED_HEADINGS = [
    "`解决方案`",
    "`给测试的总结`",
    "`原因`",
    "`接口与输入输出`",
    "`证据`",
    "`归属与影响`",
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

    output_contract = text[text.index("Lead with `解决方案`"):]
    positions = [output_contract.index(heading) for heading in REQUIRED_HEADINGS]
    if positions != sorted(positions):
        fail(f"required output headings are out of order: {', '.join(REQUIRED_HEADINGS)}")

    fast_online = text.index("## Fast Online Investigation")
    fix_workflow = text.index("## Fix Workflow")
    if fast_online > fix_workflow:
        fail("fast online investigation must precede fix workflow")

    output_gate = text[text.index("## Evidence and Output Gate"):text.index("## Shared Guardrails")]
    if output_gate.index("default final answer is one sentence") > output_gate.index("When the user explicitly asks for a detailed report"):
        fail("online one-sentence default must precede detailed-report opt-in")
    for legacy in [
        "When the user's current request includes a ZenTao URL",
        "one self-contained SQL script per request",
        "If the user says production can run only one query",
        "`接口`",
        "`输入参数`",
        "`输出结果`",
    ]:
        if legacy in output_gate or legacy in text[:fast_online]:
            fail(f"legacy default contract detected: {legacy}")
    for scope_phrase in ["For test environments", "For grey environments"]:
        if scope_phrase not in text:
            fail(f"non-production scope guard missing: {scope_phrase}")
    if output_gate.count("`接口与输入输出`") != 1:
        fail("detailed report must have one merged interface/input/output section")
    if len([heading for heading in REQUIRED_HEADINGS if heading in output_gate]) != len(REQUIRED_HEADINGS):
        fail("detailed report section count is incomplete")

    for forbidden in [
        "## Shared Output",
        "## Final Output Contract",
    ]:
        if forbidden in text:
            fail(f"legacy or conflicting section heading detected: {forbidden}")

    print("PASS: skill text contract")


def check_event_sourcing_reference() -> None:
    if not EVENT_SOURCING_REFERENCE.exists():
        fail("缺少异步事件溯源排查参考文件")

    text = EVENT_SOURCING_REFERENCE.read_text(encoding="utf-8")
    required = [
        "事件生产",
        "消息是否投递",
        "消费者处理",
        "回调或后续事件",
        "持久化写入",
        "事件发生时间",
        "处理时间",
        "观测时间",
        "当前快照",
        "业务 ID、任务 ID、消息 ID、Trace ID、回调 ID",
        "服务或日期分片 0 命中",
        "部署版本、镜像标签或提交",
        "已证实",
        "未验证",
        "需补证据",
        "example.test",
    ]
    for phrase in required:
        if phrase not in text:
            fail(f"异步事件溯源参考文件缺少必要内容：{phrase}")

    forbidden_patterns = [
        (r"(?i)\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", "真实唯一标识"),
        (r"\b(?:10|172|192)\.(?:\d+\.){2}\d+\b", "私有 IPv4 地址"),
        (r"(?i)\b(?:localhost|[^\s/]+\.(?:internal|corp|local))\b", "内网主机名"),
        (r"(?i)(?:\b(?:[0-9a-f]{1,4}:){2,}[0-9a-f:]*\b)", "IPv6 地址"),
        (r"(?:/Users/|/private/|/tmp/|/home/)[^\s`]+", "绝对路径"),
        (r"(?i)\b(?:token|password|cookie|secret)\s*[:=]", "凭据赋值"),
    ]
    for pattern, label in forbidden_patterns:
        if re.search(pattern, text):
            fail(f"异步事件溯源参考文件包含禁止的敏感残留：{label}")

    print("通过：异步事件溯源参考文件契约")


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
    if len(config_paths) != 1:
        fail(f"bug.local.json should load from exactly one path, got {len(config_paths)}")
    if not config.get("zentaoBaseUrl"):
        fail("zentaoBaseUrl is missing")
    if not resolve_config_secret(config, "username", "usernameSource"):
        fail("username is missing")
    if not resolve_config_secret(config, "password", "passwordSource"):
        fail("password is missing")

    projects = config.get("projects")
    if not isinstance(projects, dict) or not projects:
        fail("project service config is missing")

    print(f"PASS: local config loaded paths={len(config_paths)} projects={len(projects)}")


def check_credential_config_contract() -> None:
    old_username_env = os.environ.get("BUG_SKILL_TEST_USERNAME")
    old_password_env = os.environ.get("BUG_SKILL_TEST_PASSWORD")
    try:
        os.environ["BUG_SKILL_TEST_USERNAME"] = "new-user"
        os.environ["BUG_SKILL_TEST_PASSWORD"] = "new-password"
        new_style_config = {
            "username": "env:BUG_SKILL_TEST_USERNAME",
            "password": "env:BUG_SKILL_TEST_PASSWORD",
        }
        legacy_config = {
            "usernameSource": "legacy-user",
            "passwordSource": "legacy-password",
        }

        if resolve_config_secret(new_style_config, "username", "usernameSource") != "new-user":
            fail("new-style username config was not resolved")
        if resolve_config_secret(new_style_config, "password", "passwordSource") != "new-password":
            fail("new-style password config was not resolved")
        if resolve_config_secret(legacy_config, "username", "usernameSource") != "legacy-user":
            fail("legacy usernameSource config was not resolved")
        if resolve_config_secret(legacy_config, "password", "passwordSource") != "legacy-password":
            fail("legacy passwordSource config was not resolved")
    finally:
        if old_username_env is None:
            os.environ.pop("BUG_SKILL_TEST_USERNAME", None)
        else:
            os.environ["BUG_SKILL_TEST_USERNAME"] = old_username_env
        if old_password_env is None:
            os.environ.pop("BUG_SKILL_TEST_PASSWORD", None)
        else:
            os.environ["BUG_SKILL_TEST_PASSWORD"] = old_password_env

    print("PASS: credential config contract")


def check_project_group_contract() -> None:
    fake_config = {
        "projects": {
            "demo": {
                "aliases": ["demo-web", "演示项目"],
                "repoPath": "/example/repo",
                "webBaseUrl": "https://web.example.test",
                "apiBaseUrl": "https://api.example.test",
                "serviceBaseUrl": "https://service.example.test",
                "swaggerUrl": "https://api.example.test/swagger",
                "apiPolicy": "local note",
                "testEnvironmentWriteAccess": True,
                "unknownField": "ignored",
            }
        }
    }

    matched = find_project_config(fake_config, "demo-web")
    if not matched or matched[0] != "demo":
        fail("project alias was not matched")

    grouped = group_project_fields(matched[1])
    expected_groups = {"repo", "web", "api_base", "swagger", "policy_note", "test_write", "relation"}
    missing_groups = expected_groups - set(grouped)
    if missing_groups:
        fail(f"project field groups missing: {sorted(missing_groups)}")
    if "unknownField" in json.dumps(grouped, ensure_ascii=False):
        fail("unknown project field leaked into grouped output")

    print("PASS: project field group contract")


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
    check_event_sourcing_reference()
    check_credential_config_contract()
    check_project_group_contract()
    check_local_config()
    check_live_fetch(args.live_bug, args.live_url)


if __name__ == "__main__":
    main()
