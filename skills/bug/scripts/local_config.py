import json
import os
from pathlib import Path
from typing import Any


PROJECT_FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "repo": ("repoPath",),
    "web": ("webBaseUrl",),
    "api_base": (
        "apiBaseUrl",
        "testApiBaseUrl",
        "serviceBaseUrl",
        "apiLayerBaseUrl",
        "rpcBaseUrl",
    ),
    "swagger": (
        "swaggerUrl",
        "swaggerIndexUrl",
        "swaggerJsonUrl",
        "serviceSwaggerUrl",
        "apiSwaggerIndexUrl",
        "apiSwaggerJsonUrl",
        "apiLayerSwaggerUrl",
    ),
    "policy_note": ("apiPolicy", "policyNote", "testNote"),
    "test_write": ("testEnvironmentWriteAccess",),
    "relation": ("relatedProjects", "aliases"),
}


def load_skill_config(skill_name: str) -> dict[str, Any]:
    config_dir = os.environ.get("CODEX_SKILL_CONFIG_DIR")
    if config_dir:
        config_path = Path(config_dir) / f"{skill_name}.local.json"
    else:
        config_path = Path.home() / ".codex" / "local" / f"{skill_name}.local.json"

    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)

    if not isinstance(value, dict):
        return {}

    value["_configPath"] = str(config_path)
    value["_configPaths"] = [str(config_path)]
    return value


def resolve_secret(source: Any) -> str:
    if not source:
        return ""

    if not isinstance(source, str):
        source = str(source)

    if source.startswith("env:"):
        return os.environ.get(source[4:], "")

    return source


def resolve_config_secret(config: dict[str, Any], value_key: str, source_key: str) -> str:
    return resolve_secret(config.get(source_key)) or resolve_secret(config.get(value_key))


def get_project_configs(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    projects = config.get("projects")
    if not isinstance(projects, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}
    for project_name, project_config in projects.items():
        if isinstance(project_name, str) and isinstance(project_config, dict):
            result[project_name] = project_config
    return result


def find_project_config(config: dict[str, Any], project_ref: str) -> tuple[str, dict[str, Any]] | None:
    projects = get_project_configs(config)
    if project_ref in projects:
        return project_ref, projects[project_ref]

    normalized_ref = project_ref.strip().lower()
    for project_name, project_config in projects.items():
        aliases = project_config.get("aliases")
        if not isinstance(aliases, list):
            continue

        for alias in aliases:
            if isinstance(alias, str) and alias.strip().lower() == normalized_ref:
                return project_name, project_config

    return None


def group_project_fields(project_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for group_name, field_names in PROJECT_FIELD_GROUPS.items():
        matched_fields = {
            field_name: project_config[field_name]
            for field_name in field_names
            if field_name in project_config and project_config[field_name] not in ("", None)
        }
        if matched_fields:
            grouped[group_name] = matched_fields
    return grouped


def count_projects_with_group(projects: dict[str, dict[str, Any]], group_name: str) -> int:
    return sum(1 for project_config in projects.values() if group_name in group_project_fields(project_config))
