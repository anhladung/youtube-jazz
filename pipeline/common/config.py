"""Configuration loading for the local pipeline."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load YAML configuration and return an empty mapping for an empty file."""
    config_path = path or PROJECT_ROOT / "config.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Configuration root must be a mapping: {config_path}")
    return data


def expand_path(value: str | Path, *, base: Path = PROJECT_ROOT) -> Path:
    """Expand environment variables and resolve relative project paths."""
    expanded = Path(os.path.expandvars(os.path.expanduser(str(value))))
    return expanded.resolve() if expanded.is_absolute() else (base / expanded).resolve()
