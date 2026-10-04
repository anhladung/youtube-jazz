"""Shared validation and atomic JSON helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temporary.replace(path)


def require_file(path: Path, label: str) -> Path:
    if not path.is_file() or path.stat().st_size <= 0:
        raise ValidationError(f"Missing or empty {label}: {path}")
    return path


def resolve_executable(value: str) -> str:
    candidate = Path(value)
    if candidate.is_file():
        return str(candidate.resolve())
    resolved = shutil.which(value)
    if not resolved:
        raise ValidationError(
            f"Required executable was not found: {value}. Install FFmpeg and "
            "ensure ffmpeg and ffprobe are available in PATH, or configure tools.*."
        )
    return resolved
