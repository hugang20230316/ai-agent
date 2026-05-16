import json
import os
from pathlib import Path
from typing import Any


def merge_config(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key == "_configPath":
            continue

        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_config(result[key], value)
            continue

        result[key] = value
    return result


def load_skill_config(skill_name: str) -> dict[str, Any]:
    candidates: list[Path] = []
    home = Path.home()
    candidates.append(home / ".codex" / "local" / f"{skill_name}.local.json")

    current = Path.cwd().resolve()
    for parent in reversed([current, *current.parents]):
        candidates.append(parent / ".codex" / "local" / f"{skill_name}.local.json")

    config_dir = os.environ.get("CODEX_SKILL_CONFIG_DIR")
    if config_dir:
        candidates.append(Path(config_dir) / f"{skill_name}.local.json")

    result: dict[str, Any] = {}
    config_paths: list[str] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
            if isinstance(value, dict):
                result = merge_config(result, value)
                config_paths.append(str(candidate))

    if config_paths:
        result["_configPath"] = config_paths[-1]
        result["_configPaths"] = config_paths
    return result


def resolve_secret(source: str | None) -> str:
    if not source:
        return ""

    if source.startswith("env:"):
        return os.environ.get(source[4:], "")

    return source
