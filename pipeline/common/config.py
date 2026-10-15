"""Configuration loading for the local pipeline."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load YAML configuration, applying config.local.yaml for the default file."""
    config_path = path or PROJECT_ROOT / "config.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Configuration root must be a mapping: {config_path}")
    local_path = PROJECT_ROOT / "config.local.yaml"
    if path is None and local_path.is_file():
        with local_path.open("r", encoding="utf-8") as handle:
            local_data = yaml.safe_load(handle) or {}
        if not isinstance(local_data, dict):
            raise ValueError(f"Configuration root must be a mapping: {local_path}")
        data = _deep_merge(data, local_data)
    return data


def expand_path(value: str | Path, *, base: Path = PROJECT_ROOT) -> Path:
    """Expand environment variables and resolve relative project paths."""
    expanded = Path(os.path.expandvars(os.path.expanduser(str(value))))
    return expanded.resolve() if expanded.is_absolute() else (base / expanded).resolve()
