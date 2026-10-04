"""Build, validate, and optionally upload every ready episode package."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.common.config import PROJECT_ROOT, expand_path, load_config
from pipeline.common.validator import atomic_write_json, load_json, require_file
from pipeline.music.audio_builder import build_audio_master
from pipeline.music.library_manager import mark_tracks_used
from pipeline.music.playlist_builder import load_locked_playlist
from pipeline.video.video_builder import prepare_thumbnail, render_video, validate_video
from pipeline.youtube.uploader import upload_video


INPUT_ROOT = PROJECT_ROOT / "input" / "batches"
TERMINAL_STATUSES = {"uploaded", "needs_attention", "library_gap"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_job_file(job_dir: Path, batch_dir: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    local = (job_dir / candidate).resolve()
    return local if local.exists() else (batch_dir / candidate).resolve()


def set_status(job_path: Path, status: str, **extra: Any) -> dict[str, Any]:
    job = load_json(job_path)
    job["status"] = status
    job["updated_at"] = now_iso()
    job.update(extra)
    atomic_write_json(job_path, job)
    return job


def update_manifest(manifest_path: Path, video_id: str, status: str) -> None:
    manifest = load_json(manifest_path)
    for item in manifest.get("jobs", []):
        if item.get("video_id") == video_id:
            item["status"] = status
    counts: dict[str, int] = {}
    for item in manifest.get("jobs", []):
        key = str(item.get("status", "unknown"))
        counts[key] = counts.get(key, 0) + 1
    manifest["summary"] = counts
    manifest["updated_at"] = now_iso()
    atomic_write_json(manifest_path, manifest)


def append_history(name: str, entry: dict[str, Any]) -> None:
    path = PROJECT_ROOT / "data" / name
    payload = load_json(path) if path.is_file() else {"entries": []}
    entries = payload.setdefault("entries", [])
    identity = (entry.get("video_id"), entry.get("event"))
    if not any((item.get("video_id"), item.get("event")) == identity for item in entries):
        entries.append(entry)
        atomic_write_json(path, payload)


def record_completion(job: dict[str, Any], playlist: dict[str, Any], result: dict[str, Any]) -> None:
    video_id = str(job["video_id"])
    stamp = now_iso()
    append_history("video_history.json", {"video_id": video_id, "event": "uploaded", "timestamp": stamp, **result})
    append_history("playlist_history.json", {"video_id": video_id, "event": "uploaded", "timestamp": stamp,
                                                "track_ids": [item.get("track_id") for item in playlist.get("tracks", [])]})
    append_history("concept_history.json", {"video_id": video_id, "event": "uploaded", "timestamp": stamp,
                                               "episode_profile": job.get("episode_profile", {})})


def process_job(manifest_path: Path, item: dict[str, Any], config: dict[str, Any], *, upload: bool) -> None:
    batch_dir = manifest_path.parent
    job_path = resolve_job_file(batch_dir, batch_dir, str(item["path"]))
    job_dir = job_path.parent
    job = load_json(job_path)
    video_id = str(job.get("video_id") or item.get("video_id"))
    status = str(job.get("status", "unknown"))
    if status in TERMINAL_STATUSES:
        print(f"[{video_id}] skipped ({status})")
        return
    check = job.get("consistency_check", {})
    if check.get("status") != "passed":
        set_status(job_path, "needs_attention", last_error="consistency_check is not passed")
        update_manifest(manifest_path, video_id, "needs_attention")
        print(f"[{video_id}] needs attention: consistency check did not pass")
        return

    files = job.get("files", {})
    playlist_path = require_file(resolve_job_file(job_dir, batch_dir, files["playlist"]), "playlist")
    thumbnail_source = require_file(resolve_job_file(job_dir, batch_dir, files["thumbnail_image"]), "thumbnail")
    metadata_path = require_file(resolve_job_file(job_dir, batch_dir, files["youtube_metadata"]), "YouTube metadata")
    playlist, tracks = load_locked_playlist(playlist_path)
    metadata = load_json(metadata_path)
    out_root = expand_path(config.get("output", {}).get("batches_dir", "output/batches")) / str(job.get("batch_id", batch_dir.name)) / video_id
    audio_path, thumbnail_path, video_path = out_root / "audio_master.wav", out_root / "thumbnail.jpg", out_root / "video.mp4"
    report_path, upload_path = out_root / "validation.json", out_root / "upload.json"
    tools = config.get("tools", {})

    # Failed FFmpeg runs can leave a non-empty but truncated file. Never treat
    # that artifact as resumable merely because it exists.
    if status == "failed_audio":
        audio_path.unlink(missing_ok=True)
    if status in {"failed_render", "failed_validation"}:
        video_path.unlink(missing_ok=True)

    try:
        if not audio_path.is_file() or audio_path.stat().st_size == 0:
            set_status(job_path, "building_audio")
            print(f"[{video_id}] building 48 kHz stereo audio master from {len(tracks)} tracks")
            build_audio_master(tracks, audio_path, config=config.get("audio", {}), ffmpeg_value=tools.get("ffmpeg", "ffmpeg"))
        set_status(job_path, "audio_ready")
        if not thumbnail_path.is_file() or thumbnail_path.stat().st_size == 0:
            prepare_thumbnail(thumbnail_source, thumbnail_path, config=config.get("thumbnail", {}), ffmpeg_value=tools.get("ffmpeg", "ffmpeg"))
        if not video_path.is_file() or video_path.stat().st_size == 0:
            set_status(job_path, "rendering_video")
            print(f"[{video_id}] rendering YouTube-ready MP4")
            render_video(thumbnail_path, audio_path, video_path, config=config.get("video", {}), ffmpeg_value=tools.get("ffmpeg", "ffmpeg"))
        set_status(job_path, "validating")
        report = validate_video(video_path, config=config.get("video", {}), ffmpeg_value=tools.get("ffmpeg", "ffmpeg"), ffprobe_value=tools.get("ffprobe", "ffprobe"))
        atomic_write_json(report_path, report)
        set_status(job_path, "ready_for_upload", outputs={"audio": str(audio_path), "thumbnail": str(thumbnail_path), "video": str(video_path), "validation": str(report_path)})
        update_manifest(manifest_path, video_id, "ready_for_upload")
        if not upload:
            print(f"[{video_id}] ready for upload: {video_path}")
            return
        set_status(job_path, "uploading")
        youtube_config = dict(config.get("youtube", {}))
        youtube_config["client_secrets_file"] = str(expand_path(youtube_config["client_secrets_file"]))
        youtube_config["token_file"] = str(expand_path(youtube_config["token_file"]))
        result = upload_video(video_path, thumbnail_path, metadata, config=youtube_config)
        atomic_write_json(upload_path, result)
        set_status(job_path, "uploaded", upload=result)
        update_manifest(manifest_path, video_id, "uploaded")
        track_ids = [str(track["track_id"]) for track in playlist.get("tracks", []) if track.get("track_id")]
        mark_tracks_used(track_ids, video_id)
        record_completion(job, playlist, result)
        print(f"[{video_id}] uploaded: {result['url']}")
    except Exception as exc:
        current = load_json(job_path).get("status", "")
        failed = "failed_audio" if current == "building_audio" else "failed_upload" if current == "uploading" else "failed_validation" if current == "validating" else "failed_render"
        set_status(job_path, failed, last_error=str(exc))
        update_manifest(manifest_path, video_id, failed)
        print(f"[{video_id}] {failed}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build all ready episode jobs into finished YouTube videos")
    parser.add_argument("--batch", type=Path, help="Specific batch_manifest.json; default scans input/batches")
    parser.add_argument("--upload", action="store_true", help="Upload after a successful render and validation")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    manifests = [args.batch.resolve()] if args.batch else sorted(INPUT_ROOT.glob("*/batch_manifest.json"))
    if not manifests:
        print(f"No episode batches found under: {INPUT_ROOT}")
        return
    upload = bool(args.upload or config.get("youtube", {}).get("upload_enabled", False))
    for manifest_path in manifests:
        manifest = load_json(manifest_path)
        print(f"Processing batch {manifest.get('batch_id', manifest_path.parent.name)} ({len(manifest.get('jobs', []))} jobs)")
        for item in manifest.get("jobs", []):
            process_job(manifest_path, item, config, upload=upload)


if __name__ == "__main__":
    main()
