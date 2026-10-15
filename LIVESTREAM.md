# YouTube Jazz 24/7 livestream

This module streams the registered music library while rotating completely static images. It is independent from the one-hour video pipeline.

## First-time YouTube setup

1. In YouTube Studio, open **Create → Go live → Stream**.
2. Create a reusable stream key, select normal latency, and enable auto-start.
3. Keep the key private. Never paste it into `config.yaml` or commit it to Git.

## Validate and preview

By default, every `thumbnail.png` below `input/batches` is shuffled and displayed
for 30 minutes. Change `livestream.visual_duration_minutes` in `config.yaml` to
adjust the interval. Override the pool with one fixed image by using
`--visual path/to/image.png`.

```powershell
python run_livestream.py --dry-run
python run_livestream.py --preview-seconds 30
```

The preview is written to `output/livestream_preview.mp4` and does not contact YouTube.

## Start the stream

Set the key only for the current PowerShell window, then launch the runner:

```powershell
$env:YOUTUBE_STREAM_KEY = Read-Host "YouTube stream key"
python run_livestream.py
```

Press `Ctrl+C` to stop. If FFmpeg exits unexpectedly, the Python supervisor reshuffles the playlist and reconnects with exponential backoff.

With `livestream.prompt_for_stream_key: true`, PyCharm's Run button opens a
masked desktop dialog. Paste the key and press Enter or click OK. The key is
kept only in memory for that run. Set the option to `false` to use the
`YOUTUBE_STREAM_KEY` environment variable or `secrets/youtube_stream_key.txt`
instead.

For unattended Windows operation, disable sleep while plugged in and use Task Scheduler to launch the script after login or startup. The machine and internet connection must remain available.

