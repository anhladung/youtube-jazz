# YouTube video pipeline

The project has four separate entry points:

1. `run_pipeline.py` processes pending Flow prompt queues, verifies downloaded WAV files, and registers completed tracks in `library/music/registry.json`.
2. `$dieu-phoi` creates locked episode packages under `input/batches/<batch_id>`.
3. `run_video_pipeline.py` consumes those packages, builds one continuous audio master, renders and validates the MP4. It never uploads.
4. `build_youtube_schedule.py` scans rendered jobs and assigns collision-free CSV schedule slots.
5. `run_youtube_uploader.py` consumes that CSV and uploads pending rows only.

## Render all ready jobs

In PyCharm, run `run_video_pipeline.py` without parameters. Outputs are written to:

```text
output/batches/<batch_id>/<video_id>/
├── audio_master.wav
├── thumbnail.jpg
├── <seo-title>-<video_id>.mp4
└── validation.json
```

The MP4 filename is derived from the title in `youtube.json`, normalized to a
Windows-safe lowercase slug, and suffixed with `video_id` to prevent collisions.

The video is 1920×1080 progressive H.264 High Profile, 30 fps, yuv420p, BT.709, with AAC stereo at 48 kHz and 384 kbps. The MP4 uses Fast Start. The upload thumbnail is normalized to 3840×2160 and encoded at the highest JPEG quality that stays under 2 MB.

Jobs are resumable. A successful render stops at `ready_for_upload`; a failure records `last_error` in `job.json` and the next run retries the failed stage. Truncated output from a failed FFmpeg run is discarded.

## Upload queue and scheduling

1. Install Python packages with `pip install -r requirements.txt`.
2. Confirm `youtube.chrome_path`, `youtube.profile_dir`, and `youtube.channel_url` in `config.yaml`.
3. Run `build_youtube_schedule.py` to add newly rendered jobs to `data/youtube_upload_queue.csv` without opening Chrome. Use `--batch input/batches/<batch_id>/batch_manifest.json` to scan one batch. The builder repairs missing or duplicate slots on editable rows.
4. Review or edit the CSV schedule, then run `run_youtube_uploader.py` to process pending rows. Use `--limit 1` to upload only the next item.

The uploader opens YouTube Studio in a dedicated persistent Chrome profile. On the first run, log in to the intended YouTube account in that Chrome window. Later runs reuse the login stored in `youtube.profile_dir`. Uploads are private by default.

On the Details step, the uploader selects both `Not made for kids` and `Yes, AI was used` before pressing Next. After scheduling completes, it keeps the Chrome window open for 180 seconds before closing the persistent context.

Before uploading, the command checks `job.json`, `upload.json`, and job status. Jobs already marked `uploaded` or carrying a completed upload record are skipped. Interrupted `processing/uploading` attempts are retried automatically on the next run.

The queue assigns two daily slots, `08:00` and `20:00` in `Asia/Saigon`, with at least 24 hours of lead time. This buffer is for HD processing, copyright checks, and monetization review—not an assumed recommendation boost. The twelve-hour-separated slots are a starting experiment for broader international coverage; change `youtube.daily_schedule_times` using channel Analytics as evidence accumulates. Queue rows preserve valid assigned dates and times across runs, while pending/error rows that are too close, missing a slot, or collide are rescheduled automatically.

Queue statuses are `pending`, `processing`, `done`, `error`, `cancelled`, and `skipped`. Failed or interrupted attempts are retried automatically; use `cancelled` to prevent a row from uploading.

## Required system tool

Install FFmpeg and make both `ffmpeg` and `ffprobe` available in `PATH`, or set their absolute paths under `tools` in `config.yaml`.
