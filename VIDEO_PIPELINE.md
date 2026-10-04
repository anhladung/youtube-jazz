# YouTube video pipeline

The project has two separate one-click entry points:

1. `run_pipeline.py` processes pending Flow prompt queues, verifies downloaded WAV files, and registers completed tracks in `library/music/registry.json`.
2. `$dieu-phoi` creates locked episode packages under `input/batches/<batch_id>`.
3. `run_video_pipeline.py` consumes those packages, builds one continuous audio master, renders and validates the MP4, and optionally uploads it.

## Render all ready jobs

In PyCharm, run `run_video_pipeline.py` without parameters. Outputs are written to:

```text
output/batches/<batch_id>/<video_id>/
├── audio_master.wav
├── thumbnail.jpg
├── video.mp4
└── validation.json
```

The video is 1920×1080 progressive H.264 High Profile, 30 fps, yuv420p, BT.709, with AAC stereo at 48 kHz and 384 kbps. The MP4 uses Fast Start. The upload thumbnail is normalized to 3840×2160 and encoded at the highest JPEG quality that stays under 2 MB.

Jobs are resumable. A successful render stops at `ready_for_upload`; a failure records `last_error` in `job.json` and the next run retries the failed stage. Truncated output from a failed FFmpeg run is discarded.

## Upload

1. Put the Google OAuth desktop-app credentials at `secrets/youtube_client_secret.json`.
2. Install Python packages with `pip install -r requirements.txt`.
3. Add `--upload` in PyCharm's **Script parameters**, or set `youtube.upload_enabled: true` in `config.yaml`.

The first upload opens Google authorization. Later runs reuse `secrets/youtube_token.json`. Uploads are private by default and only become `uploaded` after YouTube processing succeeds.

## Required system tool

Install FFmpeg and make both `ffmpeg` and `ffprobe` available in `PATH`, or set their absolute paths under `tools` in `config.yaml`.
