"""Maintain a CSV queue and upload scheduled YouTube videos through Studio."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pipeline.common.config import PROJECT_ROOT, expand_path, load_config
from pipeline.common.validator import atomic_write_json, load_json, require_file
from pipeline.music.library_manager import mark_tracks_used
from pipeline.music.playlist_builder import load_locked_playlist
from pipeline.youtube.uploader import upload_video


INPUT_ROOT = PROJECT_ROOT / "input" / "batches"
FIELDS = [
    "queue_id", "batch_id", "video_id", "job_path", "video_path",
    "thumbnail_path", "metadata_path", "playlist_path", "title",
    "schedule_date", "schedule_time", "timezone", "status", "retry",
    "error", "youtube_url", "uploaded_at",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_job_file(job_dir: Path, batch_dir: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    local = (job_dir / candidate).resolve()
    return local if local.exists() else (batch_dir / candidate).resolve()


def load_queue(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def save_queue(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def schedule_slots(config: dict[str, Any]) -> tuple[Any, str, list[str], int]:
    timezone_name = str(config.get("schedule_timezone", "Asia/Saigon"))
    if timezone_name in {"Asia/Saigon", "Asia/Ho_Chi_Minh"}:
        schedule_timezone = timezone(timedelta(hours=7), name=timezone_name)
    else:
        schedule_timezone = ZoneInfo(timezone_name)
    slots = [str(value) for value in config.get("daily_schedule_times", ["08:00", "20:00"])]
    if len(slots) != 2:
        raise ValueError("youtube.daily_schedule_times must contain exactly two times")
    for value in slots:
        datetime.strptime(value, "%H:%M")
    return (
        schedule_timezone,
        timezone_name,
        sorted(slots),
        int(config.get("minimum_schedule_lead_minutes", 120)),
    )


def next_schedule(
    rows: list[dict[str, str]], config: dict[str, Any]
) -> tuple[str, str, str]:
    schedule_timezone, timezone_name, slots, lead_minutes = schedule_slots(config)
    threshold = datetime.now(schedule_timezone) + timedelta(minutes=lead_minutes)
    occupied = {
        (row.get("schedule_date", ""), row.get("schedule_time", ""))
        for row in rows
        if row.get("status") not in {"cancelled", "skipped"}
    }
    day = threshold.date()
    for offset in range(3660):
        candidate_day = day + timedelta(days=offset)
        for slot in slots:
            hour, minute = map(int, slot.split(":"))
            candidate = datetime(
                candidate_day.year, candidate_day.month, candidate_day.day,
                hour, minute, tzinfo=schedule_timezone,
            )
            key = (candidate_day.isoformat(), slot)
            if candidate >= threshold and key not in occupied:
                return key[0], key[1], timezone_name
    raise RuntimeError("No free YouTube schedule slot found")


def repair_schedule_collisions(
    rows: list[dict[str, str]], config: dict[str, Any]
) -> int:
    """Reassign editable rows with missing, duplicate, or too-soon slots."""
    schedule_timezone, _, _, lead_minutes = schedule_slots(config)
    threshold = datetime.now(schedule_timezone) + timedelta(minutes=lead_minutes)
    accepted: list[dict[str, str]] = []
    occupied: set[tuple[str, str]] = set()
    repaired = 0
    for row in rows:
        key = (row.get("schedule_date", ""), row.get("schedule_time", ""))
        valid = bool(key[0] and key[1]) and key not in occupied
        editable = row.get("status") in {"pending", "error"}
        if valid and editable:
            try:
                scheduled = datetime.strptime(
                    f"{key[0]} {key[1]}", "%Y-%m-%d %H:%M"
                ).replace(tzinfo=schedule_timezone)
                valid = scheduled >= threshold
            except ValueError:
                valid = False
        if not valid and editable:
            date_value, time_value, timezone_name = next_schedule(accepted, config)
            row["schedule_date"] = date_value
            row["schedule_time"] = time_value
            row["timezone"] = timezone_name
            key = (date_value, time_value)
            repaired += 1
        if key[0] and key[1]:
            occupied.add(key)
        accepted.append(row)
    return repaired


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
    append_history("video_history.json", {
        "video_id": video_id, "event": "uploaded", "timestamp": stamp, **result
    })
    append_history("playlist_history.json", {
        "video_id": video_id, "event": "uploaded", "timestamp": stamp,
        "track_ids": [item.get("track_id") for item in playlist.get("tracks", [])],
    })
    append_history("concept_history.json", {
        "video_id": video_id, "event": "uploaded", "timestamp": stamp,
        "episode_profile": job.get("episode_profile", {}),
    })


def sync_queue(
    rows: list[dict[str, str]], manifests: list[Path], config: dict[str, Any]
) -> int:
    existing = {row.get("queue_id"): row for row in rows}
    added = 0
    for manifest_path in manifests:
        manifest = load_json(manifest_path)
        batch_dir = manifest_path.parent
        for item in manifest.get("jobs", []):
            job_path = resolve_job_file(batch_dir, batch_dir, str(item["path"]))
            job = load_json(job_path)
            status = str(job.get("status", "unknown"))
            if status not in {"ready_for_upload", "failed_upload", "uploaded"}:
                continue
            video_id = str(job.get("video_id") or item.get("video_id"))
            batch_id = str(job.get("batch_id") or manifest.get("batch_id"))
            queue_id = f"{batch_id}:{video_id}"
            if queue_id in existing:
                if status == "uploaded":
                    existing[queue_id]["status"] = "done"
                continue
            outputs = job.get("outputs") or {}
            files = job.get("files") or {}
            metadata_path = resolve_job_file(
                job_path.parent, batch_dir, str(files.get("youtube_metadata", ""))
            )
            playlist_path = resolve_job_file(
                job_path.parent, batch_dir, str(files.get("playlist", ""))
            )
            metadata = load_json(metadata_path) if metadata_path.is_file() else {}
            schedule_date, schedule_time, timezone_name = next_schedule(rows, config)
            row = {
                "queue_id": queue_id,
                "batch_id": batch_id,
                "video_id": video_id,
                "job_path": str(job_path),
                "video_path": str(outputs.get("video") or ""),
                "thumbnail_path": str(outputs.get("thumbnail") or ""),
                "metadata_path": str(metadata_path),
                "playlist_path": str(playlist_path),
                "title": str(metadata.get("title") or ""),
                "schedule_date": schedule_date,
                "schedule_time": schedule_time,
                "timezone": timezone_name,
                "status": "done" if status == "uploaded" else "pending",
                "retry": "0",
                "error": "",
                "youtube_url": str((job.get("upload") or {}).get("url") or ""),
                "uploaded_at": "",
            }
            rows.append(row)
            existing[queue_id] = row
            added += 1
    return added


def process_row(row: dict[str, str], config: dict[str, Any]) -> None:
    job_path = Path(row["job_path"])
    job = load_json(job_path)
    video_id = row["video_id"]
    manifest_path = job_path.parents[2] / "batch_manifest.json"
    output_dir = Path(row["video_path"]).parent
    upload_path = output_dir / "upload.json"
    if str(job.get("status")) == "uploaded" or upload_path.is_file():
        row["status"] = "done"
        row["error"] = ""
        if upload_path.is_file():
            result = load_json(upload_path)
            row["youtube_url"] = str(result.get("url") or "")
        print(f"[{video_id}] skipped (already uploaded)")
        return
    if row.get("status") not in {"pending", "error", "processing"}:
        print(f"[{video_id}] skipped ({row.get('status')})")
        return

    metadata = load_json(require_file(Path(row["metadata_path"]), "YouTube metadata"))
    metadata["schedule_date"] = row["schedule_date"]
    metadata["schedule_time"] = row["schedule_time"]
    playlist, _ = load_locked_playlist(Path(row["playlist_path"]))
    video_path = require_file(Path(row["video_path"]), "rendered video")
    thumbnail_path = require_file(Path(row["thumbnail_path"]), "upload thumbnail")
    row["error"] = ""
    set_status(job_path, "uploading")
    update_manifest(manifest_path, video_id, "uploading")
    result = upload_video(
        video_path, thumbnail_path, metadata, config=dict(config.get("youtube", {}))
    )
    atomic_write_json(upload_path, result)
    completed_job = set_status(job_path, "uploaded", upload=result)
    update_manifest(manifest_path, video_id, "uploaded")
    track_ids = [
        str(track["track_id"])
        for track in playlist.get("tracks", []) if track.get("track_id")
    ]
    mark_tracks_used(track_ids, video_id)
    record_completion(completed_job, playlist, result)
    row["status"] = "done"
    row["youtube_url"] = str(result.get("url") or "")
    row["uploaded_at"] = now_iso()
    print(
        f"[{video_id}] scheduled {row['schedule_date']} {row['schedule_time']} "
        f"{row['timezone']}: {row['youtube_url']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Process the existing YouTube CSV queue")
    parser.add_argument("--queue", type=Path, help="Alternative queue CSV path")
    parser.add_argument("--limit", type=int, help="Maximum pending rows to process")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    youtube_config = config.get("youtube", {})
    queue_path = (
        args.queue.resolve()
        if args.queue
        else expand_path(youtube_config.get("queue_file", "data/youtube_upload_queue.csv"))
    )
    rows = load_queue(queue_path)
    print(f"Queue: {queue_path} ({len(rows)} rows)")
    if not rows:
        print("Queue is empty. Run build_youtube_schedule.py first.")
        return
    processed = 0
    for row in rows:
        if args.limit is not None and processed >= args.limit:
            break
        if row.get("status") == "processing":
            row["status"] = "error"
            row["error"] = "Previous upload was interrupted; retrying automatically"
        if row.get("status") not in {"pending", "error"}:
            continue
        row["status"] = "processing"
        row["error"] = ""
        save_queue(queue_path, rows)
        try:
            process_row(row, config)
        except Exception as exc:
            row["status"] = "error"
            row["retry"] = str(int(row.get("retry") or 0) + 1)
            row["error"] = str(exc)
            job_path = Path(row["job_path"])
            job = load_json(job_path)
            manifest_path = job_path.parents[2] / "batch_manifest.json"
            set_status(job_path, "failed_upload", last_error=str(exc))
            update_manifest(manifest_path, row["video_id"], "failed_upload")
            print(f"[{row['video_id']}] upload error: {exc}")
        finally:
            save_queue(queue_path, rows)
        processed += 1


if __name__ == "__main__":
    main()
