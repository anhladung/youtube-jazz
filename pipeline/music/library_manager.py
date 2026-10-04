"""Register downloaded Flow WAV files as reusable library tracks."""

from __future__ import annotations

import hashlib
import wave
from pathlib import Path
from typing import Any

from pipeline.common.config import PROJECT_ROOT
from pipeline.common.validator import atomic_write_json, load_json


REGISTRY_PATH = PROJECT_ROOT / "library" / "music" / "registry.json"


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ingest_flow_queue(
    queue_path: Path, registry_path: Path = REGISTRY_PATH
) -> list[str]:
    """Register real completed outputs; returns newly added track IDs."""
    queue = load_json(queue_path)
    prompts = queue.get("prompts") if isinstance(queue, dict) else queue
    if not isinstance(prompts, list):
        raise ValueError(f"Invalid Flow queue: {queue_path}")

    registry = load_json(registry_path) if registry_path.is_file() else {"tracks": {}}
    tracks = registry.setdefault("tracks", {})
    checksum_index = {
        record.get("checksum_sha256"): track_id
        for track_id, record in tracks.items()
        if record.get("checksum_sha256")
    }
    added: list[str] = []

    for prompt in prompts:
        if prompt.get("status") not in {"completed", "completed_partial"}:
            continue
        outputs = prompt.get("outputs") or []
        for output in outputs:
            file_value = output.get("file")
            if not isinstance(file_value, str) or not file_value:
                continue
            candidate = Path(file_value)
            file_path = candidate if candidate.is_absolute() else PROJECT_ROOT / candidate
            if not file_path.is_file() or file_path.suffix.casefold() != ".wav":
                continue
            checksum = sha256_file(file_path)
            if checksum in checksum_index:
                continue
            track_id = f"track_{checksum[:16]}"
            try:
                relative_file = str(file_path.resolve().relative_to(PROJECT_ROOT))
            except ValueError:
                relative_file = str(file_path.resolve())
            record: dict[str, Any] = {
                "track_id": track_id,
                "file": relative_file.replace("\\", "/"),
                "source_prompt_id": prompt.get("prompt_id"),
                "source_visual_reference_id": prompt.get("visual_reference_id"),
                "flow_variant_index": output.get("variant_index"),
                "title": output.get("title"),
                "song_url": output.get("song_url"),
                "format": "wav",
                "duration_seconds": round(wav_duration_seconds(file_path), 3),
                "checksum_sha256": checksum,
                "status": "available",
                "track_metadata": prompt.get("track_metadata", {}),
                "usage_count": 0,
                "used_in": [],
                "last_used": None,
            }
            tracks[track_id] = record
            checksum_index[checksum] = track_id
            added.append(track_id)

    registry["schema_version"] = 1
    atomic_write_json(registry_path, registry)
    return added


def mark_tracks_used(
    track_ids: list[str], video_id: str, registry_path: Path = REGISTRY_PATH
) -> None:
    registry = load_json(registry_path)
    tracks = registry.get("tracks", {})
    for track_id in track_ids:
        record = tracks.get(track_id)
        if not record:
            continue
        used_in = record.setdefault("used_in", [])
        if video_id not in used_in:
            used_in.append(video_id)
            record["usage_count"] = int(record.get("usage_count", 0)) + 1
        record["last_used"] = video_id
    atomic_write_json(registry_path, registry)
