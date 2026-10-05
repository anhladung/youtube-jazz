"""Build or extend the YouTube upload schedule without uploading anything."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.common.config import expand_path, load_config
from run_youtube_uploader import (
    INPUT_ROOT,
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
    args = parser.parse_args()
    config = load_config(args.config)
    youtube_config = config.get("youtube", {})
    queue_path = (
        args.queue.resolve()
        if args.queue
        else expand_path(youtube_config.get("queue_file", "data/youtube_upload_queue.csv"))
    )
    manifests = (
        [args.batch.resolve()]
        if args.batch
        else sorted(INPUT_ROOT.glob("*/batch_manifest.json"))
    )
    rows = load_queue(queue_path)
    added = sync_queue(rows, manifests, youtube_config)
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
