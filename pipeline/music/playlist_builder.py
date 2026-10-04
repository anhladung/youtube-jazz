"""Validation for playlists already selected and locked by the orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline.common.config import PROJECT_ROOT
from pipeline.common.validator import ValidationError, load_json, require_file


def load_locked_playlist(path: Path) -> tuple[dict[str, Any], list[Path]]:
    payload = load_json(path)
    tracks = payload.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        raise ValidationError(f"Playlist contains no tracks: {path}")

    ordered = sorted(tracks, key=lambda item: int(item.get("position", 0)))
    positions = [int(item.get("position", 0)) for item in ordered]
    if positions != list(range(1, len(ordered) + 1)):
        raise ValidationError(f"Playlist positions must be contiguous from 1: {path}")

    files: list[Path] = []
    for item in ordered:
        value = item.get("file")
        if not isinstance(value, str) or not value:
            raise ValidationError(f"Playlist track has no file path: {item}")
        candidate = Path(value)
        resolved = candidate if candidate.is_absolute() else PROJECT_ROOT / candidate
        files.append(require_file(resolved.resolve(), "playlist track"))
    return payload, files
