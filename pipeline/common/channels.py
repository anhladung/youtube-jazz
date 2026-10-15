"""Resolve isolated storage and settings for each music channel."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline.common.config import expand_path


ALIASES = {
    "vintage-jazz": "vintage_jazz",
    "vintage_jazz": "vintage_jazz",
    "jazz": "vintage_jazz",
    "relax-music": "relax_music",
    "relax_music": "relax_music",
    "relax": "relax_music",
}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


@dataclass(frozen=True)
class ChannelProfile:
    channel_id: str
    label: str
    expected_genre: str
    config: dict[str, Any]
    library_builds_dir: Path
    registry_path: Path
    tracks_dir: Path
    batches_input_dir: Path
    batches_output_dir: Path
    data_dir: Path
    youtube_queue_path: Path


def normalize_channel_id(value: str | None) -> str:
    key = (value or "vintage_jazz").strip().casefold()
    return ALIASES.get(key, key.replace("-", "_"))


def resolve_channel(config: dict[str, Any], requested: str | None = None) -> ChannelProfile:
    channel_id = normalize_channel_id(requested or config.get("default_channel"))
    channels = config.get("channels") or {}
    if channel_id not in channels:
        choices = ", ".join(sorted(channels)) or "none configured"
        raise ValueError(f"Unknown channel '{channel_id}'. Configured channels: {choices}")
    raw = channels[channel_id]
    if not isinstance(raw, dict):
        raise ValueError(f"channels.{channel_id} must be a mapping")
    paths = raw.get("paths") or {}
    if not isinstance(paths, dict):
        raise ValueError(f"channels.{channel_id}.paths must be a mapping")
    merged = _merge(config, raw.get("overrides") or {})
    merged["active_channel"] = channel_id
    merged["channel_label"] = str(raw.get("label") or channel_id)

    def path(name: str) -> Path:
        value = paths.get(name)
        if not value:
            raise ValueError(f"Missing channels.{channel_id}.paths.{name}")
        return expand_path(value)

    return ChannelProfile(
        channel_id=channel_id,
        label=merged["channel_label"],
        expected_genre=str(raw.get("expected_genre") or ""),
        config=merged,
        library_builds_dir=path("library_builds"),
        registry_path=path("registry"),
        tracks_dir=path("tracks"),
        batches_input_dir=path("batches_input"),
        batches_output_dir=path("batches_output"),
        data_dir=path("data"),
        youtube_queue_path=path("youtube_queue"),
    )


def assert_channel(payload: dict[str, Any], profile: ChannelProfile, source: Path) -> None:
    """Reject explicitly labelled artifacts belonging to another channel."""
    actual = payload.get("channel_id")
    if not actual:
        try:
            inside_owned_root = source.resolve().is_relative_to(
                profile.batches_input_dir.resolve()
            )
        except (OSError, ValueError):
            inside_owned_root = False
        if not inside_owned_root:
            raise ValueError(
                f"Unlabelled artifact is outside the selected {profile.channel_id} batch root: "
                f"{source}. Add channel_id='{profile.channel_id}' or move it under "
                f"{profile.batches_input_dir}."
            )
    if actual and normalize_channel_id(str(actual)) != profile.channel_id:
        raise ValueError(
            f"Channel mismatch in {source}: expected {profile.channel_id}, found {actual}"
        )


def assert_library_queue(queue_path: Path, profile: ChannelProfile) -> None:
    """Prevent a Flow queue from being generated or ingested into the wrong library."""
    resolved = queue_path.resolve()
    if not resolved.is_relative_to(profile.library_builds_dir.resolve()):
        raise ValueError(
            f"Flow queue for {profile.channel_id} must be under "
            f"{profile.library_builds_dir}: {resolved}"
        )


def assert_playlist_registry(
    playlist: dict[str, Any], profile: ChannelProfile, source: Path
) -> None:
    """Require every locked track ID to exist in the selected channel registry."""
    from pipeline.common.validator import load_json

    registry = load_json(profile.registry_path)
    registered = registry.get("tracks") or {}
    missing = [
        str(item.get("track_id"))
        for item in playlist.get("tracks", [])
        if not item.get("track_id") or item.get("track_id") not in registered
    ]
    if missing:
        preview = ", ".join(missing[:5])
        raise ValueError(
            f"Playlist {source} contains tracks outside the {profile.channel_id} "
            f"registry: {preview}"
        )

