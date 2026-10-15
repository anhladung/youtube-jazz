"""Build and validate episode packages; uploading is a separate command."""

from __future__ import annotations

import argparse
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.common.channels import (
    ChannelProfile,
    assert_channel,
    assert_playlist_registry,
    resolve_channel,
)
from pipeline.common.config import expand_path, load_config
from pipeline.common.validator import atomic_write_json, load_json, require_file
from pipeline.music.audio_builder import build_audio_master
from pipeline.music.playlist_builder import load_locked_playlist
from pipeline.video.video_builder import prepare_thumbnail, render_video, validate_video


TERMINAL_STATUSES = {"ready_for_upload", "uploaded", "needs_attention", "library_gap"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def video_filename(title: str, video_id: str) -> str:
    """Build a readable, Windows-safe MP4 filename from YouTube metadata."""
    normalized = unicodedata.normalize("NFKD", title)
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")
    slug = slug[:120].rstrip("-") or "untitled-video"
    safe_video_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", video_id).strip("-")
    return f"{slug}-{safe_video_id}.mp4"


def write_youtube_manual_text(path: Path, metadata: dict[str, Any]) -> None:
    """Write only the title and description for quick manual upload."""
    title = str(metadata.get("title") or "").strip()
    description = str(metadata.get("description") or "").strip()
    if not title or not description:
        raise ValueError("youtube.json must contain a title and description")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(f"{title}\n\n{description}\n", encoding="utf-8")
    temporary.replace(path)


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


def manifest_has_actionable_jobs(manifest_path: Path) -> bool:
    """Return True when a batch contains at least one job the renderer can run."""
    manifest = load_json(manifest_path)
    batch_dir = manifest_path.parent
    for item in manifest.get("jobs", []):
        try:
            job_path = resolve_job_file(batch_dir, batch_dir, str(item["path"]))
            status = str(load_json(job_path).get("status", item.get("status", "unknown")))
        except (KeyError, FileNotFoundError, ValueError):
            status = str(item.get("status", "unknown"))
        if status not in TERMINAL_STATUSES:
            return True
    return False


def latest_actionable_manifest(input_root: Path) -> Path | None:
    """Select the newest batch that still has work, for one-click IDE runs."""
    manifests = sorted(input_root.glob("*/batch_manifest.json"), reverse=True)
    return next((path for path in manifests if manifest_has_actionable_jobs(path)), None)


def process_job(manifest_path: Path, item: dict[str, Any], profile: ChannelProfile) -> None:
    config = profile.config
    batch_dir = manifest_path.parent
    job_path = resolve_job_file(batch_dir, batch_dir, str(item["path"]))
    job_dir = job_path.parent
    job = load_json(job_path)
    assert_channel(job, profile, job_path)
    video_id = str(job.get("video_id") or item.get("video_id"))
    status = str(job.get("status", "unknown"))
    if status in TERMINAL_STATUSES:
        if status in {"ready_for_upload", "uploaded"}:
            files = job.get("files", {})
            metadata_path = require_file(
                resolve_job_file(job_dir, batch_dir, files["youtube_metadata"]),
                "YouTube metadata",
            )
            out_root = profile.batches_output_dir / str(job.get("batch_id", batch_dir.name)) / video_id
            if any(out_root.glob("*.mp4")):
                write_youtube_manual_text(out_root / "youtube_manual.txt", load_json(metadata_path))
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
    assert_playlist_registry(playlist, profile, playlist_path)
    metadata = load_json(metadata_path)
    out_root = profile.batches_output_dir / str(job.get("batch_id", batch_dir.name)) / video_id
    audio_path = out_root / "audio_master.wav"
    thumbnail_path = out_root / "thumbnail.jpg"
    video_path = out_root / video_filename(str(metadata.get("title") or ""), video_id)
    report_path = out_root / "validation.json"
    youtube_manual_path = out_root / "youtube_manual.txt"
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
            render_video(thumbnail_path, audio_path, video_path, config=config.get("video", {}), ffmpeg_value=tools.get("ffmpeg", "ffmpeg"), ffprobe_value=tools.get("ffprobe", "ffprobe"))
        set_status(job_path, "validating")
        report = validate_video(video_path, config=config.get("video", {}), ffmpeg_value=tools.get("ffmpeg", "ffmpeg"), ffprobe_value=tools.get("ffprobe", "ffprobe"))
        atomic_write_json(report_path, report)
        write_youtube_manual_text(youtube_manual_path, metadata)
        set_status(job_path, "ready_for_upload", outputs={"audio": str(audio_path), "thumbnail": str(thumbnail_path), "video": str(video_path), "validation": str(report_path), "youtube_manual_text": str(youtube_manual_path)})
        update_manifest(manifest_path, video_id, "ready_for_upload")
        print(f"[{video_id}] ready for upload: {video_path}")
    except Exception as exc:
        current = load_json(job_path).get("status", "")
        failed = "failed_audio" if current == "building_audio" else "failed_validation" if current == "validating" else "failed_render"
        set_status(job_path, failed, last_error=str(exc))
        update_manifest(manifest_path, video_id, failed)
        print(f"[{video_id}] {failed}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and validate ready episode jobs")
    parser.add_argument("--batch", type=Path, help="Specific batch_manifest.json; default scans input/batches")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--channel", default=None, help="vintage-jazz or relax-music")
    args = parser.parse_args()
    config = load_config(args.config)
    profile = resolve_channel(config, args.channel)
    print(f"Channel: {profile.label} [{profile.channel_id}]")
    if args.batch:
        manifests = [args.batch.resolve()]
    else:
        latest = latest_actionable_manifest(profile.batches_input_dir)
        manifests = [latest] if latest else []
    if not manifests:
        print(f"No actionable episode batches found under: {profile.batches_input_dir}")
        return
    for manifest_path in manifests:
        manifest = load_json(manifest_path)
        assert_channel(manifest, profile, manifest_path)
        print(f"Processing batch {manifest.get('batch_id', manifest_path.parent.name)} ({len(manifest.get('jobs', []))} jobs)")
        for item in manifest.get("jobs", []):
            process_job(manifest_path, item, profile)


if __name__ == "__main__":
    main()
