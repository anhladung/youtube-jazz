"""Build or extend the YouTube upload schedule without uploading anything."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.common.channels import resolve_channel
from pipeline.common.config import load_config
from run_youtube_uploader import (
    load_queue,
    repair_schedule_collisions,
    save_queue,
    sync_queue,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add rendered videos to the CSV schedule using unique time slots"
    )
    parser.add_argument("--batch", type=Path, help="Only scan one batch manifest")
    parser.add_argument("--queue", type=Path, help="Alternative queue CSV path")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--channel", default=None, help="vintage-jazz or relax-music")
    args = parser.parse_args()
    config = load_config(args.config)
    profile = resolve_channel(config, args.channel)
    config = profile.config
    youtube_config = config.get("youtube", {})
    queue_path = (
        args.queue.resolve()
        if args.queue
        else profile.youtube_queue_path
    )
    manifests = (
        [args.batch.resolve()]
        if args.batch
        else sorted(profile.batches_input_dir.glob("*/batch_manifest.json"))
    )
    rows = load_queue(queue_path)
    added = sync_queue(rows, manifests, youtube_config, profile)
    print(f"Channel: {profile.label} [{profile.channel_id}]")
    repaired = repair_schedule_collisions(rows, youtube_config)
    save_queue(queue_path, rows)
    pending = sum(row.get("status") == "pending" for row in rows)
    done = sum(row.get("status") == "done" for row in rows)
    print(f"Schedule: {queue_path}")
    print(
        f"Rows: {len(rows)} | added: {added} | rescheduled: {repaired} | "
        f"pending: {pending} | done: {done}"
    )
    for row in rows:
        print(
            f"[{row['video_id']}] {row['schedule_date']} {row['schedule_time']} "
            f"{row['timezone']} | {row['status']} | {row['title']}"
        )


if __name__ == "__main__":
    main()
