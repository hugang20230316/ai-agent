#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输出 bug skill 本机配置的安全诊断结果。"""

from __future__ import annotations

from local_config import (
    PROJECT_FIELD_GROUPS,
    count_projects_with_group,
    get_project_configs,
    load_skill_config,
    resolve_config_secret,
)


def main() -> None:
    config = load_skill_config("bug")
    projects = get_project_configs(config)

    print(f"config_paths_count={len(config.get('_configPaths') or [])}")
    print(f"has_zentao_base_url={bool(config.get('zentaoBaseUrl'))}")
    print(f"has_username={bool(resolve_config_secret(config, 'username', 'usernameSource'))}")
    print(f"has_password={bool(resolve_config_secret(config, 'password', 'passwordSource'))}")
    print(f"project_count={len(projects)}")
    for group_name in PROJECT_FIELD_GROUPS:
        print(f"project_group_{group_name}_count={count_projects_with_group(projects, group_name)}")


if __name__ == "__main__":
    main()
