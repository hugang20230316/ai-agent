import json
import os
from pathlib import Path
from typing import Any, Optional


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


def resolve_secret(source: Optional[str]) -> str:
    if not source:
        return ""

    if source.startswith("env:"):
        return os.environ.get(source[4:], "")

    return source
