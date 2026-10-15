"""Build and supervise the FFmpeg process used by the 24/7 livestream."""

from __future__ import annotations

import json
import os
import random
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline.common.config import PROJECT_ROOT, expand_path
from pipeline.common.logger import get_logger


LOGGER = get_logger("livestream")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True)
class LivestreamSettings:
    ffmpeg: str
    registry_path: Path
    visual_paths: tuple[Path, ...]
    playlist_path: Path
    visual_duration_seconds: int
    width: int
    height: int
    fps: int
    video_bitrate: str
    min_bitrate: str
    max_bitrate: str
    buffer_size: str
    audio_bitrate: str
    stream_url: str
    stream_key_file: Path
    prompt_for_stream_key: bool
    restart_delay_seconds: int
    max_restart_delay_seconds: int


def _thumbnail_pool(root: Path) -> tuple[Path, ...]:
    candidates = [
        path
        for path in root.glob("**/thumbnail.*")
        if path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No livestream visual configured and no thumbnail was found under {root}."
        )
    return tuple(sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True))


def settings_from_config(config: dict[str, Any], visual_override: Path | None = None) -> LivestreamSettings:
    live = config.get("livestream", {})
    tools = config.get("tools", {})
    configured_visual = live.get("visual_path")
    if visual_override:
        visuals = (visual_override.resolve(),)
    elif configured_visual:
        visuals = (expand_path(configured_visual),)
    else:
        visuals = _thumbnail_pool(expand_path(live.get("thumbnails_dir", "input/batches")))
    return LivestreamSettings(
        ffmpeg=str(tools.get("ffmpeg", "ffmpeg")),
        registry_path=expand_path(live.get("registry", "library/music/registry.json")),
        visual_paths=visuals,
        playlist_path=expand_path(live.get("runtime_playlist", "temp/livestream_playlist.txt")),
        visual_duration_seconds=int(live.get("visual_duration_minutes", 30)) * 60,
        width=int(live.get("width", 1920)),
        height=int(live.get("height", 1080)),
        fps=int(live.get("fps", 30)),
        video_bitrate=str(live.get("video_bitrate", "8M")),
        min_bitrate=str(live.get("min_bitrate", live.get("video_bitrate", "8M"))),
        max_bitrate=str(live.get("max_bitrate", "10M")),
        buffer_size=str(live.get("buffer_size", "16M")),
        audio_bitrate=str(live.get("audio_bitrate", "128k")),
        stream_url=str(live.get("stream_url", "rtmps://a.rtmps.youtube.com/live2")),
        stream_key_file=expand_path(live.get("stream_key_file", "secrets/youtube_stream_key.txt")),
        prompt_for_stream_key=bool(live.get("prompt_for_stream_key", True)),
        restart_delay_seconds=int(live.get("restart_delay_seconds", 5)),
        max_restart_delay_seconds=int(live.get("max_restart_delay_seconds", 60)),
    )


def load_available_tracks(registry_path: Path) -> list[Path]:
    with registry_path.open("r", encoding="utf-8") as handle:
        registry = json.load(handle)
    tracks: list[Path] = []
    raw_tracks = registry.get("tracks", [])
    items = raw_tracks.values() if isinstance(raw_tracks, dict) else raw_tracks
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("status") != "available" or not item.get("file"):
            continue
        path = expand_path(item["file"])
        if path.is_file():
            tracks.append(path)
    if not tracks:
        raise RuntimeError(f"No available audio files were found in {registry_path}")
    return tracks


def write_shuffled_playlist(tracks: list[Path], destination: Path, seed: int | None = None) -> None:
    shuffled = tracks.copy()
    random.Random(seed).shuffle(shuffled)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for track in shuffled:
            # FFmpeg concat uses single quotes; escape an embedded quote defensively.
            escaped = track.as_posix().replace("'", "'\\''")
            handle.write(f"file '{escaped}'\n")


def build_ffmpeg_command(
    settings: LivestreamSettings,
    destination: str,
    duration_seconds: int | None = None,
    visual_path: Path | None = None,
) -> list[str]:
    keyframe_interval = settings.fps * 2
    visual_filter = (
        f"scale={settings.width}:{settings.height}:"
        "force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={settings.width}:{settings.height},"
        f"fps={settings.fps},format=yuv420p"
    )
    command = [
        settings.ffmpeg,
        "-hide_banner",
        "-loglevel", "info",
        "-re",
        "-stream_loop", "-1",
        "-f", "concat",
        "-safe", "0",
        "-i", str(settings.playlist_path),
        "-loop", "1",
        "-framerate", str(settings.fps),
        "-i", str(visual_path or settings.visual_paths[0]),
        "-map", "1:v:0",
        "-map", "0:a:0",
        "-vf", visual_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "stillimage",
        "-profile:v", "high",
        "-b:v", settings.video_bitrate,
        "-minrate", settings.min_bitrate,
        "-maxrate", settings.max_bitrate,
        "-bufsize", settings.buffer_size,
        "-g", str(keyframe_interval),
        "-keyint_min", str(keyframe_interval),
        "-sc_threshold", "0",
        "-c:a", "aac",
        "-b:a", settings.audio_bitrate,
        "-ar", "48000",
        "-ac", "2",
        "-af", "aresample=async=1:first_pts=0",
    ]
    if not destination.startswith("rtmp"):
        command.append("-y")
    if duration_seconds is not None:
        command.extend(["-t", str(duration_seconds)])
    command.extend(["-f", "flv" if destination.startswith("rtmp") else "mp4", destination])
    return command


def masked_command(command: list[str]) -> str:
    safe = command.copy()
    if safe:
        final = safe[-1]
        if final.startswith("rtmp") and "/" in final:
            safe[-1] = final.rsplit("/", 1)[0] + "/***"
    return subprocess.list2cmdline(safe)


def _prompt_stream_key() -> str:
    """Ask for a stream key in a masked desktop dialog."""
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()
        value = simpledialog.askstring(
            "YouTube Livestream",
            "Paste the NEW YouTube Stream Key:",
            show="*",
            parent=root,
        )
        root.destroy()
        return (value or "").strip()
    except Exception as exc:
        raise RuntimeError(
            "Could not open the Stream Key dialog. Set YOUTUBE_STREAM_KEY in the Run Configuration."
        ) from exc


def stream_destination(settings: LivestreamSettings) -> str:
    if settings.prompt_for_stream_key:
        stream_key = _prompt_stream_key()
    else:
        stream_key = os.environ.get("YOUTUBE_STREAM_KEY", "").strip()
        if not stream_key and settings.stream_key_file.is_file():
            stream_key = settings.stream_key_file.read_text(encoding="utf-8").strip()
    if not stream_key:
        raise RuntimeError("No YouTube Stream Key was provided; livestream cancelled.")
    return f"{settings.stream_url.rstrip('/')}/{stream_key}"


def run_supervisor(settings: LivestreamSettings) -> None:
    destination = stream_destination(settings)
    tracks = load_available_tracks(settings.registry_path)
    stop_requested = False
    process: subprocess.Popen[str] | None = None

    def stop_handler(_signum: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True
        if process and process.poll() is None:
            process.terminate()

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)
    delay = settings.restart_delay_seconds
    visual_queue: list[Path] = []
    while not stop_requested:
        if not visual_queue:
            visual_queue = list(settings.visual_paths)
            random.shuffle(visual_queue)
        visual = visual_queue.pop()
        write_shuffled_playlist(tracks, settings.playlist_path)
        command = build_ffmpeg_command(
            settings,
            destination,
            settings.visual_duration_seconds if len(settings.visual_paths) > 1 else None,
            visual,
        )
        LOGGER.info(
            "Starting FFmpeg with %d tracks; visual %s for %d minutes",
            len(tracks),
            visual,
            settings.visual_duration_seconds // 60,
        )
        LOGGER.info("Command: %s", masked_command(command))
        started_at = time.monotonic()
        process = subprocess.Popen(command, text=True)
        return_code = process.wait()
        if stop_requested:
            break
        if return_code == 0:
            LOGGER.info("Visual interval completed; switching to the next image.")
            delay = settings.restart_delay_seconds
            continue
        runtime = time.monotonic() - started_at
        if runtime >= 300:
            delay = settings.restart_delay_seconds
        LOGGER.warning("FFmpeg stopped with code %s; restarting in %s seconds", return_code, delay)
        time.sleep(delay)
        delay = min(delay * 2, settings.max_restart_delay_seconds)
    LOGGER.info("Livestream stopped.")

