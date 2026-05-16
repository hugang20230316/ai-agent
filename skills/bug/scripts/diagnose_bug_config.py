#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输出 bug skill 本机配置的安全诊断结果。"""

from __future__ import annotations

from local_config import load_skill_config, resolve_secret


def main() -> None:
    config = load_skill_config("bug")
    projects = config.get("projects")
    if not isinstance(projects, dict):
        projects = {}

    print(f"config_paths_count={len(config.get('_configPaths') or [])}")
    print(f"has_zentao_base_url={bool(config.get('zentaoBaseUrl'))}")
    print(f"has_username={bool(config.get('username') or resolve_secret(config.get('usernameSource')))}")
    print(f"has_password={bool(config.get('password') or resolve_secret(config.get('passwordSource')))}")
    print(f"project_count={len(projects)}")
    print(f"has_teacher_ai_project={any(key.lower().replace('_', '-') == 'teacher-ai' for key in projects)}")


if __name__ == "__main__":
    main()
